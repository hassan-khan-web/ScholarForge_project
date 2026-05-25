# ScholarForge Monitoring & Observability Guide

## Overview

ScholarForge now includes comprehensive monitoring capabilities:
- **Prometheus Metrics**: Request latency, error rates, and system health
- **Flower Dashboard**: Real-time Celery task monitoring and worker status

---

## 1. Prometheus Metrics

### What's Tracked

The Prometheus instrumentation automatically tracks:

| Metric | Description |
|--------|-------------|
| `requests_total` | Total number of requests per endpoint/method |
| `requests_created` | Request creation timestamp |
| `requests_in_progress` | Number of requests currently being processed |
| `requests_duration_seconds` | Request latency distribution (histogram) |
| `requests_duration_seconds_sum` | Total time spent processing requests |
| `requests_duration_seconds_count` | Count of requests (for averaging) |

### Accessing Metrics

**Raw Prometheus format:**
```
GET http://localhost:5000/metrics
```

**Example output:**
```
# HELP requests_total Total count of requests
# TYPE requests_total counter
requests_total{handler="/chat",method="POST",status_code="200"} 42.0

# HELP requests_duration_seconds Request latency (seconds)
# TYPE requests_duration_seconds histogram
requests_duration_seconds_bucket{handler="/chat",le="0.01",method="POST"} 5.0
requests_duration_seconds_bucket{handler="/chat",le="0.05",method="POST"} 38.0
requests_duration_seconds_bucket{handler="/chat",le="+Inf",method="POST"} 42.0
requests_duration_seconds_sum{handler="/chat",method="POST"} 125.34
requests_duration_seconds_count{handler="/chat",method="POST"} 42.0
```

### Using with Docker Compose

When running locally:
```bash
docker-compose up --build
```

Then access metrics:
```bash
curl http://localhost:5000/metrics
```

### Integrating with Monitoring Systems

#### Grafana
1. Add Prometheus data source pointing to `http://prometheus:9090`
2. Import pre-built dashboard or create custom panels
3. Use PromQL queries:
   ```promql
   # Average request latency (last 5 minutes)
   avg(rate(requests_duration_seconds_sum[5m])) / avg(rate(requests_duration_seconds_count[5m]))
   
   # Error rate
   sum(rate(requests_total{status_code=~"5.."}[5m])) / sum(rate(requests_total[5m]))
   
   # Request volume by endpoint
   sum(rate(requests_total[1m])) by (handler)
   ```

#### CloudWatch
```python
# Example: Send metrics to AWS CloudWatch
import boto3
from prometheus_client import CollectorRegistry, generate_latest

cloudwatch = boto3.client('cloudwatch')
metrics_text = generate_latest(CollectorRegistry())
# Parse and send to CloudWatch...
```

#### Datadog
```python
# Example: Send metrics to Datadog
import requests

metrics = [
    {
        "series": [
            {
                "metric": "scholarforge.requests.duration",
                "points": [[timestamp, latency]],
                "tags": ["endpoint:/chat"]
            }
        ]
    }
]
requests.post("https://api.datadoghq.com/api/v1/series",
    json=metrics,
    headers={"DD-API-KEY": os.environ.get("DATADOG_API_KEY")})
```

---

## 2. Flower Dashboard - Celery Task Monitoring

### What's Available

Flower provides real-time insights into:
- **Task Status**: Running, pending, successful, failed tasks
- **Worker Status**: CPU, memory, queue depth per worker
- **Task Timing**: Execution time, ETA, processing rate
- **Error Tracking**: Failed task logs and stack traces
- **Statistics**: Historical task metrics and trends

### Accessing Flower

**Local (Docker):**
```
http://localhost:5555
```

**Production:**
```
http://<your-domain>:5555
```

### Flower Dashboard Features

#### 1. **Tasks View**
- See all tasks in real-time
- Filter by status (active, reserved, success, failure)
- Click task to view details:
  - Input arguments
  - Worker processing it
  - Execution time
  - Exceptions (if failed)

#### 2. **Workers View**
- Monitor worker health
- See worker pool stats (queued, processing, successful)
- Check resource usage (CPU, memory)
- Restart/shutdown workers

