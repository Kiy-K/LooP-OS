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
import shutil
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
from fyodoros.kernel.cloud.docker_interface import DockerInterface
from fyodoros.kernel.cloud.k8s_interface import KubernetesInterface

app = typer.Typer()
plugin_app = typer.Typer()
network_app = typer.Typer()
docker_app = typer.Typer()
k8s_app = typer.Typer()
memory_app = typer.Typer()
app.add_typer(plugin_app, name="plugin")
app.add_typer(network_app, name="network")
app.add_typer(docker_app, name="docker")
app.add_typer(k8s_app, name="k8s")
app.add_typer(memory_app, name="memory")
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

    Args:
        user (str): Username to pre-fill in the login prompt.
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

    Args:
        username (str): The username for the new user.
        password (str): The password for the new user. If not provided, will be prompted.
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
    """
    Activate a plugin by module name.

    Args:
        name (str): The name of the plugin to activate.
    """
    reg = PluginRegistry()
    if reg.activate(name):
        console.print(f"[green]Plugin '{name}' activated.[/green]")
    else:
        console.print(f"[yellow]Plugin '{name}' already active.[/yellow]")


@plugin_app.command("deactivate")
def deactivate_plugin(name: str):
    """
    Deactivate a plugin.

    Args:
        name (str): The name of the plugin to deactivate.
    """
    reg = PluginRegistry()
    if reg.deactivate(name):
        console.print(f"[green]Plugin '{name}' deactivated.[/green]")
    else:
        console.print(f"[yellow]Plugin '{name}' was not active.[/yellow]")


@plugin_app.command("install")
def install_plugin(url: str, name: str = typer.Option(None, help="Rename plugin directory")):
    """
    Install a plugin from a Git URL.

    Args:
        url (str): The Git URL of the plugin repository.
        name (str): The directory name for the plugin (defaults to repo name).
    """
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
    """
    Build a plugin (Node/C++/Python).

    Args:
        name (str): The name of the plugin to build.
    """
    target_dir = Path.home() / ".fyodor" / "plugins" / name
    if not target_dir.exists():
        console.print(f"[red]Plugin '{name}' not found.[/red]")
        return
    _build_plugin(target_dir)


def _build_plugin(path: Path):
    """
    Detects and builds plugin dependencies.

    Args:
        path (Path): The path to the plugin directory.
    """
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
    """
    Scaffold a new plugin.

    Args:
        name (str): The name of the new plugin.
        lang (str): The programming language for the plugin ('python', 'cpp', or 'node').
    """
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
    """
    Configure plugin settings.

    Args:
        name (str): The name of the plugin.
        key (str): The setting key to retrieve or set.
        value (str): The value to set (if updating).
    """
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


@docker_app.command("ps")
def docker_ps(all: bool = False):
    """
    List Docker containers.

    Args:
        all (bool): If True, lists all containers (including stopped ones).
    """
    docker = DockerInterface()
    res = docker.list_containers(all=all)
    if res["success"]:
        containers = res["data"]
        if not containers:
            console.print("[yellow]No containers found.[/yellow]")
            return

        from rich.table import Table
        table = Table(title="Docker Containers")
        table.add_column("ID", style="cyan")
        table.add_column("Image", style="magenta")
        table.add_column("Name", style="green")
        table.add_column("Status")
        table.add_column("Ports")

        for c in containers:
            table.add_row(c["id"], c["image"], c["name"], c["status"], str(c["ports"]))
        console.print(table)
    else:
        console.print(f"[red]Error: {res['error']}[/red]")


@docker_app.command("run")
def docker_run(image: str, name: str = typer.Option(None), ports: str = typer.Option(None, help="JSON string or '80:80'"), env: str = typer.Option(None, help="JSON string")):
    """
    Run a Docker container.

    Args:
        image (str): The Docker image to run.
        name (str, optional): The name to assign to the container.
        ports (str, optional): Port mapping as a JSON string or 'host:container' format.
        env (str, optional): Environment variables as a JSON string.
    """
    docker = DockerInterface()

    ports_dict = None
    if ports:
        try:
            ports_dict = json.loads(ports)
        except json.JSONDecodeError:
            # Simple format '8080:80'
            if ":" in ports:
                host, container = ports.split(":")
                ports_dict = {f"{container}/tcp": int(host)}
            else:
                 console.print("[red]Invalid port format. Use JSON or host:container[/red]")
                 return

    env_dict = None
    if env:
        try:
            env_dict = json.loads(env)
        except json.JSONDecodeError:
            console.print("[red]Invalid env format. Must be JSON.[/red]")
            return

    res = docker.run_container(image, name, ports=ports_dict, env=env_dict)
    if res["success"]:
        console.print(f"[green]Container started: {res['data']['container_id']} ({res['data']['name']})[/green]")
    else:
        console.print(f"[red]Error: {res['error']}[/red]")


