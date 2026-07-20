from __future__ import annotations

import ctypes
import ctypes.wintypes
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PyQt6.QtCore import QAbstractNativeEventFilter

LOGGER = logging.getLogger(__name__)
IS_WINDOWS = sys.platform == "win32"

WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

GWLP_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_LAYERED = 0x00080000
WS_EX_NOACTIVATE = 0x08000000
WDA_NONE = 0x00000000
WDA_EXCLUDEFROMCAPTURE = 0x00000011
MONITOR_DEFAULTTONEAREST = 2
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020
SWP_SHOWWINDOW = 0x0040

if IS_WINDOWS:
    _USER32 = ctypes.WinDLL("user32", use_last_error=True)
    _KERNEL32 = ctypes.WinDLL("kernel32", use_last_error=True)

    _USER32.RegisterHotKey.argtypes = [ctypes.wintypes.HWND, ctypes.c_int, ctypes.wintypes.UINT, ctypes.wintypes.UINT]
    _USER32.RegisterHotKey.restype = ctypes.wintypes.BOOL
    _USER32.UnregisterHotKey.argtypes = [ctypes.wintypes.HWND, ctypes.c_int]
    _USER32.UnregisterHotKey.restype = ctypes.wintypes.BOOL
    _USER32.GetWindowLongPtrW.argtypes = [ctypes.wintypes.HWND, ctypes.c_int]
    _USER32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
    _USER32.SetWindowLongPtrW.argtypes = [ctypes.wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
    _USER32.SetWindowLongPtrW.restype = ctypes.c_ssize_t
    _USER32.SetWindowDisplayAffinity.argtypes = [ctypes.wintypes.HWND, ctypes.wintypes.DWORD]
    _USER32.SetWindowDisplayAffinity.restype = ctypes.wintypes.BOOL
    _USER32.SetWindowPos.argtypes = [
        ctypes.wintypes.HWND,
        ctypes.wintypes.HWND,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.wintypes.UINT,
    ]
    _USER32.SetWindowPos.restype = ctypes.wintypes.BOOL
    _USER32.GetForegroundWindow.restype = ctypes.wintypes.HWND
    _USER32.GetWindowRect.argtypes = [ctypes.wintypes.HWND, ctypes.POINTER(ctypes.wintypes.RECT)]
    _USER32.GetWindowRect.restype = ctypes.wintypes.BOOL
    _USER32.MonitorFromWindow.argtypes = [ctypes.wintypes.HWND, ctypes.wintypes.DWORD]
    _USER32.MonitorFromWindow.restype = ctypes.wintypes.HANDLE
    _USER32.GetMonitorInfoW.argtypes = [ctypes.wintypes.HANDLE, ctypes.c_void_p]
    _USER32.GetMonitorInfoW.restype = ctypes.wintypes.BOOL
    _USER32.GetWindowThreadProcessId.argtypes = [ctypes.wintypes.HWND, ctypes.POINTER(ctypes.wintypes.DWORD)]
    _USER32.GetWindowThreadProcessId.restype = ctypes.wintypes.DWORD

    _KERNEL32.OpenProcess.argtypes = [ctypes.wintypes.DWORD, ctypes.wintypes.BOOL, ctypes.wintypes.DWORD]
    _KERNEL32.OpenProcess.restype = ctypes.wintypes.HANDLE
    _KERNEL32.QueryFullProcessImageNameW.argtypes = [
        ctypes.wintypes.HANDLE,
        ctypes.wintypes.DWORD,
        ctypes.wintypes.LPWSTR,
        ctypes.POINTER(ctypes.wintypes.DWORD),
    ]
    _KERNEL32.QueryFullProcessImageNameW.restype = ctypes.wintypes.BOOL
    _KERNEL32.CloseHandle.argtypes = [ctypes.wintypes.HANDLE]
    _KERNEL32.CloseHandle.restype = ctypes.wintypes.BOOL
else:
    _USER32 = None
    _KERNEL32 = None


@dataclass(frozen=True)
class ForegroundWindow:
    hwnd: int
    process_name: str
    rect: tuple[int, int, int, int]
    monitor_rect: tuple[int, int, int, int]

    @property
    def fullscreen(self) -> bool:
        tolerance = 2
        return all(abs(a - b) <= tolerance for a, b in zip(self.rect, self.monitor_rect))


class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.wintypes.DWORD),
        ("rcMonitor", ctypes.wintypes.RECT),
        ("rcWork", ctypes.wintypes.RECT),
        ("dwFlags", ctypes.wintypes.DWORD),
    ]


