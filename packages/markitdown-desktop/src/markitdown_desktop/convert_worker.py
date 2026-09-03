from pathlib import Path
from traceback import format_exception_only

from PySide6.QtCore import QObject, Signal, Slot

from markitdown import MarkItDown


class ConvertWorker(QObject):
    finished = Signal(str, str)
    failed = Signal(str, str)

    def __init__(self, path: str, *, enable_plugins: bool = False) -> None:
        super().__init__()
        self._path = path
        self._enable_plugins = enable_plugins

    @Slot()
    def run(self) -> None:
        source_path = Path(self._path)
        try:
            markitdown = MarkItDown(enable_plugins=self._enable_plugins)
            result = markitdown.convert_local(str(source_path))
        except Exception as exc:  # Keep worker exceptions visible in the GUI.
            message = "".join(format_exception_only(type(exc), exc)).strip()
            self.failed.emit(str(source_path), message)
            return

        self.finished.emit(str(source_path), result.markdown)
