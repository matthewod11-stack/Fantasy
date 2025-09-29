"""
CLI for metrics ingestion and simple reporting.
"""
from typing import Optional
import typer
import json
from apps.metrics.storage import upsert_post, list_posts_by_date
from apps.metrics.schemas import PostRecord, DailySummary

app = typer.Typer(name="ff-metrics")


@app.command()
def record_post(
    post_id: str = typer.Option(..., help="Unique post id"),
    date: str = typer.Option(..., help="YYYY-MM-DD"),
    player: Optional[str] = typer.Option(None),
    type: Optional[str] = typer.Option(None),
    views: Optional[int] = typer.Option(0),
    likes: Optional[int] = typer.Option(0),
    comments: Optional[int] = typer.Option(0),
    shares: Optional[int] = typer.Option(0),
    retention_3s: Optional[float] = typer.Option(0.0),
    retention_10s: Optional[float] = typer.Option(0.0),
    ctr: Optional[float] = typer.Option(0.0),
    email_signups: Optional[int] = typer.Option(0),
    utm_campaign: Optional[str] = typer.Option(None),
    week: Optional[int] = typer.Option(None),
    json_record: Optional[str] = typer.Option(None, help="JSON payload instead of flags"),
):
    """Record or update a post's metrics.

    Accepts either individual flags or a JSON record via --json-record.
    """
    if json_record:
        payload = json.loads(json_record)
        record = PostRecord(**payload)
    else:
        record = PostRecord(
            post_id=post_id,
            date=date,
            player=player,
            type=type,
            views=views,
            likes=likes,
            comments=comments,
            shares=shares,
            retention_3s=retention_3s,
            retention_10s=retention_10s,
            ctr=ctr,
            email_signups=email_signups,
            utm_campaign=utm_campaign,
            week=week,
        )

    upsert_post(record)
    typer.echo(f"Recorded post {record.post_id}")


@app.command()
def daily_summary(date: str = typer.Option(..., help="YYYY-MM-DD")):
    """Aggregate posts for a date and output a DailySummary."""
    posts = list_posts_by_date(date)
    total_posts = len(posts)
    total_views = sum(p.views or 0 for p in posts)
    total_likes = sum(p.likes or 0 for p in posts)
    total_comments = sum(p.comments or 0 for p in posts)
    total_shares = sum(p.shares or 0 for p in posts)
    total_email_signups = sum(p.email_signups or 0 for p in posts)

    summary = DailySummary(
        date=date,
        total_posts=total_posts,
        total_views=total_views,
        total_likes=total_likes,
        total_comments=total_comments,
        total_shares=total_shares,
        total_email_signups=total_email_signups,
    )
    # Write summary to CSV/console — for simplicity, print JSON
    typer.echo(summary.json())


@app.command()
def export_week(week: int = typer.Option(...), out: str = typer.Option(".metrics/manifest_week.csv")):
    """Export posts for a given week into a CSV manifest for review/scheduling."""
    # Simple approach: iterate all posts and filter by week
    from apps.metrics.storage import _read_all
    rows = _read_all()
    filtered = [r for r in rows if r.get("week") == str(week)]
    # Write to out
    import csv
    import os
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if filtered:
        keys = list(filtered[0].keys())
        with open(out, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for r in filtered:
                writer.writerow(r)
    else:
        # create empty file with header
        with open(out, "w", newline="", encoding="utf-8") as f:
            f.write("post_id,date,player,type,views,likes,comments,shares,retention_3s,retention_10s,ctr,email_signups,utm_campaign,week\n")

    typer.echo(f"Wrote manifest to {out}")


if __name__ == "__main__":
    app()
