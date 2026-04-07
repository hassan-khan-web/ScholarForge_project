FROM python:3.10-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Try apt-get with timeout and retries
RUN apt-get update -o APT::Acquire::Retries=3 && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/* || echo "Note: Some packages may not be available due to network"

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
# Install with retries and increase timeout
RUN pip install --no-cache-dir --retries 5 --default-timeout=1000 -r requirements.txt


FROM python:3.10-slim AS runner

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    pandoc \
    texlive-latex-base \
    texlive-latex-extra \
    texlive-fonts-recommended \
    texlive-xetex \
    fonts-liberation \
    lmodern \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN useradd -m -u 1000 scholar

RUN mkdir -p /app/data /app/static/charts && \
    chown -R scholar:scholar /app

USER scholar

COPY --chown=scholar:scholar . .

EXPOSE 5000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "5000"]