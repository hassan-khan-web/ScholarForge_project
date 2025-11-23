import os
import urllib.parse
import tempfile
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, render_template, jsonify, send_file, session
from celery.result import AsyncResult

# --- Local Imports ---
from task import generate_report_task, celery_app
import AI_engine 
import chat_engine 
import report_formats

# --- App Configuration ---
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "your-fallback-secret-key-for-development")

# --- ROUTES ---

@app.route('/', methods=['GET'])
def index():
    return render_template('report_generator.html')

@app.route('/start-report', methods=['POST'])
def start_report():
    """
    Starts the background Celery task for report generation.
    Now accepts 'page_count'.
    """
    try:
        data = request.json
        user_query = data.get('query')
        format_key = data.get('format_key')
        format_content = data.get('format_content')
        # Default to 15 if not provided
        page_count = int(data.get('page_count', 15))

        if not user_query:
            return jsonify({'error': 'No query provided'}), 400
        
        if format_key == "custom":
            if not format_content or format_content.strip() == "":
                return jsonify({'error': 'Custom format selected but no content provided.'}), 400
            user_format = format_content
        else:
            user_format = report_formats.FORMAT_TEMPLATES.get(format_key)
            if not user_format:
                return jsonify({'error': f'Invalid format key: {format_key}'}), 400

        # Start the background task, passing page_count
        task = generate_report_task.delay(user_query, user_format, page_count)

        return jsonify({'task_id': task.id}), 202
        
    except Exception as e:
        return jsonify({'error': f'Failed to start task: {str(e)}'}), 500

@app.route('/report-status/<task_id>', methods=['GET'])
def report_status(task_id):
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
    report_content = request.form.get('report_content')
    topic = request.form.get('topic')
    format_type = request.form.get('format')
    return send_converted_file(report_content, topic, format_type)

@app.route('/get-report-formats', methods=['GET'])
def get_report_formats():
    try:
        return jsonify(report_formats.FORMAT_TEMPLATES)
    except Exception as e:
        return jsonify({"error": f"Could not load report formats: {str(e)}"}), 500

def send_converted_file(report_content, topic, format_type):
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

# --- CHAT ROUTES ---
@app.route('/chat', methods=['GET'])
def chat_page():
    return render_template('ai_assistant.html')

@app.route('/chat', methods=['POST'])
def handle_chat():
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

@app.route('/add-hook', methods=['POST'])
def add_hook():
    hook_content = request.json.get('content')
    # Placeholder logic
    return jsonify({'status': 'success', 'message': 'Hook saved!'}), 201

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)