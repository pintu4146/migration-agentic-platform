# Observability Stack: LangSmith + Prometheus + Grafana

## Overview

This document describes the complete observability stack for the migration copilot POC, combining LangSmith for LLM-specific tracing with Prometheus and Grafana for system metrics and visualization.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                         │
│              FastAPI + LangGraph + Agents                    │
└────────┬────────────────────────────────┬────────────────────┘
         │                                │
         │ LLM Traces                     │ System Metrics
         │                                │
    ┌────▼─────────────┐          ┌──────▼──────────────┐
    │   LangSmith      │          │   Prometheus        │
    │   (SaaS)         │          │   (Self-Hosted)     │
    │                  │          │                     │
    │ - Prompts        │          │ - Request Rate      │
    │ - Responses      │          │ - Latency           │
    │ - Agent Traces   │          │ - Cache Hit Rate    │
    │ - Workflows      │          │ - Token Usage       │
    │ - Token Counts   │          │ - Cost Tracking     │
    └──────────────────┘          └──────┬──────────────┘
                                         │
                                  ┌──────▼──────────────┐
                                  │     Grafana         │
                                  │   (Self-Hosted)     │
                                  │                     │
                                  │ - Dashboards        │
                                  │ - Alerts            │
                                  │ - LangSmith Links   │
                                  └─────────────────────┘
```

## Components

### 1. LangSmith (LLM Tracing)

**Purpose:** AI/LLM-specific observability

**What it tracks:**
- Individual LLM calls (prompts, responses, tokens)
- Agent decision-making process
- LangGraph workflow execution
- State transitions
- Prompt templates and versions
- Model performance

**Configuration:**
```python
# backend/app/config.py
class Settings(BaseSettings):
    LANGSMITH_API_KEY: str
    LANGSMITH_PROJECT: str = "migration-copilot-poc"
    LANGSMITH_TRACING: bool = True
    LANGSMITH_ENDPOINT: str = "https://api.smith.langchain.com"
```

**Setup:**
```python
# backend/app/tracing/langsmith.py
import os
from langsmith import Client

# Enable tracing
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "migration-copilot-poc"
os.environ["LANGCHAIN_API_KEY"] = settings.LANGSMITH_API_KEY

# Client for custom traces
client = Client(api_key=settings.LANGSMITH_API_KEY)
```

**Usage:**
```python
from langsmith import traceable

@traceable(name="extract_facts")
async def extract_facts(docs: List[Dict]) -> Dict:
    # Automatically traced
    response = await llm.invoke(prompt)
    return response
```

---

### 2. Prometheus (Metrics Collection)

**Purpose:** System and application metrics

**What it tracks:**
- HTTP request rate and latency
- Cache hit/miss rates
- LLM token usage and costs
- State transaction metrics
- Redis performance
- System resources (CPU, memory)

**Configuration:**
```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  # FastAPI application metrics
  - job_name: 'migration-copilot-api'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'

  # Redis metrics
  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']

  # Prometheus self-monitoring
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
```

**Metrics Implementation:**
```python
# backend/app/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# ===== LLM Metrics =====
llm_requests_total = Counter(
    'llm_requests_total',
    'Total LLM requests',
    ['provider', 'model', 'status']
)

