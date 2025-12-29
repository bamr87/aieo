"""Dashboard command."""
import click
import httpx
import json
import sys


@click.command()
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.option("--api-key", envvar="AIEO_API_KEY", help="API key (or set AIEO_API_KEY env var)")
@click.option("--api-url", default="http://localhost:8000/api/v1", help="API base URL")
def dashboard(output_json, api_key, api_url):
    """View citation dashboard data."""
    # Make API request
    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{api_url}/aieo/dashboard",
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
    
    # Output results
    if output_json:
        click.echo(json.dumps(result, indent=2))
    else:
        click.echo("Citation Dashboard\n")
        
        by_engine = result.get("by_engine", {})
        if by_engine:
            click.echo("Citations by Engine:")
            for engine, count in by_engine.items():
                click.echo(f"  {engine}: {count}")
        
        top_cited = result.get("top_cited_pages", [])
        if top_cited:
            click.echo("\nTop Cited Pages:")
            for i, page in enumerate(top_cited[:10], 1):
                url = page.get("url", "unknown")
                count = page.get("count", 0)
                click.echo(f"  {i}. {url} ({count} citations)")


