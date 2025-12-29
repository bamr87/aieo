"""Audit command."""
import click
import httpx
import json
import sys
from pathlib import Path


@click.command()
@click.argument("input", required=False)
@click.option("--file", "-f", type=click.Path(exists=True), help="Path to markdown file")
@click.option("--url", "-u", help="URL to audit")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.option("--api-key", envvar="AIEO_API_KEY", help="API key (or set AIEO_API_KEY env var)")
@click.option("--api-url", default="http://localhost:8000/api/v1", help="API base URL")
def audit(input, file, url, output_json, api_key, api_url):
    """Audit content for AIEO score.
    
    INPUT can be a URL or path to a markdown file.
    Alternatively, use --file or --url options.
    """
    # Determine content source
    content = None
    content_url = None
    
    if file:
        try:
            content = Path(file).read_text()
            content_format = "markdown"
        except Exception as e:
            click.echo(f"Error reading file: {e}", err=True)
            sys.exit(1)
    elif url:
        content_url = url
    elif input:
        # Try to determine if it's a URL or file path
        if input.startswith(("http://", "https://")):
            content_url = input
        else:
            try:
                content = Path(input).read_text()
                content_format = "markdown"
            except Exception:
                click.echo(f"Error: '{input}' is not a valid file or URL", err=True)
                sys.exit(1)
    else:
        click.echo("Error: Please provide a URL, file path, or use --file/--url", err=True)
        sys.exit(1)
    
    # Prepare request
    request_data = {}
    if content_url:
        request_data["url"] = content_url
    else:
        request_data["content"] = content
        request_data["format"] = content_format
    
    # Make API request
    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key
    
    click.echo("Auditing content...", err=True)
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{api_url}/aieo/audit",
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
    
    # Output results
    if output_json:
        click.echo(json.dumps(result, indent=2))
    else:
        click.echo(f"\nScore: {result.get('score', 0)}/100")
        click.echo(f"Grade: {result.get('grade', 'F')}")
        
        gaps = result.get("gaps", [])
        if gaps:
            click.echo(f"\nTop {min(5, len(gaps))} Gaps:")
            for i, gap in enumerate(gaps[:5], 1):
                click.echo(f"  {i}. [{gap.get('category', 'unknown')}] {gap.get('description', '')}")
                click.echo(f"     Severity: {gap.get('severity', 'unknown')}")
        else:
            click.echo("\nNo gaps found!")


