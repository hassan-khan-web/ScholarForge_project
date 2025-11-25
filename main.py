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
from task import generate_report_task, celery_app
import AI_engine 
import chat_engine 
import report_formats

app = FastAPI(title="ScholarForge")

# Add Session Middleware (Replaces Flask app.secret_key)
app.add_middleware(SessionMiddleware, secret_key=os.environ.get("FLASK_SECRET_KEY", "secret"))

# Setup Templates
templates = Jinja2Templates(directory="templates")

# --- Pydantic Models (Data Validation) ---
class ReportRequest(BaseModel):
    query: str
    format_key: str
    format_content: str = None
    page_count: int = 15

class ChatRequest(BaseModel):
    message: str

class HookRequest(BaseModel):
    content: str

# --- ROUTES ---

@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("report_generator.html", {"request": request})

@app.post("/start-report")
async def start_report(data: ReportRequest):
    """
    Starts the background Celery task.
    """
    try:
        if not data.query:
            return JSONResponse({'error': 'No query provided'}, status_code=400)
        
        user_format = ""
        if data.format_key == "custom":
            if not data.format_content or data.format_content.strip() == "":
                return JSONResponse({'error': 'Custom format selected but no content provided.'}, status_code=400)
            user_format = data.format_content
        else:
            user_format = report_formats.FORMAT_TEMPLATES.get(data.format_key)
            if not user_format:
                return JSONResponse({'error': f'Invalid format key: {data.format_key}'}, status_code=400)

        # Start Celery Task
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
        if result['status'] == 'FAILURE':
            return {'status': 'FAILURE', 'error': result['error']}
        
        return {
            'status': 'SUCCESS',
            'report_content': result['report_content'],
            'search_content': result['search_content']
        }

    elif task.state == 'FAILURE':
        return {'status': 'FAILURE', 'error': str(task.info)}
        
    else:
        return {'status': task.state}

@app.post("/download")
async def download(
    report_content: str = Form(...),
    topic: str = Form(...),
    format: str = Form(...)
):
    return send_converted_file(report_content, topic, format)

@app.get("/get-report-formats")
async def get_report_formats():
    return report_formats.FORMAT_TEMPLATES

# --- Helper for File Download ---
def send_converted_file(report_content, topic, format_type):
    if not report_content or not topic:
        raise HTTPException(status_code=400, detail="Missing report data.")

    safe_topic = urllib.parse.quote_plus(topic.replace(' ', '_'))
    
    try:
        with tempfile.NamedTemporaryFile(suffix=f".{format_type}", delete=False) as f:
            temp_filepath = f.name
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating temp file: {e}")

    if format_type == 'pdf':
        filename = f"{safe_topic}_Report.pdf"
        result = AI_engine.convert_to_pdf(report_content, topic, temp_filepath)
        media_type = 'application/pdf'
    elif format_type == 'docx':
        filename = f"{safe_topic}_Report.docx"
        result = AI_engine.convert_to_docx(report_content, topic, temp_filepath)
        media_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    elif format_type == 'txt':
        filename = f"{safe_topic}_Report.txt"
        result = AI_engine.convert_to_txt(report_content, temp_filepath)
        media_type = 'text/plain'
    else:
        if os.path.exists(temp_filepath): os.remove(temp_filepath)
        raise HTTPException(status_code=400, detail="Invalid format.")

    if result.startswith("Success"):
        # Background task to clean up file after sending
        return FileResponse(
            path=temp_filepath, 
            filename=filename, 
            media_type=media_type, 
            background=None # File cleanup in FastAPI is tricky with tempfiles, usually OS handles /tmp
        )
    else:
        if os.path.exists(temp_filepath): os.remove(temp_filepath)
        raise HTTPException(status_code=500, detail=f"File generation failed: {result}")

# --- CHAT ROUTES ---

@app.get("/chat")
async def chat_page(request: Request):
    return templates.TemplateResponse('ai_assistant.html', {"request": request})

@app.post("/chat")
async def handle_chat(data: ChatRequest, request: Request):
    # Access session data via request.session
    chat_history = request.session.get('chat_history', [])

    # We use await here because we updated chat_engine to be async
    ai_response = await chat_engine.get_chat_response_async(data.message, chat_history)
    
    chat_history.append({'role': 'user', 'content': data.message})
    chat_history.append({'role': 'assistant', 'content': ai_response})
    
    request.session['chat_history'] = chat_history
    return {'response': ai_response}

@app.post("/add-hook")
async def add_hook(data: HookRequest):
    # Placeholder
    return {'status': 'success', 'message': 'Hook saved!'}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)