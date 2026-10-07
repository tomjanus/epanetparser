"""Shared presentation helpers for demonstration examples."""

from rich.console import Console

def render_section(
        console: Console, 
        number: int, 
        title: str, 
        description: str
    ) -> None:
    """Render a consistently styled section header."""
    console.print()
    console.print(f"[bold cyan]{number}. {title}[/bold cyan]")
    console.print(f"[dim]{description}[/dim]")
    console.print()

