"""
PM Agent — CLI tool

Usage:
    python pm_agent.py

The tool will prompt for your Figma URL interactively.

Options:
    --goal "text"       skip problem selection, use this goal directly
    --model qwen2.5:14b use a bigger model
    --out   ./docs/prds custom output folder
    --fast              auto-detect goal, skip selection
    --no-open           skip auto-opening HTML in browser
"""
import os
import sys
import argparse
import webbrowser
from pathlib import Path
from dotenv import load_dotenv, set_key
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.rule import Rule
from rich.prompt import Prompt
from rich import box

load_dotenv()
console = Console()


def parse_args():
    parser = argparse.ArgumentParser(
        prog="pm-agent",
        description="Generate a PRD from a Figma design using a local LLM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pm_agent.py
  python pm_agent.py --model qwen2.5:14b
  python pm_agent.py --out ./docs/prds
        """,
    )
    parser.add_argument("--goal", default=None, metavar="TEXT",
                        help="(Optional) Skip problem selection and use this goal directly")
    parser.add_argument("--model", default=os.getenv("OLLAMA_MODEL", None),
                        metavar="MODEL", help="Ollama model (default: auto-detect fastest installed)")
    parser.add_argument("--host", default=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
                        metavar="URL", help="Ollama host (default: http://localhost:11434)")
    parser.add_argument("--out", default="./output", metavar="DIR",
                        help="Output directory (default: ./output)")
    parser.add_argument("--no-open", action="store_true",
                        help="Do not auto-open HTML report in browser")
    parser.add_argument("--fast", action="store_true",
                        help="Skip problem statement selection, auto-detect goal and generate PRD immediately")
    return parser.parse_args()


def prompt_figma_url() -> str:
    """Prompt user to enter their Figma design URL."""
    console.print()
    console.print(Rule("[bold cyan]Step 1 — Figma Design URL[/bold cyan]"))
    console.print(
        "\n[dim]Paste the URL of your Figma design (must include node-id for a specific frame).[/dim]\n"
        "[dim]Example: https://figma.com/design/ABC123/App?node-id=1-2[/dim]\n"
    )
    while True:
        url = Prompt.ask("[bold cyan]Figma URL[/bold cyan]").strip()
        if url.startswith("http") and "figma.com" in url:
            return url
        console.print("[red]Invalid URL — must be a figma.com link. Try again.[/red]")


def prompt_figma_token() -> str:
    """Interactively ask the user for their Figma token and save it to .env."""
    console.print()
    console.print(Panel(
        "[bold yellow]Figma Access Token Required[/bold yellow]\n\n"
        "1. Go to [cyan]figma.com[/cyan] → [dim]Account Settings → Security[/dim]\n"
        "2. Click [bold]Generate new token[/bold]\n"
        "3. Paste it below\n\n"
        "[dim]Your token will be saved to .env so you only need to do this once.[/dim]",
        border_style="yellow",
    ))
    token = Prompt.ask("\n[bold cyan]Paste your Figma token[/bold cyan]").strip()
    if not token:
        console.print("[red]No token entered. Exiting.[/red]")
        sys.exit(1)
    env_file = Path(".env")
    if not env_file.exists():
        env_file.write_text("", encoding="utf-8")
    set_key(str(env_file), "FIGMA_ACCESS_TOKEN", token)
    os.environ["FIGMA_ACCESS_TOKEN"] = token
    console.print("[green]✓[/green] Token saved to .env\n")
    return token


def get_figma_token() -> str:
    token = os.getenv("FIGMA_ACCESS_TOKEN", "")
    if not token or token == "your_figma_token_here":
        return prompt_figma_token()
    return token


def show_problem_choices(suggestions) -> str:
    """
    Display 3 problem statement options and return the chosen statement text.
    """
    angle_colors = {"UX": "magenta", "Business": "green", "Technical": "blue"}

    console.print()
    console.print(Rule("[bold yellow]Choose a Problem Statement[/bold yellow]"))
    console.print()

    for i, opt in enumerate(suggestions.suggestions, 1):
        color = angle_colors.get(opt.angle, "white")
        console.print(Panel(
            f"[dim]{opt.statement}[/dim]",
            title=f"[bold]{i}. {opt.title}[/bold]  [{color}][ {opt.angle} ][/{color}]",
            border_style=color,
            padding=(1, 2),
        ))
        console.print()

    choice = Prompt.ask(
        "[bold cyan]Pick one[/bold cyan]",
        choices=["1", "2", "3"],
        default="1",
    )
    selected = suggestions.suggestions[int(choice) - 1]
    console.print(
        f"\n[green]✓[/green] Selected: [bold]{selected.title}[/bold]\n"
    )
    return selected.statement


def print_summary(prd, md_path, json_path, html_path):
    console.print()
    console.print(Rule("[bold green]Done[/bold green]"))
    console.print()

    table = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
    table.add_column("Label", style="dim")
    table.add_column("Value", style="cyan")
    table.add_row("Feature", prd.feature_name)
    table.add_row("Goals", str(len(prd.goals)))
    table.add_row("User Stories", str(len(prd.structured_stories)))
    table.add_row("Acceptance Criteria", str(len(prd.acceptance_criteria)))
    table.add_row("Edge Cases", str(len(prd.edge_cases)))
    table.add_row("Open Questions", str(len(prd.open_questions)))
    console.print(table)

    console.print()
    console.print(f"  [green]→[/green] [bold]Markdown:[/bold] {md_path}")
    console.print(f"  [green]→[/green] [bold]JSON:[/bold]     {json_path}")
    console.print(f"  [green]→[/green] [bold]HTML:[/bold]     {html_path}")
    console.print()


def main():
    args = parse_args()

    console.print(Panel(
        "[bold cyan]PM Agent[/bold cyan]  —  Figma → PRD\n\n"
        "[dim]Enter your Figma link when prompted and the tool will:[/dim]\n"
        "  [dim]1.[/dim] Read your design\n"
        "  [dim]2.[/dim] Suggest 3 problem statements\n"
        "  [dim]3.[/dim] Generate a full PRD based on your choice",
        border_style="cyan",
    ))

    figma_token = get_figma_token()
    figma_url = prompt_figma_url()

    console.print()
    console.print(Panel(
        f"[dim]Figma:[/dim]  {figma_url[:70]}{'...' if len(figma_url) > 70 else ''}\n"
        f"[dim]Out:[/dim]   {args.out}",
        border_style="dim",
    ))

    from connectors.figma_connector import FigmaConnector
    from ollama_client import OllamaClient
    from writers import write_markdown, write_json, write_html

    figma = FigmaConnector(figma_token)
    llm = OllamaClient(host=args.host, model=args.model or None)
    output_dir = Path(args.out)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── Step 1: Check Ollama ──────────────────────────────────────────────────
    with Progress(SpinnerColumn(), TextColumn("{task.description}"),
                  console=console, transient=False) as p:
        t = p.add_task("Connecting to Ollama...", total=None)
        ready, msg = llm.check_connection()
        if not ready:
            p.stop()
            console.print(f"\n[red]Ollama not ready:[/red] {msg}")
            sys.exit(1)
        p.update(t, description=f"[green]✓[/green] Ollama ready ({args.model})")
        p.stop_task(t)

    # ── Step 2: Fetch Figma ───────────────────────────────────────────────────
    with Progress(SpinnerColumn(), TextColumn("{task.description}"),
                  console=console, transient=False) as p:
        t = p.add_task("Fetching Figma wireframe...", total=None)
        try:
            design_ctx = figma.extract_design_context(figma_url)
            design_text = figma.format_for_prompt(design_ctx)
        except Exception as e:
            p.stop()
            console.print(f"\n[red]Figma error:[/red] {e}")
            sys.exit(1)
        p.update(t, description=f"[green]✓[/green] Figma: {design_ctx['target_name']}  ({len(design_ctx['screens'])} screen(s) found)")
        p.stop_task(t)

    # ── Step 3: Problem statement — auto-suggest or use --goal ───────────────
    if args.goal:
        feature_goal = args.goal
        console.print(f"\n[green]✓[/green] Using provided goal: {feature_goal}\n")
    elif args.fast:
        feature_goal = f"Build the core user experience for {design_ctx['file_name']}"
        console.print(f"\n[green]✓[/green] Fast mode — auto goal: [dim]{feature_goal}[/dim]\n")
    else:
        with Progress(SpinnerColumn(), TextColumn("{task.description}"),
                      console=console, transient=False) as p:
            t = p.add_task("Analysing design — generating 3 problem statements...", total=None)
            try:
                suggestions = llm.suggest_problem_statements(design_text)
            except Exception as e:
                p.stop()
                console.print(f"\n[red]LLM error during suggestion:[/red] {e}")
                sys.exit(1)
            p.update(t, description="[green]✓[/green] 3 problem statements ready")
            p.stop_task(t)

        feature_goal = show_problem_choices(suggestions)

    # ── Step 4: Generate full PRD ─────────────────────────────────────────────
    with Progress(SpinnerColumn(), TextColumn("{task.description}"),
                  console=console, transient=False) as p:
        t = p.add_task(f"Generating PRD with {args.model}...", total=None)
        try:
            prd = llm.generate_prd(design_context=design_text, feature_goal=feature_goal)
        except Exception as e:
            p.stop()
            console.print(f"\n[red]LLM error:[/red] {e}")
            sys.exit(1)
        p.update(t, description=f"[green]✓[/green] PRD generated: {prd.feature_name}")
        p.stop_task(t)

    # ── Step 5: Write output files ────────────────────────────────────────────
    with Progress(SpinnerColumn(), TextColumn("{task.description}"),
                  console=console, transient=False) as p:
        t = p.add_task("Writing output files...", total=None)
        md_path   = write_markdown(prd, output_dir, figma_url)
        json_path = write_json(prd, output_dir)
        html_path = write_html(prd, output_dir, figma_url)
        p.update(t, description="[green]✓[/green] Files saved")
        p.stop_task(t)

    print_summary(prd, md_path, json_path, html_path)

    if not args.no_open:
        webbrowser.open(html_path.resolve().as_uri())
        console.print("[dim]HTML report opened in browser.[/dim]")


if __name__ == "__main__":
    main()
