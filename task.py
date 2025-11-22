import os
from dotenv import load_dotenv

# --- THIS IS THE FIX ---
# Add these two lines to load the .env file
# for the Celery worker.
from dotenv import load_dotenv
load_dotenv()
# --- END OF FIX ---

from celery import Celery
import AI_engine  # Import your existing engine

# Configure Celery
# Replace 'redis://localhost:6379/0' if your Redis server is elsewhere
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

celery_app = Celery(
    'task',  # This should match the filename
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND
)

# --- MODIFIED LINE: Added bind=True and user_format ---
@celery_app.task(bind=True)
def generate_report_task(self, query: str, user_format: str) -> dict: # <-- Added 'self' and 'user_format'
    """
    This is the Celery task that runs the full AI pipeline in the background.
    It returns a dictionary with the results or an error.
    """
    try:
        # --- MODIFIED LINE: Passed 'self' AND 'user_format' to the engine ---
        result = AI_engine.run_ai_engine_with_return(query, user_format, task=self)
        
        if isinstance(result, str):
            # Handle error case (e.g., "Failed to run search pipeline...")
            return {'status': 'FAILURE', 'error': result}
        
        # Unpack the successful result
        search_content, report_content = result
        
        return {
            'status': 'SUCCESS',
            'search_content': search_content,
            'report_content': report_content
        }
    except Exception as e:
        # Catch any unexpected errors during the task execution
        self.update_state(state='FAILURE', meta={'message': str(e)})
        return {'status': 'FAILURE', 'error': str(e)}