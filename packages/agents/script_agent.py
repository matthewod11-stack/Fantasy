"""Script Agent using Jinja2 templates with optional OpenAI post-processing.

This module provides a deterministic, strict-template rendering path using
Jinja2 (StrictUndefined). When OPENAI_ENABLED is set to a truthy value the
rendered template will be passed to the OpenAI adapter as a prompt for
optional polishing/rewriting. If no OpenAI API key is present the adapter is
used in dry-run mode so this code is safe to run with no `.env`.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateNotFound, UndefinedError

from adapters.openai_adapter import OpenAIAdapter, ScriptRequest


TEMPLATES_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "generation", "templates")
)


def _jinja_env() -> Environment:
    loader = FileSystemLoader(TEMPLATES_DIR)
    return Environment(loader=loader, undefined=StrictUndefined, autoescape=False)


DEFAULT_KIND_TO_TEMPLATE = {
    "waiver-wire": "waiver_wire.j2",
    "top-performers-week": "top_performers_week.j2",
}


def render_script(kind: str, context: Dict[str, Any], template_path: Optional[str] = None) -> str:
    """Render a script from a Jinja2 template.

    Args:
        kind: logical template kind (used to pick a default template)
        context: mapping used to render the template; StrictUndefined is used so
                 missing keys raise an exception.
        template_path: optional explicit path to a template file. If provided
                       and the path exists it will be used directly.

    Returns:
        Final script text. If OPENAI_ENABLED is truthy the rendered template
        will be sent to the OpenAI adapter which may rewrite it; otherwise
        the raw rendered template is returned.

    Raises:
        jinja2.UndefinedError: when required context keys are missing.
        FileNotFoundError: when the requested template cannot be found.
    """
    # Load and render using Jinja2 StrictUndefined so missing variables fail fast
    env = _jinja_env()

    # If an explicit template path is provided and exists, render from its
    # contents (this makes tests and callers flexible).
    if template_path:
        if os.path.exists(template_path):
            with open(template_path, "r", encoding="utf-8") as fh:
                template_src = fh.read()
            template = env.from_string(template_src)
        else:
            # If the template_path is not a file, try to treat it as a template
            # name within the templates directory.
            try:
                template_name = os.path.basename(template_path)
                template = env.get_template(template_name)
            except TemplateNotFound as exc:
                raise FileNotFoundError(f"Template not found: {template_path}") from exc
    else:
        # Choose a sensible default template for the kind
        template_name = DEFAULT_KIND_TO_TEMPLATE.get(kind)
        if not template_name:
            raise FileNotFoundError(f"No template specified for kind: {kind}")
        try:
            template = env.get_template(template_name)
        except TemplateNotFound as exc:
            raise FileNotFoundError(f"Template not found: {template_name}") from exc

    # Render the template. StrictUndefined will raise UndefinedError on missing keys.
    rendered = template.render(**context)

    # Optionally pass the rendered text to OpenAI for polishing when enabled.
    enabled = os.getenv("OPENAI_ENABLED", "false").lower() in ("1", "true", "yes")
    if not enabled:
        return rendered

    api_key = os.getenv("OPENAI_API_KEY")
    dry_run = api_key is None
    adapter = OpenAIAdapter(api_key=api_key, client=None, dry_run=dry_run)
    req = ScriptRequest(
        prompt=rendered,
        audience=context.get("audience"),
        tone=context.get("tone", "energetic"),
        max_output_tokens=512,
        temperature=float(context.get("temperature", 0.7)),
    )
    return adapter.generate_script(req)
