"""
PM Agent — CLI tool

Just run:
    python pm_agent.py

Or with optional flags:
    python pm_agent.py --figma <url> --goal "Add mobile checkout flow"
    python pm_agent.py --describe                 ← skip Figma, type design manually

Options:
    --describe          skip Figma, type your design description instead
    --goal "..."        skip problem selection, use this goal directly
    --fast              skip problem selection, auto-detect goal
    --model qwen2.5:14b use a bigger Ollama model
    --out ./docs/prds   custom output folder
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

ENV_PATH = Path(__file__).parent / ".env"


def parse_args():
    parser = argparse.ArgumentParser(
        prog="figprd",
        description="Generate a PRD from a Figma design using a local LLM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  figprd
  figprd --describe
  figprd --figma "https://figma.com/design/abc/App?node-id=1-2"
  figprd --figma <url> --goal "Add mobile checkout"
  figprd --figma <url> --out ./docs/prds
        """,
    )
    parser.add_argument("--figma", default=None, metavar="URL",
                        help="Figma design URL")
    parser.add_argument("--describe", action="store_true",
                        help="Skip Figma — type your design description instead")
    parser.add_argument("--goal", default=None, metavar="TEXT",
                        help="Skip problem selection and use this goal directly")
    parser.add_argument("--model", default=os.getenv("OLLAMA_MODEL", None),
                        metavar="MODEL", help="Ollama model (default: auto-detect)")
    parser.add_argument("--host", default=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
                        metavar="URL", help="Ollama host")
    parser.add_argument("--out", default="./output", metavar="DIR",
                        help="Output directory (default: ./output)")
    parser.add_argument("--no-open", action="store_true",
                        help="Do not auto-open HTML report in browser")
    parser.add_argument("--fast", action="store_true",
                        help="Skip problem statement selection, auto-detect goal")
    return parser.parse_args()


def prompt_for_token() -> str:
    console.print()
    console.print(Panel(
        "[bold yellow]Figma Access Token required[/bold yellow]\n\n"
        "1. Go to [cyan]figma.com[/cyan] → Settings → Security\n"
        "2. Click [bold]Generate new personal access token[/bold]\n"
        "3. Paste it below",
        border_style="yellow",
        padding=(1, 2),
    ))
    token = Prompt.ask("[bold cyan]Figma token[/bold cyan]").strip()
    if not token:
        console.print("[red]No token entered. Exiting.[/red]")
        sys.exit(1)
    ENV_PATH.touch(exist_ok=True)
    set_key(str(ENV_PATH), "FIGMA_ACCESS_TOKEN", token)
    console.print("[green]✓[/green] Token saved to .env\n")
    return token


def get_figma_token() -> str:
    token = os.getenv("FIGMA_ACCESS_TOKEN", "")
    if not token or token == "your_figma_token_here":
        return prompt_for_token()
    return token


def prompt_for_figma_url() -> str:
    console.print()
    console.print("[dim]Paste your Figma design URL (e.g. figma.com/design/...?node-id=...)[/dim]")
    url = Prompt.ask("[bold cyan]Figma URL[/bold cyan]").strip()
    if not url:
        console.print("[red]No URL entered. Exiting.[/red]")
        sys.exit(1)
    return url


def prompt_for_description() -> str:
    console.print()
    console.print(Panel(
        "[bold yellow]Describe your design[/bold yellow]\n\n"
        "Paste or type a description of the screens, features, user flows,\n"
        "interactive elements, and any relevant context.\n\n"
        "[dim]Enter your description, then press Enter twice when done.[/dim]",
        border_style="yellow",
        padding=(1, 2),
    ))
    lines = []
    while True:
        line = input()
        if line == "" and lines and lines[-1] == "":
            break
        lines.append(line)
    description = "\n".join(lines).strip()
    if not description:
        console.print("[red]No description entered. Exiting.[/red]")
        sys.exit(1)
    return description


