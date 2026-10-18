# CitrusDrop — Windows file toolkit (v0.1)

An independent, Tangerine-inspired **offline** desktop file utility for Windows 10/11. This is a functional first version, **not** a clone of Tangerine's branding or proprietary interface.

## Features working in v0.1

- **Images:** PNG/JPEG/WebP conversion, compression by quality setting, aspect-ratio-preserving resize, **center crop** to pixel dimensions, rotate 90°. Supports JPEG, PNG, WebP, BMP, TIFF input.
- **PDF:** merge PDFs in list order, split into individual pages, rotate all pages by 90/180/270 degrees.
- **Video:** convert/compress common videos to H.264/AAC MP4, trim by start time and duration, control CRF quality.
- Batch processing, multi-file selection, custom output folder, unique output filenames, background jobs, all processing local.

## Install prerequisites

1. Install **Python 3.11 or newer** for Windows from https://www.python.org/downloads/windows/ . Enable **Add Python to PATH** in the installer. Tkinter is included with standard Windows Python.
2. Open **PowerShell** in this folder and run:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   python app.py
   ```

   If PowerShell blocks activation, run these commands without activating:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   .\.venv\Scripts\python.exe app.py
   ```

3. For **video tools only**, install FFmpeg from https://ffmpeg.org/download.html . On Windows, you can use `winget install --id Gyan.FFmpeg -e` if available. Restart PowerShell and the app, then check `ffmpeg -version`.

## Using the app

1. Click **Add files** and choose files.
2. Select **Images**, **PDF**, or **Video** tab and configure its settings.
3. Set an output folder (default: `Documents\CitrusDrop Output`).
4. Click **Process selected tab**. Selected list items are processed; if none are selected, all supported files for that tab are processed.
5. Originals are never overwritten. If an output filename already exists, the app appends a number.

**Note:** This version uses an **exact center crop**. Interactive drag-to-select crop, Explorer right-click integration, radial drop menu, PDF OCR, video preview, DOCX conversion, redaction, and file metadata tools are planned, not implemented. The app does not support drag-and-drop yet.

## Build an EXE

From a Windows terminal inside this folder:

```powershell
py -m pip install -r requirements.txt pyinstaller
py -m PyInstaller --noconfirm --clean --onefile --windowed --name CitrusDrop app.py
```

Output: `dist\CitrusDrop.exe`. Build the EXE **on Windows**, not Linux/macOS. The executable packages Python and Python dependencies but **does not bundle FFmpeg**; install FFmpeg separately for video operations. You can also double-click `build.bat` if `python` is on PATH.

## Architecture

```text
CitrusDrop/
├── app.py              # Tkinter UI, background processing and operations
├── requirements.txt    # Pillow + pypdf
├── build.bat           # Windows executable build
└── README.md           # Setup, use, limitations
```

## Next milestones

1. File drag-and-drop and radial action overlay.
2. Interactive image crop preview, batch presets and thumbnails.
3. PDF preview, page reorder, image-to-PDF, password workflows.
4. Video timeline and crop preview; progress and cancellation.
5. Windows Explorer context menu and installer; code signing.

## Security / license notes

Treat unknown PDFs/media as untrusted; use current dependency versions and FFmpeg updates. Do not distribute proprietary Tangerine assets or branding. Review licenses for third-party binaries before bundling or selling the app. This project has not yet been tested on a Windows machine.
