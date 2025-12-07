# fyodoros/cli.py
"""
FyodorOS Command Line Interface.

This module provides the main entry point for the `fyodor` command.
It uses `typer` to define subcommands for managing the OS, plugins, network,
users, and launching the TUI or GUI.
"""

import typer
import os
import json
from pathlib import Path
import sys
import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich import print as rprint
from fyodoros.kernel.users import UserManager
from fyodoros.kernel.network import NetworkManager
from fyodoros.plugins.registry import PluginRegistry
from fyodoros.utils.security import encrypt_value, decrypt_value

app = typer.Typer()
plugin_app = typer.Typer()
network_app = typer.Typer()
app.add_typer(plugin_app, name="plugin")
app.add_typer(network_app, name="network")
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
    Safely loads environment variables from the `.env` file.
    Handles decryption of sensitive values.

    Returns:
        dict: The loaded environment variables.
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

                    # Decrypt if encrypted
                    val = decrypt_value(val)
                    env[key.strip()] = val
    return env

def _run_kernel(args=None):
    """
    Runs the FyodorOS kernel in a subprocess.

    Args:
        args (list, optional): Command-line arguments to pass to the kernel.
    """
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

    # When running from CLI, we assume 'root' privilege unless we want to implement
    # a sudo mechanism. For now, we pass 'root' as requestor, but
    # if the TeamCollaboration plugin is active, it might inspect real user context.
    # Since CLI is outside the "login session", we assume it's an admin op.
    # However, to demonstrate RBAC, we should ideally check who is running this.
    # But for CLI 'fyodor user', it IS the admin tool.

    um = UserManager()
    # By default, CLI usage is considered 'root' / admin action.
    if um.add_user(username, password, requestor="root"):
        console.print(f"[green]User '{username}' created successfully![/green]")
    else:
        console.print(f"[red]Failed to create user '{username}' (Permission denied or already exists).[/red]")

@app.command()
def setup():
    """
    Configure FyodorOS (LLM Provider, API Keys).
    Interactve wizard to set up .env file.
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
    # Set strict permissions on .env (600)
    env_path = Path(".env")
    if not env_path.exists():
        env_path.touch(mode=0o600)
    else:
        os.chmod(env_path, 0o600)

    with open(env_path, "w") as f:
        f.write(f"# FyodorOS Configuration\n")
        f.write(f"LLM_PROVIDER={provider}\n")
        if api_key:
            # Encrypt API Key
            encrypted_key = encrypt_value(api_key)
            f.write(f"{key_name}={encrypted_key}\n")

    console.print(f"\n[green]Configuration saved to .env[/green]")
    console.print("[bold]Setup Complete![/bold] Run [cyan]fyodor tui[/cyan] or [cyan]fyodor start[/cyan] to launch.")

@app.command()
def tui():
    """
    Launcher TUI Menu.
    Displays an interactive menu for common tasks.
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

@plugin_app.command("install")
def install_plugin(url: str, name: str = typer.Option(None, help="Rename plugin directory")):
    """Install a plugin from a Git URL."""
    if not name:
        name = url.split("/")[-1].replace(".git", "")

    target_dir = Path.home() / ".fyodor" / "plugins" / name
    if target_dir.exists():
        console.print(f"[red]Plugin '{name}' already exists.[/red]")
        return

    console.print(f"Installing {name} from {url}...")
    try:
        subprocess.check_call(["git", "clone", url, str(target_dir)])
        console.print(f"[green]Installed to {target_dir}[/green]")
        console.print("Running build detection...")
        _build_plugin(target_dir)
    except Exception as e:
        console.print(f"[red]Installation failed: {e}[/red]")

@plugin_app.command("build")
def build_plugin(name: str):
    """Build a plugin (Node/C++/Python)."""
    target_dir = Path.home() / ".fyodor" / "plugins" / name
    if not target_dir.exists():
        console.print(f"[red]Plugin '{name}' not found.[/red]")
        return
    _build_plugin(target_dir)

def _build_plugin(path: Path):
    if (path / "package.json").exists():
        console.print("[cyan]Detected Node.js plugin. Installing dependencies...[/cyan]")
        try:
            # Check for bun
            try:
                subprocess.check_call(["bun", "install"], cwd=path)
            except FileNotFoundError:
                subprocess.check_call(["npm", "install"], cwd=path)
            console.print("[green]Node dependencies installed.[/green]")
        except Exception as e:
            console.print(f"[red]Node build failed: {e}[/red]")

    if (path / "CMakeLists.txt").exists():
        console.print("[cyan]Detected C++ plugin. compiling...[/cyan]")
        try:
            build_dir = path / "build"
            build_dir.mkdir(exist_ok=True)
            subprocess.check_call(["cmake", ".."], cwd=build_dir)
            subprocess.check_call(["make"], cwd=build_dir)
            console.print("[green]C++ compilation complete.[/green]")
        except Exception as e:
            console.print(f"[red]C++ build failed: {e}[/red]")

    if (path / "requirements.txt").exists():
        console.print("[cyan]Detected Python dependencies. Installing...[/cyan]")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], cwd=path)
            console.print("[green]Python dependencies installed.[/green]")
        except Exception as e:
            console.print(f"[red]Python dependency installation failed: {e}[/red]")

