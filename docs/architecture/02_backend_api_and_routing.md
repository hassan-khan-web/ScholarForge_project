# ScholarForge: Backend API and Routing

Let's dissect `backend/main.py`. This file acts as the primary web application gateway. It is built on top of **FastAPI** to provide high-performance, asynchronous routing, auto-generated OpenAPI documentation, and structured request validation.

---

## Application Setup and Middleware Configuration

When the FastAPI app is initialized, several middleware layers are configured to ensure security, rate limiting, session tracking, and monitoring:

1. **CORS Middleware (`CORSMiddleware`)**:
   Enables Cross-Origin Resource Sharing. This allows web frontend applications hosted on different domains/ports to query the ScholarForge API. While configured as `"allow_origins=["*"]"` for development, it can be scoped to specific domains in production.
   
2. **Session Middleware (`SessionMiddleware`)**:
   Uses signed cookies to maintain client sessions. The application retrieves `APP_SECRET_KEY` from environment variables to sign session cookies, defaulting to a fallback string `"super-secret-key"` if undefined.
   
3. **SlowAPI Rate Limiter (`Limiter`)**:
   To protect the backend from API key depletion or DDoS attacks, SlowAPI is integrated. It uses the client's IP address (`get_remote_address`) to track rates:
   * **Chat requests (`POST /chat`)** are limited to **30 requests per minute**.
   * **Report generations (`POST /start-report`)** are limited to **10 requests per minute**.
   * Exceeding these limits raises a `RateLimitExceeded` exception, caught by a custom handler returning an HTTP `429 Too Many Requests` response.

4. **Prometheus Instrumentator (`Instrumentator`)**:
   Before the routes are defined, the app is instrumented with `prometheus_fastapi_instrumentator`. This layer listens to all traffic, measuring request processing times, path variables, status codes, and methods, and exposes these at the `/metrics` endpoint.

---

## Global Exception Handling

A key phase of the backend design is **graceful error handling**. If any unhandled exception propagates out of a route, the app intercepts it with the global exception handler:

```python
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_id = f"{exc.__class__.__name__}_{id(exc)}"
    logger.exception(f"Unhandled exception [{error_id}]: {exc}", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": "An internal server error occurred. Please try again later.",
            "error_id": error_id
        }
    )
```

**Why is this done?**
1. **Security**: Returning database errors or system stack traces directly to the client could leak internal information.
2. **Debugging**: It assigns a unique `error_id` to each crash, allowing developers to query the structured server logs while presenting the user with a clean, friendly error.

---

## File Upload Parsing Flow

When a user attaches files in the chat or report interface, the backend parses them in-memory using the async function `extract_text_from_file`:

* **PDF Files**: Handled via `fitz` (PyMuPDF). It reads the bytes directly into memory (`pdf_bytes = await file.read()`), opens the stream, loops over each page, extracts the raw text (`page.get_text()`), and truncates the content to 20,000 characters to prevent context-window bloat on the LLMs.
* **DOCX Files**: Handled using `python-docx` (`DocxDocument`). Reads the bytes, loads them into an in-memory buffer (`BytesIO`), loops through document paragraphs, and appends the text.
* **TXT & MD Files**: Read directly as UTF-8 text strings, ignoring encoding errors.

The extracted text is wrapped in demarcated headers:
`--- FILE: <filename> --- ... ------------------`
which are then appended to the system context prompt.

---

## API Endpoints Catalog

Here is the exact routing list configured in `backend/main.py`:

### 1. View Render Endpoints (Jinja2)
* `GET /`: Renders `report_generator.html`.
* `GET /chat`: Renders `ai_assistant.html` (the interactive chatbot).
* `GET /search`: Renders `search.html`.

### 2. Folder and Session CRUD Endpoints
To support structured workspace organization, chat sessions are housed under folders.
* `GET /api/folders`: Retrieves all folders along with their child chat sessions.
* `POST /api/folders`: Creates a new folder. Uses Pydantic body validation (`CreateFolderRequest` validates that name is between 1 and 200 chars).
* `PUT /api/folders/{folder_id}`: Renames a folder.
* `DELETE /api/folders/{folder_id}`: Deletes a folder and all its cascade-linked chat sessions.
* `POST /api/sessions`: Creates a new chat session inside a folder.
* `PUT /api/sessions/{session_id}`: Renames a chat session.
* `DELETE /api/sessions/{session_id}`: Deletes a chat session.
* `GET /api/sessions/{session_id}/messages`: Fetches the history of messages for a chat.
* `GET /api/sessions/{session_id}/info`: Fetches the meta metadata (title, folder) of a session.

### 3. Report Actions
* `POST /start-report`: Spawns a background Celery task. It reads the query, selected format (e.g., Literature Review, Technical Manual), requested page count, and any uploaded PDFs, compiles them, and triggers the Celery job, returning the `task_id` instantly.
* `GET /report-status/{task_id}`: Checks on task progress. It queries the Redis backend using Celery's `AsyncResult` to check if it's `PROGRESS`, `SUCCESS`, or `FAILURE`.
* `GET /api/history`: Lists all previously generated reports stored in the database.
* `GET /api/report/{id}`: Fetches the content of a specific report.
* `PUT /api/report/{id}/content`: Saves manual user edits made to a report inside the UI.
* `DELETE /api/report/{id}`: Deletes a report.
* `DELETE /api/reports/all`: Deletes all reports.

### 4. Interactive Chat
* `POST /chat`: Receives the prompt, session history, model configuration, normal vs deep-dive mode, and files. Calls `chat_engine.get_chat_response_async` and saves both the user query and AI response in the database.

### 5. Hook Management
Hooks are specific interesting research notes users save during chat/generation sessions.
* `POST /add-hook`: Saves a text hook.
* `GET /api/hooks`: Fetches all saved hooks.
* `DELETE /api/hooks/{hook_id}`: Deletes a hook.
* `POST /api/merge-hook`: Uses the AI to insert a saved research hook into a completed report text.

### 6. Document Downloading
* `POST /download`: Downloads a report. It generates a temporary file path, converts the markdown content (plus the Matplotlib graph, if present) to PDF, DOCX, TXT, MD, or JSON using the conversion methods inside `AI_engine`, returns the file stream, and hooks an async **background task** to delete the temp file once the download completes.

---

This covers the entire routing layer. Let's move on to **Chapter 3: Database and Storage** to see how these objects are represented and query-managed in SQLAlchemy.