@docker_app.command("build")
def docker_build(path: str, tag: str, dockerfile: str = "Dockerfile"):
    """
    Build a Docker image.

    Args:
        path (str): The path to the build context.
        tag (str): The tag to assign to the built image.
        dockerfile (str, optional): The name of the Dockerfile (default: 'Dockerfile').
    """
    docker = DockerInterface()
    console.print(f"Building {tag} from {path}...")
    res = docker.build_image(path, tag, dockerfile)
    if res["success"]:
        console.print(f"[green]Build complete: {res['data']['image_id']}[/green]")
        # Could print logs if verbose
    else:
        console.print(f"[red]Error: {res['error']}[/red]")


@docker_app.command("stop")
def docker_stop(container_id: str):
    """
    Stop a Docker container.

    Args:
        container_id (str): The ID or name of the container to stop.
    """
    docker = DockerInterface()
    res = docker.stop_container(container_id)
    if res["success"]:
        console.print(f"[green]{res['data']}[/green]")
    else:
        console.print(f"[red]Error: {res['error']}[/red]")


@docker_app.command("logs")
def docker_logs(container_id: str, tail: int = 100):
    """
    Get logs from a container.

    Args:
        container_id (str): The ID or name of the container.
        tail (int): Number of lines to retrieve from the end of the logs.
    """
    docker = DockerInterface()
    res = docker.get_logs(container_id, tail)
    if res["success"]:
        console.print(Panel(res["data"], title=f"Logs: {container_id}"))
    else:
        console.print(f"[red]Error: {res['error']}[/red]")


@docker_app.command("login")
def docker_login(username: str, registry: str = "https://index.docker.io/v1/"):
    """
    Login to Docker registry.

    Args:
        username (str): The username for the registry.
        registry (str): The registry URL (default: Docker Hub).
    """
    password = Prompt.ask("Password", password=True)
    docker = DockerInterface()
    res = docker.login(username, password, registry)
    if res["success"]:
        console.print("[green]Login successful[/green]")
    else:
        console.print(f"[red]Login failed: {res['error']}[/red]")


@k8s_app.command("pods")
def k8s_pods(namespace: str = "default"):
    """
    List K8s pods.

    Args:
        namespace (str): The Kubernetes namespace.
    """
    k8s = KubernetesInterface()
    res = k8s.get_pods(namespace)
    if res["success"]:
        pods = res["data"]
        if not pods:
            console.print("[yellow]No pods found.[/yellow]")
            return

        from rich.table import Table
        table = Table(title=f"Pods ({namespace})")
        table.add_column("Name", style="cyan")
        table.add_column("Status", style="magenta")
        table.add_column("IP")
        table.add_column("Node")

        for p in pods:
            table.add_row(p["name"], p["status"], p["ip"], p["node"])
        console.print(table)
    else:
        console.print(f"[red]Error: {res['error']}[/red]")


@k8s_app.command("deploy")
def k8s_deploy(name: str, image: str = typer.Option(..., "--image", "-i"), replicas: int = typer.Option(1, "--replicas", "-r"), namespace: str = "default"):
    """
    Create a Deployment.

    Args:
        name (str): The name of the deployment.
        image (str): The container image to use.
        replicas (int): The number of replicas.
        namespace (str): The Kubernetes namespace.
    """
    k8s = KubernetesInterface()
    res = k8s.create_deployment(name, image, replicas, namespace)
    if res["success"]:
        console.print(f"[green]Deployment created: {res['data']['name']}[/green]")
    else:
        console.print(f"[red]Error: {res['error']}[/red]")


