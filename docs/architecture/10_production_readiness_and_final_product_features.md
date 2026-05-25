# ScholarForge: Production Readiness and Final Product Features

This chapter serves as the definitive specification and roadmap for transitioning **ScholarForge** from a high-quality engineering prototype into a polished, production-ready SaaS application. Each section provides a detailed blueprint of the architecture, data schemas, API endpoints, and user interfaces required to implement these systems.

---

## 1. Authentication and Multi-Tenant User Isolation

To move beyond a local utility, ScholarForge requires a robust multi-tenant authentication framework. This guarantees that user sessions, files, folders, and reports are fully isolated and secure.

### Authentication Architecture

```mermaid
sequenceDiagram
    actor User as User Browser
    participant API as FastAPI Gateway
    participant DB as PostgreSQL DB
    
    User->>API: POST /api/auth/signup (email, password)
    API->>API: Hash password via bcrypt
    API->>DB: Save User record
    API-->>User: Signup success (201 Created)
    
    User->>API: POST /api/auth/login (email, password)
    API->>DB: Fetch user by email
    API->>API: Verify hash matches
    API->>API: Generate JWT Access & Refresh Token
    API-->>User: Set HTTPOnly Cookie or return JSON JWT
    
    User->>API: GET /api/reports (with JWT header)
    API->>API: Validate signature & expiration
    API->>DB: Fetch reports where user_id = JWT.sub
    API-->>User: Return isolated reports list
```

### Database Schema Changes

To support user isolation, the database schema must map all user-created resources to a central `User` model. Below is the SQLAlchemy model definition for user registration and isolation:

```python
# backend/database.py (Additions)
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserDB(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)

    # Relationships representing ownership and isolation
    folders = relationship("FolderDB", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("SessionDB", back_populates="user", cascade="all, delete-orphan")
    reports = relationship("ReportDB", back_populates="user", cascade="all, delete-orphan")

# Modify existing models to include user isolation
class FolderDB(Base):
    __tablename__ = "folders"
    # ... existing fields ...
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user = relationship("UserDB", back_populates="folders")
```

### Protected Route Implementation
The application uses FastAPI dependencies to inject and validate the current authenticated user context:

```python
# api/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from backend.database import get_db, UserDB

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme), db = Depends(get_db)) -> UserDB:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(UserDB).filter(UserDB.email == email).first()
    if user is None:
        raise credentials_exception
    return user
```

---

## 2. Real-Time Task Monitoring via WebSockets

Currently, the frontend uses HTTP polling to track the status of long-running Celery report generation tasks. Implementing an asynchronous WebSocket architecture improves performance and makes the application feel dynamic.

### WebSocket Communication Pattern

```mermaid
graph TD
    WebServer[FastAPI Web Server]
    RedisBroker[(Redis Pub/Sub)]
    CeleryWorker[Celery Task Worker]
    UserBrowser[User UI Browser]

    CeleryWorker -->|Publishes progress event| RedisBroker
    RedisBroker -->|Forwards message| WebServer
    WebServer <-->|WebSocket Connection /api/ws/tasks/id| UserBrowser
```

### Event Structuring and Handling
During the multi-stage compilation process, the background worker reports state updates to Redis:

```python
# Example state broadcast payload sent by Celery worker
{
    "task_id": "8fa8d39c-8512-42ea-a417-1bb27c62c90e",
    "status": "PROGRESS",
    "meta": {
        "current_step": "Nexus Synthesizing",
        "progress_percentage": 45.0,
        "message": "Synthesizing parallel drafts generated by Legion into a single cohesive structure...",
        "active_agent": "Nexus",
        "timestamp": "2026-05-19T18:42:00Z"
    }
}
```

The FastAPI web server subscribes to these events and sends them down to the browser:

```python
# api/endpoints/websockets.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.task import celery_app
import aioredis
import json

router = APIRouter()

@router.websocket("/api/ws/tasks/{task_id}")
async def task_websocket_endpoint(websocket: WebSocket, task_id: str):
    await websocket.accept()
    redis = await aioredis.from_url("redis://localhost:6379/1")
    pubsub = redis.pubsub()
    await pubsub.subscribe(f"task_channel_{task_id}")
    
    try:
        while True:
            # Check the celery result database directly or listen to the pub/sub event channel
            message = await pubsub.get_message(ignore_subscribe_messages=True)
            if message:
                data = json.loads(message["data"])
                await websocket.send_json(data)
                if data["status"] in ["SUCCESS", "FAILURE"]:
                    break
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe(f"task_channel_{task_id}")
```

