import os
from dotenv import load_dotenv
load_dotenv()

from celery import Celery
import AI_engine 

# Configure Celery
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

celery_app = Celery(
    'task', 
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND
)

@celery_app.task(bind=True)
def generate_report_task(self, query: str, user_format: str, page_count: int) -> dict:
    """
    Runs the AI pipeline.
    Now accepts 'page_count' and passes it to the engine.
    """
    try:
        # Pass page_count to the engine
        result = AI_engine.run_ai_engine_with_return(query, user_format, page_count, task=self)
        
        if isinstance(result, str):
            return {'status': 'FAILURE', 'error': result}
        
        search_content, report_content = result
        
        return {
            'status': 'SUCCESS',
            'search_content': search_content,
            'report_content': report_content
        }
    except Exception as e:
        self.update_state(state='FAILURE', meta={'message': str(e)})
        return {'status': 'FAILURE', 'error': str(e)}