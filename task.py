import os
from celery import Celery
import AI_engine
import database 

# FIX: Use 'redis' (docker service name), NOT 'localhost'
# Fallback to localhost only if running outside docker for testing
REDIS_URL = os.environ.get('CELERY_BROKER_URL', 'redis://redis:6379/0')

celery_app = Celery(
    'scholarforge_tasks',
    broker=REDIS_URL,
    backend=REDIS_URL
)

@celery_app.task(bind=True)
def generate_report_task(self, query: str, format_content: str, page_count: int):
    try:
        self.update_state(state='PROGRESS', meta={'message': 'Initializing AI Engine...'})
        
        # 1. Run Engine
        search_content, report_content, chart_path = AI_engine.run_ai_engine_with_return(
            query, 
            format_content, 
            page_count,
            task=self
        )

        # 2. Save to DB
        self.update_state(state='PROGRESS', meta={'message': 'Saving to Archive...'})
        database.save_report(query, report_content)

        return {
            'status': 'SUCCESS',
            'search_content': search_content,
            'report_content': report_content,
            'chart_path': chart_path
        }
    except Exception as e:
        return {'status': 'FAILURE', 'error': str(e)}