@k8s_app.command("scale")
def k8s_scale(name: str, replicas: int = typer.Option(..., "--replicas", "-r"), namespace: str = "default"):
    """
    Scale a Deployment.

    Args:
        name (str): The name of the deployment to scale.
        replicas (int): The new number of replicas.
        namespace (str): The Kubernetes namespace.
    """
    k8s = KubernetesInterface()
    res = k8s.scale_deployment(name, replicas, namespace)
    if res["success"]:
        console.print(f"[green]Scaled {name} to {replicas} replicas[/green]")
    else:
        console.print(f"[red]Error: {res['error']}[/red]")


@k8s_app.command("delete")
def k8s_delete(name: str, namespace: str = "default"):
    """
    Delete a Deployment.

    Args:
        name (str): The name of the deployment to delete.
        namespace (str): The Kubernetes namespace.
    """
    k8s = KubernetesInterface()
    res = k8s.delete_deployment(name, namespace)
    if res["success"]:
        console.print(f"[green]{res['data']}[/green]")
    else:
        console.print(f"[red]Error: {res['error']}[/red]")


@k8s_app.command("logs")
def k8s_logs(pod: str, namespace: str = "default"):
    """
    Get logs from a Pod.

    Args:
        pod (str): The name of the pod.
        namespace (str): The Kubernetes namespace.
    """
    k8s = KubernetesInterface()
    res = k8s.get_pod_logs(pod, namespace)
    if res["success"]:
        console.print(Panel(res["data"], title=f"Logs: {pod}"))
    else:
        console.print(f"[red]Error: {res['error']}[/red]")


@memory_app.command("query")
def memory_query(query: str, limit: int = 5):
    """
    Query the persistent memory.

    Args:
        query (str): Search query.
        limit (int): Max results.
    """
    from fyodoros.kernel.memory import MemoryManager
    mem = MemoryManager()
    results = mem.recall(query, n_results=limit)

    if not results:
        console.print("[yellow]No memories found.[/yellow]")
        return

    for m in results:
        console.print(Panel(f"[bold]{m['content']}[/bold]\n\n[dim]{m['metadata']}[/dim]", title=f"Memory {m['id']}"))


@memory_app.command("clear")
def memory_clear():
    """
    Clear all memories.
    """
    from fyodoros.kernel.memory import MemoryManager
    if Confirm.ask("Are you sure you want to delete ALL persistent memories?"):
        mem = MemoryManager()
        mem.clear()
        console.print("[green]Memory cleared.[/green]")


@app.command()
def resources():
    """
    View Live Resource Usage & Costs.
    """
    from fyodoros.kernel.resource_monitor import ResourceMonitor
    from rich.live import Live
    from rich.table import Table
    import time

    # ResourceMonitor now persists stats to JSON, allowing us to see Kernel activity
    monitor = ResourceMonitor()

    console.print("[dim]Monitoring System & Agent Resources...[/dim]")

    with Live(refresh_per_second=1) as live:
        while True:
            try:
                # Reload stats from disk
                monitor.usage = monitor._load_stats()
                stats = monitor.get_stats()
                limits = monitor.limits

                table = Table(title="Resource Monitor")
                table.add_column("Metric", style="cyan")
                table.add_column("Current", style="green")
                table.add_column("Limit", style="red")

                table.add_row("CPU Usage", f"{stats['cpu_percent']}%", f"{limits['max_cpu_percent']}%")
                table.add_row("Memory Usage", f"{stats['memory_percent']}%", f"{limits['max_memory_percent']}%")
                table.add_row("Session Tokens", f"{stats['tokens']}", f"{limits['max_tokens_per_task']}")
                table.add_row("Session Cost", f"${stats['cost']:.4f}", f"${limits['budget_per_session_usd']:.4f}")
                table.add_row("Duration", f"{stats['duration']:.1f}s", f"{limits['timeout_seconds']}s")

                live.update(Panel(table))
                time.sleep(1)
            except KeyboardInterrupt:
                break


