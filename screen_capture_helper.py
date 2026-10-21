import ctypes
import os
import re
import sys
import threading
import time
import tkinter as tk
from ctypes import wintypes
from tkinter import filedialog
from PIL import Image, ImageChops, ImageStat, ImageTk


try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


try:
    ctypes.windll.winmm.timeBeginPeriod(1)
except Exception:
    pass

stop_flag = threading.Event()
skip_event = threading.Event()
VK_LBUTTON = 0x01
app = {"hwnd": None, "running": False}

COUNTDOWN = 3
TYPE_INTERVAL = 0.002
CAPTURE_DELAY = 0.2
HOLD_PAUSE = 0.04
PROMPT_WAIT = 0.2
SESSION_SWITCH_DELAY = 0.25
RECORD_LOAD_DELAY = 0.6
RECORD_ENTER_DELAY = 0.6
F6_DELAY = 0.4
ENTER_DELAY = 0.2
DOUBLE_ENTER_DELAY = 0.15
F3_DELAY = 0.1
SMALL_PAUSE = 0.04
SCREEN_DELAY = 0.35
STEP_DELAY = 0.1
AFTER_KEY_SETTLE = 0.03
SCREEN_TIMEOUT = 1.2
SCREEN_SETTLE = 0.03
AFTER_KEY_TIMEOUT = 1.5
KEY_HOLD = 0.006

CAPTURE_ONLY_APP = True
CAPTURE_KEYS = "alt+f, c, c"
F6_KEY = "f6"
FORM_NAV_KEYS = "tab, tab, tab, tab"
FORM_VALUE = "S"
TO_DATE_KEYS = ""
DATE_REMOVE_SLASHES = False
TO_SECOND_FIELD_KEYS = "tab"
SECOND_FIELD_VALUE = "A"
TO_SECOND_DATE_KEYS = ""

F3_MODE = "match"
F3_PRESSES = 3
F3_MAX_PRESSES = 10
F3_MATCH_THRESHOLD = 4.0

FAST_CAPTURE = True
COPY_TIMEOUT = 0.6
CLIPBOARD_POLL_INTERVAL = 0.003

SCREEN7_EXTRA_ENTERS = 2
SCREEN7_SECOND_BLANK_KEYS = "tab"
SCREEN7_SECOND_BLANK_VALUE = "3"

# Screen 95: you click the row yourself, then the script presses F4 and captures
SCREEN95_PRESS_F4 = True            # press F4 automatically after your click
SCREEN95_CLICK_SETTLE = 0.15        # wait after your click before F4

SCREEN4_MAX_PAGES = 500
SCREEN4_PAGEDOWN_KEYS = "pagedown"
SCREEN4_END_WORD = "bottom"
SCREEN4_TAIL_LINES = 8
SCREEN4_CHANGE_TIMEOUT = 1.2
SCREEN4_SETTLE = 0.01
SCREEN4_SAME_SCREEN = 0.15
SCREEN4_LOG = True
SCREEN4_SKIP_FIRST_PAGE = False     # True = do not keep the first page of screen 4 in the PDF (the rest are kept)

# ---------- Faster timings used from page 3 onward in screen 95 and screen 4 ----------
# These are NOT multiplied by SLOWDOWN. Pages 1..FAST_AFTER_PAGE use the normal safe timings.
FAST_AFTER_PAGE = 2          # pages 1..2 use the normal safe timings, page 3+ is fast
FAST_STABLE_FRAMES = 2       # identical screenshots needed before capture (normal = STABLE_FRAMES)
FAST_STABLE_INTERVAL = 0.02  # seconds between those screenshots (normal = STABLE_INTERVAL)
FAST_STABLE_TIMEOUT = 0.6    # never wait longer than this for the screen to settle
FAST_SETTLE = 0.005          # wait after the screen changes following Page Down
FAST_CHANGE_TIMEOUT = 0.8    # how long to wait for Page Down to redraw the screen
FAST_RETRY_SLEEP = 0.03      # pause before re-sending Page Down if the screen did not change
# If a page comes out half-drawn or duplicated: raise FAST_STABLE_FRAMES to 3 or FAST_SETTLE to 0.02.
# If you want it even faster: FAST_STABLE_FRAMES = 1 and FAST_AFTER_PAGE = 1.
# If a Page Down is missed and the loop ends early: raise FAST_CHANGE_TIMEOUT toward 1.2.

# ---------- Overall speed control ----------
# 1.0 = original speed. Higher = slower and safer (1.5 = 50% slower, 2.0 = twice as slow).
# If problems remain, raise it (try 2.0). If it is too slow, lower it (try 1.25).
SLOWDOWN = 1.6