---

## 3. Academic Citation & Reference System

Academic reports require precise, verifiable citations. The system automatically structures and cross-references assertions with external documents or web searches.

### Citation Flow

1. **Context Acquisition**: Tavily queries or local RAG operations retrieve sources with associated metadata (URLs, titles, authors, snippets).
2. **Source Registering**: During prompt construction, the source documents are organized into a numbered registry:
   * `[1]` Tavily: "How Quantum Computing Works", `https://example.com/quantum`
   * `[2]` RAG: "Local PDF - Corporate Strategy Q3", page 14
3. **Drafting Constraints**: The agent council is instructed via system prompt constraints to append references:
   * *System Prompt Guardrail*: "When citing external facts or local document content, append the source number in bracket format, e.g., `[1]` or `[1, 2]`. Do not synthesize facts without a citation."
4. **Post-Processing Compilation**: The `Artisan` reviews all citations, consolidates duplicate sources, sorts them sequentially by appearance, and generates a formatted markdown references appendix at the bottom of the document.

### Compiled Reference Section Format

```markdown
Here is the final generated report summary content proving that enterprise data integration saves up to 40% in infrastructure overhead [1]. Additionally, multi-agent frameworks reduce deployment validation bottlenecks by 22% [2, 3].

---

## References

[1] IBM Cloud Research, "The True ROI of Hybrid Cloud Integration," https://ibm.com/insights/cloud-roi (2025).
[2] Google Deepmind, "Multi-Agent System Optimization in Devops Pipelines," https://arxiv.org/abs/2410.xxxxx (2024).
[3] ScholarForge Internal Research, "Local PDF - RAG File: complete_performance_analysis.pdf", Section 4.2 (2026).
```

---

## 4. Dynamic Frontend UI/UX & Council Visualizer

The user experience should be interactive and engaging, highlighting the complex multi-agent execution happening on the backend.

### Agent Council Visualizer UI

The UI features a dynamic, real-time widget showing the progress of the multi-agent consensus workflow:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        AGENT COUNCIL PIPELINE                          │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐          │
│  │   LEGION     ├─────►│    NEXUS     ├─────►│  INQUISITOR  │          │
│  │  (Drafting)  │      │(Synthesizing)│      │  (Reviewing) │          │
│  └──────┬───────┘      └──────────────┘      └──────┬───────┘          │
│         ▲                                           │                  │
│         │               Feedback Loop               │ (Fact Failure)   │
│         └───────────────────────────────────────────┘                  │
│                                                     │                  │
│                                                     ▼                  │
│                                              ┌──────────────┐          │
│                                              │   ARTISAN    │          │
│                                              │ (Polishing)  │          │
│                                              └──────┬───────┘          │
│                                                     │                  │
│                                                     ▼                  │
│                                              ┌──────────────┐          │
│                                              │ Final Report │          │
│                                              └──────────────┘          │
└────────────────────────────────────────────────────────────────────────┘
```

* **Legion Node**: Pulsates with an amber glow when generating parallel outlines and draft choices. A text tooltip shows: *"Legion: Simulating 3 independent writers..."*
* **Nexus Node**: Emits light rays converging to a center node when consolidating drafts. Tooltip: *"Nexus: Merging structures, extracting unique value..."*
* **Inquisitor Node**: Displays a rotating scanline when auditing statements. Tooltip: *"Inquisitor: Querying web APIs to verify 4 factual statements..."*
* **Artisan Node**: Plays a typing animation when polishing text. Tooltip: *"Artisan: Formatting references, styling headings, and applying style guides..."*

### CSS Styling & Theme Tokens

The UI follows modern styling standards with a toggleable light/dark theme, consistent layout metrics, and Outfit/Inter fonts. CSS variables are defined in the global stylesheet:

```css
/* frontend/static/css/variables.css */
:root {
  --font-primary: 'Inter', sans-serif;
  --font-accent: 'Outfit', sans-serif;
  
  --bg-primary: #0b0f19;
  --bg-secondary: #131926;
  --border-color: #202b3f;
  
  --accent-color: #6366f1;
  --accent-glow: rgba(99, 102, 241, 0.15);
  
  --text-primary: #f3f4f6;
  --text-secondary: #9ca3af;
  
  --agent-legion: #f59e0b;
  --agent-nexus: #3b82f6;
  --agent-inquisitor: #ef4444;
  --agent-artisan: #10b981;
}

