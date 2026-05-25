# ScholarForge: Celery Task Queue

This chapter explains the background processing system managed by `backend/task.py` and its interaction with the Redis broker.

---

## Why a Task Queue?

Report generation in ScholarForge can take several minutes, especially when Council Mode is enabled. A standard web server expects requests to finish quickly; if a request takes more than a few seconds, the connection may time out.

To avoid this, ScholarForge offloads report generation to **Celery**, a distributed task queue, using **Redis** as a message broker:

```
1. User clicks "Generate"
       │
       ▼
2. FastAPI (main.py)
   │
   ├─► Enqueues task in Redis (returns Task ID immediately)
   │
   └─► Responds to Browser with Task ID (HTTP 200)
       │
       ▼
3. Browser displays loading screen and starts polling
       │
       ├─► GET /report-status/<Task ID> every few seconds
       │
       ▼
4. Celery Worker (task.py)
   │
   ├─► Pulls task from Redis
   ├─► Processes research, agent loop, and compilation
   ├─► Updates task state in Redis (e.g., "Step 3/7: Synthesizing Data...")
   │
   ▼
5. Generation Finished
   │
   ├─► Worker saves report to database and sets state to SUCCESS
   │
   ▼
6. Browser receives SUCCESS status, stops polling, and displays the report
```

---

## Task Configuration and Redis Connection

Celery is initialized in `backend/task.py`:

```python
REDIS_URL = os.environ.get('CELERY_BROKER_URL', 'redis://redis:6379/0')

celery_app = Celery(
    'scholarforge_tasks',
    broker=REDIS_URL,
    backend=REDIS_URL
)
```

* **Broker**: Redis serves as the message broker, storing the queue of pending tasks.
* **Backend**: Redis also serves as the result backend, storing task results and execution metadata (such as error messages or progress logs) so the FastAPI server can query them.

---

## The Report Generation Task

The core background task is defined as:

```python
@celery_app.task(bind=True)
def generate_report_task(self, query: str, format_content: str, page_count: int, file_data_list: list = None, use_council: bool = False):
```

Setting `bind=True` passes the task instance (`self`) as the first argument, allowing it to update its progress state dynamically:

```python
self.update_state(state='PROGRESS', meta={'message': 'Initializing Deep Research...'})
```

The task coordinates the generation process:
1. **Initializes State**: Sets progress status to "Initializing Deep Research...".
2. **Executes AI Engine**: Calls `AI_engine.run_ai_engine_with_return`, passing `task=self`. This allows the engine to update task progress as it completes each of its 7 steps:
   * `"Step 1/7: Processing Inputs..."`
   * `"Step 2/7: Checking Information Needs..."`
   * `"Step 3/7: Synthesizing Data..."`
   * `"Step 4/7: Generating Visuals..."`
   * `"Step 5/7: Planning Structure..."`
   * `"Step 6/7: Writing Section X/Y..."` (where the agent council loop runs)
   * `"Step 7/7: Finalizing..."`
3. **Saves Results**: Once generation is complete, the task saves the report content to the database via `database.save_report`.
4. **Returns Status**: Returns a dictionary containing the generated text, web search references, and chart paths.

---

## Polling and Status Checking

While the task runs, the browser polls the `GET /report-status/{task_id}` endpoint:

```python
@app.get("/report-status/{task_id}")
async def report_status(task_id: str):
    task = AsyncResult(task_id, app=celery_app)
    if task.state == 'SUCCESS':
        res = task.result
        return {'status': 'SUCCESS', 'report_content': res.get('report_content'), 'chart_path': res.get('chart_path')}
    elif task.state == 'FAILURE': 
        return {'status': 'FAILURE', 'error': str(task.info)}
    return {'status': task.state, 'message': task.info.get('message', 'Running...') if isinstance(task.info, dict) else 'Running...'}
```

* **`AsyncResult`**: Checks the state of the task in Redis.
* **`SUCCESS`**: Returns the completed report content and file paths.
* **`PROGRESS`**: Returns the current step message (e.g., `"Writing Section 3/7"`), which is displayed to the user in the loading screen.
* **`FAILURE`**: Returns the error stack trace for debugging.

This architecture ensures long-running generation tasks do not block the web server or cause client-side timeouts. Let's move on to **Chapter 8: Monitoring and Observability** to examine the system metrics and dashboard configuration.
