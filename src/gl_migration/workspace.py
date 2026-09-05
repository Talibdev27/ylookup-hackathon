"""Where dataset 02's files live, once uploading is a real option.

`analyze()` always took explicit `gl_path`/`output_path` arguments, but nothing above it
ever passed anything but the bundled hackathon sample's hardcoded paths (`load.SOURCE_GL`,
`load.OUTPUT_LOADER`) -- there was no place for an uploaded file to land. This mirrors
`src/spine/workspace.py`'s pattern for dataset 01:

    data/gl-workspace/
        gl.xlsx       this tranche's investor-level GL, uploaded when a new one runs
        loader.xlsx   the corresponding upload template / reference loader workbook

Uploaded wins; the bundled sample is the fallback, per file independently -- uploading a
new GL against a loader workbook that is already set up is a real case, the same reason
dataset 01's workspace treats its workbook and statements independently rather than as an
all-or-nothing pair.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.gl_migration import load

WORKSPACE = Path("data/gl-workspace")


@dataclass
class GLWorkspace:
    gl: Path
    output: Path
    gl_is_bundled: bool
    output_is_bundled: bool

    @property
    def is_bundled(self) -> bool:
        return self.gl_is_bundled and self.output_is_bundled


def current() -> GLWorkspace:
    """What `analyze()` should read. Uploaded files win; the bundled sample is the
    fallback, checked independently for the GL and the loader workbook."""
    uploaded_gl = WORKSPACE / "gl.xlsx"
    uploaded_output = WORKSPACE / "loader.xlsx"
    gl_ready = uploaded_gl.exists()
    output_ready = uploaded_output.exists()
    return GLWorkspace(
        gl=uploaded_gl if gl_ready else load.SOURCE_GL,
        output=uploaded_output if output_ready else load.OUTPUT_LOADER,
        gl_is_bundled=not gl_ready,
        output_is_bundled=not output_ready,
    )


def save(gl_file=None, output_file=None) -> GLWorkspace:
    """Save whichever of the two uploaded workbooks was provided, leaving the other
    (uploaded or bundled) untouched -- same one-piece-at-a-time upload as dataset 01."""
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    if gl_file is not None:
        gl_file.save(str(WORKSPACE / "gl.xlsx"))
    if output_file is not None:
        output_file.save(str(WORKSPACE / "loader.xlsx"))
    return current()
