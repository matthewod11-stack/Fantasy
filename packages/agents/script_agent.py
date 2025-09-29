"""
Script Agent for Fantasy TikTok Engine.

Renders content templates with player context data to generate TikTok scripts.
TODO: Enhance template system as specified in PRD sections:
- Dynamic template selection based on player performance trends
- A/B testing framework for different content variations
- Personalization based on user preferences and engagement history
"""

import os
from typing import Dict, Any


def render_script(kind: str, context: Dict[str, Any], template_path: str) -> str:
    """
    Render a content script using template and context data.
    
    Args:
        kind: Content type ("start-sit", "waiver-wire", etc.)
        context: Player and game context data
        template_path: Path to template file
        
    Returns:
        Rendered script content ready for TikTok
        
    TODO: Enhance per PRD requirements:
    - Add template versioning and A/B testing capabilities
    - Implement dynamic template selection based on player trends
    - Add content personalization based on user engagement data
    - Include automated hashtag optimization
    - Add content length optimization for TikTok algorithm
    """
    
    try:
        # Prefer canonical template path; if not present, try legacy prompts/templates
        if not os.path.exists(template_path):
            # Try swapping to legacy location if available
            legacy_path = template_path.replace("templates/script_templates/", "prompts/templates/")
            if os.path.exists(legacy_path):
                template_path = legacy_path

        # Load template content
        if not os.path.exists(template_path):
            print(f"⚠️  [Script Agent] Template not found: {template_path}")
            # Return a basic fallback template
            return _get_fallback_template(kind, context)

        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()

        # Render template with context data
        try:
            rendered_script = template_content.format(**context)
            print(f"📝 [Script Agent] Rendered {kind} script ({len(rendered_script)} chars)")
            return rendered_script

        except KeyError as e:
            print(f"⚠️  [Script Agent] Missing template variable: {e}")
            # Try to render with available variables
            return _safe_render_template(template_content, context)

    except Exception as e:
        print(f"❌ [Script Agent] Error rendering template: {e}")
        return _get_fallback_template(kind, context)


def _get_fallback_template(kind: str, context: Dict[str, Any]) -> str:
    """Generate a basic fallback template when main template fails."""
    
    player = context.get("player", "Player")
    week = context.get("week", "X")
    
    if kind == "start-sit":
        return f"""🔥 **WEEK {week} START/SIT ALERT** 🔥

Should you start **{player}** this week?

My take: {context.get("recommendation", "Analyze carefully")}

Confidence: {context.get("confidence", 5)}/10

What do YOU think? Drop your lineup questions below! 👇

#FantasyFootball #NFL #Week{week} #StartSit"""
    
    elif kind == "waiver-wire":
        return f"""🚨 **WAIVER WIRE ALERT** 🚨

**{player}** needs to be on your radar!

Rostered: {context.get("rostered_pct", "XX")}%

Don't let someone else snag this gem! Hit that waiver wire! 🏃‍♂️💨

#WaiverWire #FantasyFootball #Week{week}"""
    
    else:
        return f"""🏈 **FANTASY ALERT** 🏈

**{player}** - Week {week}

{context.get("summary", "Check out this fantasy football insight!")}

#FantasyFootball #NFL #Week{week}"""


def _safe_render_template(template: str, context: Dict[str, Any]) -> str:
    """Safely render template, skipping missing variables."""
    
    # Simple approach: try to replace what we can
    try:
        # Create a safe context that provides empty strings for missing keys
        from string import Formatter
        
        class SafeFormatter(Formatter):
            def get_value(self, key, args, kwargs):
                # Formatter.get_value expects (self, key, args, kwargs)
                if isinstance(key, str):
                    try:
                        return kwargs[key]
                    except KeyError:
                        return f"{{{key}}}"  # Keep placeholder for missing keys
                else:
                    return super().get_value(key, args, kwargs)
        
        formatter = SafeFormatter()
        return formatter.format(template, **context)
        
    except Exception:
        # Last resort: return template as-is
        return template