from __future__ import annotations

import subprocess
import threading
import uuid
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .config import settings
from .filesystem import VIDEO_EXTENSIONS, resolve_allowed
from .models import JobCreate, VcsiOptions


@dataclass
class Job:
    id: str
    status: str
    created_at: str
    files: list[str]
    output_dir: str
    commands: list[list[str]] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    current_file: str | None = None
    error: str | None = None
    logs: deque[str] = field(default_factory=lambda: deque(maxlen=settings.max_log_lines))

    def public(self) -> dict:
        data = asdict(self)
        data["logs"] = list(self.logs)
        return data


_jobs: dict[str, Job] = {}
_lock = threading.Lock()


def _output_extension(fmt: str) -> str:
    return "jpg" if fmt == "jpeg" else fmt


def build_command(input_file: Path, output_file: Path, o: VcsiOptions) -> list[str]:
    args = [
        settings.vcsi_binary,
        str(input_file),
        "-o", str(output_file),
        "-w", str(o.width),
        "-g", o.grid,
        "-f", o.image_format,
        "--quality", str(o.quality),
        "--start-delay-percent", str(o.start_delay_percent),
        "--end-delay-percent", str(o.end_delay_percent),
        "--timestamp-position", o.timestamp_position,
        "--metadata-position", o.metadata_position,
        "--background-color", o.background_color,
        "--metadata-font-color", o.metadata_font_color,
        "--timestamp-font-color", o.timestamp_font_color,
        "--timestamp-background-color", o.timestamp_background_color,
        "--timestamp-border-color", o.timestamp_border_color,
        "--timestamp-format", o.timestamp_format,
    ]
    if o.num_samples is not None:
        args += ["--num-samples", str(o.num_samples)]
    if o.show_timestamp:
        args.append("--show-timestamp")
    if o.accurate:
        args.append("--accurate")
    if o.fast:
        args.append("--fast")
    if o.no_overwrite:
        args.append("--no-overwrite")
    if o.frame_type:
        args += ["--frame-type", o.frame_type]
    if o.interval:
        args += ["--interval", o.interval]
    if o.manual_timestamps:
        args += ["--manual", o.manual_timestamps]
    return args


def validate_request(payload: JobCreate) -> tuple[list[Path], Path]:
    output_dir = resolve_allowed(payload.output_dir, settings.output_roots)
    if not output_dir.is_dir():
        raise ValueError("Output path must be a directory")

    files: list[Path] = []
    seen: set[Path] = set()
    for raw in payload.files:
        path = resolve_allowed(raw, settings.input_roots)
        if not path.is_file():
            raise ValueError(f"Input is not a file: {path}")
        if path.suffix.lower() not in VIDEO_EXTENSIONS:
            raise ValueError(f"Unsupported video file: {path.name}")
        if path not in seen:
            files.append(path)
            seen.add(path)
    return files, output_dir


def preview_commands(payload: JobCreate) -> list[list[str]]:
    files, output_dir = validate_request(payload)
    ext = _output_extension(payload.options.image_format)
    commands = []
    for input_file in files:
        output_file = output_dir / f"{input_file.stem}_contact-sheet.{ext}"
        commands.append(build_command(input_file, output_file, payload.options))
    return commands


def create_job(payload: JobCreate) -> Job:
    files, output_dir = validate_request(payload)
    job = Job(
        id=uuid.uuid4().hex[:12],
        status="queued",
        created_at=datetime.now(timezone.utc).isoformat(),
        files=[str(p) for p in files],
        output_dir=str(output_dir),
    )
    with _lock:
        _jobs[job.id] = job
    thread = threading.Thread(target=_run_job, args=(job.id, payload.options), daemon=True)
    thread.start()
    return job


def _run_job(job_id: str, options: VcsiOptions) -> None:
    job = _jobs[job_id]
    job.status = "running"
    ext = _output_extension(options.image_format)

    for raw in job.files:
        input_file = Path(raw)
        output_file = Path(job.output_dir) / f"{input_file.stem}_contact-sheet.{ext}"
        command = build_command(input_file, output_file, options)
        job.commands.append(command)
        job.current_file = str(input_file)
        job.logs.append(f"$ {' '.join(_quote_for_display(a) for a in command)}")

        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
            assert process.stdout is not None
            for line in process.stdout:
                job.logs.append(line.rstrip())
            return_code = process.wait()
        except FileNotFoundError:
            job.status = "failed"
            job.error = f"vcsi binary not found: {settings.vcsi_binary}"
            job.logs.append(job.error)
            return
        except Exception as exc:  # pragma: no cover - last-resort runtime guard
            job.status = "failed"
            job.error = str(exc)
            job.logs.append(f"ERROR: {exc}")
            return

        if return_code != 0:
            job.status = "failed"
            job.error = f"vcsi exited with code {return_code}"
            job.logs.append(job.error)
            return

        if output_file.exists():
            job.outputs.append(str(output_file))
        elif options.no_overwrite and output_file.exists():
            job.outputs.append(str(output_file))
        else:
            job.logs.append(f"Warning: expected output not found: {output_file}")

    job.current_file = None
    job.status = "completed"


def _quote_for_display(value: str) -> str:
    if value and all(c.isalnum() or c in "-._/:{}" for c in value):
        return value
    return '"' + value.replace('"', '\\"') + '"'


def get_job(job_id: str) -> Job | None:
    return _jobs.get(job_id)


def list_jobs() -> list[dict]:
    return [job.public() for job in reversed(list(_jobs.values()))]