#### 3. **Pool View**
- Queue depth analysis
- Worker distribution
- Task routing visualization

#### 4. **Graph View**
- Request volume over time
- Task success/failure rate
- Execution time trends

### Common Flower Queries

```bash
# View all active tasks
curl http://localhost:5555/api/tasks

# View specific worker stats
curl http://localhost:5555/api/workers

# View task details
curl http://localhost:5555/api/tasks/<task_id>

# Revoke a task
curl -X POST http://localhost:5555/api/task/revoke/<task_id>
```

### Monitoring Key Metrics

#### Report Generation Tasks
```
Endpoint: /start-report
Worker Queue: default
Metrics to track:
- Task count/minute
- Average execution time (target: < 5 minutes for 15-page reports)
- Failure rate (target: < 1%)
- Queue depth (target: < 20 pending)
```

#### Chat Messages
```
Endpoint: /chat
Queue: default (synchronous, not via Celery for now)
Note: Future optimization could move chat to Celery
```

---

## 3. Setting Up External Monitoring

### Docker Prometheus + Grafana Stack

Create `monitoring/docker-compose.yml`:

```yaml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana

volumes:
  prometheus_data:
  grafana_data:
```

Create `monitoring/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'scholarforge'
    static_configs:
      - targets: ['localhost:5000']
    metrics_path: '/metrics'
```

Run:
```bash
docker-compose -f monitoring/docker-compose.yml up -d
```

Then access:
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)

---

## 4. Alert Examples

### Prometheus Alert Rules

Create `monitoring/alerts.yml`:

```yaml
groups:
  - name: scholarforge_alerts
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: sum(rate(requests_total{status_code=~"5.."}[5m])) / sum(rate(requests_total[5m])) > 0.05
        for: 5m
        annotations:
          summary: "ScholarForge error rate > 5%"

      # High latency
      - alert: HighLatency
        expr: histogram_quantile(0.95, requests_duration_seconds) > 5
        for: 5m
        annotations:
          summary: "Request p95 latency > 5s"

      # Celery queue backup
      - alert: CeleryQueueBackup
        expr: celery_queue_length > 50
        for: 5m
        annotations:
          summary: "Celery queue has {{ $value }} pending tasks"
```

---

## 5. Best Practices

✅ **Do:**
- Export metrics daily for trend analysis
- Set up alerts for error rates > 5%
- Monitor Celery queue depth (< 50 recommended)
- Track p95 latency for report generation (target: < 5 min for 15-page)
- Review Flower logs for recurring failures

❌ **Avoid:**
- Leaving Flower exposed on production without authentication
- Storing metrics in memory (use persistent storage)
- Ignoring worker failures (monitor /health endpoint)
- Scraping metrics too frequently (15-30s intervals recommended)

---

## 6. Troubleshooting

### Prometheus Not Collecting Metrics

```bash
# Verify /metrics endpoint is working
curl http://localhost:5000/metrics | head -20

# Check Prometheus targets
# In browser: http://localhost:9090/targets
```

### Flower Not Showing Tasks

```bash
# Verify Celery broker connection
docker logs scholarforge_flower | grep -i redis

# Check worker health
docker logs scholarforge_worker | grep -i "ready"

# Test broker connection manually
redis-cli -h redis ping
```

### High Memory Usage in Flower

```bash
# Reduce history retention
# Edit docker-compose.yml flower service:
command: celery -A backend.task.celery_app flower --port=5555 --max_tasks=1000
```

---

## 7. Migration from Manual Monitoring

If you were previously monitoring via logs:

| Old Method | New Method |
|----------|-----------|
| Grep logs for errors | Query requests_total{status_code=~"5.."} |
| Manual latency tracking | Histogram requests_duration_seconds |
| SSH into servers for status | Flower dashboard |
| Time-based guessing | Real-time queue depth metrics |

---

## Quick Reference

| Service | URL | Purpose |
|---------|-----|---------|
| Prometheus Metrics | http://localhost:5000/metrics | Raw metrics for scraping |
| Flower Dashboard | http://localhost:5555 | Celery task & worker monitoring |
| Health Check | http://localhost:5000/health | System health verification |

