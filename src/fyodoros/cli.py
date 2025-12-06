# fyodoros/cli.py
import typer
import os
import sys
import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich import print as rprint
from fyodoros.kernel.users import UserManager
from fyodoros.plugins.registry import PluginRegistry

app = typer.Typer()
plugin_app = typer.Typer()
app.add_typer(plugin_app, name="plugin")
console = Console()

BANNER = """
███████╗██╗   ██╗ ██████╗ ██████╗  ██████╗ ██████╗
██╔════╝╚██╗ ██╔╝██╔═══██╗██╔══██╗██╔═══██╗██╔══██╗
█████╗   ╚████╔╝ ██║   ██║██║  ██║██║   ██║██████╔╝
██╔══╝    ╚██╔╝  ██║   ██║██║  ██║██║   ██║██╔══██╗
██║        ██║   ╚██████╔╝██████╔╝╚██████╔╝██║  ██║
╚═╝        ╚═╝    ╚═════╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝
          The Experimental AI Microkernel
"""

def _load_env_safely():
    """
    Robust .env loading.
    """
    env_file = ".env"
    env = os.environ.copy()
    if os.path.exists(env_file):
        console.print(f"[dim]Loading environment from {env_file}...[/dim]")
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    # Strip quotes if present
                    val = val.strip()
                    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                        val = val[1:-1]
                    env[key.strip()] = val
    return env

def _run_kernel(args=None):
    env = _load_env_safely()

    # Run the OS script via module
    cmd = [sys.executable, "-m", "fyodoros"]
    if args:
        cmd.extend(args)

    try:
        ret = subprocess.call(cmd, env=env)
        if ret != 0:
            console.print(f"[red]Kernel exited with code {ret}[/red]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutdown.[/yellow]")

@app.command()
def start():
    """
    Launch FyodorOS (Auto-login as Guest).
    """
    console.print(BANNER, style="bold cyan")
    _run_kernel(["--user", "guest", "--password", "guest"])

@app.command()
def login(user: str = typer.Option(None, help="Username to pre-fill")):
    """
    Launch FyodorOS with interactive login.
    """
    console.print(BANNER, style="bold cyan")
    args = []
    if user:
        args.extend(["--user", user])
    _run_kernel(args)

@app.command()
def user(username: str, password: str = typer.Argument(None)):
    """
    Create a new user.
    """
    if not password:
        password = Prompt.ask(f"Enter password for '{username}'", password=True)

    um = UserManager()
    if um.add_user(username, password):
        console.print(f"[green]User '{username}' created successfully![/green]")
    else:
        console.print(f"[red]Failed to create user '{username}' (already exists?).[/red]")

@app.command()
def setup():
    """
    Configure FyodorOS (LLM Provider, API Keys).
    """
    console.print(BANNER, style="bold cyan")
    console.print(Panel("Welcome to FyodorOS Setup", title="Setup", style="blue"))

    providers = ["openai", "gemini", "anthropic", "mock"]
    provider = Prompt.ask("Select LLM Provider", choices=providers, default="openai")

    api_key = ""
    if provider != "mock":
        key_name = f"{provider.upper()}_API_KEY"
        if provider == "gemini": key_name = "GOOGLE_API_KEY" # Standardize

        api_key = Prompt.ask(f"Enter your {key_name}", password=True)

    # Write robustly
    with open(".env", "w") as f:
        f.write(f"# FyodorOS Configuration\n")
        f.write(f"LLM_PROVIDER={provider}\n")
        if api_key:
            f.write(f"{key_name}={api_key}\n")

    console.print(f"\n[green]Configuration saved to .env[/green]")
    console.print("[bold]Setup Complete![/bold] Run [cyan]fyodor tui[/cyan] or [cyan]fyodor start[/cyan] to launch.")

@app.command()
def tui():
    """
    Launcher TUI Menu.
    """
    while True:
        console.clear()
        console.print(BANNER, style="bold cyan")
        console.print(Panel("[1] Start OS (Guest)\n[2] Login\n[3] Create User\n[4] Setup\n[5] Exit", title="Launcher Menu", style="purple"))

        choice = Prompt.ask("Select option", choices=["1", "2", "3", "4", "5"], default="1")

        if choice == "1":
            start()
            Prompt.ask("\nPress Enter to return to menu...")
        elif choice == "2":
            login()
            Prompt.ask("\nPress Enter to return to menu...")
        elif choice == "3":
            u = Prompt.ask("Username")
            user(u)
            Prompt.ask("\nPress Enter to return to menu...")
        elif choice == "4":
            setup()
            Prompt.ask("\nPress Enter to return to menu...")
        elif choice == "5":
            console.print("Goodbye!")
            break

@plugin_app.command("list")
def list_plugins():
    """List active plugins."""
    reg = PluginRegistry()
    plugins = reg.list_plugins()
    if plugins:
        console.print(f"[green]Active Plugins:[/green] {', '.join(plugins)}")
    else:
        console.print("[yellow]No active plugins.[/yellow]")

@plugin_app.command("activate")
def activate_plugin(name: str):
    """Activate a plugin by module name."""
    reg = PluginRegistry()
    if reg.activate(name):
        console.print(f"[green]Plugin '{name}' activated.[/green]")
    else:
        console.print(f"[yellow]Plugin '{name}' already active.[/yellow]")

@plugin_app.command("deactivate")
def deactivate_plugin(name: str):
    """Deactivate a plugin."""
    reg = PluginRegistry()
    if reg.deactivate(name):
        console.print(f"[green]Plugin '{name}' deactivated.[/green]")
    else:
        console.print(f"[yellow]Plugin '{name}' was not active.[/yellow]")

@app.command()
def info():
    """
    Show info about the installation.
    """
    console.print(BANNER, style="bold cyan")
    console.print("Version: 0.3.0")
    console.print("Location: " + os.getcwd())

    if os.path.exists(".env"):
        console.print("[green]Config found (.env)[/green]")
        with open(".env", "r") as f:
            for line in f:
                if "LLM_PROVIDER" in line:
                    console.print(f"  {line.strip()}")
    else:
        console.print("[red]Config missing (run setup)[/red]")

if __name__ == "__main__":
    app()
