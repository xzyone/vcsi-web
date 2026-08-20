from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class VcsiOptions(BaseModel):
    width: int = Field(default=1500, ge=320, le=12000)
    grid: str = "4x4"
    num_samples: int | None = Field(default=None, ge=1, le=1000)
    show_timestamp: bool = True
    image_format: Literal["jpg", "jpeg", "png", "webp"] = "jpg"
    quality: int = Field(default=95, ge=0, le=100)
    start_delay_percent: float = Field(default=7, ge=0, le=99)
    end_delay_percent: float = Field(default=7, ge=0, le=99)
    timestamp_position: Literal["north", "south", "east", "west", "ne", "nw", "se", "sw", "center"] = "se"
    metadata_position: Literal["top", "bottom", "hidden"] = "top"
    background_color: str = "000000FF"
    metadata_font_color: str = "FFFFFFFF"
    timestamp_font_color: str = "FFFFFFFF"
    timestamp_background_color: str = "000000AA"
    timestamp_border_color: str = "000000FF"
    accurate: bool = False
    fast: bool = False
    no_overwrite: bool = False
    frame_type: Literal["I", "B", "P", "key"] | None = None
    interval: str | None = Field(default=None, max_length=80)
    manual_timestamps: str | None = Field(default=None, max_length=1000)
    timestamp_format: str = Field(default="{TIME}", max_length=200)

    @field_validator("grid")
    @classmethod
    def validate_grid(cls, value: str) -> str:
        parts = value.lower().split("x")
        if len(parts) != 2 or not all(part.isdigit() for part in parts):
            raise ValueError("Grid must look like 4x4")
        rows, cols = (int(p) for p in parts)
        if rows < 1 or cols < 1 or rows > 50 or cols > 50:
            raise ValueError("Grid values must be between 1 and 50")
        return f"{rows}x{cols}"

    @field_validator(
        "background_color",
        "metadata_font_color",
        "timestamp_font_color",
        "timestamp_background_color",
        "timestamp_border_color",
    )
    @classmethod
    def validate_color(cls, value: str) -> str:
        value = value.strip().lstrip("#").upper()
        if len(value) not in (6, 8) or any(c not in "0123456789ABCDEF" for c in value):
            raise ValueError("Color must be 6 or 8 hex digits")
        return value


class JobCreate(BaseModel):
    files: list[str] = Field(min_length=1, max_length=200)
    output_dir: str
    options: VcsiOptions = Field(default_factory=VcsiOptions)
