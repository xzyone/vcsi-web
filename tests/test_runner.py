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


def test_build_command_uses_integer_delay_percentages_and_custom_grid():
    cmd = build_command(
        Path("/media/example.mkv"),
        Path("/output/example.jpg"),
        VcsiOptions(grid="5x4", start_delay_percent=7, end_delay_percent=20),
    )
    start_index = cmd.index("--start-delay-percent")
    end_index = cmd.index("--end-delay-percent")
    grid_index = cmd.index("-g")

    assert cmd[start_index + 1] == "7"
    assert cmd[end_index + 1] == "20"
    assert cmd[grid_index + 1] == "5x4"
    assert "7.0" not in cmd
    assert "20.0" not in cmd
