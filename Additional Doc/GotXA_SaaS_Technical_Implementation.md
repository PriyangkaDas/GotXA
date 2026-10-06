# GotXA SaaS - Technical Implementation Checklist

> **SaaS Documentation Suite**:
> - 🚀 **Commercial Strategy**: [`GotXA_SaaS_Strategy.md`](GotXA_SaaS_Strategy.md)
> - 📊 **Pricing & ROI**: [`GotXA_SaaS_Pricing_Guide.md`](GotXA_SaaS_Pricing_Guide.md)
> - 📑 **Directory Index**: [`README.md`](README.md)

## IMMEDIATE CHANGES NEEDED (3-4 months)

### 1. Tenant Isolation Layer

**Current problem:** All data mixed in single database

**Solution:**

```python
# /backend/app/tenant.py - NEW FILE

from flask import g, request
from functools import wraps
import jwt
from app.models import db, Tenant

class TenantContext:
    def __init__(self):
        self.tenant_id = None
        self.tenant = None
        self.db_url = None
    
    def load_from_request(self):
        """Extract tenant from subdomain or API token"""
        if request.host.startswith('localhost'):
            self.tenant_id = 'dev'
            return
        
        # Extract subdomain: tenant-name.gotxa.com
        parts = request.host.split('.')
        if len(parts) > 2:
            subdomain = parts[0]
            self.tenant = db.session.query(Tenant).filter_by(
                subdomain=subdomain
            ).first()
            if self.tenant:
                self.tenant_id = self.tenant.id
            else:
                raise Exception("Invalid tenant")

def require_tenant(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        g.tenant = TenantContext()
        g.tenant.load_from_request()
        
        # Set tenant for all queries
        g.tenant_id = g.tenant.tenant_id
        return f(*args, **kwargs)
    return decorated

# Update main.py
@app.before_request
@require_tenant
def before_request():
    g.tenant_id = g.tenant.tenant_id
```

### 2. Database Schema Updates

```sql
-- Add tenant_id to all tables
ALTER TABLE users ADD COLUMN tenant_id UUID NOT NULL DEFAULT gen_random_uuid();
ALTER TABLE alerts ADD COLUMN tenant_id UUID NOT NULL DEFAULT gen_random_uuid();
ALTER TABLE incidents ADD COLUMN tenant_id UUID NOT NULL DEFAULT gen_random_uuid();
ALTER TABLE tasks ADD COLUMN tenant_id UUID NOT NULL DEFAULT gen_random_uuid();
ALTER TABLE evidence ADD COLUMN tenant_id UUID NOT NULL DEFAULT gen_random_uuid();
ALTER TABLE audit_events ADD COLUMN tenant_id UUID NOT NULL DEFAULT gen_random_uuid();

-- Create indexes for performance
CREATE INDEX idx_alerts_tenant ON alerts(tenant_id);
CREATE INDEX idx_incidents_tenant ON incidents(tenant_id);
CREATE INDEX idx_users_tenant ON users(tenant_id);

-- Create Tenant registry table
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    subdomain VARCHAR(255) UNIQUE NOT NULL,
    tier VARCHAR(50) DEFAULT 'professional',
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    status VARCHAR(50) DEFAULT 'active',
    stripe_customer_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255),
    max_users INT DEFAULT 10,
    max_log_sources INT DEFAULT 5,
    retention_days INT DEFAULT 90,
    api_quota_per_month INT DEFAULT 100000
);

-- Usage tracking for billing
CREATE TABLE usage_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    event_type VARCHAR(50),  -- 'log_ingested', 'report_generated', 'api_call'
    gb_processed DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);

-- Audit trail (immutable, append-only)
CREATE TABLE audit_trail (
    id BIGSERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL,
    actor_id UUID,
    action VARCHAR(255),
    resource_type VARCHAR(100),
    resource_id UUID,
    before_state JSONB,
    after_state JSONB,
    created_at TIMESTAMP DEFAULT NOW() IMMUTABLE,
    ip_address INET,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);

-- Make audit_trail append-only
ALTER TABLE audit_trail SET (fillfactor = 90);
CREATE TRIGGER audit_trail_immutable BEFORE UPDATE ON audit_trail
FOR EACH ROW EXECUTE FUNCTION prevent_update();
```

### 3. Query Pattern Changes

