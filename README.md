# vcsi-web

A lightweight Web GUI for [vcsi](https://github.com/amietn/vcsi), designed for Docker, NAS and home-server use.

It lets you browse mounted video directories, select one or more files, map common `vcsi` CLI flags to GUI controls, choose a mounted output directory, preview the generated command, run jobs, inspect logs, and preview generated contact sheets.

## Features

- Browse only configured/mounted input roots
- Select multiple video files
- Browse and choose an output directory
- GUI controls for common `vcsi` options
- Advanced options for colors, frame type, interval and manual timestamps
- Backend-generated command preview
- Safe `subprocess.Popen([...])` execution with `shell=False`
- In-memory job queue/status/logs
- Generated image preview
- Docker / Docker Compose ready
- Input path confinement to reduce path traversal risk

## Quick start with Docker Compose

```bash
git clone https://github.com/xzyone/vcsi-web.git
cd vcsi-web
mkdir -p media output
# Put a test video under ./media, or edit docker-compose.yml to mount your real paths.
docker compose up -d --build
```

Open:

```text
http://YOUR-SERVER-IP:8080
```

Example NAS volume mapping:

```yaml
volumes:
  - /volume1/video:/media:ro
  - /volume1/vcsi-output:/output
```

For multiple input roots, mount them and set a comma-separated environment variable:

```yaml
environment:
  VCSI_INPUT_ROOTS: /movies,/tv,/downloads
  VCSI_OUTPUT_ROOTS: /output
volumes:
  - /volume1/movies:/movies:ro
  - /volume1/tv:/tv:ro
  - /volume1/downloads:/downloads:ro
  - /volume1/vcsi-output:/output
```

## Supported GUI options

The current UI maps these `vcsi` arguments:

- `-w / --width`
- `-g / --grid`
- `-s / --num-samples`
- `-t / --show-timestamp`
- `-f / --format`
- `--quality`
- `--start-delay-percent`
- `--end-delay-percent`
- `-T / --timestamp-position`
- `--metadata-position`
- `--background-color`
- `--metadata-font-color`
- `--timestamp-font-color`
- `--timestamp-background-color`
- `--timestamp-border-color`
- `-a / --accurate`
- `--fast`
- `--no-overwrite`
- `--frame-type`
- `--interval`
- `-m / --manual`
- `--timestamp-format`

Each input video is executed as a separate `vcsi` process so the GUI can write a predictable output file into the selected output directory:

```text
<video_stem>_contact-sheet.<format>
```

## Security model

This project intentionally does **not** expose a free-form shell command box.

- Input paths must resolve under `VCSI_INPUT_ROOTS`.
- Output paths must resolve under `VCSI_OUTPUT_ROOTS`.
- Only known video extensions can be submitted.
- GUI fields are validated with Pydantic.
- Commands are passed as argument arrays to `subprocess.Popen`; `shell=True` is not used.
- Mount source media as read-only when possible.

The app has no authentication in v0.1. Keep it on a trusted LAN or put it behind your reverse proxy/authentication layer before exposing it to the Internet.

## Local development

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export VCSI_INPUT_ROOTS="$PWD/media"
export VCSI_OUTPUT_ROOTS="$PWD/output"
mkdir -p media output
uvicorn app.main:app --reload
```

## Notes

`vcsi` requires `ffmpeg` and `ffprobe` in `PATH`. The supplied Dockerfile installs FFmpeg and DejaVu fonts.

Job state is in memory in this first version. Restarting the container clears job history, but generated files remain in the mounted output directory.

## License

MIT
