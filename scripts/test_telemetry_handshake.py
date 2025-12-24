
import sys
import subprocess
import re
import time
import asyncio
import websockets
import os
import signal

def test_telemetry_handshake():
    """
    Tests the server startup with dynamic port allocation and WebSocket connection.
    """
    print("Starting test_telemetry_handshake...")

    # 1. Launch Server with port 0
    cmd = [sys.executable, "-u", "-m", "loop.cli", "serve", "--port", "0"]

    # We need to capture stdout to find the port
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1 # Line buffered
    )

    server_port = None

    try:
        # 2. Read stdout to find the port
        print("Waiting for server to start...")
        start_time = time.time()
        timeout = 20 # seconds

        while time.time() - start_time < timeout:
            line = process.stdout.readline()
            if not line:
                if process.poll() is not None:
                    print("Server process exited unexpectedly.")
                    stderr_out = process.stderr.read()
                    print(f"Stderr: {stderr_out}")
                    sys.exit(1)
                continue

            print(f"[Server Output] {line.strip()}")

            match = re.search(r"\[Server\] Listening on port: (\d+)", line)
            if match:
                server_port = int(match.group(1))
                print(f"Detected Server Port: {server_port}")
                break

        if server_port is None:
            print("Failed to detect server port within timeout.")
            sys.exit(1)

        # 3. Connect via WebSocket
        uri = f"ws://127.0.0.1:{server_port}/ws"
        print(f"Connecting to {uri}...")

        async def connect():
            max_retries = 10
            for i in range(max_retries):
                try:
                    print(f"Attempt {i+1}/{max_retries}...")
                    async with websockets.connect(uri) as websocket:
                        print("WebSocket Connected!")
                        return True
                except (OSError, ConnectionRefusedError) as e:
                    print(f"Connection attempt {i+1} failed: {e}. Retrying in 1s...")
                    await asyncio.sleep(1)
                except Exception as e:
                     print(f"Unexpected error: {e}")
                     return False
            return False

        # Run the async connection test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success = loop.run_until_complete(connect())

        if success:
            print("Handshake Test Passed!")
        else:
            print("Handshake Test Failed after retries.")
            sys.exit(1)

    except Exception as e:
        print(f"Test Exception: {e}")
        sys.exit(1)

    finally:
        # 4. Teardown
        print("Tearing down server process...")
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        print("Server stopped.")

if __name__ == "__main__":
    test_telemetry_handshake()