TYPE_INTERVAL *= SLOWDOWN
CAPTURE_DELAY *= SLOWDOWN
HOLD_PAUSE *= SLOWDOWN
PROMPT_WAIT *= SLOWDOWN
SESSION_SWITCH_DELAY *= SLOWDOWN
RECORD_LOAD_DELAY *= SLOWDOWN
RECORD_ENTER_DELAY *= SLOWDOWN
F6_DELAY *= SLOWDOWN
ENTER_DELAY *= SLOWDOWN
DOUBLE_ENTER_DELAY *= SLOWDOWN
F3_DELAY *= SLOWDOWN
SMALL_PAUSE *= SLOWDOWN
SCREEN_DELAY *= SLOWDOWN
STEP_DELAY *= SLOWDOWN
AFTER_KEY_SETTLE *= SLOWDOWN
SCREEN_SETTLE *= SLOWDOWN
KEY_HOLD *= SLOWDOWN
SCREEN4_SETTLE *= SLOWDOWN
SCREEN95_CLICK_SETTLE *= SLOWDOWN

# Screen must stop changing (popup fully gone, page fully drawn) before every capture
STABLE_FRAMES = 3         # how many identical screenshots in a row count as "settled"
STABLE_INTERVAL = 0.04    # seconds between those screenshots
STABLE_DIFF = 0.05        # below this difference two screenshots count as identical
STABLE_TIMEOUT = 1.5      # never wait longer than this for the screen to settle

# ---------- 64-bit Safe Win32 API Definitions ----------
user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32

# Use c_void_p instead of wintypes.HWND to prevent 64-bit OverflowError
user32.GetForegroundWindow.restype = ctypes.c_void_p
user32.GetDC.restype = ctypes.c_void_p
user32.GetDC.argtypes = [ctypes.c_void_p]
user32.ReleaseDC.restype = ctypes.c_int
user32.ReleaseDC.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
user32.GetWindowTextW.argtypes = [ctypes.c_void_p, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int
user32.GetWindowRect.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.RECT)]
user32.GetWindowRect.restype = wintypes.BOOL
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
user32.GetCursorPos.restype = wintypes.BOOL
user32.GetSystemMetrics.argtypes = [ctypes.c_int]
user32.GetSystemMetrics.restype = ctypes.c_int
user32.VkKeyScanW.argtypes = [wintypes.WCHAR]
user32.VkKeyScanW.restype = ctypes.c_short
user32.MapVirtualKeyW.argtypes = [wintypes.UINT, wintypes.UINT]
user32.MapVirtualKeyW.restype = wintypes.UINT

gdi32.CreateCompatibleDC.restype = ctypes.c_void_p
gdi32.CreateCompatibleDC.argtypes = [ctypes.c_void_p]
gdi32.CreateCompatibleBitmap.restype = ctypes.c_void_p
gdi32.CreateCompatibleBitmap.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
gdi32.SelectObject.restype = ctypes.c_void_p
gdi32.SelectObject.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
gdi32.BitBlt.restype = wintypes.BOOL
gdi32.BitBlt.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                         ctypes.c_void_p, ctypes.c_int, ctypes.c_int, wintypes.DWORD]
gdi32.DeleteObject.restype = wintypes.BOOL
gdi32.DeleteObject.argtypes = [ctypes.c_void_p]
gdi32.DeleteDC.restype = wintypes.BOOL
gdi32.DeleteDC.argtypes = [ctypes.c_void_p]

user32.OpenClipboard.restype = wintypes.BOOL
user32.OpenClipboard.argtypes = [ctypes.c_void_p]
user32.CloseClipboard.restype = wintypes.BOOL
user32.EmptyClipboard.restype = wintypes.BOOL
user32.GetClipboardData.restype = ctypes.c_void_p
user32.GetClipboardData.argtypes = [wintypes.UINT]
user32.GetClipboardSequenceNumber.restype = wintypes.DWORD
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
kernel32.GlobalUnlock.restype = wintypes.BOOL
kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]

SRCCOPY = 0x00CC0020
CF_UNICODETEXT = 13

# Virtual screen metrics (covers all monitors)
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79

# Direct SendInput definitions
INPUT_KEYBOARD = 1
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class INPUT(ctypes.Structure):
    # The union MUST include MOUSEINPUT (largest member) so that
    # sizeof(INPUT) == 40 on 64-bit Windows. Otherwise SendInput fails silently.
    class _I(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT)]
    _anonymous_ = ("_input",)
    _fields_ = [("type", wintypes.DWORD), ("_input", _I)]


LPINPUT = ctypes.POINTER(INPUT)
user32.SendInput.argtypes = [wintypes.UINT, LPINPUT, ctypes.c_int]
user32.SendInput.restype = wintypes.UINT

SCAN_CODES = {
    "shift": (0x2A, False),
    "esc": (0x01, False),
    "enter": (0x1C, False),
    "tab": (0x0F, False),
    "f1": (0x3B, False),
    "f3": (0x3D, False),
    "f4": (0x3E, False),
    "f6": (0x40, False),
    "f9": (0x43, False),
    "f10": (0x44, False),
    "f12": (0x58, False),
    "pagedown": (0x51, True),
    "alt": (0x38, False),
    "ctrl": (0x1D, False),
}


