#!/usr/bin/env bash
# Testing API Endpoints
# ====================

# Get Alerts
curl -s "http://localhost:5000/api/alerts" -H "X-User-ID: admin" | jq '.data | length'

# Get Incidents Summary
curl -s "http://localhost:5000/api/incidents/summary" -H "X-User-ID: admin" | jq '.data'

# Get Data Sources Metrics
curl -s "http://localhost:5000/api/data-sources/metrics" -H "X-User-ID: admin" | jq '.data'

# Get Threat Feeds
curl -s "http://localhost:5000/api/threat-intelligence/feeds" -H "X-User-ID: admin" | jq '.data | length'

# Get Settings
curl -s "http://localhost:5000/api/settings/general" -H "X-User-ID: admin" | jq '.data'
