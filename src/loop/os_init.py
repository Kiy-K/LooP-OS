"""
LooP Init System - Container Entrypoint
Runs as PID 1 and manages the OS lifecycle
"""

import os
import sys
import time
import signal
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from loop.kernel.kernel import Kernel


class LooPInit:
    """
    OS Init System - Runs as PID 1 in container
    """
    
    def __init__(self):
        self.kernel = None
        self.running = False
        
        # Register signal handlers
        signal.signal(signal.SIGTERM, self.handle_shutdown)
        signal.signal(signal.SIGINT, self.handle_shutdown)
    
    def print_banner(self):
        """Print LooP boot banner"""
        banner = """
███████╗██╗   ██╗ ██████╗ ██████╗  ██████╗ ██████╗
██╔════╝╚██╗ ██╔╝██╔═══██╗██╔══██╗██╔═══██╗██╔══██╗
█████╗   ╚████╔╝ ██║   ██║██║  ██║██║   ██║██████╔╝
██╔══╝    ╚██╔╝  ██║   ██║██║  ██║██║   ██║██╔══██╗
██║        ██║   ╚██████╔╝██████╔╝╚██████╔╝██║  ██║
╚═╝        ╚═╝    ╚═════╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝
          The Experimental AI Microkernel
          
🚀 LooP v0.6.0 - Container Mode
"""
        print(banner)
    
    def setup_environment(self):
        """Setup container environment"""
        print("[INIT] Setting up environment...")
        
        # Create essential directories
        directories = [
            os.environ.get('LOOP_HOME', '/root/.loop'),
            '/var/log/loop',
            '/tmp/loop',
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
            print(f"  ✓ Created {directory}")
    
    def bootstrap_kernel(self):
        """Initialize the kernel"""
        print("[INIT] Bootstrapping kernel...")
        
        try:
            self.kernel = Kernel()
            print("  ✓ Kernel initialized")
            
            # Start autostart services
            if hasattr(self.kernel, 'service_manager'):
                print("[INIT] Starting system services...")
                self.kernel.service_manager.start_autostart_services()
                print("  ✓ Services started")
            
        except Exception as e:
            print(f"  ✗ Kernel initialization failed: {e}")
            sys.exit(1)
    
    def run(self):
        """Main init loop"""
        self.running = True
        
        print("[INIT] LooP is running (PID 1)")
        print("[INIT] Press Ctrl+C to shutdown\n")
        
        # Check if interactive mode
        interactive = os.environ.get('LOOP_INTERACTIVE', 'false').lower() == 'true'
        
        if interactive:
            print("Starting interactive shell...\n")
            # Launch shell
            os.system('loop start')
        else:
            # Keep container running
            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.handle_shutdown()
    
    def handle_shutdown(self, signum=None, frame=None):
        """Handle shutdown signals"""
        if not self.running:
            return
        
        print("\n[INIT] Shutdown signal received")
        self.running = False
        
        # Shutdown services
        if self.kernel and hasattr(self.kernel, 'service_manager'):
            print("[INIT] Stopping all services...")
            try:
                self.kernel.service_manager.shutdown()
                print("  ✓ Services stopped")
            except Exception as e:
                print(f"  ✗ Service shutdown error: {e}")
        
        print("[INIT] LooP halted")
        sys.exit(0)


def main():
    """Entry point for container"""
    init = LooPInit()
    
    try:
        init.print_banner()
        init.setup_environment()
        init.bootstrap_kernel()
        init.run()
    except Exception as e:
        print(f"\n[INIT] FATAL ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
