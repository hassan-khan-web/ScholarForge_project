# ScholarForge: Monitoring and Observability

This chapter outlines the monitoring and observability systems in ScholarForge, covering structured logging, Prometheus metrics, the Flower Celery dashboard, and the system health check API.

---

## Structured JSON Logging

Standard console logs (like strings formatted with f-strings) can be difficult to parse and query when aggregated in cloud environments. ScholarForge uses structured logging, defined in `backend/logging_config.py`, to output logs in JSON format:

```python
class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)
```

**Benefits**:
1. **Searchability**: Log management systems (like Datadog, AWS CloudWatch, or Elasticsearch) can index JSON keys, allowing developers to filter logs by log level, file module, or function name.
2. **Traceback Packaging**: Stack trace exceptions are formatted into a single JSON field (`"exception"`), keeping log lines compact and readable.

---

## Prometheus Metrics

The FastAPI server exposes real-time performance metrics at `GET /metrics` using `prometheus-fastapi-instrumentator`:

* **`requests_total`**: A counter tracking the total number of HTTP requests processed, categorized by route and status code.
* **`requests_in_progress`**: A gauge tracking the number of active HTTP requests currently running.
* **`requests_duration_seconds`**: A histogram measuring request latency.

### PromQL Query Examples
These metrics can be queried in a Prometheus-linked Grafana dashboard to track performance:

```promql
# 1. Average latency (last 5 minutes)
avg(rate(requests_duration_seconds_sum[5m])) / avg(rate(requests_duration_seconds_count[5m]))

# 2. Server error rate (5xx responses)
sum(rate(requests_total{status_code=~"5.."}[5m])) / sum(rate(requests_total[5m]))

# 3. Active requests by endpoint
sum(rate(requests_total[1m])) by (handler)
```

---

## Flower Celery Monitor

For background tasks, ScholarForge includes the **Flower Dashboard** (configured on port `5555`). Flower communicates with the Redis broker to monitor:

* **Task Status**: Real-time tracking of pending, active, completed, and failed tasks.
* **Worker Resource Usage**: Monitoring CPU and memory consumption across the worker pool.
* **Error Tracking**: Aggregating failure exception details and stack traces.
* **Queue Depth**: Measuring pending task backlogs to support auto-scaling.

---

## Health Check API

To support container health checks and load balancer monitoring, the application exposes a health check endpoint at `GET /health`:

```python
@app.get("/health")
async def health_check():
    health_status = {"status": "healthy", "components": {}}
    
    # 1. Test database connection
    try:
        session = database.SessionLocal()
        session.execute("SELECT 1")
        session.close()
        health_status["components"]["database"] = {"status": "ok"}
    except Exception as e:
        health_status["components"]["database"] = {"status": "error", "message": str(e)}
        health_status["status"] = "degraded"
        
    # 2. Test Celery/Redis connection
    ...
    return JSONResponse(status_code=status_code, content=health_status)
```

This endpoint verifies database and Redis connectivity, returning an HTTP `200` status if all systems are operational, or `503 Service Unavailable` if critical components fail. Let's move on to **Chapter 9: Migrations, CI/CD, and Testing** to review code integration and deployment processes.