@plugin_app.command("create")
def create_plugin(name: str, lang: str = typer.Option("python", help="Language: python, cpp, node")):
    """Scaffold a new plugin."""
    target_dir = Path.home() / ".fyodor" / "plugins" / name
    if target_dir.exists():
        console.print(f"[red]Directory already exists.[/red]")
        return

    target_dir.mkdir(parents=True)

    if lang == "python":
        with open(target_dir / "__init__.py", "w") as f:
            f.write(f"""from fyodoros.plugins import Plugin
class {name.capitalize()}Plugin(Plugin):
    def setup(self, kernel):
        print("Hello from {name}!")
""")
    elif lang == "node":
        with open(target_dir / "package.json", "w") as f:
            f.write(f'{{"name": "{name}", "version": "0.1.0", "main": "index.js"}}')
        with open(target_dir / "index.js", "w") as f:
            f.write("""console.log("Hello from Node Plugin!");""")
    elif lang == "cpp":
        with open(target_dir / "CMakeLists.txt", "w") as f:
            f.write(f"""cmake_minimum_required(VERSION 3.10)
project({name})
add_library({name} SHARED library.cpp)
""")
        with open(target_dir / "library.cpp", "w") as f:
            f.write("""#include <iostream>
extern "C" void init_plugin() {
    std::cout << "Hello from C++ Plugin!" << std::endl;
}
""")

    console.print(f"[green]Created {lang} plugin at {target_dir}[/green]")

@plugin_app.command("settings")
def plugin_settings(name: str, key: str = typer.Argument(None), value: str = typer.Argument(None)):
    """Configure plugin settings."""
    reg = PluginRegistry()

    if not key:
        # List settings for this plugin (if we had schema, but here we just show existing)
        # Since we don't have a schema, we just say use key value
        console.print(f"Current settings for {name}:")
        console.print(reg.plugin_settings.get(name, {}))
        return

    if value:
        reg.set_setting(name, key, value)
        console.print(f"[green]Set {name}.{key} = {value}[/green]")
    else:
        val = reg.get_setting(name, key)
        console.print(f"{name}.{key} = {val}")

@network_app.command("status")
def network_status():
    """Check network status."""
    nm = NetworkManager()
    status = "Active" if nm.is_enabled() else "Inactive"
    color = "green" if nm.is_enabled() else "red"
    console.print(f"Network Status: [{color}]{status}[/{color}]")

@network_app.command("on")
def network_on():
    """Enable network."""
    # Note: RBAC is handled inside Manager/Syscall, but CLI is "admin"
    nm = NetworkManager()
    nm.set_enabled(True)
    console.print("[green]Network Enabled[/green]")

@network_app.command("off")
def network_off():
    """Disable network."""
    nm = NetworkManager()
    nm.set_enabled(False)
    console.print("[red]Network Disabled[/red]")

@app.command()
def dashboard(view: str = typer.Argument("tui", help="View mode: tui or logs")):
    """
    View Usage Dashboard (requires usage_dashboard plugin).
    """
    log_file = Path.home() / ".fyodor" / "dashboard" / "stats.json"

    if not log_file.exists():
        console.print("[red]No dashboard data found. Is the 'usage_dashboard' plugin active?[/red]")
        return

    if view == "logs":
        with open(log_file, "r") as f:
            data = json.load(f)
            console.print(json.dumps(data, indent=2))
    elif view == "tui":
        try:
            from rich.live import Live
            from rich.table import Table
            import time

            with Live(refresh_per_second=1) as live:
                while True:
                    try:
                        with open(log_file, "r") as f:
                            data = json.load(f)
                            if not data:
                                continue
                            latest = data[-1]

                            table = Table(title="System Dashboard")
                            table.add_column("Metric", style="cyan")
                            table.add_column("Value", style="magenta")

                            table.add_row("Timestamp", str(latest["timestamp"]))
                            table.add_row("CPU Usage", f"{latest['cpu_percent']}%")
                            table.add_row("Memory Usage", f"{latest['memory_percent']}%")
                            table.add_row("Boot Time", str(latest["boot_time"]))

                            live.update(Panel(table))
                    except Exception:
                        pass
                    time.sleep(1)
        except KeyboardInterrupt:
            console.print("Dashboard closed.")
    else:
        console.print(f"[red]Unknown view mode: {view}[/red]")

@app.command()
def gui():
    """
    Launch FyodorOS Desktop GUI (Tauri).
    Installs/builds if necessary.
    """
    gui_dir = Path("gui")
    if not gui_dir.exists():
        console.print("[red]GUI directory not found![/red]")
        return

    # Check if built binary exists (assuming Linux/Release for now)
    # The path depends on Cargo target dir. Default is src-tauri/target/release
    binary_path = gui_dir / "src-tauri" / "target" / "release" / "fyodor-gui"

    # Simple check: if not built or user requests rebuild (not implemented yet), run installer
    if not binary_path.exists():
        console.print("[yellow]GUI not installed/built. Running setup...[/yellow]")
        setup_script = gui_dir / "setup_gui.py"
        try:
            subprocess.check_call([sys.executable, str(setup_script)])
        except subprocess.CalledProcessError:
            console.print("[red]GUI Setup Failed.[/red]")
            return

    console.print("[green]Launching GUI...[/green]")
    try:
        # Launch the binary
        # We might need to handle detaching or blocking. Blocking for now.
        subprocess.call([str(binary_path)])
    except Exception as e:
        console.print(f"[red]Failed to launch GUI: {e}[/red]")

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
