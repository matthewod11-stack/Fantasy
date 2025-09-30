from pathlib import Path
import os

from packages.generation.template_resolver import resolve_template, TEMPLATE_ROOT, LEGACY_TEMPLATE_ROOT


def test_resolve_template_prefers_canonical(tmp_path, monkeypatch):
    # Create canonical and legacy files
    can_dir = tmp_path / "templates" / "script_templates"
    leg_dir = tmp_path / "prompts" / "templates"
    can_dir.mkdir(parents=True)
    leg_dir.mkdir(parents=True)

    # Write files
    kind = "sample-kind"
    can_file = can_dir / f"{kind}.md"
    leg_file = leg_dir / f"{kind}.md"
    can_file.write_text("canonical")
    leg_file.write_text("legacy")

    # Monkeypatch module paths to point at our tmp dirs
    monkeypatch.setattr("packages.generation.template_resolver.TEMPLATE_ROOT", can_dir)
    monkeypatch.setattr("packages.generation.template_resolver.LEGACY_TEMPLATE_ROOT", leg_dir)

    p = resolve_template(kind)
    assert p is not None
    assert Path(p).read_text() == "canonical"


def test_resolve_template_falls_back_to_legacy(tmp_path, monkeypatch):
    can_dir = tmp_path / "templates" / "script_templates"
    leg_dir = tmp_path / "prompts" / "templates"
    can_dir.mkdir(parents=True)
    leg_dir.mkdir(parents=True)

    kind = "other-kind"
    leg_file = leg_dir / f"{kind}.md"
    leg_file.write_text("legacy-only")

    monkeypatch.setattr("packages.generation.template_resolver.TEMPLATE_ROOT", can_dir)
    monkeypatch.setattr("packages.generation.template_resolver.LEGACY_TEMPLATE_ROOT", leg_dir)

    p = resolve_template(kind)
    assert p is not None
    assert Path(p).read_text() == "legacy-only"
