# AGENTS.md - Behavioral Rules & Operational Constraints

> **CRITICAL DIRECTIVE**: You are operating in **STRICT READ-ONLY / CONSULTATION MODE**.
> **NEVER EDIT, CREATE, REFACTOR, RENAME, OR DELETE ANY FILE IN THIS REPOSITORY WITHOUT EXPLICIT USER CONSENT.**

## Mandatory Operational Rules

1. **Strict Read-Only Default:**
   - Do not make unprompted file edits, code refactoring, cleanup, or formatting.
   - When asked to inspect, debug, diagnose, explain, or investigate, provide analysis only. Do NOT make code changes unless explicitly instructed (e.g. "please edit file X to fix Y").

2. **Approval Before Modifications:**
   - If changes are needed, present the diagnosis, explain the proposed solution, specify the exact files/lines to be changed, and ask for user confirmation before applying any changes.

3. **Protected Core Infrastructure:**
   - Under NO circumstances modify SCADA/ICS components (`scada_gateway.py`, `modbus_plc_server.py`, `Dockerfile.scada`, `New_Machine/`), environment variables (`.env`), or Docker configurations (`docker-compose.yml`) without explicit, verified permission.

4. **Zero Destructive Actions:**
   - Never run destructive git commands (`git reset`, `git clean`, `git checkout -- .`) or file deletion commands.
   - Preserve all existing comments, docstrings, and established architecture.

5. **Full Project Rules:**
   - Refer to [rules.md](file:///c:/Users/RJDhu/OneDrive/Desktop/Project/GotXA/rules.md) for full project governance and API architecture standards.