```python
# OLD: Query all alerts
# SELECT * FROM alerts;

# NEW: Query only current tenant's alerts
@api.route('/alerts')
@authenticate
def get_alerts():
    return Alert.query.filter_by(tenant_id=g.tenant_id).all()

# This must be applied to EVERY query in the codebase
# Use SQLAlchemy event listeners for automatic filtering

from sqlalchemy.orm import events

@events.listens_for(db.session, "before_flush")
def receive_before_flush(session, flush_context, instances):
    """Automatically add tenant_id to new objects"""
    for obj in session.new:
        if hasattr(obj, 'tenant_id'):
            obj.tenant_id = g.tenant_id

@events.listens_for(Query, "before_all_from_statement")
def auto_filter_tenant(query, *args, **kwargs):
    """Automatically filter queries by tenant"""
    for table in query.column_descriptions:
        entity = table['entity']
        if hasattr(entity, 'tenant_id'):
            query = query.filter(entity.tenant_id == g.tenant_id)
    return query
```

### 4. Authentication & Subdomain Routing

```python
# /backend/app/auth.py - UPDATE

def authenticate_tenant_request(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Get tenant from subdomain
        tenant = Tenant.query.filter_by(
            subdomain=request.host.split('.')[0]
        ).first()
        
        if not tenant:
            return error_response('Invalid tenant', '', 404)
        
        g.tenant_id = tenant.id
        g.tenant = tenant
        
        # Get user token
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user = verify_jwt_token(token, tenant.id)
        
        if not user:
            return error_response('Unauthorized', '', 401)
        
        g.user = user
        g.tenant_id = tenant.id
        
        return f(*args, **kwargs)
    return decorated
```

### 5. Billing Integration (Stripe)

```python
# /backend/app/billing.py - NEW FILE

import stripe

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

class BillingEngine:
    @staticmethod
    def create_customer(tenant):
        """Create Stripe customer for new tenant"""
        customer = stripe.Customer.create(
            name=tenant.name,
            email=tenant.admin_email,
            metadata={"tenant_id": str(tenant.id)}
        )
        tenant.stripe_customer_id = customer.id
        db.session.commit()
        return customer
    
    @staticmethod
    def create_subscription(tenant, tier='professional'):
        """Create Stripe subscription"""
        prices = {
            'starter': 'price_starter',
            'professional': 'price_professional',
            'enterprise': 'price_enterprise'
        }
        
        subscription = stripe.Subscription.create(
            customer=tenant.stripe_customer_id,
            items=[{"price": prices[tier]}],
            billing_cycle_anchor='auto'
        )
        
        tenant.stripe_subscription_id = subscription.id
        tenant.tier = tier
        db.session.commit()
        return subscription
    
    @staticmethod
    def calculate_monthly_charges(tenant_id, month_start, month_end):
        """Calculate usage-based overage charges"""
        usage = db.session.query(
            func.sum(UsageEvent.gb_processed)
        ).filter(
            UsageEvent.tenant_id == tenant_id,
            UsageEvent.created_at >= month_start,
            UsageEvent.created_at < month_end
        ).scalar()
        
        usage_gb = usage or 0
        tier = Tenant.query.get(tenant_id)
        
        # Tier limits (GB/month)
        limits = {
            'starter': 100,
            'professional': 500,
            'enterprise': float('inf')
        }
        
        included = limits[tier.tier]
        if usage_gb > included:
            overage_gb = usage_gb - included
            overage_charge = overage_gb * 0.50  # $0.50/GB
            return overage_charge
        return 0
    
    @staticmethod
    def emit_usage_event(tenant_id, event_type, gb_processed):
        """Track usage for billing"""
        event = UsageEvent(
            tenant_id=tenant_id,
            event_type=event_type,
            gb_processed=gb_processed,
            created_at=datetime.utcnow()
        )
        db.session.add(event)
        db.session.commit()

# Usage in API endpoints
@api.route('/api/ingest/events', methods=['POST'])
@authenticate_tenant_request
def ingest_events():
    data = request.get_json()
    gb = len(str(data).encode()) / 1024**3
    
    # Save events
    # ...
    
    # Track for billing
    BillingEngine.emit_usage_event(g.tenant_id, 'log_ingested', gb)
```

### 6. Environment Variables