def _send_scan(code, extended, press):
    flags = KEYEVENTF_SCANCODE
    if extended:
        flags |= KEYEVENTF_EXTENDEDKEY
    if not press:
        flags |= KEYEVENTF_KEYUP
    inp = INPUT(type=INPUT_KEYBOARD)
    inp.ki = KEYBDINPUT(wVk=0, wScan=code, dwFlags=flags, time=0, dwExtraInfo=0)
    sent = user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
    return sent


def _lookup(key):
    """Return (scan_code, extended, needs_shift) for a key name or single character."""
    name = key.lower()
    if name in SCAN_CODES:
        code, ext = SCAN_CODES[name]
        return code, ext, False
    if len(key) == 1:
        res = user32.VkKeyScanW(key)
        if res == -1:
            return 0, False, False
        vk = res & 0xFF
        shift_state = (res >> 8) & 0xFF
        code = user32.MapVirtualKeyW(vk, 0)  # MAPVK_VK_TO_VSC
        return code, False, bool(shift_state & 1)
    return 0, False, False


def raw_send_key(key, press=True):
    """Send a single key event (down or up) for a named key or a lowercase character."""
    name = key.lower()
    if name in SCAN_CODES:
        code, ext = SCAN_CODES[name]
    elif len(key) == 1:
        code, ext, _ = _lookup(key.lower())
    else:
        code, ext = 0, False
    if not code:
        return
    _send_scan(code, ext, press)


def fast_press(key, hold=KEY_HOLD):
    raw_send_key(key, True)
    if hold > 0:
        time.sleep(hold)
    raw_send_key(key, False)


def fast_hotkey(*keys):
    for k in keys:
        raw_send_key(k, True)
        time.sleep(0.002)
    for k in reversed(keys):
        raw_send_key(k, False)
        time.sleep(0.002)


def fast_type(text):
    """Type text using scancodes, honoring Shift for uppercase letters and symbols
    according to the current keyboard layout."""
    for char in text:
        code, ext, needs_shift = _lookup(char)
        if not code:
            continue
        if needs_shift:
            _send_scan(0x2A, False, True)
            time.sleep(0.002)
        _send_scan(code, ext, True)
        time.sleep(KEY_HOLD)
        _send_scan(code, ext, False)
        if needs_shift:
            time.sleep(0.002)
            _send_scan(0x2A, False, False)
        if TYPE_INTERVAL > 0:
            time.sleep(TYPE_INTERVAL)


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


gdi32.GetDIBits.argtypes = [ctypes.c_void_p, ctypes.c_void_p, wintypes.UINT, wintypes.UINT,
                            ctypes.c_void_p, ctypes.POINTER(BITMAPINFOHEADER), wintypes.UINT]
gdi32.GetDIBits.restype = ctypes.c_int


def virtual_screen():
    x = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
    y = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
    w = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
    h = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
    if w <= 0 or h <= 0:
        w = user32.GetSystemMetrics(0)
        h = user32.GetSystemMetrics(1)
        x = y = 0
    return x, y, w, h


def win32_capture_rect(l, t, w, h):
    hwin_dc = user32.GetDC(None)
    mem_dc = gdi32.CreateCompatibleDC(hwin_dc)
    bitmap = gdi32.CreateCompatibleBitmap(hwin_dc, w, h)
    old_obj = gdi32.SelectObject(mem_dc, bitmap)

    gdi32.BitBlt(mem_dc, 0, 0, w, h, hwin_dc, l, t, SRCCOPY)

    # The bitmap must NOT be selected into a DC when calling GetDIBits
    gdi32.SelectObject(mem_dc, old_obj)

    bih = BITMAPINFOHEADER()
    bih.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bih.biWidth = w
    bih.biHeight = -h  # top-down
    bih.biPlanes = 1
    bih.biBitCount = 32
    bih.biCompression = 0

    buf_size = w * h * 4
    buf = ctypes.create_string_buffer(buf_size)
    gdi32.GetDIBits(mem_dc, bitmap, 0, h, buf, ctypes.byref(bih), 0)

    gdi32.DeleteObject(bitmap)
    gdi32.DeleteDC(mem_dc)
    user32.ReleaseDC(None, hwin_dc)

    img = Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", 0, 1)
    return img.convert("RGB")