[data-theme="light"] {
  --bg-primary: #f9fafb;
  --bg-secondary: #ffffff;
  --border-color: #e5e7eb;
  --text-primary: #111827;
  --text-secondary: #4b5563;
  --accent-color: #4f46e5;
}
```

---

## 5. Academic Export Pipeline Polish

Final reports must meet high formatting standards to be useful for academic and professional review.

```mermaid
graph LR
    Markdown[Final Council Markdown] --> Pandoc[Pandoc Converter Engine]
    Template[Custom LaTeX/DOCX Template] --> Pandoc
    Pandoc --> PDF[Academic PDF]
    Pandoc --> DOCX[Professional Word Doc]
```

### PDF Compilation Optimization
We use Pandoc configured with the XeLaTeX engine to ensure correct symbol rendering, consistent margins, and proper page layouts. The backend triggers the compilation command with custom configurations:

```python
# backend/AI_engine.py (Optimized Export Routine)
import subprocess
import os

def export_markdown_to_pdf(md_filepath: str, pdf_filepath: str):
    # Uses customized LaTeX configurations to structure page breaks and margins
    cmd = [
        "pandoc",
        md_filepath,
        "-o", pdf_filepath,
        "--pdf-engine=xelatex",
        "-V", "geometry:margin=1in",
        "-V", "fontsize=11pt",
        "-V", "colorlinks=true",
        "-V", "linkcolor=blue",
        "--toc", # Auto-generates Table of Contents
        "--number-sections", # Prefixes numbers to chapters
        "--highlight-style=tango" # Clean code highlighting
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
         raise Exception(f"Pandoc failed: {result.stderr}")
```

### Export Styling Standards
* **Title Page**: Generates titles, author names, and timestamps dynamically using LaTeX template blocks.
* **Table of Contents**: Indents headers properly and includes clickable links.
* **Page Numbers**: Placed in the page footer using standard `Page X of Y` formats.
* **Code Fencing**: Converts code blocks into syntax-highlighted sections, preventing overflow issues.
* **Citations & References Page**: Formatted on a separate page at the end of the report.

---

## 6. Vector Search & RAG Integration

Injecting entire source documents directly into prompts quickly hits context window limitations. A RAG (Retrieval-Augmented Generation) pipeline ensures that only the most relevant document chunks are injected as context.

```mermaid
graph TD
    PDF[User Uploaded PDF] --> Parser[PyPDF / PdfPlumber]
    Parser --> Chunker[Recursive Character Splitter]
    Chunker --> Embedder[SentenceTransformers Embedding]
    Embedder --> VectorDB[(Vector DB: ChromaDB / FAISS)]
    
    Query[User Prompt / Agent Search Task] --> EmbedderQuery[Embed Query]
    EmbedderQuery --> Retrieval[Vector Similarity Search]
    VectorDB -->|Top-K Context Chunks| Retrieval
    Retrieval --> PromptCompiler[Compile LLM Prompt Context]
```

### Vector DB Service Integration
A containerized instance of **ChromaDB** is used to store document chunks and coordinate vector searches:

```python
# backend/rag_engine.py
import chromadb
from chromadb.utils import embedding_functions

chroma_client = chromadb.HttpClient(host="chromadb", port=8000)
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

def ingest_document(session_id: str, file_path: str, text: str):
    # Splits text into 1000-character chunks with a 200-character overlap
    chunk_size = 1000
    overlap = 200
    chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size - overlap)]
    
    collection = chroma_client.get_or_create_collection(
        name=f"session_{session_id}",
        embedding_function=embedding_fn
    )
    
    ids = [f"chunk_{i}" for i in range(len(chunks))]
    metadatas = [{"source": os.path.basename(file_path)} for _ in chunks]
    
    collection.add(
        documents=chunks,
        metadatas=metadatas,
        ids=ids
    )

