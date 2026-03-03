"""
PM Agent — CLI tool

Usage (auto problem-statement selection):
    python pm_agent.py --figma <url>

Usage (manual goal):
    python pm_agent.py --figma <url> --goal "Add mobile checkout flow"

Options:
    --model qwen2.5:14b     use a bigger model
    --out   ./docs/prds     custom output folder
    --no-open               skip auto-opening HTML in browser
"""
import os
import sys
import argparse
import webbrowser
from pathlib import Path
from dotenv import load_dotenv
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
  python pm_agent.py --figma "https://figma.com/design/abc/App?node-id=1-2"
  python pm_agent.py --figma <url> --goal "Add mobile checkout" --model qwen2.5:14b
  python pm_agent.py --figma <url> --out ./docs/prds
        """,
    )
    parser.add_argument("--figma", required=True, metavar="URL",
                        help="Figma design URL with node-id")
    parser.add_argument("--goal", default=None, metavar="TEXT",
                        help="(Optional) Skip problem selection and use this goal directly")
    parser.add_argument("--model", default=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
                        metavar="MODEL", help="Ollama model (default: qwen2.5:7b)")
    parser.add_argument("--host", default=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
                        metavar="URL", help="Ollama host (default: http://localhost:11434)")
    parser.add_argument("--out", default="./output", metavar="DIR",
                        help="Output directory (default: ./output)")
    parser.add_argument("--no-open", action="store_true",
                        help="Do not auto-open HTML report in browser")
    parser.add_argument("--fast", action="store_true",
                        help="Skip problem statement selection, auto-detect goal and generate PRD immediately")
    return parser.parse_args()


def check_env() -> tuple[str, str]:
    token = os.getenv("FIGMA_ACCESS_TOKEN", "")
    if not token or token == "your_figma_token_here":
        return "", (
            "FIGMA_ACCESS_TOKEN is not set.\n"
            "1. Go to figma.com → Settings → Security → Generate new token\n"
            "2. Add it to .env: FIGMA_ACCESS_TOKEN=your_token"
        )
    return token, ""


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
        f"[bold cyan]PM Agent[/bold cyan]  —  Figma → PRD\n\n"
        f"[dim]Figma:[/dim]  {args.figma[:70]}{'...' if len(args.figma) > 70 else ''}\n"
        f"[dim]Model:[/dim] {args.model}\n"
        f"[dim]Out:[/dim]   {args.out}",
        border_style="cyan",
    ))

    figma_token, err = check_env()
    if err:
        console.print(f"\n[red]Setup required:[/red]\n{err}")
        sys.exit(1)

    from connectors.figma_connector import FigmaConnector
    from ollama_client import OllamaClient
    from writers import write_markdown, write_json, write_html

    figma = FigmaConnector(figma_token)
    llm = OllamaClient(host=args.host, model=args.model)
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
            design_ctx = figma.extract_design_context(args.figma)
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
        # Auto-detect goal from file name — no LLM call needed
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
        md_path   = write_markdown(prd, output_dir, args.figma)
        json_path = write_json(prd, output_dir)
        html_path = write_html(prd, output_dir, args.figma)
        p.update(t, description="[green]✓[/green] Files saved")
        p.stop_task(t)

    print_summary(prd, md_path, json_path, html_path)

    if not args.no_open:
        webbrowser.open(html_path.resolve().as_uri())
        console.print("[dim]HTML report opened in browser.[/dim]")


if __name__ == "__main__":
    main()