def window_title(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(ctypes.c_void_p(hwnd), buf, 256)
    return buf.value


def window_rect(hwnd):
    rect = wintypes.RECT()
    try:
        res = ctypes.windll.dwmapi.DwmGetWindowAttribute(
            ctypes.c_void_p(hwnd), ctypes.c_uint(9), ctypes.byref(rect), ctypes.sizeof(rect)
        )
        if res != 0:
            raise OSError
    except Exception:
        user32.GetWindowRect(ctypes.c_void_p(hwnd), ctypes.byref(rect))
    return rect.left, rect.top, rect.right, rect.bottom


def grab():
    vx, vy, vw, vh = virtual_screen()
    if CAPTURE_ONLY_APP and app["hwnd"]:
        try:
            l, t, r, b = window_rect(app["hwnd"])
            # Clamp to the whole virtual desktop (all monitors), not just the primary one
            l, t = max(vx, l), max(vy, t)
            r, b = min(vx + vw, r), min(vy + vh, b)
            w, h = r - l, b - t
            if w > 50 and h > 50:
                return win32_capture_rect(l, t, w, h)
        except Exception:
            pass
    return win32_capture_rect(vx, vy, vw, vh)


def win32_read_clipboard():
    for _ in range(3):
        if user32.OpenClipboard(None):
            try:
                handle = user32.GetClipboardData(CF_UNICODETEXT)
                if not handle:
                    return None
                ptr = kernel32.GlobalLock(handle)
                if not ptr:
                    return None
                try:
                    return ctypes.c_wchar_p(ptr).value
                finally:
                    kernel32.GlobalUnlock(handle)
            finally:
                user32.CloseClipboard()
        time.sleep(0.002)
    return None


def parse_keys(text):
    return [
        [k.strip().lower() for k in step.split("+")]
        for step in text.split(",")
        if step.strip()
    ]


def send_steps(steps):
    for keys in steps:
        if len(keys) == 1:
            fast_press(keys[0])
        else:
            fast_hotkey(*keys)


def check_stop():
    if stop_flag.is_set():
        raise InterruptedError


def release_all():
    for k in ("1", "esc", "shift", "alt", "ctrl", "c", "f"):
        raw_send_key(k, False)


def switch_session():
    raw_send_key("shift", True)
    time.sleep(HOLD_PAUSE)
    raw_send_key("esc", True)
    time.sleep(HOLD_PAUSE)
    raw_send_key("esc", False)
    time.sleep(0.01)
    raw_send_key("shift", False)

    time.sleep(PROMPT_WAIT)
    fast_press("1")


def open_screen_popup(set_status):
    check_stop()
    set_status("Opening screen pop up (Shift+F1)...")
    ref = grab()
    raw_send_key("shift", True)
    time.sleep(0.05)
    fast_press("f1", hold=0.03)
    time.sleep(0.02)
    raw_send_key("shift", False)
    if wait_for_screen_change(ref, 1.2):
        time.sleep(0.05)
    else:
        time.sleep(0.3)
    return True


def switch_back_to_main(set_status):
    set_status("Switching back to main page...")
    switch_session()
    time.sleep(SESSION_SWITCH_DELAY)
    return True


clip_state = {"ok": True, "fails": 0}


def wait_for_stable_screen(frames=None, interval=None, timeout=None):
    """Wait until the screen stops changing (e.g. the 'Open screen' popup has finished
    fading out) and return that settled screenshot. Gives up after the timeout.
    Called with no arguments it uses the normal safe timings; fast mode passes its own."""
    frames = STABLE_FRAMES if frames is None else frames
    interval = STABLE_INTERVAL if interval is None else interval
    timeout = STABLE_TIMEOUT if timeout is None else timeout

    end = time.time() + timeout
    prev = grab()
    same = 0
    while time.time() < end:
        check_stop()
        time.sleep(interval)
        cur = grab()
        if fast_img_diff(cur, prev) < STABLE_DIFF:
            same += 1
            if same >= frames:
                return cur
        else:
            same = 0
        prev = cur
    return prev


def take_capture(shots, fast=False):
    check_stop()
    if fast:
        shots.append(wait_for_stable_screen(FAST_STABLE_FRAMES, FAST_STABLE_INTERVAL, FAST_STABLE_TIMEOUT))
    else:
        shots.append(wait_for_stable_screen())

    if not FAST_CAPTURE or not clip_state["ok"]:
        send_steps(parse_keys(CAPTURE_KEYS))
        time.sleep(CAPTURE_DELAY)
        return None

    seq_before = user32.GetClipboardSequenceNumber()
    send_steps(parse_keys(CAPTURE_KEYS))

    end = time.time() + COPY_TIMEOUT
    while time.time() < end:
        check_stop()
        if user32.GetClipboardSequenceNumber() != seq_before:
            text = win32_read_clipboard()
            if text:
                clip_state["fails"] = 0
                return text
        time.sleep(CLIPBOARD_POLL_INTERVAL)

    # The copy did not show up on the clipboard in time: give it a fixed wait
    # so the next key is not sent while the copy is still running
    clip_state["fails"] += 1
    if clip_state["fails"] >= 2:
        clip_state["ok"] = False
    time.sleep(CAPTURE_DELAY)
    return None


def fast_img_diff(a, b):
    """Average brightness difference between two screenshots (0 = identical). Runs at C speed."""
    if a.size != b.size:
        return 255.0
    ra = a.reduce(6).convert("L")
    rb = b.reduce(6).convert("L")
    return ImageStat.Stat(ImageChops.difference(ra, rb)).mean[0]


def go_back_to_first_page(first_page_shot, set_status):
    if F3_MODE == "count":
        for i in range(F3_PRESSES):
            check_stop()
            set_status(f"Pressing F3 ({i + 1}/{F3_PRESSES})...")
            fast_press("f3")
            time.sleep(F3_DELAY)
        return True

    for i in range(F3_MAX_PRESSES):
        check_stop()
        if fast_img_diff(grab(), first_page_shot) < F3_MATCH_THRESHOLD:
            return True
        set_status(f"Pressing F3 (press {i + 1})...")
        fast_press("f3")
        time.sleep(F3_DELAY)
    return fast_img_diff(grab(), first_page_shot) < F3_MATCH_THRESHOLD


def open_screen(number, set_status):
    """Type the screen number, press Enter, and carry on as soon as the screen screen appears."""
    check_stop()
    set_status(f"Screen {number}...")
    fast_type(str(number))
    ref = grab()
    fast_press("enter")
    if wait_for_screen_change(ref, SCREEN_TIMEOUT):
        time.sleep(SCREEN_SETTLE)
    else:
        time.sleep(SCREEN_DELAY)


def tail_text(text):
    if not text:
        return ""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return " | ".join(lines[-SCREEN4_TAIL_LINES:])


def screen4_log(msg):
    if not SCREEN4_LOG:
        return
    try:
        folder = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(folder, "screen4_log.txt"), "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass


def wait_for_screen_change(ref, timeout, settle=None):
    """Wait until the screen differs from ref. 'settle' is the extra wait after the change
    (defaults to SCREEN4_SETTLE; fast mode passes FAST_SETTLE)."""
    settle = SCREEN4_SETTLE if settle is None else settle
    end = time.time() + timeout
    while time.time() < end:
        check_stop()
        if fast_img_diff(grab(), ref) >= SCREEN4_SAME_SCREEN:
            if settle > 0:
                time.sleep(settle)
            return True
        time.sleep(0.003)
    return False


def scroll_pages(shots, set_status, label="Screen 4", skip_first=False):
    """Screen copy of every page until 'Bottom' shows, with Page Down between pages.
    Pages 1..FAST_AFTER_PAGE use the safe timings; later pages use the FAST_* timings."""
    screen4_log(f"---- {label}: run ----")
    page_index = 0
    max_pages = SCREEN4_MAX_PAGES if SCREEN4_MAX_PAGES > 0 else 9999

    while page_index < max_pages:
        check_stop()
        page_index += 1
        fast = page_index > FAST_AFTER_PAGE
        set_status(f"{label}: reading page {page_index}...")

        text = take_capture(shots, fast=fast)
        last_shot = shots[-1]
        if page_index == 1 and skip_first:
            shots.pop()          # still used above to compare screens, just not saved in the PDF

        tail = tail_text(text)
        full_text = text or ""
        screen4_log(f"page {page_index}: tail={tail!r}")

        is_bottom = bool(re.search(r"\b" + re.escape(SCREEN4_END_WORD) + r"\b", tail, re.IGNORECASE))
        if not is_bottom and text:
            is_bottom = bool(re.search(r"\b" + re.escape(SCREEN4_END_WORD) + r"\b", full_text[-500:], re.IGNORECASE))

        if is_bottom:
            set_status(f"{label}: Bottom reached ({page_index} pages).")
            screen4_log(f"{label} complete: bottom flag on page {page_index}.")
            return

        had_more = bool(re.search(r"\bmore\b", tail, re.IGNORECASE) or re.search(r"\bmore\b", full_text[-500:], re.IGNORECASE))

        tries = 0
        page_changed = False
        while tries < 4:
            check_stop()
            send_steps(parse_keys(SCREEN4_PAGEDOWN_KEYS))

            if wait_for_screen_change(
                last_shot,
                FAST_CHANGE_TIMEOUT if fast else SCREEN4_CHANGE_TIMEOUT,
                FAST_SETTLE if fast else None,
            ):
                page_changed = True
                break

            tries += 1
            screen4_log(f"page {page_index}: retry {tries} for screen redraw")
            time.sleep(FAST_RETRY_SLEEP if fast else 0.08)

        if not page_changed:
            if not had_more or tries >= 4:
                set_status(f"{label}: Finished at last page ({page_index} pages).")
                screen4_log(f"{label} complete: screen stopped updating after page {page_index}.")
                return

    set_status(f"{label}: Reached max safe threshold ({max_pages} pages).")


def scroll_screen4(shots, set_status):
    scroll_pages(shots, set_status, "Screen 4", skip_first=SCREEN4_SKIP_FIRST_PAGE)


def press_and_wait(key, set_status, label=None):
    """Press a key once, then wait until the screen changes (or AFTER_KEY_TIMEOUT).
    The key is never re-sent, so it cannot double-fire."""
    check_stop()
    if label:
        set_status(label)
    ref = grab()
    fast_press(key)
    changed = wait_for_screen_change(ref, AFTER_KEY_TIMEOUT)
    time.sleep(AFTER_KEY_SETTLE if changed else F3_DELAY)
    return changed


def wait_for_click(prompt, set_status):
    """Wait until the user left-clicks inside the locked terminal window.
    Returns True on a click, False if the user pressed Skip."""
    set_status(prompt)
    skip_event.clear()

    # Ignore a button that is already held down
    while user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000:
        check_stop()
        time.sleep(0.01)

    while True:
        check_stop()
        if skip_event.is_set():
            skip_event.clear()
            return False
        if user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000:
            pt = wintypes.POINT()
            user32.GetCursorPos(ctypes.byref(pt))
            inside = True
            if app["hwnd"]:
                l, t, r, b = window_rect(app["hwnd"])
                inside = l <= pt.x <= r and t <= pt.y <= b
            while user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000:
                time.sleep(0.01)
            if inside:
                time.sleep(SCREEN95_CLICK_SETTLE)
                return True
        time.sleep(0.01)


def select_and_capture(label, shots, set_status):
    """Ask the user to click the row, then press F4 and copy every page until Bottom."""
    clicked = wait_for_click(f"Screen 95: click {label}, then wait (or press Skip)...", set_status)
    if not clicked:
        set_status(f"Screen 95: {label} skipped.")
        return False
    if SCREEN95_PRESS_F4:
        fast_press("f4")
        time.sleep(STEP_DELAY)
    scroll_pages(shots, set_status, f"Screen 95 {label.title()}")
    return True


def run_screen_steps(record_id, shots, set_status):
    # Screen pop up (Shift+F1)
    if not open_screen_popup(set_status):
        return False

    # Screen 7: Enter x2, record ID, 3 in second blank, Enter, copy
    open_screen(7, set_status)
    for _ in range(SCREEN7_EXTRA_ENTERS):
        fast_press("enter")
        time.sleep(STEP_DELAY)
    fast_type(record_id)
    send_steps(parse_keys(SCREEN7_SECOND_BLANK_KEYS))
    fast_type(SCREEN7_SECOND_BLANK_VALUE)
    fast_press("enter")
    time.sleep(STEP_DELAY)
    take_capture(shots)

    # Screen 3: copy, F3
    press_and_wait("f3", set_status, "Screen 7: F3")
    open_screen(3, set_status)
    take_capture(shots)
    press_and_wait("f3", set_status, "Screen 3: F3")

    # Screen 95: Section A (click, F4, copy), F12, Section B (click, F4, copy)
    open_screen(95, set_status)
    select_and_capture("SECTION A", shots, set_status)
    press_and_wait("f12", set_status, "Screen 95: F12")
    select_and_capture("SECTION B", shots, set_status)

    # After screen 95: F3, then screen 4
    press_and_wait("f3", set_status, "Screen 95 exit: F3")
    open_screen(4, set_status)

    # Screen 4: copy every page until Bottom, Page Down between pages
    scroll_screen4(shots, set_status)

    # After screen 4: F3, then F9 + copy, Page Down + copy, Enter.
    # Each key waits for the screen to actually change before the next one is sent.
    press_and_wait("f3", set_status, "Screen 4 exit: F3")

    press_and_wait("f9", set_status, "Pressing F9")
    set_status("Screen copy after F9...")
    take_capture(shots)

    press_and_wait("pagedown", set_status, "Pressing Page Down")
    set_status("Screen copy after Page Down...")
    take_capture(shots)

    press_and_wait("enter", set_status, "Pressing Enter")

    # Screen 1: copy, F3
    open_screen(1, set_status)
    take_capture(shots)
    press_and_wait("f3", set_status, "Screen 1: F3")

    # Screen 105: copy, F10, copy
    open_screen(105, set_status)
    take_capture(shots)
    fast_press("f10")
    time.sleep(STEP_DELAY)
    take_capture(shots)
    return True


def safe_name(text):
    return re.sub(r'[\\/:*?"<>|\s]+', "-", text.strip())


def ask_save_path(default_name):
    result = {}
    done = threading.Event()

    def ask():
        root.lift()
        root.attributes("-topmost", True)
        result["path"] = filedialog.asksaveasfilename(
            parent=root,
            title="Save screen copies as PDF",
            defaultextension=".pdf",
            filetypes=[("PDF file", "*.pdf")],
            initialfile=default_name,
        )
        root.attributes("-topmost", False)
        done.set()

    root.after(0, ask)
    done.wait()
    return result["path"]


def save_pdf(shots, path):
    pages = [s.convert("RGB") for s in shots]
    pages[0].save(path, "PDF", save_all=True, append_images=pages[1:], resolution=100, quality=95)


def save_screen_copies(shots, record_id, date, set_status):
    default_name = f"{safe_name(record_id)}_{safe_name(date)}.pdf"
    set_status("Choose where to save PDF...")
    path = ask_save_path(default_name)

    if not path:
        folder = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(folder, default_name)
        set_status("Saved next to script...")

    save_pdf(shots, path)
    return path


def run_sequence(record_id, date, set_status):
    stop_flag.clear()
    clip_state["ok"] = True
    clip_state["fails"] = 0
    shots = []
    app["hwnd"] = None
    try:
        date_text = date.replace("/", "") if DATE_REMOVE_SLASHES else date

        for n in range(COUNTDOWN, 0, -1):
            set_status(f"Click terminal RECORD ID field ({n})...")
            time.sleep(1)
        check_stop()

        hwnd = user32.GetForegroundWindow()
        title = window_title(hwnd) if hwnd else ""
        if title.startswith("Screen Capture Helper"):
            set_status("Helper was focused. Click terminal and retry.")
            return
        app["hwnd"] = hwnd
        set_status(f"Locked to window: {title or 'Terminal'}")
        time.sleep(0.1)

        # 1. First session
        fast_type(record_id)
        fast_press("enter")
        time.sleep(RECORD_LOAD_DELAY)
        check_stop()

        take_capture(shots)
        check_stop()

        # 2. Session Switch
        switch_session()
        time.sleep(SESSION_SWITCH_DELAY)
        check_stop()

        first_page_shot = grab()

        # 3. Form fields
        fast_type(record_id)
        fast_press("enter")
        time.sleep(RECORD_ENTER_DELAY)
        check_stop()

        fast_press(F6_KEY)
        time.sleep(F6_DELAY)
        check_stop()

        send_steps(parse_keys(FORM_NAV_KEYS))
        time.sleep(SMALL_PAUSE)
        fast_type(FORM_VALUE)
        fast_press("enter")
        time.sleep(ENTER_DELAY)
        check_stop()

        send_steps(parse_keys(TO_DATE_KEYS))
        fast_type(date_text)
        check_stop()

        send_steps(parse_keys(TO_SECOND_FIELD_KEYS))
        time.sleep(SMALL_PAUSE)
        fast_type(SECOND_FIELD_VALUE)
        check_stop()

        fast_press("enter")
        time.sleep(DOUBLE_ENTER_DELAY)
        fast_press("enter")
        time.sleep(DOUBLE_ENTER_DELAY)
        check_stop()

        send_steps(parse_keys(TO_SECOND_DATE_KEYS))
        fast_type(date_text)
        time.sleep(SMALL_PAUSE)
        check_stop()

        fast_press("enter")
        time.sleep(DOUBLE_ENTER_DELAY)
        fast_press("enter")
        time.sleep(DOUBLE_ENTER_DELAY)
        check_stop()

        take_capture(shots)
        check_stop()

        # 4. F3 return & switch back
        reached = go_back_to_first_page(first_page_shot, set_status)
        if not reached:
            set_status("First page recognition failed.")
            return
        check_stop()

        if not switch_back_to_main(set_status):
            set_status("Could not return to main page.")
            return
        check_stop()

        # 5. Screens sequence
        if not run_screen_steps(record_id, shots, set_status):
            return
        check_stop()

        # 6. Save PDF
        saved_path = save_screen_copies(shots, record_id, date, set_status)
        set_status(f"Done: {saved_path}")
    except InterruptedError:
        set_status("Stopped.")
    except Exception as e:
        set_status(f"Error: {e}")
    finally:
        release_all()
        app["running"] = False
        root.after(0, lambda: start_btn.config(state="normal"))


# ---------- Interface settings ----------
def resource_path(name):
    # Works both when run as a script and when packaged with PyInstaller
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


LOGO_FILE = "logo.png"            # optional: place a logo next to this script with this name
LOGO_WIDTH = 190                  # logo width in pixels, change to resize
BRAND_RED = "#2563eb"

BG        = "#0f172a"
CARD      = "#1e293b"
BORDER    = "#334155"
FG        = "#e2e8f0"
MUTED     = "#94a3b8"
ACCENT    = BRAND_RED
ACCENT_H  = "#3b82f6"
DANGER    = "#ef4444"
DANGER_H  = "#f87171"
NEUTRAL   = "#334155"
NEUTRAL_H = "#475569"
OK_COL, WARN_COL, INFO_COL = "#22c55e", "#f59e0b", "#38bdf8"

FONT       = ("Segoe UI", 10)
FONT_BOLD  = ("Segoe UI Semibold", 10)
FONT_TITLE = ("Segoe UI Semibold", 15)

# ---- GUI Layout (dark, modern, with logo) ----
root = tk.Tk()
root.title("Screen Capture Helper")
root.configure(bg=BG)
root.resizable(False, False)

# Logo banner (white strip so the red logo looks right on the dark theme)
banner = tk.Frame(root, bg="white")
banner.pack(fill="x")
try:
    img = Image.open(resource_path(LOGO_FILE)).convert("RGBA")
    h = int(img.height * LOGO_WIDTH / img.width)
    img = img.resize((LOGO_WIDTH, h), Image.LANCZOS)
    flat = Image.new("RGBA", img.size, "white")
    flat.alpha_composite(img)
    logo_img = ImageTk.PhotoImage(flat.convert("RGB"))   # keep a reference
    tk.Label(banner, image=logo_img, bg="white").pack(pady=14)
except Exception:
    tk.Label(banner, text="Screen Capture", font=("Segoe UI Semibold", 22),
             bg="white", fg=BRAND_RED).pack(pady=14)
tk.Frame(root, bg=BRAND_RED, height=3).pack(fill="x")      # red accent line

# Header
header = tk.Frame(root, bg=BG)
header.pack(fill="x", padx=20, pady=(14, 0))
tk.Label(header, text="Screen Capture Helper", font=FONT_TITLE, bg=BG, fg=FG).pack(anchor="w")
tk.Label(header, text="Enter the record ID and date, press Start, then click the terminal.",
         font=("Segoe UI", 9), bg=BG, fg=MUTED).pack(anchor="w")

# Input card
card = tk.Frame(root, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
card.pack(fill="x", padx=20, pady=12)


def make_field(parent, label):
    tk.Label(parent, text=label, font=FONT_BOLD, bg=CARD, fg=MUTED).pack(anchor="w", padx=14, pady=(12, 3))
    e = tk.Entry(parent, font=("Segoe UI", 11), bg=BG, fg=FG, insertbackground=FG,
                 relief="flat", highlightthickness=1, highlightbackground=BORDER,
                 highlightcolor=ACCENT, width=34)
    e.pack(padx=14, ipady=6, fill="x")
    return e


record_id_box = make_field(card, "RECORD ID")
date_box = make_field(card, "DATE")
tk.Frame(card, bg=CARD, height=14).pack()

# Status bar
status_frame = tk.Frame(root, bg=BG)
status_frame.pack(fill="x", padx=20)
status_dot = tk.Label(status_frame, text="●", font=("Segoe UI", 11), bg=BG, fg=OK_COL)
status_dot.pack(side="left")
status_label = tk.Label(status_frame, text="Ready.", font=FONT, bg=BG, fg=FG,
                        wraplength=330, justify="left", anchor="w")
status_label.pack(side="left", padx=(6, 0), fill="x", expand=True)


def set_status(text):
    def apply():
        low = text.lower()
        if low.startswith("error") or "failed" in low or "could not" in low:
            colour = DANGER
        elif low.startswith("stopped") or "skipped" in low:
            colour = WARN_COL
        elif low.startswith("done") or low == "ready.":
            colour = OK_COL
        else:
            colour = INFO_COL
        status_dot.config(fg=colour)
        status_label.config(text=text)
    root.after(0, apply)


def start():
    if app["running"]:
        return
    record_id = record_id_box.get().strip()
    date = date_box.get().strip()
    if not record_id or not date:
        set_status("Please fill in both record ID and date.")
        return
    app["running"] = True
    start_btn.config(state="disabled")
    threading.Thread(target=run_sequence, args=(record_id, date, set_status), daemon=True).start()


def make_button(parent, text, command, bg, hover, **kw):
    b = tk.Button(parent, text=text, command=command, font=FONT_BOLD, bg=bg, fg="white",
                  activebackground=hover, activeforeground="white", disabledforeground="#64748b",
                  relief="flat", bd=0, cursor="hand2", padx=12, pady=8, **kw)
    b.bind("<Enter>", lambda e: b.config(bg=hover) if str(b["state"]) == "normal" else None)
    b.bind("<Leave>", lambda e: b.config(bg=bg))
    return b


# Buttons
btns = tk.Frame(root, bg=BG)
btns.pack(fill="x", padx=20, pady=(14, 20))
start_btn = make_button(btns, "▶  Start", start, ACCENT, ACCENT_H)
start_btn.pack(fill="x")
row = tk.Frame(btns, bg=BG)
row.pack(fill="x", pady=(8, 0))
row.columnconfigure((0, 1), weight=1, uniform="b")
make_button(row, "⏭  Skip step", skip_event.set, NEUTRAL, NEUTRAL_H).grid(row=0, column=0, sticky="ew", padx=(0, 4))
make_button(row, "■  Stop", stop_flag.set, DANGER, DANGER_H).grid(row=0, column=1, sticky="ew", padx=(4, 0))

record_id_box.bind("<Return>", lambda e: date_box.focus_set())
date_box.bind("<Return>", lambda e: start())
record_id_box.focus_set()

root.mainloop()