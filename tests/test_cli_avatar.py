"""
Tests for the avatar CLI.

Tests the avatar CLI's rendering functionality with DRY_RUN=True.
"""
import os
import json
import tempfile
from pathlib import Path
from typer.testing import CliRunner
from apps.cli.avatar import app

runner = CliRunner()


def test_avatar_render_dry_run(monkeypatch):
    """Test avatar render command in dry-run mode."""
    # Set DRY_RUN environment variable
    monkeypatch.setenv("DRY_RUN", "true")
    
    # Create a temporary script file
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.txt', delete=False) as tmp:
        tmp.write("This is a test script for avatar rendering.")
    
    try:
        # Create temporary output directory
        with tempfile.TemporaryDirectory() as outdir:
            # Run the CLI command
            result = runner.invoke(
                app, 
                [
                    "render",
                    "--week", "5", 
                    "--kind", "start-sit",
                    "--script", tmp.name,
                    "--avatar-id", "test-avatar-id",
                    "--voice-id", "test-voice-id",
                    "--outdir", outdir
                ]
            )
            
            # Check command succeeded
            assert result.exit_code == 0, f"CLI failed with output: {result.stdout}"
            
            # Check output directory structure was created
            output_path = Path(outdir) / "week-5" / "start-sit" / "avatar"
            assert output_path.exists(), "Output directory structure not created"
            
            # Check render.json was created
            json_path = output_path / "render.json"
            assert json_path.exists(), "render.json not created"
            
            # Check video.mp4 placeholder was created
            video_path = output_path / "video.mp4"
            assert video_path.exists(), "video.mp4 not created"
            
            # In dry run mode, the video file should be empty
            assert video_path.stat().st_size == 0, "Dry run should create empty video file"
            
            # Verify render.json content
            with open(json_path, 'r') as f:
                render_data = json.load(f)
                assert "video_id" in render_data, "render.json missing video_id"
                assert "avatar_id" in render_data, "render.json missing avatar_id"
                assert render_data["avatar_id"] == "test-avatar-id"
            
            # Check expected output messages
            assert "Rendering avatar video" in result.stdout
            assert "Created dry-run video placeholder" in result.stdout
            assert "Avatar render complete!" in result.stdout
    
    finally:
        # Clean up temporary script file
        os.unlink(tmp.name)


def test_avatar_render_invalid_week():
    """Test CLI validation for invalid week number."""
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.txt', delete=False) as tmp:
        tmp.write("Test script")
    
    try:
        result = runner.invoke(
            app, 
            [
                "render",
                "--week", "25",  # Invalid week number
                "--kind", "start-sit",
                "--script", tmp.name
            ]
        )
        
        # Should fail with validation error
        assert result.exit_code != 0
        assert "Week must be between 1 and 18" in result.stdout
    
    finally:
        os.unlink(tmp.name)


def test_avatar_render_missing_script():
    """Test CLI validation for missing script file."""
    nonexistent_file = "/path/to/nonexistent/script.txt"
    
    result = runner.invoke(
        app, 
        [
            "render",
            "--week", "5",
            "--kind", "start-sit",
            "--script", nonexistent_file
        ]
    )
    
    # Should fail with file not found error
    assert result.exit_code != 0
    assert "Script file not found" in result.stdout