# fyodoros/cli.py
import typer
import os
import sys
import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from fyodoros.kernel.users import UserManager

app = typer.Typer()
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

def _run_kernel(args=None):
    console.print(BANNER, style="bold cyan")
    console.print("[green]Starting FyodorOS Kernel...[/green]")

    # Check for .env file
    env_file = ".env"
    env = os.environ.copy()
    if os.path.exists(env_file):
        console.print(f"[dim]Loading environment from {env_file}...[/dim]")
        with open(env_file, "r") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    key, val = line.strip().split("=", 1)
                    env[key] = val

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
    _run_kernel(["--user", "guest", "--password", "guest"])

@app.command()
def login(user: str = typer.Option(None, help="Username to pre-fill")):
    """
    Launch FyodorOS with interactive login.
    """
    args = []
    if user:
        args.extend(["--user", user])
    _run_kernel(args)

@app.command()
def user(username: str, password: str = typer.Argument(None)):
    """
    Create a new user.
    Usage: fyodor user <username> [password]
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
    Configure FyodorOS (API Keys, etc).
    """
    console.print(BANNER, style="bold cyan")
    console.print(Panel("Welcome to FyodorOS Setup", title="Setup", style="blue"))

    api_key = Prompt.ask("Enter your OpenAI API Key (leave blank to use Mock LLM)", password=True)

    with open(".env", "w") as f:
        if api_key:
            f.write(f"OPENAI_API_KEY={api_key}\n")
            console.print("[green]API Key saved to .env[/green]")
        else:
            f.write("# No API Key set, using Mock LLM\n")
            console.print("[yellow]No key provided. Using Mock LLM.[/yellow]")

    console.print("\n[bold]Setup Complete![/bold] Run [cyan]fyodor start[/cyan] to launch.")

@app.command()
def info():
    """
    Show info about the installation.
    """
    console.print(BANNER, style="bold cyan")
    console.print("Version: 0.1.0-alpha")
    console.print("Location: " + os.getcwd())

    if os.path.exists(".env"):
        console.print("[green]Config found (.env)[/green]")
    else:
        console.print("[red]Config missing (run setup)[/red]")

if __name__ == "__main__":
    app()
