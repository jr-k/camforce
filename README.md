# camforce

Parallel RTSP probe. Sweeps a target camera/NVR across dozens of vendor-specific paths, prints a live table with the forged URI for each attempt, and shows the real status (OK / 401 / 404 / TIMEOUT) so you can quickly find the working stream URL.

Built-in features:

- Self-contained vendor **presets** (paths + factory creds) shipped as plain text files under `vendors/<brand>/`. Drop your own `vendors/<brand>/` folder to register a new preset.
- Automatic Digest auth with **tolerance for quirky firmwares** (LIVE555, EvoStream, etc.): tries URI/algorithm variants until one is accepted
- Multi-instance YAML configuration: declare all your cameras once and probe them in one run
- Built-in presets: Ubiquiti, Hikvision, Dahua, Reolink, Axis, Foscam, plus a generic catch-all

## Install

<details open>
<summary><b>From source (venv)</b></summary>

```bash
git clone <repo-url> camforce
cd camforce

python3 -m venv .venv
source .venv/bin/activate

pip install .
```

Once installed, the `camforce` command is on your PATH as long as the venv is active.

</details>

<details>
<summary><b>Dev mode (no install)</b></summary>

If you don't want to reinstall on every edit, run the top-level shebang script from the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt    # runtime deps only, not the package

./camforce.py -c config.yaml
# or:
python3 camforce.py -c config.yaml
```

Source changes are picked up immediately on the next run, no reinstall needed.

</details>

<details>
<summary><b>System-wide wrapper</b></summary>

To call `camforce` from any shell without activating the venv every time:

```bash
sudo tee /usr/local/bin/camforce > /dev/null <<EOF
#!/usr/bin/env bash
exec $(pwd)/.venv/bin/camforce "\$@"
EOF
sudo chmod +x /usr/local/bin/camforce
```

</details>

<details>
<summary><b>Docker</b></summary>

Build the image, then run it with the config and vendors folder mounted (so you can edit presets without rebuilding):

```bash
docker build -t camforce:latest .

docker run --rm --network host \
    -v "$(pwd)/config.yaml:/app/config.yaml:ro" \
    -v "$(pwd)/vendors:/app/vendors:ro" \
    camforce:latest -c /app/config.yaml
```

</details>

<details>
<summary><b>Docker Compose</b></summary>

The shipped `docker-compose.yml` already wires `./config.yaml`, `./vendors/` and `network_mode: host`. Build once, then run:

```bash
docker compose build
docker compose run --rm camforce
```

The default command targets the mounted config. Override at runtime with flags:

```bash
docker compose run --rm camforce --host 192.168.1.10 -u admin -p secret -V ubiquiti
```

</details>

<details>
<summary><b>Docker networking note</b></summary>

- **Linux** : `--network host` (or `network_mode: host` in the compose file) puts the container directly on the host's network stack, LAN cameras (`192.168.x.x`) are reachable as if camforce was running on the host.
- **macOS / Windows** : `--network host` is largely a no-op (Docker Desktop runs the engine inside a Linux VM, so "host" is the VM, not your Mac/Windows). Drop the flag and rely on the default bridge. Whether the container can reach LAN cameras then depends on your Docker Desktop version, active VPN, and firewall. If `192.168.x.x` is unreachable from the container, the easiest path is the venv install (Docker won't help you here).

</details>

## Usage

**The recommended way to run camforce is from a YAML config file**: you describe every camera/NVR once, including which vendor presets to apply, and probe them all in a single command:

```bash
cp config.yaml.dist config.yaml
# edit config.yaml...
camforce -c config.yaml
```

Minimal `config.yaml`:

```yaml
instances:
  - name: "Garage"
    host: cam-garage.lan
    username: ubnt
    password: changeme
    vendors_presets:
      ubiquiti: true

  - name: "NVR"
    host: nvr.example.com
    port: 5542
    username: viewer
    password: changeme
    vendors_presets:
      hikvision: true
      dahua: true
    paths:
      - /Streaming/Channels/201
```

Every available knob (timeouts, workers, well-known scan, custom paths, etc.) is documented inline in `config.yaml.dist`. Start from there.

### Custom vendor presets

Drop your own brand by creating a `vendors/<name>/` folder with `credentials.txt` and/or `paths.txt`, then enable it in `config.yaml` via `vendors_presets: { name: true }`. File formats, semantics, and a worked example are documented in [vendors/README.md](vendors/README.md).

### Ad-hoc one-shot

For quick exploration of a single camera without writing a config file, all options are also available as CLI flags:

```bash
camforce --help
```

## License

MIT. See [LICENSE](LICENSE).
