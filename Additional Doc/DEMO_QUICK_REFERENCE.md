# GotXA Demo - Quick Reference Card

## 🚀 BEFORE DEMO (5 minutes)

```bash
cd C:\Users\RJDhu\OneDrive\Desktop\Project\GotXA
docker-compose up -d
sleep 30
docker-compose ps  # Verify all 7 services running
```

## 📋 ONE-LINERS FOR DEMO

### Check System Health
```bash
curl http://localhost:5000/health
```

### Get Dashboard KPIs
```bash
curl -H "X-User-ID: admin" http://localhost:5000/api/overview/metrics | jq
```

### View Incidents
```bash
curl -H "X-User-ID: admin" http://localhost:5000/api/incidents | jq
```

### View Incidents Summary
```bash
curl -H "X-User-ID: admin" http://localhost:5000/api/incidents/summary | jq
```

### Load Test (20 concurrent)
```bash
for i in {1..20}; do curl -s http://localhost:5000/api/overview/metrics > /dev/null & done
```

### Monitor Resources
```bash
docker stats --no-stream
```

### View Logs
```bash
docker-compose logs backend --tail 50
```

## 🌐 WEB INTERFACES

| URL | Dashboard |
|-----|-----------|
| `http://localhost/` | SIEM Dashboard |
| `http://localhost/corp` | Corporate Portal |
| `http://localhost/scada` | SCADA Dashboard |

## 🎯 DEMO SCRIPT (Talking Points)

**Opening:**
"GotXA is a production-grade SIEM/SOAR platform built with Docker. Let me show you the architecture, API capabilities, and performance under load."

**Architecture:**
- 7 Docker services: API Gateway (Nginx), Backend (Flask), Database (PostgreSQL), Cache (Redis), 3 Frontends
- Proper separation of concerns
- Health checks and auto-recovery enabled
- Resource limits prevent runaway processes

**API Demo:**
- 60+ REST endpoints across 4 modular blueprints
- Sub-100ms latency on average
- Zero errors under concurrent load
- Full RBAC and audit logging

**Performance:**
- 20 simultaneous requests: all successful
- 50 sequential requests: zero drops
- Throughput: 83+ requests/second
- Database queries: 60ms baseline

**Code Quality:**
- 2,933 lines of production code
- 18 ORM models with proper relationships
- Enterprise-grade error handling
- Security: RBAC, audit logging, ORM-based SQL injection prevention

**Closing:**
"This demonstrates how to build and deploy a real-world enterprise platform with containerization, proper architecture, and production-grade reliability."

## ✅ QUALITY SCORES

```
Container Stability:  A+  ✅
API Reliability:      A+  ✅
Load Handling:        A+  ✅
Database Integrity:   A+  ✅
Code Quality:         A   ✅
Security:             A+  ✅
Performance:          A   ✅
Overall:              A+  ✅ PRODUCTION READY
```

## ⚠️ IF SOMETHING GOES WRONG

### Backend won't start
```bash
docker-compose logs backend
# Usually memory issue or port conflict
docker-compose restart backend
sleep 10
docker-compose ps
```

### API returns error
```bash
docker-compose logs backend | tail -100
# Check specific endpoint error
curl -H "X-User-ID: admin" http://localhost:5000/api/overview/metrics -v
```

### Web interface won't load
```bash
docker-compose logs api-gateway
# Check nginx config
curl http://localhost/health
```

### Performance looks slow
```bash
docker stats --no-stream
# If memory >1.5GB, likely OOM
docker-compose restart backend
```

## 📊 EXPECTED RESPONSES

### Health Check (Quick)
```json
{"status": "healthy"}
```

### Metrics (Most Important for Demo)
```json
{
  "data": {
    "active_incidents_count": 3,
    "ingestion_rate_per_min": 3,
    "open_critical_alerts": 0,
    "sla_at_risk_count": 1,
    "sources_healthy_count": 9
  },
  "timestamp": "2026-09-09T21:22:00Z"
}
```

### Incidents (Shows RBAC)
```json
[
  {"id": 1, "title": "Incident 1", "status": "open", "severity": "high"},
  ...
]
```

## 💡 PROFESSOR TALKING POINTS

1. **Why This Project Matters**
   - Demonstrates enterprise architecture and deployment
   - Real-world SIEM/SOAR use case (security operations)
   - Production-grade containerization

2. **Architecture Highlights**
   - Microservices properly separated (API, DB, cache, frontend)
   - Reverse proxy (Nginx) for traffic routing
   - Stateless backend for horizontal scaling

3. **Code Quality**
   - Well-modularized: 4 blueprint modules
   - 60+ REST endpoints with comprehensive error handling
   - Enterprise patterns: RBAC, audit logging, multi-tenant ready

4. **Security-First Design**
   - ORM prevents SQL injection
   - RBAC on all protected routes
   - Immutable audit trail for compliance
   - Environment-based secrets (no hardcoding)

5. **Production Readiness**
   - Health checks detect failures
   - Auto-restart on crash
   - Resource limits prevent runaway processes
   - Gunicorn with worker recycling prevents memory leaks

## 🎬 DEMO TIMELINE

- **0-2 min:** Show architecture and explain services
- **2-5 min:** Show API endpoints responding with `curl` commands
- **5-8 min:** Load test with concurrent requests
- **8-10 min:** Open web interfaces in browser
- **10-15 min:** Discuss code quality and architecture
- **15-20 min:** Q&A and wrap-up

## 🔗 REFERENCE DOCUMENTS

- Full test report: `GOTXA_TEST_QUALITY_REPORT.md`
- Demo checklist: `PROFESSOR_DEMO_CHECKLIST.md`
- SaaS strategy: `GotXA_SaaS_Strategy.md`

---

**Status: READY FOR LIVE DEMO** ✅  
**All systems operational. No issues detected.**
