from pathlib import Path
from traceback import format_exception_only

from PySide6.QtCore import QObject, Signal, Slot

from markitdown import MarkItDown


class BatchConvertWorker(QObject):
    file_finished = Signal(str, str, str)
    file_failed = Signal(str, str)
    progress = Signal(int, int)
    finished = Signal()

    def __init__(
        self,
        paths: list[str],
        output_dir: str,
        *,
        enable_plugins: bool = False,
    ) -> None:
        super().__init__()
        self._paths = paths
        self._output_dir = output_dir
        self._enable_plugins = enable_plugins

    @Slot()
    def run(self) -> None:
        markitdown = MarkItDown(enable_plugins=self._enable_plugins)
        output_dir = Path(self._output_dir)
        total = len(self._paths)

        for index, raw_path in enumerate(self._paths, start=1):
            source_path = Path(raw_path)
            output_path = output_dir / f"{source_path.stem}.md"

            try:
                result = markitdown.convert_local(str(source_path))
                output_path.write_text(result.markdown, encoding="utf-8")
            except Exception as exc:  # Keep the batch moving when one file fails.
                message = "".join(format_exception_only(type(exc), exc)).strip()
                self.file_failed.emit(str(source_path), message)
            else:
                self.file_finished.emit(
                    str(source_path),
                    str(output_path),
                    result.markdown,
                )
            finally:
                self.progress.emit(index, total)

        self.finished.emit()
