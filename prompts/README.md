# Content Templates

This directory contains content templates used by the Script Agent to generate fantasy football content for TikTok.

## Template System

Templates use Python string formatting with named variables. Each template should:

1. Define clear variable placeholders (e.g. `{player}`, `{week}`, `{matchup}`)
2. Include engaging hooks and calls-to-action
3. Follow TikTok best practices for short-form content
4. Maintain consistent brand voice

## Available Templates

- **start_sit.md** - Start/sit recommendations for weekly lineup decisions
- **waiver_wire.md** - Waiver wire pickup suggestions with roster percentages
- **injury_pivot.md** - Alternative player suggestions when injuries occur (coming soon)
- **trade_thermometer.md** - Trade value analysis and recommendations (coming soon)

## Usage

Templates are loaded by the Script Agent (`packages/agents/script_agent.py`) and populated with context data from the Data Agent.

Example:
```python
from packages.agents.script_agent import render_script

script = render_script(
    kind="start-sit",
    context={"player": "Bijan Robinson", "week": 5, "matchup": "vs TB"},
    # Prefer canonical templates in templates/script_templates/
    template_path="templates/script_templates/start_sit.md"
)
```

## Adding New Templates

1. Create a new `.md` file in this directory
2. Use descriptive variable names in `{curly_braces}`
3. Include engaging hooks and clear calls-to-action
4. Test with sample data before deploying