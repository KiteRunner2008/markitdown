import os
import sys
from pathlib import Path

_DLL_DIRECTORY_HANDLES: list[object] = []


def _add_packaged_dll_dirs() -> None:
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root is None or not hasattr(os, "add_dll_directory"):
        return

    internal_dir = Path(bundle_root)
    dll_dirs = [internal_dir / "PySide6", internal_dir / "shiboken6", internal_dir]
    existing_dll_dirs = [dll_dir for dll_dir in dll_dirs if dll_dir.exists()]

    if existing_dll_dirs:
        os.environ["PATH"] = os.pathsep.join(
            [str(dll_dir) for dll_dir in existing_dll_dirs] + [os.environ.get("PATH", "")]
        )

    for dll_dir in existing_dll_dirs:
        _DLL_DIRECTORY_HANDLES.append(os.add_dll_directory(str(dll_dir)))


def main() -> int:
    _add_packaged_dll_dirs()
    from markitdown_desktop.app import main as app_main

    return app_main()


if __name__ == "__main__":
    raise SystemExit(main())
