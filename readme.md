# ScholarForge

ScholarForge is an advanced, AI-powered research assistant and report generation platform. It automatically synthesizes information from web searches and user-uploaded documents to generate comprehensive, structured, and long-form academic or technical reports in multiple formats.

## 🌟 Core Features

- **Intelligent Report Generation**: Generates multi-section, highly detailed reports based on user queries or topics.
- **Adaptive Web Research**: Utilizes the Tavily Search API with recursive gap analysis to locate missing specific data and include verifiable sources.
- **Document Ingestion**: Supports uploading local files (PDF, DOCX, TXT, MD) to provide direct context to the AI engine for both chat and report generation.
- **Multi-Format Export**: Seamlessly exports generated reports to PDF, DOCX, Markdown, TXT, and JSON. It includes auto-generated data visualizations (charts) using Matplotlib.
- **Asynchronous Processing**: Employs Celery and Redis to handle long-running, heavy AI tasks in the background, ensuring a smooth user experience.
- **Interactive Chat Assistant**: Features a conversational UI that can reference uploaded documents and workspace context.
- **Persistent Storage**: Maintains report history, chat sessions, folders, and research "hooks" within a PostgreSQL database.

## 🛠️ Technology Stack

- **Backend Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python)
- **Database**: PostgreSQL (via SQLAlchemy)
- **Task Queue**: Celery + Redis
- **Frontend**: Jinja2 Templates, HTML/JS, and [Tailwind CSS v4](https://tailwindcss.com/)
- **AI Integrations**: [OpenRouter API](https://openrouter.ai/) for LLM routing (defaulting to Gemini/Llama variants), Tavily API for semantic search.
- **Document Processing**: `PyMuPDF` (fitz), `python-docx`, `reportlab`, `BeautifulSoup4`
- **Containerization**: Docker & Docker Compose

## 🚀 Getting Started

The easiest way to run ScholarForge is using Docker Compose, which spins up the FastAPI backend, Celery worker, Redis broker, and PostgreSQL database automatically.

### Prerequisites

- [Docker](https://www.docker.com/) and Docker Compose installed
- [Node.js / npm](https://nodejs.org/) (Only needed if modifying frontend Tailwind CSS)

### 1. Clone & Environment Setup

Clone the repository and create a `.env` file in the root directory:

```env
# Required API Keys
OPENROUTER_API_KEY=your_openrouter_api_key
SERP_KEY=your_tavily_api_key

# Application Secret
APP_SECRET_KEY=your_random_secret_string

# Below are managed by docker-compose, but can be customized
POSTGRES_USER=scholar
POSTGRES_PASSWORD=forgepass
POSTGRES_DB=scholarforge
```

### 2. Run the Application

Build and start the services using Docker Compose:

```bash
docker-compose up --build
```

This will start:
- **web**: The FastAPI web server running on `http://localhost:5000`
- **worker**: The Celery worker processing background tasks
- **db**: The PostgreSQL database
- **redis**: The Redis broker

### 3. Frontend Development (Optional)

If you plan to modify the frontend styles, install the Tailwind CSS dependencies:

```bash
npm install
```

## 📂 Project Structure

- `backend/`: Core FastAPI application logic, database models, AI engine logic, and Celery task definitions.
  - `AI_engine.py`: Contains the logic for interacting with LLMs, generating summaries, creating outlines, and assembling reports.
  - `chat_engine.py`: Manages the conversational AI interactions.
- `frontend/`: Contains the Jinja2 HTML templates (`templates/`) and static assets like generated charts and custom CSS (`static/`).
- `docs/`: Comprehensive repository guide, containing testing, monitoring, CI/CD, and DB migration manuals.
  - `architecture/`: 10-chapter architectural blueprint explaining RAG chunking, WebSocket streamer, and council agents logic.
- `data/`: Directory for persistent local data (bound as a volume in Docker).
- `Dockerfile` & `docker-compose.yml`: Container orchestration configurations.

## 🧪 Testing

You can verify the connection to the configured AI models via the handy debugging script:

```bash
# Ensure your virtual environment is active and variables are loaded
python test_model_connection.py
```
