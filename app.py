import os
import urllib.parse
import tempfile

# --- THIS IS THE FIX ---
# Add these two lines to load the .env file
# for the Flask app.
from dotenv import load_dotenv
load_dotenv()
# --- END OF FIX ---

from flask import Flask, request, render_template, jsonify, send_file, session
from celery.result import AsyncResult

# --- Local Imports ---
from task import generate_report_task, celery_app
import AI_engine 
import chat_engine 
# This is the new file with all your templates
import report_formats

# --- App Configuration ---
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "your-fallback-secret-key-for-development")

# ---
# --- FEATURE 1: REPORT GENERATOR ROUTES
# ---

@app.route('/', methods=['GET'])
def index():
    """
    Serves the main Report Generator page.
    """
    return render_template('report_generator.html')


@app.route('/start-report', methods=['POST'])
def start_report():
    """
    Starts the background Celery task for report generation.
    """
    try:
        data = request.json
        user_query = data.get('query')
        format_key = data.get('format_key')
        format_content = data.get('format_content')

        if not user_query:
            return jsonify({'error': 'No query provided'}), 400
        
        # --- NEW: Get the final format string ---
        # If the user selected "custom", use their content.
        # Otherwise, fetch the template from our dictionary.
        if format_key == "custom":
            if not format_content or format_content.strip() == "":
                return jsonify({'error': 'Custom format selected but no content provided.'}), 400
            user_format = format_content
        else:
            # Get the template from the imported dictionary
            user_format = report_formats.FORMAT_TEMPLATES.get(format_key)
            if not user_format:
                return jsonify({'error': f'Invalid format key: {format_key}'}), 400
        # --- END NEW ---

        # Start the background task, now passing the user_format
        task = generate_report_task.delay(user_query, user_format)

        return jsonify({'task_id': task.id}), 202
        
    except Exception as e:
        return jsonify({'error': f'Failed to start task: {str(e)}'}), 500


@app.route('/report-status/<task_id>', methods=['GET'])
def report_status(task_id):
    """
    Checks the status of the Celery task.
    """
    task = AsyncResult(task_id, app=celery_app)

    if task.state == 'PENDING':
        return jsonify({'status': 'PENDING', 'message': 'Task is in queue...'})
    
    elif task.state == 'PROGRESS':
        message = task.info.get('message', 'Task is running...')
        return jsonify({'status': 'PROGRESS', 'message': message})

    elif task.state == 'SUCCESS':
        result = task.result
        if result['status'] == 'FAILURE':
            return jsonify({'status': 'FAILURE', 'error': result['error']})
        
        return jsonify({
            'status': 'SUCCESS',
            'report_content': result['report_content'],
            'search_content': result['search_content']
        })

    elif task.state == 'FAILURE':
        return jsonify({'status': 'FAILURE', 'error': str(task.info)})
        
    else:
        return jsonify({'status': task.state})


@app.route('/download', methods=['POST'])
def download():
    """
    Handles the file download request.
    """
    report_content = request.form.get('report_content')
    topic = request.form.get('topic')
    format_type = request.form.get('format')

    return send_converted_file(report_content, topic, format_type)

# ---
# --- NEW: Route to provide formats to the frontend
# ---
@app.route('/get-report-formats', methods=['GET'])
def get_report_formats():
    """
    This route sends the dictionary of report formats to the frontend.
    """
    try:
        # This will send the full dictionary
        return jsonify(report_formats.FORMAT_TEMPLATES)
    except Exception as e:
        # This will catch the AttributeError if the file is still empty
        return jsonify({"error": f"Could not load report formats: {str(e)}"}), 500
# --- END NEW ---


def send_converted_file(report_content, topic, format_type):
    """
    Helper function for the download route.
    Uses tempfile for safety.
    """
    if not report_content or not topic:
        return "Missing report data.", 400

    safe_topic = urllib.parse.quote_plus(topic.replace(' ', '_'))
    
    try:
        with tempfile.NamedTemporaryFile(suffix=f".{format_type}", delete=False) as f:
            temp_filepath = f.name
    except Exception as e:
        return f"Error creating temp file: {e}", 500

    if format_type == 'pdf':
        filename = f"{safe_topic}_Report.pdf"
        result = AI_engine.convert_to_pdf(report_content, topic, temp_filepath)
        mimetype = 'application/pdf'
    elif format_type == 'docx':
        filename = f"{safe_topic}_Report.docx"
        result = AI_engine.convert_to_docx(report_content, topic, temp_filepath)
        mimetype = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    elif format_type == 'txt':
        filename = f"{safe_topic}_Report.txt"
        result = AI_engine.convert_to_txt(report_content, temp_filepath)
        mimetype = 'text/plain'
    else:
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)
        return "Invalid download format.", 400

    if result.startswith("Success"):
        try:
            response = send_file(
                temp_filepath,
                as_attachment=True,
                mimetype=mimetype,
                download_name=filename
            )
            response.call_on_close(lambda: os.remove(temp_filepath) if os.path.exists(temp_filepath) else None)
            return response
        except Exception as e:
            if os.path.exists(temp_filepath):
                os.remove(temp_filepath)
            return f"File serving error: {e}", 500
    else:
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)
        return f"File generation failed: {result}", 500


# ---
# --- FEATURE 2: AI ASSISTANT & CHAT ROUTES
# ---

@app.route('/chat', methods=['GET'])
def chat_page():
    """
    Serves the new AI Assistant chat page.
    """
    return render_template('ai_assistant.html')


@app.route('/chat', methods=['POST'])
def handle_chat():
    """
    Handles chat messages sent from the 'ai_assistant.html' page.
    """
    user_message = request.json.get('message')
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400

    chat_history = session.get('chat_history', [])

    try:
        ai_response = chat_engine.get_chat_response(user_message, chat_history)
        
        chat_history.append({'role': 'user', 'content': user_message})
        chat_history.append({'role': 'assistant', 'content': ai_response})
        
        session['chat_history'] = chat_history

        return jsonify({'response': ai_response})
        
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500


# ---
# --- FEATURE 3: "HOOK" & EDITOR ROUTES (Placeholders)
# ---

@app.route('/editor', methods=['GET'])
def editor_page():
    """
    (Placeholder) Serves the "History & Editor" page.
    """
    return "Editor page not yet implemented", 501


@app.route('/add-hook', methods=['POST'])
def add_hook():
    """
    (Placeholder) This is where your "Hook" button will send data.
    """
    hook_content = request.json.get('content')
    print(f"Hook received: {hook_content}") # For debugging
    return jsonify({'status': 'success', 'message': 'Hook saved!'}), 201


@app.route('/get-hooks', methods=['GET'])
def get_hooks():
    """
    (Placeholder) This is what your editor page will call to load hooks.
    """
    fake_hooks = [
        {"id": 1, "content": "This is the first hook snippet."},
        {"id": 2, "content": "Retrieval-Augmented Generation (RAG) is a key technique."},
        {"id": 3, "content": "LLMs can sometimes hallucinate without external data."}
    ]
    return jsonify(fake_hooks)


# --- Main Entry Point ---

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)