def query_vector_db(session_id: str, query: str, top_k: int = 5):
    try:
        collection = chroma_client.get_collection(
            name=f"session_{session_id}",
            embedding_function=embedding_fn
        )
        results = collection.query(
            query_texts=[query],
            n_results=top_k
        )
        return results["documents"][0]
    except Exception:
        return [] # Return empty context if collection doesn't exist
```

---

## 7. Academic & Professional Templates

ScholarForge implements customized formats using report template configurations, modifying the drafting rules, outline layouts, and citation styles depending on the selected category.

| Template | Structure | Focus Area | Citation Style |
| :--- | :--- | :--- | :--- |
| **Research Paper** | Abstract $\rightarrow$ Introduction $\rightarrow$ Literature Review $\rightarrow$ Methodology $\rightarrow$ Results $\rightarrow$ Conclusion | Academic and theoretical rigor, experimental setups | IEEE / APA |
| **Case Study** | Executive Summary $\rightarrow$ Problem Statement $\rightarrow$ Alternatives $\rightarrow$ Proposed Solutions $\rightarrow$ Execution $\rightarrow$ Results | Enterprise decisions, post-mortems, real-world events | Harvard |
| **Technical Docs** | System Architecture $\rightarrow$ Requirements $\rightarrow$ Installation Guide $\rightarrow$ API Reference $\rightarrow$ Troubleshooting | Developer implementation guides, source configurations | Markdown Source links |
| **Market Analysis** | Market Landscape $\rightarrow$ Key Drivers $\rightarrow$ SWOT Analysis $\rightarrow$ Competitor Review $\rightarrow$ Forecasts | Financial predictions, business strategy, opportunities | Chicago / MLA |
| **Literature Review** | Research Overview $\rightarrow$ Current State of Art $\rightarrow$ Gaps Identification $\rightarrow$ Comparative Evaluation | Documenting and synthesizing existing publications | Vancouver / APA |

### System Configuration
The template engine maps user selections to prompt constraints in the orchestration process:

```python
# backend/report_formats.py
REPORT_TEMPLATES = {
    "research_paper": {
        "outline_structure": ["Abstract", "Introduction", "Literature Review", "Methodology", "Discussion", "Conclusion"],
        "tone_instruction": "Strictly academic, objective, third-person perspective. Avoid colloquialisms.",
        "citation_format": "IEEE style (e.g., [1], [2]) with an alphabetical Reference List at the end."
    },
    "case_study": {
        "outline_structure": ["Executive Summary", "Background Context", "The Core Challenge", "Proposed Solution", "Implementation Results"],
        "tone_instruction": "Analytical, business-focused, professional. Highlighting challenges and quantitative metrics.",
        "citation_format": "Harvard author-date style (e.g., Smith 2024) linked to references at the end."
    }
}
```

---

## 8. Multi-Container Dockerization

To simplify local setup and ensure consistent behavior across development and production environments, the entire application is containerized using Docker Compose.

```
                  ┌───────────────────────┐
                  │  docker-compose.yml   │
                  └───────────┬───────────┘
                              │
         ┌────────────┬───────┴────┬────────────┬─────────────┐
         │            │            │            │             │
   ┌─────▼─────┐┌─────▼─────┐┌─────▼─────┐┌─────▼─────┐ ┌─────▼─────┐
   │    web    ││  worker   ││   redis   ││ postgres  │ │ chromadb  │
   │ (FastAPI) ││ (Celery)  ││  (Broker) ││    (DB)   │ │(Vector DB)│
   └───────────┘└───────────┘└───────────┘└────────────┘ └───────────┘
```

### Dockerfile Specification

```dockerfile
# Dockerfile
FROM python:3.11-slim as base

# Install system dependencies (XeLaTeX and Pandoc for PDF generation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    pandoc \
    texlive-xetex \
    texlive-fonts-recommended \
    texlive-plain-generic \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Multi-stage targets for Web and Celery processes
