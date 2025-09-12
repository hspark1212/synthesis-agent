"""
SKY - Synthesis Knowledge Yield Agent
Main CLI entry point for materials synthesis discovery
"""

import os
import sys
import shutil
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich import print as rprint

from .ascii_art import SKY_FULL_LOGO, get_responsive_logo

app = typer.Typer(
    name="sky",
    help="SKY - Synthesis Knowledge Yield Agent for materials synthesis discovery",
    add_completion=False
)
console = Console()


def show_banner():
    """Display SKY banner"""
    terminal_width = shutil.get_terminal_size().columns
    logo = get_responsive_logo(terminal_width)
    console.print(Panel(logo, style="bold cyan", expand=False))


@app.command()
def search(
    query: str = typer.Argument(..., help="Material composition (e.g., Fe2O3) or CIF file path"),
    top_n: int = typer.Option(10, "--top", "-n", help="Number of similar materials"),
    structure: bool = typer.Option(False, "--structure", "-s", help="Force structure-based search"),
    show_synthesis: bool = typer.Option(True, "--synthesis/--no-synthesis", help="Show synthesis recipes")
):
    """
    Search for similar materials and their synthesis recipes.
    
    Examples:
        sky search Fe2O3                     # Composition search
        sky search LiFePO4 --top 5           # Top 5 similar materials
        sky search /path/to/file.cif         # Structure search from CIF
        sky search LiFe.cif                  # Local CIF file
    """
    show_banner()
    
    # Detect if input is a CIF file
    is_cif = query.endswith('.cif') and Path(query).exists()
    
    if is_cif:
        console.print(f"[bold cyan]🔬 Analyzing structure from CIF file:[/] {query}\n")
        search_type = "structure"
    else:
        console.print(f"[bold cyan]🔍 Searching for materials similar to:[/] {query}\n")
        search_type = "composition"
    
    try:
        from ..core.synthesis_agent import SKYSynthesisAgent
        
        # Initialize agent
        console.print("[dim]Initializing SKY agent...[/]")
        session_id = f"sky_search_{Path(query).stem if is_cif else query}"
        agent = SKYSynthesisAgent(session_id=session_id)
        
        # Run discovery
        console.print(f"[dim]Discovering synthesis methods using {search_type} similarity...[/]")
        result = agent.discover_synthesis_sync(query)
        
        # Display results
        console.print("\n[bold green]📊 Results:[/]\n")
        console.print(Markdown(result))
        
    except Exception as e:
        console.print(f"[bold red]❌ Error:[/] {e}")
        raise typer.Exit(1)


@app.command()
def chat():
    """
    Interactive chat mode for synthesis discovery.
    """
    show_banner()
    console.print("[bold cyan]💬 SKY Interactive Chat Mode[/]")
    console.print("[dim]Type 'quit' or 'exit' to leave[/]\n")
    
    try:
        from ..core.synthesis_agent import SKYSynthesisAgent
        
        # Initialize agent with session
        agent = SKYSynthesisAgent(session_id="sky_chat_session")
        console.print("[green]✅ SKY agent ready![/]\n")
        
        while True:
            # Get user input
            query = typer.prompt("\n[bold]You[/]", prompt_suffix=": ")
            
            if query.lower() in ["quit", "exit", "bye"]:
                console.print("\n[cyan]👋 Goodbye! Thank you for using SKY.[/]")
                break
            
            # Process query
            console.print("\n[dim]SKY is thinking...[/]")
            try:
                result = agent.discover_synthesis_sync(query)
                console.print(f"\n[bold cyan]SKY:[/]\n")
                console.print(Markdown(result))
            except Exception as e:
                console.print(f"[red]Error processing query: {e}[/]")
                
    except KeyboardInterrupt:
        console.print("\n\n[cyan]👋 Chat interrupted. Goodbye![/]")
    except Exception as e:
        console.print(f"[bold red]❌ Error initializing chat:[/] {e}")
        raise typer.Exit(1)


