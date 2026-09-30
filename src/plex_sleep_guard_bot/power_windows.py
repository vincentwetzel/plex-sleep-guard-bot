"""Thin ctypes wrapper for the Windows system-required power request API."""

from __future__ import annotations

import ctypes
import os
from ctypes import wintypes


POWER_REQUEST_CONTEXT_VERSION = 0
POWER_REQUEST_CONTEXT_SIMPLE_STRING = 0x00000001
POWER_REQUEST_SYSTEM_REQUIRED = 1
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


class _ReasonUnion(ctypes.Union):
    _fields_ = [("simple_reason_string", wintypes.LPWSTR)]


class _ReasonContext(ctypes.Structure):
    _anonymous_ = ("reason",)
    _fields_ = [
        ("version", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("reason", _ReasonUnion),
    ]


class WindowsPowerRequest:
    """Owns one request object and its single system-required count."""

    def __init__(self, reason: str) -> None:
        if os.name != "nt":
            raise OSError("Windows power requests are available only on Windows.")
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._bind_functions()
        self._handle: int | None = None
        self._is_set = False

        reason_buffer = ctypes.create_unicode_buffer(reason)
        context = _ReasonContext()
        context.version = POWER_REQUEST_CONTEXT_VERSION
        context.flags = POWER_REQUEST_CONTEXT_SIMPLE_STRING
        context.simple_reason_string = ctypes.cast(reason_buffer, wintypes.LPWSTR)
        handle = self._kernel32.PowerCreateRequest(ctypes.byref(context))
        if handle == INVALID_HANDLE_VALUE or not handle:
            raise ctypes.WinError(ctypes.get_last_error())
        self._handle = handle
        try:
            if not self._kernel32.PowerSetRequest(self._handle, POWER_REQUEST_SYSTEM_REQUIRED):
                raise ctypes.WinError(ctypes.get_last_error())
            self._is_set = True
        except BaseException:
            self._kernel32.CloseHandle(self._handle)
            self._handle = None
            raise

    def _bind_functions(self) -> None:
        self._kernel32.PowerCreateRequest.argtypes = [ctypes.POINTER(_ReasonContext)]
        self._kernel32.PowerCreateRequest.restype = wintypes.HANDLE
        self._kernel32.PowerSetRequest.argtypes = [wintypes.HANDLE, ctypes.c_int]
        self._kernel32.PowerSetRequest.restype = wintypes.BOOL
        self._kernel32.PowerClearRequest.argtypes = [wintypes.HANDLE, ctypes.c_int]
        self._kernel32.PowerClearRequest.restype = wintypes.BOOL
        self._kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self._kernel32.CloseHandle.restype = wintypes.BOOL

    def close(self) -> None:
        handle = self._handle
        if handle is None:
            return
        self._handle = None
        try:
            if self._is_set and not self._kernel32.PowerClearRequest(handle, POWER_REQUEST_SYSTEM_REQUIRED):
                raise ctypes.WinError(ctypes.get_last_error())
            self._is_set = False
        finally:
            if not self._kernel32.CloseHandle(handle):
                error = ctypes.WinError(ctypes.get_last_error())
                if self._is_set:
                    raise error

    def __enter__(self) -> WindowsPowerRequest:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
