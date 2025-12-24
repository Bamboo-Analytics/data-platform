"""
Command-line interface for the data platform pipeline.

Provides commands for running daily/quarterly ingestion, backfills, etc.
"""

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional
import sys
import logging

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from data_platform.pipeline import PipelineRunner
from data_platform.config import get_config
from data_platform.connectors.base import ConnectorFactory

app = typer.Typer(
    name="data-platform",
    help="Cross-asset data ingestion pipeline",
    add_completion=False,
)

console = Console()


def setup_logging(log_level: str = "INFO", log_format: str = "text") -> None:
    """Setup logging configuration."""
    level = getattr(logging, log_level.upper())

    if log_format == "json":
        # JSON structured logging
        import json_log_formatter
        
        formatter = json_log_formatter.JSONFormatter()
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        
        logging.basicConfig(
            level=level,
            handlers=[handler],
        )
    else:
        # Rich text logging
        logging.basicConfig(
            level=level,
            format="%(message)s",
            datefmt="[%X]",
            handlers=[RichHandler(rich_tracebacks=True, console=console)],
        )


@app.command()
def daily(
    start_date: str = typer.Option(
        ..., "--start-date", "-s", help="Start date (YYYY-MM-DD)"
    ),
    end_date: Optional[str] = typer.Option(
        None, "--end-date", "-e", help="End date (YYYY-MM-DD), default: today"
    ),
    tickers: Optional[str] = typer.Option(
        None, "--tickers", "-t", help="Comma-separated list of tickers (default: all)"
    ),
    log_level: str = typer.Option(
        "INFO", "--log-level", "-l", help="Log level"
    ),
) -> None:
    """
    Run daily ingestion pipeline.
    
    Example:
        data-platform daily --start-date 2024-01-01 --end-date 2024-01-31
    """
    setup_logging(log_level)

    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = (
            datetime.strptime(end_date, "%Y-%m-%d").date()
            if end_date
            else date.today()
        )

        ticker_list = tickers.split(",") if tickers else None

        console.print(
            f"[bold blue]Running daily ingestion:[/bold blue] {start} to {end}"
        )

        runner = PipelineRunner()
        result = runner.run_daily(start, end, ticker_list)

        # Display results
        table = Table(title="Ingestion Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Success", str(result.success))
        table.add_row("Records Extracted", str(result.records_extracted))
        table.add_row("Records Transformed", str(result.records_transformed))
        table.add_row("Records Validated", str(result.records_validated))
        table.add_row("Records Loaded", str(result.records_loaded))
        table.add_row("Errors", str(len(result.errors)))
        table.add_row("Warnings", str(len(result.warnings)))

        console.print(table)

        if result.errors:
            console.print("\n[bold red]Errors:[/bold red]")
            for error in result.errors:
                console.print(f"  ❌ {error}")

        if result.warnings:
            console.print("\n[bold yellow]Warnings:[/bold yellow]")
            for warning in result.warnings:
                console.print(f"  ⚠️  {warning}")

        if not result.success:
            raise typer.Exit(code=1)

    except ValueError as e:
        console.print(f"[bold red]Invalid date format:[/bold red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[bold red]Pipeline failed:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def backfill(
    start_date: str = typer.Option(
        ..., "--start-date", "-s", help="Start date (YYYY-MM-DD)"
    ),
    end_date: str = typer.Option(
        ..., "--end-date", "-e", help="End date (YYYY-MM-DD)"
    ),
    chunk_size: int = typer.Option(
        365, "--chunk-size", "-c", help="Chunk size in days"
    ),
    tickers: Optional[str] = typer.Option(
        None, "--tickers", "-t", help="Comma-separated list of tickers"
    ),
    log_level: str = typer.Option(
        "INFO", "--log-level", "-l", help="Log level"
    ),
) -> None:
    """
    Run backfill for historical data.
    
    Example:
        data-platform backfill --start-date 2020-01-01 --end-date 2024-12-31
    """
    setup_logging(log_level)

    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
        ticker_list = tickers.split(",") if tickers else None

        console.print(
            f"[bold blue]Running backfill:[/bold blue] {start} to {end} "
            f"in {chunk_size}-day chunks"
        )

        runner = PipelineRunner()
        results = runner.run_backfill(start, end, chunk_size, ticker_list)

        # Display summary
        total_loaded = sum(r.records_loaded for r in results)
        successful_chunks = sum(1 for r in results if r.success)

        table = Table(title="Backfill Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Total Chunks", str(len(results)))
        table.add_row("Successful Chunks", str(successful_chunks))
        table.add_row("Failed Chunks", str(len(results) - successful_chunks))
        table.add_row("Total Records Loaded", str(total_loaded))

        console.print(table)

        if successful_chunks < len(results):
            raise typer.Exit(code=1)

    except ValueError as e:
        console.print(f"[bold red]Invalid date format:[/bold red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[bold red]Backfill failed:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def init_db(
    log_level: str = typer.Option("INFO", "--log-level", "-l", help="Log level"),
) -> None:
    """
    Initialize ClickHouse database tables.
    
    Creates daily_features and quarterly_features tables.
    """
    setup_logging(log_level)

    try:
        console.print("[bold blue]Initializing database...[/bold blue]")

        runner = PipelineRunner()
        runner.initialize_database()

        console.print("[bold green]✓ Database initialized successfully[/bold green]")

    except Exception as e:
        console.print(f"[bold red]Database initialization failed:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def list_sources() -> None:
    """List all configured data sources."""
    config = get_config()
    sources = config.get_enabled_daily_sources()

    table = Table(title="Configured Data Sources")
    table.add_column("Name", style="cyan")
    table.add_column("Ticker", style="green")
    table.add_column("Asset Class", style="yellow")
    table.add_column("Vendor", style="magenta")
    table.add_column("Enabled", style="blue")

    for source in sources:
        table.add_row(
            source["name"],
            source["ticker"],
            source["asset_class"],
            source["vendor"],
            "✓" if source.get("enabled", True) else "✗",
        )

    console.print(table)
    console.print(f"\n[bold]Total sources:[/bold] {len(sources)}")


@app.command()
def list_connectors() -> None:
    """List all registered connectors."""
    registered = ConnectorFactory.list_registered()

    table = Table(title="Registered Connectors")
    table.add_column("Vendor", style="cyan")
    table.add_column("Asset Class", style="green")

    for vendor, asset_class in registered:
        table.add_row(vendor.value, asset_class.value)

    console.print(table)
    console.print(f"\n[bold]Total connectors:[/bold] {len(registered)}")


@app.command()
def version() -> None:
    """Show version information."""
    console.print("[bold]Data Platform Pipeline[/bold]")
    console.print("Version: 0.1.0")
    console.print("Python: " + sys.version.split()[0])


if __name__ == "__main__":
    app()
