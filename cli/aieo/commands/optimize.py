"""Optimize command."""
import click
import httpx
import json
import sys
from pathlib import Path


@click.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Output file (default: stdout)")
@click.option("--style", type=click.Choice(["preserve", "aggressive"]), default="preserve", help="Optimization style")
@click.option("--diff", is_flag=True, help="Show diff view")
@click.option("--api-key", envvar="AIEO_API_KEY", help="API key (or set AIEO_API_KEY env var)")
@click.option("--api-url", default="http://localhost:8000/api/v1", help="API base URL")
def optimize(file, output, style, diff, api_key, api_url):
    """Optimize content with AIEO patterns.
    
    FILE is the path to the markdown file to optimize.
    """
    # Read input file
    try:
        content = Path(file).read_text()
    except Exception as e:
        click.echo(f"Error reading file: {e}", err=True)
        sys.exit(1)
    
    # Prepare request
    request_data = {
        "content": content,
        "style": style,
    }
    
    # Make API request
    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key
    
    click.echo("Optimizing content...", err=True)
    
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{api_url}/aieo/optimize",
                json=request_data,
                headers=headers,
            )
            response.raise_for_status()
            result = response.json()
    except httpx.HTTPStatusError as e:
        error_data = e.response.json() if e.response.headers.get("content-type", "").startswith("application/json") else {}
        error_msg = error_data.get("error", {}).get("message", str(e))
        click.echo(f"Error: {error_msg}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    
    # Show score improvement
    score_before = result.get("score_before", 0)
    score_after = result.get("score_after", 0)
    uplift = result.get("uplift", 0)
    
    click.echo(f"\nScore: {score_before} → {score_after} (+{uplift} points)", err=True)
    
    # Show diff if requested
    if diff:
        changes = result.get("changes", [])
        if changes:
            click.echo("\nChanges:", err=True)
            for change in changes:
                click.echo(f"  [{change.get('type', 'unknown')}] {change.get('description', '')}", err=True)
    
    # Output optimized content
    optimized_content = result.get("optimized_content", "")
    
    if output:
        try:
            Path(output).write_text(optimized_content)
            click.echo(f"\nOptimized content written to: {output}", err=True)
        except Exception as e:
            click.echo(f"Error writing output file: {e}", err=True)
            sys.exit(1)
    else:
        click.echo(optimized_content)