@app.command()
def dashboard(view: str = typer.Argument("tui", help="View mode: tui or logs")):
    """
    View Usage Dashboard (requires usage_dashboard plugin).

    Args:
        view (str): The view mode, either 'tui' (interactive) or 'logs' (JSON dump).
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
def trust(action: str, allow: bool = typer.Option(False, "--allow", help="Whitelist this action")):
    """
    Manage trusted actions.

    Args:
        action (str): The action name (e.g., 'browser', 'run_process').
        allow (bool): Whitelist the action.
    """
    from fyodoros.kernel.confirmation import ConfirmationManager
    cm = ConfirmationManager()

    if allow:
        if cm.whitelist_action(action):
            console.print(f"[green]Action '{action}' is now trusted.[/green]")
        else:
            console.print(f"[yellow]Action '{action}' was already trusted.[/yellow]")
    else:
        # Show status
        if action in cm.whitelist["allowed_actions"]:
            console.print(f"[green]'{action}' is currently TRUSTED.[/green]")
        else:
            console.print(f"[yellow]'{action}' is NOT trusted.[/yellow]")


@app.command()
def replay(task_id: str = typer.Argument(None, help="Task ID to replay"), last: bool = typer.Option(False, "--last", help="Replay last task"), filter_app: str = typer.Option(None, "--filter", help="Filter by app (action arg)")):
    """
    Replay agent actions.
    """
    from fyodoros.kernel.action_logger import ActionLogger
    logger = ActionLogger()

    if last:
        task_id = logger.get_last_task_id()
        if not task_id:
            console.print("[red]No logs found.[/red]")
            return

    if not task_id:
        console.print("[red]Please provide a TASK_ID or use --last[/red]")
        return

    logs = logger.get_logs(task_id)
    if not logs:
        console.print(f"[yellow]No logs found for task {task_id}[/yellow]")
        return

    console.print(f"[bold cyan]Replaying Task: {task_id}[/bold cyan]")

    for entry in logs:
        # Check filter
        if filter_app:
            # Check if filter string is in action name or args
            if filter_app not in str(entry["action"]) and filter_app not in str(entry["args"]):
                continue

        console.print(Panel(
            f"[bold]Step {entry['step']}: {entry['action']}[/bold]\n"
            f"Args: {entry['args']}\n"
            f"Reasoning: {entry['reasoning']}\n"
            f"Result: {entry['result']}\n"
            f"[dim]Duration: {entry['duration_ms']:.2f}ms | Tokens: {entry['tokens_used']}[/dim]",
            title=f"{entry['timestamp']}"
        ))


@app.command()
def diagnose():
    """
    Troubleshoot system issues.
    Checks logs, config, network, and services.
    """
    console.print(Panel("FyodorOS Diagnostic Tool", style="bold blue"))

    # 1. Check Config
    config_path = Path(".env")
    if config_path.exists():
        console.print("[green]✓ Configuration file exists[/green]")
        # Check permission (should be 600)
        mode = oct(config_path.stat().st_mode)[-3:]
        if mode == "600":
            console.print("[green]✓ Config permissions secure (600)[/green]")
        else:
            console.print(f"[yellow]! Config permissions insecure ({mode}). Run 'chmod 600 .env'[/yellow]")
    else:
        console.print("[red]✗ Configuration file missing (run 'fyodor setup')[/red]")

    # 2. Check Network
    try:
        import socket
        socket.create_connection(("8.8.8.8", 53), timeout=2)
        console.print("[green]✓ Network connectivity verified[/green]")
    except Exception as e:
        console.print(f"[red]✗ Network unreachable: {e}[/red]")

    # 3. Check Dependencies
    deps = ["docker", "kubectl", "nasm"]
    for dep in deps:
        if shutil.which(dep):
            console.print(f"[green]✓ {dep} found[/green]")
        else:
            console.print(f"[yellow]! {dep} not found in PATH[/yellow]")

    # 4. Check Logs
    log_dir = Path.home() / ".fyodor" / "logs"
    error_log = log_dir / "errors.log"
    if error_log.exists() and error_log.stat().st_size > 0:
        console.print(f"[yellow]! Found errors in {error_log}:[/yellow]")
        try:
            with open(error_log, "r") as f:
                lines = f.readlines()
                last_few = lines[-5:]
                for line in last_few:
                    console.print(f"  [red]{line.strip()}[/red]")
        except:
            pass
    else:
        console.print("[green]✓ No recent error logs found[/green]")

    console.print("\n[blue]Diagnosis complete.[/blue]")


@app.command()
def info():
    """
    Show info about the installation.
    """
    console.print(BANNER, style="bold cyan")
    console.print("Version: 0.7.0")
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
