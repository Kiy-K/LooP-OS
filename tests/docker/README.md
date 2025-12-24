# LooP Kiosk Test Bench

This directory contains the Docker configuration to simulate a "Kiosk Mode" Linux Desktop environment using `linuxserver/webtop`. This validates that LooP can successfully act as the Primary Shell/Session Manager.

## 1. Build the Image

From the root of the repository:

```bash
docker build -t loop-kiosk -f tests/docker/Dockerfile.kiosk .
```

## 2. Run the Container

Run the container in detached mode, mapping port 3000.

```bash
docker run -d \
  -p 3000:3000 \
  --name loop-lab \
  --cap-add=SYS_ADMIN \
  loop-kiosk
```

## 3. Access the Desktop

Open your browser and navigate to:
[http://localhost:3000](http://localhost:3000)

You should see a standard Ubuntu XFCE desktop.

## 4. Trigger Kiosk Takeover

Once inside the desktop (via browser), open a terminal inside the GUI, or execute the script via `docker exec`:

```bash
# Copy the script into the running container (if not already there via build, but build copies src, not scripts unless added)
# Since the Dockerfile only copies src/ and pyproject.toml, you might need to copy the script manually or mount it.
# The takeover script is located in tests/docker/simulate_takeover.sh in your repo.

docker cp tests/docker/simulate_takeover.sh loop-lab:/config/simulate_takeover.sh
docker exec -it loop-lab bash -c "chmod +x /config/simulate_takeover.sh && /config/simulate_takeover.sh"
```

## 5. Verify

After running the takeover script:
1.  Restart the container: `docker restart loop-lab`
2.  Refresh the browser page.
3.  You should see LooP starting up automatically (Terminal shell), and the XFCE panel should be missing or suppressed.
