from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:
        # Run the frontend build so static assets are present for packaging.
        if os.environ.get("HIPPOBOX_SKIP_FRONTEND_BUILD") == "1":
            return

        root = Path(self.root)
        frontend_dir = (root / ".." / "frontend").resolve()
        if not frontend_dir.is_dir():
            raise RuntimeError(f"Frontend directory not found: {frontend_dir}")

        npm = shutil.which("npm")
        if not npm:
            raise RuntimeError("npm not found on PATH. Install Node.js to build the frontend.")

        node_modules = frontend_dir / "node_modules"
        if not node_modules.exists():
            self._run([npm, "install"], cwd=frontend_dir)

        self._run([npm, "run", "build"], cwd=frontend_dir)

        backend_dist = (root / "hippobox" / "static" / "dist").resolve()
        if not backend_dist.is_dir():
            raise RuntimeError("Frontend build did not produce backend static assets at " f"{backend_dist}.")

    def _run(self, cmd: list[str], cwd: Path) -> None:
        try:
            subprocess.run(cmd, cwd=str(cwd), check=True)
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(f"Command failed: {' '.join(cmd)}") from exc
