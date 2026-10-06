# GOTXA Backend API — Documentation Index

This directory contains the Python Flask REST API server and Celery background task code. To maintain clean documentation and avoid duplication drift, all project reports and guides have been consolidated and centralized in the repository root.

Please refer to the following documentation resources:

1.  **[IMPORTANT_FACTS.md](../doc/IMPORTANT_FACTS.md)** — **Start Here.** Cheat-sheet reference detailing port maps, default credentials (database, frontend, vulnerable-app), environment variables, directory structures, alert mappings, and troubleshooting commands.
2.  **[ARCHITECTURE.md](../doc/ARCHITECTURE.md)** — Detailed architectural report covering network zoning, relational database schemas, authentication/RBAC matrices, audit logger workflows, Modbus PLC configurations, SCADA HMI gateways, and the SOAR playbook execution logic.
3.  **[API_SPECIFICATION.md](../doc/API_SPECIFICATION.md)** — Complete REST API specifications detailing response wrappers, authentication headers, error formats, and request/response schemas for all 40+ endpoints.
4.  **[TESTING_AND_INTEGRATION.md](../doc/TESTING_AND_INTEGRATION.md)** — Guide for executing testing scenarios (pen-testing attack scripts) and integrating React frontend applications with the REST API.
5.  **[CODE_SNIPPETS.md](../doc/CODE_SNIPPETS.md)** — Implementation references compiling code snippets for IP bans, Docker quarantines, reboots, RBAC permission handlers, and Modbus simulation loops.
6.  **[For Avirup/](../For%20Avirup/)** — Specialized documentation directory containing compliance mappings, alarm thresholds, MITRE matrix mappings, layman guides, incident response runbooks, glossary lists, and docker container overviews.
7.  **[Additional Doc/](../Additional%20Doc/)** — Strategic planning and commercial SaaS transition resources:
    - **[GotXA_SaaS_Strategy.md](../Additional%20Doc/GotXA_SaaS_Strategy.md)**: Market positioning, pricing strategy, and GTM execution.
    - **[GotXA_SaaS_Pricing_Guide.md](../Additional%20Doc/GotXA_SaaS_Pricing_Guide.md)**: Customer pricing calculator, overages, and sales templates.
    - **[GotXA_SaaS_Technical_Implementation.md](../Additional%20Doc/GotXA_SaaS_Technical_Implementation.md)**: Tenant isolation layers, routing, and metering checklist.
8.  **[Root README.md](../README.md)** — General platform overview, quick-start instructions, and Additional Resources index.