llm_request_duration = Histogram(
    'llm_request_duration_seconds',
    'LLM request duration',
    ['provider', 'model'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

llm_tokens_used = Counter(
    'llm_tokens_used_total',
    'Total tokens used',
    ['provider', 'model', 'type']  # type: prompt/completion
)

llm_cost_estimate = Counter(
    'llm_cost_estimate_dollars',
    'Estimated LLM cost in dollars',
    ['provider', 'model']
)

# ===== Cache Metrics =====
cache_hits = Counter(
    'cache_hits_total',
    'Cache hits',
    ['cache_type']  # llm, mcp, embedding
)

cache_misses = Counter(
    'cache_misses_total',
    'Cache misses',
    ['cache_type']
)

cache_operation_duration = Histogram(
    'cache_operation_duration_seconds',
    'Cache operation duration',
    ['operation', 'cache_type']
)

# ===== Workflow Metrics =====
workflow_executions = Counter(
    'workflow_executions_total',
    'Total workflow executions',
    ['phase', 'status']
)

workflow_phase_duration = Histogram(
    'workflow_phase_duration_seconds',
    'Workflow phase duration',
    ['phase'],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0]
)

state_transactions = Counter(
    'state_transactions_total',
    'State transactions',
    ['status']  # success, version_mismatch, error
)

state_version = Gauge(
    'state_version_current',
    'Current state version',
    ['project_id']
)

# ===== MCP Metrics =====
mcp_requests = Counter(
    'mcp_requests_total',
    'MCP requests',
    ['profile', 'status']
)

mcp_request_duration = Histogram(
    'mcp_request_duration_seconds',
    'MCP request duration',
    ['profile']
)

mcp_documents_retrieved = Histogram(
    'mcp_documents_retrieved',
    'Number of documents retrieved',
    ['profile']
)

# ===== System Metrics =====
active_workflows = Gauge(
    'active_workflows',
    'Number of active workflows'
)

http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)
```

**Metrics Endpoint:**
```python
# backend/app/main.py
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
```

---

### 3. Grafana (Visualization)

**Purpose:** Unified dashboard and alerting

**What it shows:**
- Real-time metrics from Prometheus
- Historical trends
- Custom dashboards
- Alerts and notifications
- Links to LangSmith traces

**Configuration:**
```yaml
# monitoring/grafana/datasources/prometheus.yml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
```

**Dashboard Configuration:**
```json
// monitoring/grafana/dashboards/migration-copilot.json
{
  "dashboard": {
    "title": "Migration Copilot POC",
    "tags": ["migration", "llm", "langgraph"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "LLM Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(llm_requests_total[5m])",
            "legendFormat": "{{provider}} - {{model}}"
          }
        ]
      },
      {
        "id": 2,
        "title": "Cache Hit Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(cache_hits_total[5m]) / (rate(cache_hits_total[5m]) + rate(cache_misses_total[5m]))",
            "legendFormat": "{{cache_type}}"
          }
        ]
      },
      {
        "id": 3,
        "title": "Workflow Phase Duration (p95)",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(workflow_phase_duration_seconds_bucket[5m]))",
            "legendFormat": "{{phase}}"
          }
        ]
      },
      {
        "id": 4,
        "title": "LLM Cost (Last Hour)",
        "type": "stat",
        "targets": [
          {
            "expr": "increase(llm_cost_estimate_dollars[1h])",
            "legendFormat": "{{provider}}"
          }
        ]
      },
      {
        "id": 5,
        "title": "Active Workflows",
        "type": "stat",
        "targets": [
          {
            "expr": "active_workflows"
          }
        ]
      },
      {
        "id": 6,
        "title": "State Transaction Success Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(state_transactions_total{status=\"success\"}[5m]) / rate(state_transactions_total[5m])",
            "legendFormat": "Success Rate"
          }
        ]
      }
    ]
  }
}
```

---

## Instrumentation Examples

### Instrumenting LLM Calls

```python
# backend/app/providers/instrumented_provider.py
import time
from prometheus_client import Counter, Histogram
from langsmith import traceable

class InstrumentedLLMProvider:
    def __init__(self, provider: LLMProvider):
        self.provider = provider
    
    @traceable(name="llm_generate_text")
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> ProviderResponse:
        # Start timer
        start_time = time.time()
        
        try:
            # Call LLM (LangSmith auto-traces)
            response = await self.provider.generate_text(
                prompt, system_prompt, **kwargs
            )
            
            # Record Prometheus metrics
            duration = time.time() - start_time
            
            llm_requests_total.labels(
                provider=self.provider.provider,
                model=self.provider.model,
                status='success'
            ).inc()
            
            llm_request_duration.labels(
                provider=self.provider.provider,
                model=self.provider.model
            ).observe(duration)
            
            llm_tokens_used.labels(
                provider=self.provider.provider,
                model=self.provider.model,
                type='prompt'
            ).inc(response.usage['prompt_tokens'])
            
            llm_tokens_used.labels(
                provider=self.provider.provider,
                model=self.provider.model,
                type='completion'
            ).inc(response.usage['completion_tokens'])
            
            # Estimate cost
            cost = self._estimate_cost(response.usage, self.provider.model)
            llm_cost_estimate.labels(
                provider=self.provider.provider,
                model=self.provider.model
            ).inc(cost)
            
            return response
            
        except Exception as e:
            llm_requests_total.labels(
                provider=self.provider.provider,
                model=self.provider.model,
                status='error'
            ).inc()
            raise
    
    def _estimate_cost(self, usage: Dict[str, int], model: str) -> float:
        """Estimate cost based on token usage"""
        # GPT-4 pricing (example)
        if model.startswith("gpt-4"):
            prompt_cost = usage['prompt_tokens'] * 0.00003  # $0.03/1k tokens
            completion_cost = usage['completion_tokens'] * 0.00006  # $0.06/1k tokens
            return prompt_cost + completion_cost
        # Add other models...
        return 0.0
