# Documentation

The complete Product Requirements Document (PRD) is located at `docs/PRD.md`.

This directory contains all project documentation including:

- **PRD.md** - Product Requirements Document v1.7
- Architecture decisions and design docs (to be added)
- API documentation (auto-generated from FastAPI)
- Deployment guides (to be added)

For API documentation, start the server (`make up`) and visit the API docs at the server `/docs` path.

Template locations
------------------
The project uses a canonical templates directory at `templates/script_templates/`. Legacy templates may live under `prompts/templates/` — the application prefers the canonical location but will fall back to the legacy path for compatibility.

If you add new templates, place them under `templates/script_templates/` and follow the naming convention used in the templates directory.