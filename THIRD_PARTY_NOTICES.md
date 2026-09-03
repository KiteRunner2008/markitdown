# Third-Party Notices

This repository is based on Microsoft MarkItDown and preserves the upstream MIT license in `LICENSE`.

The desktop package in `packages/markitdown-desktop` bundles or depends on third-party open-source packages when building Windows binaries. Review the installed package metadata before each public release, especially if dependency versions change.

## Direct Desktop Dependencies

| Component | Version used during v0.1.1 packaging | License noted by package metadata | Purpose |
| --- | --- | --- | --- |
| MarkItDown | 0.1.7 | MIT | Document-to-Markdown conversion engine |
| PySide6 | 6.10.1 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | Qt desktop GUI bindings |
| pandas | 3.0.5 | BSD 3-Clause | Excel data handling used by MarkItDown optional dependencies |
| openpyxl | 3.1.5 | MIT | `.xlsx` file support |
| xlrd | 2.0.2 | BSD | `.xls` file support |
| PyInstaller | 6.22.2 | GPLv2-or-later with PyInstaller bootloader exception | Windows application packaging |

## Distribution Notes

The Windows installer and portable zip include Python runtime files and transitive dependencies collected by PyInstaller. Keep license files and metadata that PyInstaller collects with the bundled application, and verify compliance for PySide6/Qt LGPL terms before distributing binaries.

This file is a practical notice for maintainers and users; it is not legal advice.