FROM base as web
EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM base as worker
CMD ["celery", "-A", "backend.task.celery_app", "worker", "--loglevel=info"]
```

### Docker Compose Configuration

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: scholarforge_db
    environment:
      POSTGRES_DB: scholarforge
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: securepassword
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    container_name: scholarforge_redis
    ports:
      - "6379:6379"

  chromadb:
    image: chromadb/chroma:latest
    container_name: scholarforge_vector_db
    ports:
      - "8000:8000"
    volumes:
      - chroma_data:/chroma/data

  web:
    build:
      context: .
      target: web
    container_name: scholarforge_web
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://admin:securepassword@postgres:5432/scholarforge
      - REDIS_URL=redis://redis:6379/0
      - CHROMA_HOST=chromadb
      - CHROMA_PORT=8000
    depends_on:
      - postgres
      - redis
      - chromadb

  worker:
    build:
      context: .
      target: worker
    container_name: scholarforge_worker
    environment:
      - DATABASE_URL=postgresql://admin:securepassword@postgres:5432/scholarforge
      - REDIS_URL=redis://redis:6379/0
      - CHROMA_HOST=chromadb
      - CHROMA_PORT=8000
    depends_on:
      - redis
      - postgres
      - chromadb

volumes:
  postgres_data:
  chroma_data:
```

---

## 9. Dynamic AI Model Selection & Fallback Routing

To compare generations and provide flexibility, users can choose their preferred LLM engine from the frontend.

### Dynamic API Routing Strategy

When calling the LLM context wrapper in the backend, the selected model name is passed dynamically to ensure proper API routing:

```python
# backend/AI_engine.py (Model Routing Logic)
from backend.agents.utils import query_model_api

SUPPORTED_MODELS = {
    "gemini": "openrouter/google/gemini-2.5-flash",
    "llama": "openrouter/meta-llama/llama-3.3-70b-instruct",
    "groq-llama": "groq/llama-3.3-70b-specdec",
    "gpt-4o": "openrouter/openai/gpt-4o-mini"
}

def generate_report_section_with_model(model_key: str, prompt: str, system_instruction: str) -> str:
    # Resolve the API provider and model identifier
    resolved_model = SUPPORTED_MODELS.get(model_key, SUPPORTED_MODELS["gemini"])
    
    # Try the preferred model; fallback to Gemini 2.5 Flash if the primary fails
    try:
        response = query_model_api(resolved_model, prompt, system_instruction)
        return response
    except Exception as api_err:
        # Structured fallback logging
        print(f"Primary model {resolved_model} failed: {str(api_err)}. Routing to fallback...")
        fallback_model = SUPPORTED_MODELS["gemini"]
        return query_model_api(fallback_model, prompt, system_instruction)
```

### UI Presentation
The report configuration form contains a clean select dropdown mapping to these backend keys:
```html
<!-- frontend/templates/report_generator.html -->
<label for="model-selection" class="form-label">AI Engine Model</label>
<select id="model-selection" name="model" class="form-select">
    <option value="gemini" selected>Google Gemini 2.5 Flash (Balanced & Fast)</option>
    <option value="llama">Meta Llama 3.3 70B (High Reasoning)</option>
    <option value="groq-llama">Groq Llama 3.3 (Ultrafast Generation)</option>
    <option value="gpt-4o">OpenAI GPT-4o Mini (Analytical Style)</option>
</select>
```

---

## 10. Observability & Analytics Dashboard

An interactive analytics dashboard provides visibility into system usage, token consumption, and generation efficiency.

### Metrics Collected

The system collects usage data and tracks metrics using a lightweight analytics schema:

* **Reports Generated**: Cumulative count of successfully completed compilation cycles.
* **Average Generation Time**: Time elapsed from task initiation to Pandoc output production.
* **Token Metrics**: Cumulative prompt tokens and completion tokens consumed per task.
* **Template Popularity**: Distributing generation counts across Research Paper, Case Study, and other formats.
* **Active Tasks**: Real-time counter of current tasks running in the Celery queue.

### Analytics DB Schema

```python
# backend/database.py (Analytics Addition)
from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime

class UsageMetricDB(Base):
    __tablename__ = "usage_metrics"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    report_type = Column(String, nullable=False)
    model_used = Column(String, nullable=False)
    duration_seconds = Column(Float, nullable=False)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    timestamp = Column(DateTime, default=datetime.utcnow)
```

These metrics are fetched via a background API endpoint and rendered on the frontend dashboard using clean canvas graphs (e.g., Chart.js) to show system utilization at a glance.