```bash
# .env for SaaS deployment

# Multi-tenancy
GOTXA_MODE=saas

# Stripe
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLIC_KEY=pk_live_...

# AWS
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1

# Tenant DB
TENANT_DB_TEMPLATE=postgresql://user:pass@rds-template.aws:5432/template_db

# S3
S3_BUCKET=gotxa-logs-prod
S3_REGION=us-east-1

# Compliance
SOC2_AUDIT_MODE=true
DATA_RESIDENCY_ENFORCE=true
```

---

## AWS INFRASTRUCTURE (Terraform)

```hcl
# /terraform/main.tf

# Load Balancer
resource "aws_lb" "gotxa_alb" {
  name = "gotxa-alb"
  load_balancer_type = "application"
  subnets = [aws_subnet.public_a.id, aws_subnet.public_b.id]
}

# ECS Cluster (Fargate)
resource "aws_ecs_cluster" "gotxa" {
  name = "gotxa-cluster"
}

resource "aws_ecs_service" "api" {
  name = "gotxa-api"
  cluster = aws_ecs_cluster.gotxa.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count = 2
  
  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name = "gotxa-backend"
    container_port = 5000
  }
}

# RDS Aurora (Shared management DB)
resource "aws_rds_cluster" "gotxa_shared" {
  cluster_identifier = "gotxa-shared-db"
  engine = "aurora-postgresql"
  database_name = "gotxa"
  master_username = "admin"
  master_password = var.db_password
  
  backup_retention_period = 30
  skip_final_snapshot = false
}

# RDS Template for per-tenant DBs
resource "aws_rds_cluster" "tenant_template" {
  cluster_identifier = "gotxa-tenant-template"
  engine = "aurora-postgresql"
  # Customers clone from this template
}

# ElastiCache (Redis per tenant tier)
resource "aws_elasticache_cluster" "redis" {
  cluster_id = "gotxa-redis"
  engine = "redis"
  node_type = "cache.r6g.xlarge"
  num_cache_nodes = 3
  # Enable automatic failover for high availability
}

# S3 Buckets
resource "aws_s3_bucket" "logs" {
  bucket = "gotxa-logs-prod"
  
  lifecycle_rule {
    id = "archive-old-logs"
    enabled = true
    
    transition {
      days = 90
      storage_class = "GLACIER"
    }
    
    expiration {
      days = 2555  # 7 years for compliance
    }
  }
}
```

---

## ESTIMATED TIMELINE & COSTS

### Engineering Effort
- Multi-tenant refactoring: 8-12 weeks, 2-3 engineers
- Billing system: 4-6 weeks
- AWS infrastructure: 3-4 weeks
- Compliance/security: 4-8 weeks
- Total: 5-6 months, $250-400K

### Infrastructure Costs (Annual)
- Development: $1,500/month (shared RDS, single availability zone)
- Production Starter tier: $8,000-10,000/month baseline
- Production Scaling: Add $2-3K per 10 customers
- Year 1 estimate: $150K (development) + $50K (prod startup)

### Compliance/Security Costs
- SOC2 Type II audit: $50-100K
- Legal (DPA, MSA templates): $25K
- Security consultants: $40-60K
- Total Year 1: $150K

---

## MIGRATION PATH FOR EXISTING CUSTOMERS

If you have on-premise customers, offer:

**Option A: Migrate to SaaS**
- Discount: 20-30% first year
- Data export: Available anytime
- Support: Dedicated migration engineer

**Option B: Keep Self-Hosted**
- Perpetual license option
- Annual support: $20-50K
- No per-GB charges

**Option C: Hybrid**
- Pilot on SaaS (free 3 months)
- Full deployment on self-hosted (licensed)

---

## SUCCESS METRICS TO TRACK

```
Technical Metrics:
├─ Tenant isolation: 0 data leaks (security audit required)
├─ Platform uptime: 99.95%+
├─ Query performance: <200ms for typical queries
└─ Billing accuracy: 99.9%+ (automated tests)

Business Metrics:
├─ MRR: $50K → $100K → $250K+ (months 3/6/9)
├─ CAC: $8K (Year 1) → $6K (Year 2)
├─ LTV:CAC: 16x+
└─ Churn: <5% monthly

Sales Metrics:
├─ Pilot customers: 5-10 in Month 1-2
├─ Paying customers: 20-30 by Month 4
├─ $500K ARR by Month 6
└─ $2.5M ARR by Month 12
```