def show_problem_choices(suggestions) -> str:
    angle_colors = {
        "UX": "magenta",
        "Business": "green",
        "Technical": "blue",
    }

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
    console.print(f"\n[green]✓[/green] Selected: [bold]{selected.title}[/bold]\n")
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
    table.add_row("User Stories", str(len(prd.user_stories)))
    table.add_row("Detailed Stories", str(len(prd.structured_stories)))
    table.add_row("Acceptance Criteria", str(len(prd.acceptance_criteria)))
    table.add_row("Edge Cases", str(len(prd.edge_cases)))
    table.add_row("Business Rules", str(len(prd.business_rules)))
    table.add_row("Technical Considerations", str(len(prd.technical_considerations)))
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
        "[bold cyan]PM Agent[/bold cyan]  —  Figma → PRD\n"
        "[dim]Powered by local Ollama LLM — no cloud needed[/dim]",
        border_style="cyan",
    ))

    from writers import write_markdown, write_json, write_html
    from cloud_client import build_cloud_client

    llm = build_cloud_client(os.environ)
    if llm is None:
        from ollama_client import OllamaClient
        llm = OllamaClient(host=args.host, model=args.model or None)

    output_dir = Path(args.out)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── Step 1: Check LLM ────────────────────────────────────────────────────
    with Progress(SpinnerColumn(), TextColumn("{task.description}"),
                  console=console, transient=False) as p:
        t = p.add_task("Connecting to LLM...", total=None)
        ready, msg = llm.check_connection()
        if not ready:
            p.stop()
            console.print(f"\n[red]LLM not ready:[/red] {msg}")
            sys.exit(1)
        p.update(t, description=f"[green]✓[/green] {msg}")
        p.stop_task(t)

    # ── Step 2: Get design context (Figma OR manual description) ─────────────
    figma_url = ""
    if args.describe:
        # Skip Figma — user types design description directly
        design_text = prompt_for_description()
        design_name = "Manual Description"
        console.print(f"\n[green]✓[/green] Design context ready ({len(design_text)} chars)\n")
    else:
        figma_token = get_figma_token()
        figma_url = args.figma or prompt_for_figma_url()
        console.print(
            f"\n[dim]Out:[/dim] {args.out}  |  "
            f"[dim]URL:[/dim] {figma_url[:60]}{'...' if len(figma_url) > 60 else ''}\n"
        )
        from connectors.figma_connector import FigmaConnector
        figma = FigmaConnector(figma_token)

        with Progress(SpinnerColumn(), TextColumn("{task.description}"),
                      console=console, transient=False) as p:
            t = p.add_task("Fetching Figma wireframe...", total=None)
            try:
                design_ctx = figma.extract_design_context(figma_url)
                design_text = figma.format_for_prompt(design_ctx)
                design_name = design_ctx["target_name"]
            except Exception as e:
                p.stop()
                console.print(f"\n[red]Figma error:[/red] {e}")
                console.print("[dim]Tip: run with [bold]--describe[/bold] to skip Figma and type your design instead.[/dim]")
                sys.exit(1)
            p.update(t, description=f"[green]✓[/green] Figma: {design_ctx['target_name']}  ({len(design_ctx['screens'])} screen(s))")
            p.stop_task(t)

    # ── Step 3: Problem statement ─────────────────────────────────────────────
    if args.goal:
        feature_goal = args.goal
        console.print(f"\n[green]✓[/green] Using provided goal: {feature_goal}\n")
    elif args.fast:
        feature_goal = f"Build the core user experience for {design_name}"
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

    # ── Step 4: Generate PRD ──────────────────────────────────────────────────
    with Progress(SpinnerColumn(), TextColumn("{task.description}"),
                  console=console, transient=False) as p:
        t = p.add_task("Generating PRD...", total=None)

        def on_token(count):
            p.update(t, description=f"Generating PRD... ({count} tokens written)")

        try:
            prd = llm.generate_prd(design_context=design_text, feature_goal=feature_goal, on_token=on_token)
        except Exception as e:
            p.stop()
            console.print(f"\n[red]LLM error:[/red] {e}")
            sys.exit(1)
        p.update(t, description=f"[green]✓[/green] PRD generated: {prd.feature_name}")
        p.stop_task(t)

    # ── Step 5: Write output ──────────────────────────────────────────────────
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
