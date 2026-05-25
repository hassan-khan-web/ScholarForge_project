import os
from celery import Celery
from . import AI_engine
from . import database

REDIS_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')

celery_app = Celery(
    'scholarforge_tasks',
    broker=REDIS_URL,
    backend=REDIS_URL
)

@celery_app.task(bind=True)
def generate_report_task(self, query: str, format_content: str, page_count: int, file_data_list: list = None, use_council: bool = False, user_id: int = None, model: str = "llama-3.3-70b-versatile"):
    """
    Sequential Deep Research Task with optional User PDF(s).
    """
    try:
        self.update_state(state='PROGRESS', meta={'message': 'Initializing Deep Research...'})
        
        search_content, report_content, chart_path = AI_engine.run_ai_engine_with_return(
            query, 
            format_content, 
            page_count,
            file_data_list,
            task=self,
            use_council=use_council,
            model=model
        )

        self.update_state(state='PROGRESS', meta={'message': 'Archiving Report...'})
        database.save_report(query, report_content, user_id)

        return {
            'status': 'SUCCESS',
            'search_content': search_content,
            'report_content': report_content,
            'chart_path': chart_path
        }
    except Exception as e:
        return {'status': 'FAILURE', 'error': str(e)}