```

### Instrumenting Cache Operations

```python
# backend/app/cache/instrumented_cache.py
import time
from prometheus_client import Counter, Histogram

class InstrumentedCache:
    def __init__(self, redis_client, cache_type: str):
        self.redis = redis_client
        self.cache_type = cache_type
    
    async def get(self, key: str) -> Optional[str]:
        start_time = time.time()
        
        value = await self.redis.get(key)
        
        duration = time.time() - start_time
        cache_operation_duration.labels(
            operation='get',
            cache_type=self.cache_type
        ).observe(duration)
        
        if value:
            cache_hits.labels(cache_type=self.cache_type).inc()
        else:
            cache_misses.labels(cache_type=self.cache_type).inc()
        
        return value
    
    async def set(self, key: str, value: str, ttl: int):
        start_time = time.time()
        
        await self.redis.setex(key, ttl, value)
        
        duration = time.time() - start_time
        cache_operation_duration.labels(
            operation='set',
            cache_type=self.cache_type
        ).observe(duration)
```

### Instrumenting Workflow Phases

```python
# backend/app/orchestration/instrumented_workflow.py
import time
from prometheus_client import Counter, Histogram, Gauge

class InstrumentedWorkflow:
    async def _context_retrieval_node(self, state: MigrationState) -> MigrationState:
        # Track active workflows
        active_workflows.inc()
        
        # Start timer
        start_time = time.time()
        
        try:
            # Execute node
            result = await self._execute_context_retrieval(state)
            
            # Record success
            duration = time.time() - start_time
            workflow_phase_duration.labels(
                phase='context_retrieval'
            ).observe(duration)
            
            workflow_executions.labels(
                phase='context_retrieval',
                status='success'
            ).inc()
            
            return result
            
        except Exception as e:
            workflow_executions.labels(
                phase='context_retrieval',
                status='error'
            ).inc()
            raise
        finally:
            active_workflows.dec()
```

---

## Deployment

### Podman Compose

```yaml
# podman-compose.yml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - LANGSMITH_API_KEY=${LANGSMITH_API_KEY}
      - LANGSMITH_PROJECT=migration-copilot-poc
      - LANGSMITH_TRACING=true
    depends_on:
      - redis
      - qdrant
      - prometheus

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./monitoring/grafana/datasources:/etc/grafana/provisioning/datasources
    depends_on:
      - prometheus

  redis-exporter:
    image: oliver006/redis_exporter:latest
    ports:
      - "9121:9121"
    environment:
      - REDIS_ADDR=redis:6379
    depends_on:
      - redis

volumes:
  prometheus_data:
  grafana_data:
