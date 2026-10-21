# Screen Capture Helper

A Windows desktop automation tool that drives a legacy terminal application, captures every screen it visits, and compiles the results into a single PDF. It replaces a manual process of navigating dozens of screens, copying each one, and pasting them into a document.

Built in Python with `tkinter`, `ctypes` (Win32 API) and `Pillow`.

## What it does

1. You enter a record ID and a date in a small GUI and press **Start**.
2. After a 3-second countdown you click the terminal window; the tool locks onto it.
3. It then runs a scripted sequence: types the record ID, navigates between screens with keyboard shortcuts, fills in form fields, and pages through long multi-page screens until the end marker appears.
4. Every screen is captured, and the full set is saved as one PDF named `<record-id>_<date>.pdf`.

Controls: **Skip step** (for the steps where the operator must click a row manually) and **Stop** (aborts safely and releases all keys).

## Technical highlights

- **Low-level keyboard input** via Win32 `SendInput` with hardware scan codes, so it works with terminal emulators that ignore virtual-key messages. Handles Shift for uppercase and symbols based on the active keyboard layout.
- **Fast screen capture** using GDI `BitBlt` / `GetDIBits`, limited to the locked window and clamped to the multi-monitor virtual desktop. DPI-aware.
- **Adaptive timing instead of fixed sleeps.** The tool waits until the screen actually changes (after a key press) and until it stops changing (before a capture), using downscaled image differencing (`PIL.ImageChops` + `ImageStat`). This is both faster and more reliable than hard-coded delays.
- **Clipboard-based end detection.** It copies each page's text through the clipboard (polling `GetClipboardSequenceNumber`) and looks for a "Bottom" marker to know when to stop paging.
- **Retry logic** for missed Page Down key presses, with a fast mode for later pages and a single `SLOWDOWN` multiplier to tune the whole script for slower machines.
- **Thread-safe GUI**: the automation runs in a worker thread, communicating with the `tkinter` UI through `root.after`, with `threading.Event` flags for stop and skip.
- **Failure-safe**: all modifier and navigation keys are released in a `finally` block so a crash never leaves a key stuck down.

## Requirements

- Windows 10/11
- Python 3.9+
- [Pillow](https://pypi.org/project/pillow/)

```bash
pip install -r requirements.txt
python screen_capture_helper.py
```

## Configuration

All timings, key sequences and screen numbers are constants at the top of `screen_capture_helper.py`. The most useful ones:

| Constant | Purpose |
| --- | --- |
| `SLOWDOWN` | Global speed multiplier (`1.0` = fastest, higher = safer) |
| `CAPTURE_KEYS` | Key sequence that copies the current screen to the clipboard |
| `FAST_AFTER_PAGE` | Page number from which faster timings are used |
| `SCREEN4_END_WORD` | Text that marks the last page of a scrolling screen |

## Note

The target application and its screen layout are specific to the environment this was built for, so this repository is a demonstration of the approach and the code, not something that runs against an arbitrary application out of the box. All company-specific names, data and branding have been removed.
