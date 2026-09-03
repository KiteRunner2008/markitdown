# MarkItDown Desktop

A small PySide6 desktop shell for converting local files to Markdown with MarkItDown.

This is an unofficial desktop package built on top of Microsoft MarkItDown. It is not affiliated with or endorsed by Microsoft.

## Development

From the repository root:

```powershell
.\.tools\Python312\python.exe -m venv .venv312
.\.venv312\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e "packages/markitdown[all]"
python -m pip install -e "packages/markitdown-desktop"
markitdown-desktop
```

The desktop shell supports local files only. Drop files into the window or use the open button, then save or copy the generated Markdown. The file table shows each file's conversion status and output path or error details. Use **Convert Selected**, double-click a row, or use **Output Folder** and **Convert All** to batch-convert every file in the table. Failed rows can be run again with **Retry Failed**.

The app remembers its window layout, file-table column widths, output folder, plugin setting, and preview mode between launches.

## Packaging on Windows

Install the packaging extra, then run the build script from the repository root:

```powershell
python -m pip install -e "packages/markitdown-desktop[package]"
.\packages\markitdown-desktop\scripts\build_windows.ps1
```

The desktop package includes MarkItDown's Excel dependencies for `.xlsx` and `.xls` files. The build script defaults to `.venv312\Scripts\python.exe` and validates the packaged executable with `--smoke-test` and `--smoke-test-xlsx`. It also removes bundled `icu*.dll` files after PyInstaller runs, which prevents PySide6's `Qt6Core.dll` from loading an incompatible app-local ICU runtime on Windows.

When building public release binaries, pass your repository URL so the installer points users to the right support location:

```powershell
.\packages\markitdown-desktop\scripts\build_windows.ps1 -RepositoryUrl "https://github.com/KiteRunner2008/markitdown"
```

The unpacked application is written to `dist\MarkItDownDesktop`, and the portable zip is written to `release\MarkItDownDesktop-0.1.1-portable.zip`.

To build the installer exe, install Inno Setup 6 so `ISCC.exe` is available, then rerun the same script. The installer is written to `release\MarkItDownDesktop-0.1.1-setup.exe`.

If `-RepositoryUrl` is omitted, the installer does not write publisher, support, or update URLs.
