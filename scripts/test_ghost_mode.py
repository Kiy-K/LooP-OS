#!/usr/bin/env python3
"""
Test Ghost Mode.

This interactive script verifies the "Ears" of LooP.
It boots the kernel, listens for the global hotkey (Alt+Space), and confirms that:
1. The Wake Signal is generated.
2. The UI Context is captured (buffered).
"""

import sys
import time
import os
from loop.kernel.kernel import Kernel
from loop.kernel.io import APIAdapter
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

def main():
    console.print(Panel.fit("[bold blue]👻 LooP Ghost Mode Test[/bold blue]", border_style="blue"))

    # 1. Boot Kernel
    console.print("[yellow]1. Booting Kernel (Simplified Mode)...[/yellow]")
    io = APIAdapter()
    kernel = Kernel(io_adapter=io)

    # Disable network guard to avoid permission prompts during test if unrelated
    # (Though we shouldn't really disable it, but for test simplicity let's assume default)

    # 2. Attach Ears
    console.print("[yellow]2. Attaching Ears (Background Listener)...[/yellow]")
    # Kernel starts listener in start(), but start() is blocking.
    # We want to run the loop manually here.
    # We can just start the listener directly since we have the instance.
    kernel.listener.start()

    # 3. Monitor Signals
    console.print(Panel("[bold green]🎧 Listening for Alt+Space... Press it now![/bold green]", border_style="green"))

    try:
        while True:
            # Poll for signals
            signal = io.get_signal()
            if signal:
                console.print(f"[bold cyan]⚡ Signal Received: {signal}[/bold cyan]")

                if signal == "WAKE":
                    # 4. Verify Context Capture
                    console.print("[yellow]   Verifying Sensory Buffer...[/yellow]")

                    last_scan = kernel.sys.last_ui_scan

                    if last_scan:
                        window_name = last_scan.get("window", "Unknown")
                        console.print(Panel.fit(
                            f"[bold green]👻 GHOST MODE ACTIVE![/bold green]\n"
                            f"Woke up and saw: [bold white]{window_name}[/bold white]",
                            border_style="green"
                        ))
                        # Dump tree snippet
                        console.print(f"   Scan Data Snippet: {str(last_scan)[:100]}...")
                        break
                    else:
                        console.print("[bold red]❌ Failed: Wake signal received but Sensory Buffer is empty![/bold red]")
                        break

            # Poll for output (just in case listener logs something)
            # The listener logs via python logging, not io.write generally, but let's check.
            output = io.get_output()
            if output:
                console.print(f"[dim]kernel: {output}[/dim]")

            time.sleep(0.1)

    except KeyboardInterrupt:
        console.print("\n[red]Test Cancelled.[/red]")
    finally:
        console.print("[yellow]Shutting down...[/yellow]")
        kernel.listener.stop()
        # kernel.shutdown() # Full shutdown might be noisy, listener stop is enough for test

if __name__ == "__main__":
    main()