@app.command()
def setup():
    """
    Check environment setup and dependencies.
    """
    show_banner()
    console.print("[bold]⚙️ SKY Environment Check[/]\n")
    
    # Create status table
    table = Table(title="Configuration Status")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Details")
    
    # Check API keys
    openai_key = os.getenv("OPENAI_MDG_API_KEY") or os.getenv("OPENAI_API_KEY")
    mp_key = os.getenv("MP_API_KEY")
    
    table.add_row(
        "OpenAI API Key",
        "✅ Set" if openai_key else "❌ Missing",
        "Required for AI synthesis analysis"
    )
    
    table.add_row(
        "Materials Project API Key",
        "✅ Set" if mp_key else "⚠️ Optional",
        "Enables live materials data"
    )
    
    # Check dependencies
    deps = [
        ("pymatgen", "Materials analysis"),
        ("openai_agents", "Agent framework"),
        ("monty", "Data serialization"),
        ("h5py", "Embedding storage"),
        ("mace_torch", "Structure embeddings")
    ]
    
    for module_name, description in deps:
        try:
            __import__(module_name.replace("-", "_"))
            table.add_row(module_name, "✅ Installed", description)
        except ImportError:
            table.add_row(module_name, "❌ Missing", description)
    
    # Check data files
    synthesis_file = Path("/home/ryan/kricthack/kricthack/synthesis-agent/assets/mp_synthesis_recipes.json.gz")
    embedding_file = Path("/home/ryan/kricthack/kricthack/synthesis-agent/assets/embedding/mp_dataset_composition_magpie.h5")
    
    table.add_row(
        "Synthesis Recipes",
        "✅ Found" if synthesis_file.exists() else "❌ Missing",
        f"{synthesis_file.stat().st_size / 1024 / 1024:.1f} MB" if synthesis_file.exists() else "Required for synthesis data"
    )
    
    table.add_row(
        "Composition Embeddings",
        "✅ Found" if embedding_file.exists() else "❌ Missing",
        f"{embedding_file.stat().st_size / 1024 / 1024:.1f} MB" if embedding_file.exists() else "Required for similarity search"
    )
    
    console.print(table)
    
    # Recommendations
    console.print("\n[bold]📝 Recommendations:[/]")
    if not openai_key:
        console.print("  1. Set OPENAI_MDG_API_KEY environment variable")
    if not mp_key:
        console.print("  2. Set MP_API_KEY for enhanced materials data")
    
    console.print("\n[green]✅ SKY is ready for synthesis discovery![/]")


@app.command()
def demo():
    """
    Show feature demonstration and examples.
    """
    show_banner()
    
    demo_text = """
# SKY - Synthesis Knowledge Yield Agent

## 🔬 Core Capabilities:
- **Composition Search**: Find materials similar to Fe2O3, LiCoO2, etc.
- **Synthesis Discovery**: Retrieve synthesis recipes from database
- **Parameter Analysis**: Extract temperature, time, atmosphere conditions
- **Smart Recommendations**: AI-powered synthesis route suggestions
- **Interactive Chat**: Multi-turn conversations with context

## 🧪 Example Workflows:

### 1. Basic Synthesis Search
```bash
sky search Fe2O3
```
→ Finds similar iron oxides (Fe3O4, FeO, α-Fe2O3)
→ Retrieves synthesis recipes for each
→ Analyzes synthesis parameters
→ Recommends optimal synthesis route

### 2. Battery Material Discovery
```bash
sky search LiFePO4 --top 5
```
→ Identifies similar cathode materials
→ Compares synthesis methods
→ Highlights critical parameters
→ Suggests alternatives based on properties

### 3. Interactive Exploration
```bash
sky chat
You: I need to synthesize BiFeO3
SKY: [Provides synthesis routes, conditions, precursors]
You: What temperature is best for phase purity?
SKY: [Analyzes temperature effects on BiFeO3 formation]
```

## 📊 Data Sources:
- **Materials Project**: Live API for properties
- **Synthesis Database**: 1M+ recipes from literature
- **Embedding Search**: Fast similarity matching
- **AI Analysis**: GPT-powered insights

## 🚀 Ready to accelerate your materials synthesis research!
    """
    
    console.print(Markdown(demo_text))


@app.command()
def version():
    """
    Show SKY version information.
    """
    console.print("[bold cyan]SKY - Synthesis Knowledge Yield Agent[/]")
    console.print("Version: 1.0.0")
    console.print("Model: o3 (configurable)")
    console.print("Copyright 2025 - Materials Discovery Team")


def main():
    """Main entry point for SKY CLI"""
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[cyan]👋 Operation cancelled.[/]")
        raise typer.Exit(0)
    except Exception as e:
        console.print(f"\n[bold red]Unexpected error:[/] {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    main()