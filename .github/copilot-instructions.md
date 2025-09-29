# Fantasy TikTok Engine Project

This is a FastAPI-based fantasy football content generation engine for TikTok that creates automated content using AI agents.

## Project Structure
- `apps/api/` - FastAPI backend service
- `apps/cli/` - Command-line interface tools
- `packages/agents/` - AI agent modules (data, script, voice, scheduler)
- `prompts/templates/` - Content templates for script generation
- `scripts/` - Development and deployment scripts
- `docs/` - Project documentation including PRD
- `tests/` - Test suite

## Development Workflow
- Use `make setup` to initialize the development environment
- Use `make up` to start the API server
- Use `make test` to run the test suite
- Use `make health` to check service status
- Use `make fmt` and `make lint` for code quality

## Key Features
- Fantasy football content generation
- Multi-agent architecture (data, script, voice, scheduling)
- TikTok Business API integration
- Google Sheets tracking
- CLI tools for content creators