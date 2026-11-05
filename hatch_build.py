"""建 wheel 時把 docs/ 放進 catime/docs，跳過卯時的資料夾 docs/maoshi/data。"""
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

SKIP = "docs/maoshi/data/"


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        root = Path(self.root)
        for f in sorted((root / "docs").rglob("*")):
            rel = f.relative_to(root).as_posix()
            if f.is_file() and not rel.startswith(SKIP):
                build_data["force_include"][str(f)] = "catime/" + rel
