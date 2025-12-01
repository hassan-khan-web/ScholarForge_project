import os
import urllib.parse
import tempfile
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, Request, Form, BackgroundTasks, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel
from celery.result import AsyncResult

# Import modules
from task import generate_report_task, celery_app
import AI_engine 
import chat_engine 
import report_formats
import database 

app = FastAPI(title="ScholarForge")

app.add_middleware(SessionMiddleware, secret_key=os.environ.get("APP_SECRET_KEY", "super-secret-key"))

if not os.path.exists("static"):
    os.makedirs("static")
if not os.path.exists("static/charts"):
    os.makedirs("static/charts")

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

@app.on_event("startup")
def startup():
    database.init_db()

# --- PYDANTIC MODELS ---
class ReportRequest(BaseModel):
    query: str
    format_key: str
    format_content: str = None
    page_count: int = 15

class ChatRequest(BaseModel):
    message: str
    session_id: int 

class CreateFolderRequest(BaseModel):
    name: str

class CreateSessionRequest(BaseModel):
    folder_id: int
    title: str

class HookRequest(BaseModel):
    content: str

# --- ROUTES ---

@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("report_generator.html", {"request": request})

@app.get("/chat")
async def chat_page(request: Request):
    return templates.TemplateResponse('ai_assistant.html', {"request": request})

# --- FOLDER & CHAT API ---

@app.get("/api/folders")
def get_folders():
    """Get the tree structure of Folders -> Sessions"""
    return database.get_folders_with_sessions()

@app.post("/api/folders")
def create_new_folder(data: CreateFolderRequest):
    try:
        folder = database.create_folder(data.name)
        return {"status": "success", "folder": {"id": folder.id, "name": folder.name, "sessions": []}}
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": f"Could not create folder. Name might be duplicate."})

@app.post("/api/sessions")
def create_new_session(data: CreateSessionRequest):
    try:
        session = database.create_chat_session(data.folder_id, data.title)
        return {"status": "success", "session": {"id": session.id, "title": session.title}}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/sessions/{session_id}/messages")
def get_session_history(session_id: int):
    msgs = database.get_session_messages(session_id)
    return [{"role": m.role, "content": m.content} for m in msgs]

@app.post("/chat")
async def handle_chat(data: ChatRequest):
    # Fetch history for context
    db_messages = database.get_session_messages(data.session_id)
    history_context = [{"role": m.role, "content": m.content} for m in db_messages]
    
    # Get AI Response
    ai_response = await chat_engine.get_chat_response_async(data.message, history_context)
    
    # Save to DB
    database.save_chat_message(data.session_id, "user", data.message)
    database.save_chat_message(data.session_id, "assistant", ai_response)
    
    return {'response': ai_response}

# --- REPORT API ---

@app.get("/api/history")
def get_history():
    reports = database.get_all_reports()
    data = []
    for r in reports:
        data.append({
            "id": r.id, 
            "topic": r.topic, 
            "date": r.created_at.strftime("%b %d, %H:%M")
        })
    return data

@app.get("/api/report/{id}")
def get_report(id: int):
    report = database.get_report_content(id)
    if report:
        return {"topic": report.topic, "content": report.content}
    return {"error": "Not found"}

@app.delete("/api/report/{id}")
def delete_report_endpoint(id: int):
    success = database.delete_report(id)
    if success:
        return {"status": "success", "message": "Report deleted"}
    return JSONResponse(status_code=404, content={"error": "Report not found"})

@app.post("/start-report")
async def start_report(data: ReportRequest):
    try:
        if not data.query:
            return JSONResponse({'error': 'No query provided'}, status_code=400)
        
        user_format = data.format_key if data.format_key in report_formats.FORMAT_TEMPLATES else "literature_review"
        if data.format_key == "custom":
            if not data.format_content or data.format_content.strip() == "":
                return JSONResponse({'error': 'Custom format selected but no content provided.'}, status_code=400)
            user_format = "custom" 

        task = generate_report_task.delay(data.query, user_format, data.page_count)
        return {"task_id": task.id}
        
    except Exception as e:
        return JSONResponse({'error': f'Failed to start task: {str(e)}'}, status_code=500)

@app.get("/report-status/{task_id}")
async def report_status(task_id: str):
    task = AsyncResult(task_id, app=celery_app)

    if task.state == 'PENDING':
        return {'status': 'PENDING', 'message': 'Task is in queue...'}
    elif task.state == 'PROGRESS':
        message = task.info.get('message', 'Task is running...')
        return {'status': 'PROGRESS', 'message': message}
    elif task.state == 'SUCCESS':
        result = task.result
        if isinstance(result, dict) and result.get('status') == 'FAILURE':
            return {'status': 'FAILURE', 'error': result.get('error')}
        return {
            'status': 'SUCCESS',
            'report_content': result.get('report_content'),
            'search_content': result.get('search_content'),
            'chart_path': result.get('chart_path')
        }
    elif task.state == 'FAILURE':
        return {'status': 'FAILURE', 'error': str(task.info)}
    else:
        return {'status': task.state}

# --- FILE OPS ---

def cleanup_file(path: str):
    try:
        if os.path.exists(path): os.remove(path)
    except Exception as e: print(f"Error cleaning up file {path}: {e}")

@app.post("/download")
async def download(
    background_tasks: BackgroundTasks, 
    report_content: str = Form(...),
    topic: str = Form(...),
    format: str = Form(...),
    chart_path: str = Form(None)
):
    return send_converted_file(report_content, topic, format, chart_path, background_tasks)

@app.get("/get-report-formats")
async def get_report_formats():
    return report_formats.FORMAT_TEMPLATES

def send_converted_file(report_content, topic, format_type, chart_path, background_tasks):
    if not report_content or not topic:
        raise HTTPException(status_code=400, detail="Missing report data.")

    safe_topic = urllib.parse.quote_plus(topic.replace(' ', '_'))
    
    try:
        with tempfile.NamedTemporaryFile(suffix=f".{format_type}", delete=False) as f:
            temp_filepath = f.name
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating temp file: {e}")

    result = "Error"
    media_type = "text/plain"
    filename = f"{safe_topic}_Report.{format_type}"

    if format_type == 'pdf':
        result = AI_engine.convert_to_pdf(report_content, topic, temp_filepath, chart_path)
        media_type = 'application/pdf'
    elif format_type == 'docx':
        result = AI_engine.convert_to_docx(report_content, topic, temp_filepath, chart_path)
        media_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    elif format_type == 'txt':
        result = AI_engine.convert_to_txt(report_content, temp_filepath)
        media_type = 'text/plain'
    elif format_type == 'json':
        result = AI_engine.convert_to_json(report_content, topic, temp_filepath)
        media_type = 'application/json'
    else:
        if os.path.exists(temp_filepath): os.remove(temp_filepath)
        raise HTTPException(status_code=400, detail="Invalid format.")

    if result.startswith("Success"):
        background_tasks.add_task(cleanup_file, temp_filepath)
        return FileResponse(path=temp_filepath, filename=filename, media_type=media_type)
    else:
        if os.path.exists(temp_filepath): os.remove(temp_filepath)
        raise HTTPException(status_code=500, detail=f"File generation failed: {result}")

@app.post("/add-hook")
async def add_hook(data: HookRequest):
    try:
        database.save_hook(data.content)
        return {'status': 'success', 'message': 'Hook saved!'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)