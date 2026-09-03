# MarkItDown Desktop v0.1.1

This is an unofficial Windows desktop build for MarkItDown.

## Downloads

- `MarkItDownDesktop-0.1.1-setup.exe`: Windows installer
- `MarkItDownDesktop-0.1.1-portable.zip`: Portable Windows build

## Checksums

```text
MarkItDownDesktop-0.1.1-portable.zip
SHA256: 854F33215C4A56E9E27D186B9B5FA40B1B660EC411114AA9F506F822877E42DF

MarkItDownDesktop-0.1.1-setup.exe
SHA256: BE3ED60FE158F3B1BA5F6293D3062C1B300485AB1EE5F06ECA5A9FA11B806EE1
```

## Highlights

- Added a PySide6 desktop GUI for local file-to-Markdown conversion.
- Added drag-and-drop file input, a file table, status column, output details, rendered/plain preview, copy, save, and output-folder batch conversion.
- Added retry support for failed conversions.
- Included Excel dependencies for `.xlsx` and `.xls` conversion.
- Added packaged smoke tests for application startup and `.xlsx` conversion.
- Removed bundled ICU DLLs after PyInstaller packaging to avoid Qt startup failures on Windows.

## Notes

- This project is not affiliated with or endorsed by Microsoft.
- The application performs local file reads with the privileges of the current user account.
- For best results, close older portable builds before running this release.

## Source

Fork source repository: `https://github.com/KiteRunner2008/markitdown`

Upstream project: `https://github.com/microsoft/markitdown`