def parse_hotkey(sequence: str) -> tuple[int, int]:
    parts = [part.strip() for part in sequence.replace("-", "+").split("+") if part.strip()]
    if not parts:
        raise ValueError("El atajo está vacío")
    modifiers = MOD_NOREPEAT
    aliases = {
        "CTRL": MOD_CONTROL,
        "CONTROL": MOD_CONTROL,
        "ALT": MOD_ALT,
        "SHIFT": MOD_SHIFT,
        "WIN": MOD_WIN,
        "META": MOD_WIN,
    }
    key_name = ""
    for part in parts:
        upper = part.upper()
        if upper in aliases:
            modifiers |= aliases[upper]
        elif key_name:
            raise ValueError(f"Atajo no reconocido: {sequence}")
        else:
            key_name = upper
    if not key_name:
        raise ValueError("El atajo necesita una tecla")
    if key_name.startswith("F") and key_name[1:].isdigit():
        number = int(key_name[1:])
        if 1 <= number <= 24:
            return modifiers, 0x70 + number - 1
    if len(key_name) == 1 and (key_name.isalpha() or key_name.isdigit()):
        return modifiers, ord(key_name)
    key_map = {"SPACE": 0x20, "TAB": 0x09, "ESC": 0x1B, "ESCAPE": 0x1B}
    if key_name in key_map:
        return modifiers, key_map[key_name]
    raise ValueError(f"Tecla global no compatible: {key_name}")


class GlobalHotkeyManager(QAbstractNativeEventFilter):
    def __init__(self):
        super().__init__()
        self.callbacks: dict[int, Callable[[], None]] = {}
        self.sequences: dict[int, str] = {}
        self.user32 = _USER32

    def register(self, hotkey_id: int, sequence: str, callback: Callable[[], None]) -> tuple[bool, str]:
        if not self.user32:
            return False, "Los atajos globales solo están disponibles en Windows"
        try:
            modifiers, virtual_key = parse_hotkey(sequence)
        except ValueError as exc:
            return False, str(exc)
        self.unregister(hotkey_id)
        if not self.user32.RegisterHotKey(None, hotkey_id, modifiers, virtual_key):
            return False, f"{sequence} ya está siendo usado por otra aplicación"
        self.callbacks[hotkey_id] = callback
        self.sequences[hotkey_id] = sequence
        return True, ""

    def unregister(self, hotkey_id: int) -> None:
        if hotkey_id in self.callbacks and self.user32:
            self.user32.UnregisterHotKey(None, hotkey_id)
        self.callbacks.pop(hotkey_id, None)
        self.sequences.pop(hotkey_id, None)

    def unregister_all(self) -> None:
        for hotkey_id in list(self.callbacks):
            self.unregister(hotkey_id)

    def nativeEventFilter(self, event_type, message):
        if event_type != b"windows_generic_MSG":
            return False, 0
        msg = ctypes.wintypes.MSG.from_address(int(message))
        callback = self.callbacks.get(int(msg.wParam)) if msg.message == WM_HOTKEY else None
        if callback:
            callback()
            return True, 0
        return False, 0


def make_window_click_through(hwnd: int, exclude_from_capture: bool = False) -> None:
    if not IS_WINDOWS:
        return
    user32 = _USER32
    assert user32 is not None
    getter = user32.GetWindowLongPtrW
    setter = user32.SetWindowLongPtrW
    style = getter(hwnd, GWLP_EXSTYLE)
    style |= WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
    setter(hwnd, GWLP_EXSTYLE, style)
    user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE if exclude_from_capture else WDA_NONE)
    user32.SetWindowPos(
        hwnd,
        ctypes.wintypes.HWND(-1),  # HWND_TOPMOST
        0,
        0,
        0,
        0,
        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_FRAMECHANGED | SWP_SHOWWINDOW,
    )


def foreground_window() -> ForegroundWindow | None:
    if not IS_WINDOWS:
        return None
    user32 = _USER32
    assert user32 is not None
    raw_hwnd = user32.GetForegroundWindow()
    if not raw_hwnd:
        return None
    hwnd = int(raw_hwnd)
    rect = ctypes.wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return None
    monitor = user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
    info = MONITORINFO(cbSize=ctypes.sizeof(MONITORINFO))
    if not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
        return None
    return ForegroundWindow(
        hwnd=hwnd,
        process_name=_process_name(hwnd),
        rect=(rect.left, rect.top, rect.right, rect.bottom),
        monitor_rect=(info.rcMonitor.left, info.rcMonitor.top, info.rcMonitor.right, info.rcMonitor.bottom),
    )


def _process_name(hwnd: int) -> str:
    user32 = _USER32
    kernel32 = _KERNEL32
    assert user32 is not None and kernel32 is not None
    process_id = ctypes.wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, process_id.value)
    if not handle:
        return ""
    try:
        buffer = ctypes.create_unicode_buffer(32768)
        size = ctypes.wintypes.DWORD(len(buffer))
        if kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return Path(buffer.value).name.lower()
    finally:
        kernel32.CloseHandle(handle)
    return ""


def set_launch_at_startup(enabled: bool, entry_script: Path) -> bool:
    if not IS_WINDOWS:
        return False
    try:
        import winreg

        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                if getattr(sys, "frozen", False):
                    command = f'"{sys.executable}"'
                else:
                    command = f'"{sys.executable}" "{entry_script}"'
                winreg.SetValueEx(key, "MonitorDimOverlay", 0, winreg.REG_SZ, command)
            else:
                try:
                    winreg.DeleteValue(key, "MonitorDimOverlay")
                except FileNotFoundError:
                    pass
        return True
    except OSError:
        LOGGER.exception("Could not update Windows startup setting")
        return False
