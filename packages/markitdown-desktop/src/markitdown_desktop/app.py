import sys
import tempfile
from pathlib import Path


def _run_smoke_test() -> int:
    checks = (
        ("shiboken6", lambda: __import__("shiboken6")),
        ("PySide6", lambda: __import__("PySide6")),
        ("PySide6.QtCore", lambda: __import__("PySide6.QtCore", fromlist=["QtCore"])),
        ("PySide6.QtGui", lambda: __import__("PySide6.QtGui", fromlist=["QtGui"])),
        ("PySide6.QtWidgets", lambda: __import__("PySide6.QtWidgets", fromlist=["QtWidgets"])),
        ("MainWindow", lambda: __import__("markitdown_desktop.main_window", fromlist=["MainWindow"])),
    )
    for name, check in checks:
        check()
        print(f"smoke ok: {name}", file=sys.stderr)
    return 0


def _run_xlsx_smoke_test() -> int:
    from markitdown import MarkItDown
    from openpyxl import Workbook

    with tempfile.TemporaryDirectory() as tmp_dir:
        workbook_path = Path(tmp_dir) / "smoke.xlsx"
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Sheet1"
        sheet.append(["Name", "Score"])
        sheet.append(["Excel smoke", 100])
        workbook.save(workbook_path)

        result = MarkItDown().convert(workbook_path)
        markdown = result.markdown
        if "Excel smoke" not in markdown or "Score" not in markdown:
            raise RuntimeError("XLSX smoke test did not produce the expected Markdown.")

    print("smoke ok: xlsx conversion", file=sys.stderr)
    return 0


def main() -> int:
    if "--smoke-test" in sys.argv:
        return _run_smoke_test()
    if "--smoke-test-xlsx" in sys.argv:
        return _run_xlsx_smoke_test()

    from PySide6.QtWidgets import QApplication

    from .main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("MarkItDown Desktop")
    app.setOrganizationName("MarkItDown")

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