```

---

## Access URLs

| Service | URL | Purpose |
|---------|-----|---------|
| **Backend API** | http://localhost:8000 | FastAPI application |
| **API Docs** | http://localhost:8000/docs | Swagger UI |
| **Metrics Endpoint** | http://localhost:8000/metrics | Prometheus metrics |
| **Prometheus** | http://localhost:9090 | Metrics database |
| **Grafana** | http://localhost:3001 | Dashboards (admin/admin) |
| **LangSmith** | https://smith.langchain.com | LLM traces |

---

## Monitoring Checklist

### Daily Monitoring

- [ ] Check Grafana dashboard for anomalies
- [ ] Review LangSmith traces for errors
- [ ] Monitor LLM cost trends
- [ ] Check cache hit rates
- [ ] Review workflow execution times

### Weekly Monitoring

- [ ] Analyze cost trends
- [ ] Review prompt performance
- [ ] Check for state transaction failures
- [ ] Optimize slow workflows
- [ ] Review alert history

### Monthly Monitoring

- [ ] Cost optimization review
- [ ] Performance trend analysis
- [ ] Capacity planning
- [ ] Dashboard updates
- [ ] Alert rule refinement

---

## Alerting Rules

```yaml
# monitoring/prometheus/alerts.yml
groups:
  - name: migration_copilot_alerts
    rules:
      # High error rate
      - alert: HighLLMErrorRate
        expr: rate(llm_requests_total{status="error"}[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High LLM error rate detected"
          description: "LLM error rate is {{ $value }} requests/sec"
      
      # Low cache hit rate
      - alert: LowCacheHitRate
        expr: rate(cache_hits_total[5m]) / (rate(cache_hits_total[5m]) + rate(cache_misses_total[5m])) < 0.5
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Low cache hit rate"
          description: "Cache hit rate is {{ $value | humanizePercentage }}"
      
      # High LLM cost
      - alert: HighLLMCost
        expr: increase(llm_cost_estimate_dollars[1h]) > 10
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High LLM cost detected"
          description: "LLM cost in last hour: ${{ $value }}"
      
      # State transaction failures
      - alert: StateTransactionFailures
        expr: rate(state_transactions_total{status!="success"}[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "State transaction failures detected"
          description: "Failure rate: {{ $value }} transactions/sec"
      
      # Slow workflow phases
      - alert: SlowWorkflowPhase
        expr: histogram_quantile(0.95, rate(workflow_phase_duration_seconds_bucket[5m])) > 60
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Slow workflow phase detected"
          description: "Phase {{ $labels.phase }} p95 latency: {{ $value }}s"
```

---

## Troubleshooting

### LangSmith Not Showing Traces

**Problem:** Traces not appearing in LangSmith dashboard

**Solutions:**
1. Check API key: `echo $LANGSMITH_API_KEY`
2. Verify tracing enabled: `LANGCHAIN_TRACING_V2=true`
3. Check network connectivity to api.smith.langchain.com
4. Review application logs for LangSmith errors

### Prometheus Not Scraping Metrics

**Problem:** Metrics not appearing in Prometheus

**Solutions:**
1. Check `/metrics` endpoint: `curl http://localhost:8000/metrics`
2. Verify Prometheus config: `cat monitoring/prometheus.yml`
3. Check Prometheus targets: http://localhost:9090/targets
4. Review Prometheus logs: `podman logs prometheus`

### Grafana Dashboard Empty

**Problem:** Grafana dashboard shows no data

**Solutions:**
1. Verify Prometheus datasource configured
2. Check Prometheus is collecting metrics
3. Verify dashboard queries are correct
4. Check time range in dashboard

---

## Best Practices

### 1. Metric Naming

Follow Prometheus naming conventions:
- Use `_total` suffix for counters
- Use `_seconds` suffix for durations
- Use snake_case for metric names
- Use descriptive labels

### 2. Cardinality Management

Avoid high-cardinality labels:
- ❌ Don't use: user IDs, request IDs, timestamps
- ✅ Use: status codes, phases, providers

### 3. Trace Sampling

For high-volume production:
- Sample traces (e.g., 10% of requests)
- Always trace errors
- Always trace slow requests

### 4. Cost Monitoring

Track LLM costs closely:
- Set budget alerts
- Monitor token usage trends
- Optimize prompts for efficiency
- Use caching aggressively

---

## Summary

This observability stack provides:

✅ **Complete Visibility**
- LLM-specific tracing (LangSmith)
- System metrics (Prometheus)
- Unified dashboards (Grafana)

✅ **Production-Ready**
- Battle-tested tools
- Self-hosted (except LangSmith)
- Scalable architecture

✅ **Cost-Effective**
- Open-source (Prometheus, Grafana)
- Free tier (LangSmith)
- Minimal infrastructure

✅ **Easy to Maintain**
- Well-documented
- Large community
- Standard tooling

This stack enables you to monitor, debug, and optimize your migration copilot POC effectively!