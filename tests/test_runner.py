from pathlib import Path

from app.models import VcsiOptions
from app.runner import build_command


def test_build_command_has_no_shell_string():
    cmd = build_command(Path("/media/movie test.mkv"), Path("/output/result.jpg"), VcsiOptions())
    assert isinstance(cmd, list)
    assert cmd[0] == "vcsi"
    assert "/media/movie test.mkv" in cmd
    assert "--show-timestamp" in cmd
    assert "-g" in cmd and "4x4" in cmd
