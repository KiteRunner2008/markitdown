from pathlib import Path
from typing import Optional

from PySide6.QtCore import QByteArray, QSettings, Qt, QThread, QUrl
from PySide6.QtGui import (
    QAction,
    QCloseEvent,
    QColor,
    QDesktopServices,
    QDragEnterEvent,
    QDropEvent,
    QFont,
)
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from .batch_convert_worker import BatchConvertWorker
from .convert_worker import ConvertWorker


COL_FILE = 0
COL_STATUS = 1
COL_DETAIL = 2

PATH_ROLE = Qt.UserRole
STATUS_ROLE = Qt.UserRole + 1

STATUS_PENDING = "Pending"
STATUS_CONVERTING = "Converting"
STATUS_DONE = "Done"
STATUS_FAILED = "Failed"


class DropTableWidget(QTableWidget):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setAlternatingRowColors(True)
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["File", "Status", "Output / Details"])
        self.setMinimumWidth(420)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionResizeMode(COL_FILE, QHeaderView.Interactive)
        self.horizontalHeader().setSectionResizeMode(COL_STATUS, QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(COL_DETAIL, QHeaderView.Stretch)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        parent = self.window()
        if not isinstance(parent, MainWindow):
            return

        paths = [
            url.toLocalFile()
            for url in event.mimeData().urls()
            if url.isLocalFile() and Path(url.toLocalFile()).is_file()
        ]
        if paths:
            parent.add_files(paths)
            event.acceptProposedAction()
            return
        super().dropEvent(event)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MarkItDown Desktop")
        self.setAcceptDrops(True)
        self.resize(1180, 760)

        self._settings = QSettings(
            QSettings.IniFormat,
            QSettings.UserScope,
            "MarkItDown",
            "MarkItDown Desktop",
        )
        self._current_path: Optional[str] = None
        self._current_markdown = ""
        self._markdown_by_path: dict[str, str] = {}
        self._output_dir: Optional[str] = None
        self._thread: Optional[QThread] = None
        self._worker: Optional[ConvertWorker | BatchConvertWorker] = None

        self._open_action = QAction("Open", self)
        self._open_action.setIcon(self.style().standardIcon(QStyle.SP_DialogOpenButton))
        self._open_action.triggered.connect(self.open_files)

        self._remove_action = QAction("Remove", self)
        self._remove_action.setIcon(self.style().standardIcon(QStyle.SP_TrashIcon))
        self._remove_action.triggered.connect(self.remove_selected_file)
        self._remove_action.setEnabled(False)

        self._clear_action = QAction("Clear", self)
        self._clear_action.setIcon(self.style().standardIcon(QStyle.SP_DialogResetButton))
        self._clear_action.triggered.connect(self.clear_files)
        self._clear_action.setEnabled(False)

        self._output_dir_action = QAction("Output Folder", self)
        self._output_dir_action.setIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon))
        self._output_dir_action.triggered.connect(self.choose_output_dir)

        self._open_output_dir_action = QAction("Open Output", self)
        self._open_output_dir_action.setIcon(self.style().standardIcon(QStyle.SP_DirLinkIcon))
        self._open_output_dir_action.triggered.connect(self.open_output_dir)
        self._open_output_dir_action.setEnabled(False)

        self._convert_selected_action = QAction("Convert Selected", self)
        self._convert_selected_action.setIcon(self.style().standardIcon(QStyle.SP_ArrowRight))
        self._convert_selected_action.triggered.connect(self.convert_selected)
        self._convert_selected_action.setEnabled(False)

        self._convert_all_action = QAction("Convert All", self)
        self._convert_all_action.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self._convert_all_action.triggered.connect(self.convert_all)
        self._convert_all_action.setEnabled(False)

        self._retry_failed_action = QAction("Retry Failed", self)
        self._retry_failed_action.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        self._retry_failed_action.triggered.connect(self.retry_failed)
        self._retry_failed_action.setEnabled(False)

        self._save_action = QAction("Save", self)
        self._save_action.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        self._save_action.triggered.connect(self.save_markdown)
        self._save_action.setEnabled(False)

        self._copy_action = QAction("Copy", self)
        self._copy_action.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        self._copy_action.triggered.connect(self.copy_markdown)
        self._copy_action.setEnabled(False)

        self._render_action = QAction("Rendered", self)
        self._render_action.setCheckable(True)
        self._render_action.triggered.connect(self._refresh_markdown_views)
        self._render_action.setEnabled(False)

        self._plugin_toggle = QCheckBox("Plugins")
        self._plugin_toggle.setToolTip("Enable installed MarkItDown plugins for conversions.")

        self._output_dir_label = QLabel("No output folder")
        self._output_dir_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        toolbar.addAction(self._open_action)
        toolbar.addAction(self._remove_action)
        toolbar.addAction(self._clear_action)
        toolbar.addSeparator()
        toolbar.addAction(self._output_dir_action)
        toolbar.addAction(self._open_output_dir_action)
        toolbar.addSeparator()
        toolbar.addAction(self._convert_selected_action)
        toolbar.addAction(self._convert_all_action)
        toolbar.addAction(self._retry_failed_action)
        toolbar.addSeparator()
        toolbar.addAction(self._save_action)
        toolbar.addAction(self._copy_action)
        toolbar.addAction(self._render_action)
        toolbar.addSeparator()
        toolbar.addWidget(self._plugin_toggle)
        toolbar.addSeparator()
        toolbar.addWidget(self._output_dir_label)
        self.addToolBar(toolbar)

        self._file_table = DropTableWidget(self)
        self._file_table.itemSelectionChanged.connect(self._selection_changed)
        self._file_table.itemDoubleClicked.connect(self._convert_table_item)

        self._empty_state = self._build_empty_state()

        self._source_view = QPlainTextEdit()
        self._source_view.setReadOnly(True)
        self._source_view.setFont(QFont("Consolas", 10))

        self._rendered_view = QTextBrowser()
        self._rendered_view.setOpenExternalLinks(True)

        self._preview_stack = QStackedWidget()
        self._preview_stack.addWidget(self._empty_state)
        self._preview_stack.addWidget(self._source_view)
        self._preview_stack.addWidget(self._rendered_view)

        self._log_view = QPlainTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setMaximumHeight(150)
        self._log_view.document().setMaximumBlockCount(500)

        self._right_splitter = QSplitter(Qt.Vertical)
        self._right_splitter.addWidget(self._preview_stack)
        self._right_splitter.addWidget(self._log_view)
        self._right_splitter.setStretchFactor(0, 1)
        self._right_splitter.setStretchFactor(1, 0)

        self._main_splitter = QSplitter(Qt.Horizontal)
        self._main_splitter.addWidget(self._file_table)
        self._main_splitter.addWidget(self._right_splitter)
        self._main_splitter.setStretchFactor(0, 0)
        self._main_splitter.setStretchFactor(1, 1)

        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(self._main_splitter)
        self.setCentralWidget(container)

        status_bar = QStatusBar()
        self._progress_bar = QProgressBar()
        self._progress_bar.setFixedWidth(180)
        self._progress_bar.hide()
        status_bar.addPermanentWidget(self._progress_bar)
        self.setStatusBar(status_bar)
        self.statusBar().showMessage("Drop files here or choose Open.")
        self._restore_settings()
        self._update_file_actions()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._thread is not None:
            QMessageBox.information(
                self,
                "Conversion in progress",
                "Wait for the current conversion to finish before closing.",
            )
            event.ignore()
            return

        self._save_settings()
        super().closeEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        paths = [
            url.toLocalFile()
            for url in event.mimeData().urls()
            if url.isLocalFile() and Path(url.toLocalFile()).is_file()
        ]
        if paths:
            self.add_files(paths)
            event.acceptProposedAction()
            return
        super().dropEvent(event)

    def open_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Open files",
            "",
            "Documents (*.*)",
        )
        self.add_files(paths)

    def add_files(self, paths: list[str]) -> None:
        existing_paths = {self._path_for_row(row) for row in range(self._file_table.rowCount())}
        added = 0
        first_new_row: Optional[int] = None

        for raw_path in paths:
            path = str(Path(raw_path))
            if path in existing_paths:
                continue

            row = self._file_table.rowCount()
            self._file_table.insertRow(row)
            self._set_row_file(row, path)
            self._set_row_state(row, STATUS_PENDING, "Ready to convert")
            existing_paths.add(path)
            added += 1
            if first_new_row is None:
                first_new_row = row

        if first_new_row is not None:
            self._file_table.selectRow(first_new_row)
            self._append_log(f"Added {added} file(s).")

        self._update_file_actions()

    def remove_selected_file(self) -> None:
        if self._thread is not None:
            return

        row = self._selected_row()
        if row is None:
            return

        path = self._path_for_row(row)
        self._file_table.removeRow(row)
        if path is not None:
            self._markdown_by_path.pop(path, None)
            self._append_log(f"Removed {path}.")

        if path == self._current_path:
            self._current_path = None
            self._current_markdown = ""
            self._preview_stack.setCurrentWidget(self._empty_state)

        self._update_file_actions()

    def clear_files(self) -> None:
        if self._thread is not None:
            return

        self._file_table.setRowCount(0)
        self._markdown_by_path.clear()
        self._current_path = None
        self._current_markdown = ""
        self._preview_stack.setCurrentWidget(self._empty_state)
        self._append_log("Cleared file table.")
        self._update_file_actions()

    def choose_output_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            "Choose output folder",
            self._output_dir or "",
        )
        if not path:
            return

        self._output_dir = path
        self._output_dir_label.setText(path)
        self._output_dir_label.setToolTip(path)
        self._open_output_dir_action.setEnabled(True)
        self._settings.setValue("paths/output_dir", path)
        self._append_log(f"Output folder set to {path}.")
        self._update_file_actions()

    def open_output_dir(self) -> None:
        if self._output_dir is None:
            return

        QDesktopServices.openUrl(QUrl.fromLocalFile(self._output_dir))

    def convert_selected(self) -> None:
        row = self._selected_row()
        if row is not None:
            self._convert_row(row)

    def convert_all(self) -> None:
        paths = [
            path
            for row in range(self._file_table.rowCount())
            if (path := self._path_for_row(row)) is not None
        ]
        self._convert_batch(paths, "Batch conversion")

    def retry_failed(self) -> None:
        paths = [
            path
            for row in range(self._file_table.rowCount())
            if self._status_for_row(row) == STATUS_FAILED
            if (path := self._path_for_row(row)) is not None
        ]
        self._convert_batch(paths, "Retry failed")

    def save_markdown(self) -> None:
        if not self._current_markdown:
            return

        suggested_name = "converted.md"
        if self._current_path:
            suggested_name = f"{Path(self._current_path).stem}.md"

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Markdown",
            suggested_name,
            "Markdown (*.md);;Text files (*.txt);;All files (*.*)",
        )
        if not path:
            return

        Path(path).write_text(self._current_markdown, encoding="utf-8")
        self.statusBar().showMessage(f"Saved {path}")
        self._append_log(f"Saved current Markdown to {path}.")

    def copy_markdown(self) -> None:
        if not self._current_markdown:
            return
        QApplication.clipboard().setText(self._current_markdown)
        self.statusBar().showMessage("Markdown copied to clipboard.")
        self._append_log("Copied current Markdown to clipboard.")

    def _selection_changed(self) -> None:
        row = self._selected_row()
        if row is None:
            self._update_file_actions()
            return

        path = self._path_for_row(row)
        if path is None:
            self._update_file_actions()
            return

        self._current_path = path
        if path in self._markdown_by_path:
            self._current_markdown = self._markdown_by_path[path]
            self._refresh_markdown_views()
            self.statusBar().showMessage(f"Showing cached conversion for {path}")
        elif self._status_for_row(row) == STATUS_FAILED:
            self._current_markdown = ""
            self._source_view.setPlainText(self._detail_for_row(row))
            self._rendered_view.setPlainText(self._detail_for_row(row))
            self._preview_stack.setCurrentWidget(self._source_view)
        else:
            self._current_markdown = ""
            self._preview_stack.setCurrentWidget(self._empty_state)

        self._update_file_actions()

    def _convert_table_item(self, item: QTableWidgetItem) -> None:
        self._convert_row(item.row())

    def _convert_row(self, row: int) -> None:
        if self._thread is not None:
            QMessageBox.information(
                self,
                "Conversion in progress",
                "Wait for the current conversion to finish before starting another one.",
            )
            return

        path = self._path_for_row(row)
        if path is None:
            return

        self._current_path = path
        self._current_markdown = ""
        self._set_row_state(row, STATUS_CONVERTING, "Converting...")
        self._start_progress()
        self._set_busy(True)
        self._source_view.setPlainText("Converting...")
        self._rendered_view.setMarkdown("Converting...")
        self._preview_stack.setCurrentWidget(self._source_view)
        self._append_log(f"Converting {path}.")
        self.statusBar().showMessage(f"Converting {path}")

        self._thread = QThread(self)
        self._worker = ConvertWorker(
            path,
            enable_plugins=self._plugin_toggle.isChecked(),
        )
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._conversion_finished)
        self._worker.failed.connect(self._conversion_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._clear_worker)

        self._thread.start()

    def _convert_batch(self, paths: list[str], label: str) -> None:
        if self._thread is not None:
            QMessageBox.information(
                self,
                "Conversion in progress",
                "Wait for the current conversion to finish before starting another one.",
            )
            return

        if not paths:
            return

        if self._output_dir is None:
            self.choose_output_dir()
            if self._output_dir is None:
                return

        output_dir = Path(self._output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        for path in paths:
            row = self._find_row(path)
            if row is not None:
                self._set_row_state(row, STATUS_CONVERTING, "Queued")

        self._start_progress(len(paths))
        self._set_busy(True)
        self._source_view.setPlainText(f"{label}...")
        self._rendered_view.setMarkdown(f"{label}...")
        self._preview_stack.setCurrentWidget(self._source_view)
        self._append_log(f"{label} started for {len(paths)} file(s).")
        self.statusBar().showMessage(f"Converting {len(paths)} files")

        self._thread = QThread(self)
        self._worker = BatchConvertWorker(
            paths,
            str(output_dir),
            enable_plugins=self._plugin_toggle.isChecked(),
        )
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.file_finished.connect(self._batch_file_finished)
        self._worker.file_failed.connect(self._batch_file_failed)
        self._worker.progress.connect(self._batch_progress)
        self._worker.finished.connect(self._batch_finished)
        self._worker.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._clear_worker)

        self._thread.start()

    def _conversion_finished(self, path: str, markdown: str) -> None:
        self._current_path = path
        self._current_markdown = markdown
        self._markdown_by_path[path] = markdown
        row = self._find_row(path)
        if row is not None:
            self._set_row_state(row, STATUS_DONE, "Converted in preview")
        self._refresh_markdown_views()
        self._stop_progress()
        self._set_busy(False)
        self._append_log(f"Converted {path}.")
        self.statusBar().showMessage(f"Converted {path}")

    def _conversion_failed(self, path: str, message: str) -> None:
        self._current_path = path
        self._current_markdown = ""
        row = self._find_row(path)
        if row is not None:
            self._set_row_state(row, STATUS_FAILED, message)
        self._source_view.setPlainText(message)
        self._rendered_view.setPlainText(message)
        self._preview_stack.setCurrentWidget(self._source_view)
        self._stop_progress()
        self._set_busy(False, has_markdown=False)
        self._append_log(f"Failed to convert {path}: {message}")
        self.statusBar().showMessage(f"Could not convert {path}")
        QMessageBox.warning(self, "Conversion failed", message)

    def _batch_file_finished(self, path: str, output_path: str, markdown: str) -> None:
        self._markdown_by_path[path] = markdown
        row = self._find_row(path)
        if row is not None:
            self._set_row_state(row, STATUS_DONE, output_path)

        self._append_log(f"Converted {path} -> {output_path}.")
        if self._current_path == path:
            self._current_markdown = markdown
            self._refresh_markdown_views()

    def _batch_file_failed(self, path: str, message: str) -> None:
        row = self._find_row(path)
        if row is not None:
            self._set_row_state(row, STATUS_FAILED, message)
        self._append_log(f"Failed to convert {path}: {message}")

    def _batch_progress(self, completed: int, total: int) -> None:
        self._progress_bar.setMaximum(total)
        self._progress_bar.setValue(completed)
        self.statusBar().showMessage(f"Converted {completed} of {total} files")

    def _batch_finished(self) -> None:
        self._stop_progress()
        self._set_busy(False, has_markdown=bool(self._current_markdown))
        self._append_log(f"Batch conversion finished in {self._output_dir}.")
        self.statusBar().showMessage(f"Batch conversion finished in {self._output_dir}")

    def _clear_worker(self) -> None:
        self._thread = None
        self._worker = None
        self._update_file_actions()

    def _refresh_markdown_views(self) -> None:
        self._source_view.setPlainText(self._current_markdown)
        self._rendered_view.setMarkdown(self._current_markdown)
        if self._render_action.isChecked():
            self._preview_stack.setCurrentWidget(self._rendered_view)
        else:
            self._preview_stack.setCurrentWidget(self._source_view)

    def _set_busy(self, busy: bool, *, has_markdown: Optional[bool] = None) -> None:
        markdown_available = bool(self._current_markdown) if has_markdown is None else has_markdown
        self._open_action.setEnabled(not busy)
        self._remove_action.setEnabled(not busy and self._selected_row() is not None)
        self._clear_action.setEnabled(not busy and self._file_table.rowCount() > 0)
        self._output_dir_action.setEnabled(not busy)
        self._open_output_dir_action.setEnabled(not busy and self._output_dir is not None)
        self._convert_selected_action.setEnabled(not busy and self._selected_row() is not None)
        self._convert_all_action.setEnabled(not busy and self._file_table.rowCount() > 0)
        self._retry_failed_action.setEnabled(not busy and self._has_failed_rows())
        self._plugin_toggle.setEnabled(not busy)
        self._save_action.setEnabled(not busy and markdown_available)
        self._copy_action.setEnabled(not busy and markdown_available)
        self._render_action.setEnabled(not busy and markdown_available)

    def _update_file_actions(self) -> None:
        self._set_busy(self._thread is not None)

    def _set_row_file(self, row: int, path: str) -> None:
        file_item = QTableWidgetItem(Path(path).name)
        file_item.setData(PATH_ROLE, path)
        file_item.setToolTip(path)

        status_item = QTableWidgetItem()
        status_item.setTextAlignment(Qt.AlignCenter)
        status_item.setData(PATH_ROLE, path)

        detail_item = QTableWidgetItem()
        detail_item.setData(PATH_ROLE, path)

        self._file_table.setItem(row, COL_FILE, file_item)
        self._file_table.setItem(row, COL_STATUS, status_item)
        self._file_table.setItem(row, COL_DETAIL, detail_item)

    def _set_row_state(self, row: int, status: str, detail: str = "") -> None:
        status_item = self._file_table.item(row, COL_STATUS)
        detail_item = self._file_table.item(row, COL_DETAIL)
        file_item = self._file_table.item(row, COL_FILE)
        if status_item is None or detail_item is None or file_item is None:
            return

        status_item.setText(status)
        status_item.setData(STATUS_ROLE, status)
        detail_item.setText(detail)
        status_item.setForeground(self._status_color(status))
        tooltip = "\n".join(part for part in [file_item.data(PATH_ROLE), detail] if part)
        file_item.setToolTip(tooltip)
        status_item.setToolTip(detail)
        detail_item.setToolTip(detail)

    def _selected_row(self) -> Optional[int]:
        indexes = self._file_table.selectionModel().selectedRows()
        if not indexes:
            return None
        return indexes[0].row()

    def _path_for_row(self, row: int) -> Optional[str]:
        item = self._file_table.item(row, COL_FILE)
        if item is None:
            return None
        path = item.data(PATH_ROLE)
        return path if isinstance(path, str) else None

    def _status_for_row(self, row: int) -> Optional[str]:
        item = self._file_table.item(row, COL_STATUS)
        if item is None:
            return None
        status = item.data(STATUS_ROLE)
        return status if isinstance(status, str) else None

    def _detail_for_row(self, row: int) -> str:
        item = self._file_table.item(row, COL_DETAIL)
        return item.text() if item is not None else ""

    def _find_row(self, path: str) -> Optional[int]:
        for row in range(self._file_table.rowCount()):
            if self._path_for_row(row) == path:
                return row
        return None

    def _has_failed_rows(self) -> bool:
        return any(
            self._status_for_row(row) == STATUS_FAILED
            for row in range(self._file_table.rowCount())
        )

    def _status_color(self, status: str) -> QColor:
        if status == STATUS_DONE:
            return QColor("#167c3a")
        if status == STATUS_FAILED:
            return QColor("#b42318")
        if status == STATUS_CONVERTING:
            return QColor("#175cd3")
        return QColor("#555555")

    def _start_progress(self, maximum: int = 0) -> None:
        self._progress_bar.setRange(0, maximum)
        self._progress_bar.setValue(0)
        self._progress_bar.show()

    def _stop_progress(self) -> None:
        self._progress_bar.hide()
        self._progress_bar.setRange(0, 1)
        self._progress_bar.setValue(0)

    def _append_log(self, message: str) -> None:
        self._log_view.appendPlainText(message)

    def _restore_settings(self) -> None:
        geometry = self._settings.value("window/geometry")
        if isinstance(geometry, QByteArray):
            self.restoreGeometry(geometry)

        main_splitter_state = self._settings.value("window/main_splitter")
        if isinstance(main_splitter_state, QByteArray):
            self._main_splitter.restoreState(main_splitter_state)

        right_splitter_state = self._settings.value("window/right_splitter")
        if isinstance(right_splitter_state, QByteArray):
            self._right_splitter.restoreState(right_splitter_state)

        table_header_state = self._settings.value("window/file_table_header")
        if isinstance(table_header_state, QByteArray):
            self._file_table.horizontalHeader().restoreState(table_header_state)

        self._plugin_toggle.setChecked(
            self._settings_bool("conversion/enable_plugins", False)
        )
        self._render_action.setChecked(self._settings_bool("preview/rendered", False))

        output_dir = self._settings.value("paths/output_dir")
        if isinstance(output_dir, str) and output_dir:
            self._output_dir = output_dir
            self._output_dir_label.setText(output_dir)
            self._output_dir_label.setToolTip(output_dir)
            self._open_output_dir_action.setEnabled(True)

    def _save_settings(self) -> None:
        self._settings.setValue("window/geometry", self.saveGeometry())
        self._settings.setValue("window/main_splitter", self._main_splitter.saveState())
        self._settings.setValue("window/right_splitter", self._right_splitter.saveState())
        self._settings.setValue(
            "window/file_table_header",
            self._file_table.horizontalHeader().saveState(),
        )
        self._settings.setValue(
            "conversion/enable_plugins",
            self._plugin_toggle.isChecked(),
        )
        self._settings.setValue("preview/rendered", self._render_action.isChecked())
        if self._output_dir is not None:
            self._settings.setValue("paths/output_dir", self._output_dir)
        self._settings.sync()

    def _settings_bool(self, key: str, default: bool) -> bool:
        value = self._settings.value(key, default)
        if isinstance(value, bool):
            return value
        return str(value).lower() in {"1", "true", "yes", "on"}

    def _build_empty_state(self) -> QWidget:
        frame = QFrame()
        frame.setFrameShape(QFrame.NoFrame)

        title = QLabel("Drop files to convert")
        title.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)

        subtitle = QLabel("Use Open, drag local documents into the table, or double-click a row.")
        subtitle.setAlignment(Qt.AlignCenter)

        open_button = QPushButton("Open files")
        open_button.clicked.connect(self.open_files)
        open_button.setFixedWidth(140)

        layout = QVBoxLayout(frame)
        layout.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(12)
        layout.addWidget(open_button, alignment=Qt.AlignCenter)
        return frame
