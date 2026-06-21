"""Main CLI entry point."""

import click
from .commands import audit, optimize, dashboard, snapshot


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """AIEO - AI Engine Optimization CLI tool."""
    pass


# Register commands
cli.add_command(audit.audit)
cli.add_command(optimize.optimize)
cli.add_command(dashboard.dashboard)
cli.add_command(snapshot.crawl)


if __name__ == "__main__":
    cli()
