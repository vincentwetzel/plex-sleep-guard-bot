"""Windows power request and sleep-timeout APIs via ctypes."""

from __future__ import annotations

import ctypes
import os
from dataclasses import dataclass
from ctypes import wintypes


POWER_REQUEST_CONTEXT_VERSION = 0
POWER_REQUEST_CONTEXT_SIMPLE_STRING = 0x00000001
POWER_REQUEST_SYSTEM_REQUIRED = 1
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
ERROR_SUCCESS = 0
AC_LINE_OFFLINE = 0
AC_LINE_ONLINE = 1
AC_LINE_UNKNOWN = 255


class _Guid(ctypes.Structure):
    _fields_ = [
        ("data1", wintypes.DWORD),
        ("data2", wintypes.WORD),
        ("data3", wintypes.WORD),
        ("data4", ctypes.c_ubyte * 8),
    ]


class _SystemPowerStatus(ctypes.Structure):
    _fields_ = [
        ("ac_line_status", wintypes.BYTE),
        ("battery_flag", wintypes.BYTE),
        ("battery_life_percent", wintypes.BYTE),
        ("system_status_flag", wintypes.BYTE),
        ("battery_life_time", wintypes.DWORD),
        ("battery_full_life_time", wintypes.DWORD),
    ]


GUID_SLEEP_SUBGROUP = _Guid(
    0x238C9FA8,
    0x0AAD,
    0x41ED,
    (ctypes.c_ubyte * 8)(0x83, 0xF4, 0x97, 0xBE, 0x24, 0x2C, 0x8F, 0x20),
)
GUID_STANDBYIDLE = _Guid(
    0x29F6C1DB,
    0x86DA,
    0x48C5,
    (ctypes.c_ubyte * 8)(0x9F, 0xDB, 0xF2, 0xB6, 0x7B, 0x1F, 0x44, 0xDA),
)


@dataclass(frozen=True, slots=True)
class SleepTimeoutInfo:
    """Configured Windows sleep timeout values and the current power source."""

    ac_seconds: int
    dc_seconds: int
    on_ac_power: bool | None

    def describe(self) -> str:
        if self.on_ac_power is True:
            return f"Windows is configured to {format_sleep_timeout(self.ac_seconds)} on AC power."
        if self.on_ac_power is False:
            return f"Windows is configured to {format_sleep_timeout(self.dc_seconds)} on battery power."
        return (
            "Windows inactivity sleep timeouts: "
            f"AC power: {format_sleep_timeout(self.ac_seconds)}; "
            f"battery power: {format_sleep_timeout(self.dc_seconds)}."
        )


def format_sleep_timeout(seconds: int) -> str:
    if seconds == 0:
        return "never sleep automatically due to inactivity"
    minutes, remaining_seconds = divmod(seconds, 60)
    if remaining_seconds:
        if minutes:
            return f"sleep automatically after {minutes} minutes and {remaining_seconds} seconds of inactivity"
        return f"sleep automatically after {remaining_seconds} seconds of inactivity"
    if minutes == 1:
        return "sleep automatically after 1 minute of inactivity"
    if minutes:
        return f"sleep automatically after {minutes} minutes of inactivity"
    return "sleep automatically after 0 seconds of inactivity"


def get_sleep_timeout_info() -> SleepTimeoutInfo:
    """Read the active scheme's AC/DC sleep timeout without changing Windows settings."""
    if os.name != "nt":
        raise OSError("Windows sleep settings are available only on Windows.")

    powrprof = ctypes.WinDLL("powrprof", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    powrprof.PowerGetActiveScheme.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.POINTER(_Guid))]
    powrprof.PowerGetActiveScheme.restype = wintypes.DWORD
    powrprof.PowerReadACValueIndex.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(_Guid),
        ctypes.POINTER(_Guid),
        ctypes.POINTER(_Guid),
        ctypes.POINTER(wintypes.DWORD),
    ]
    powrprof.PowerReadACValueIndex.restype = wintypes.DWORD
    powrprof.PowerReadDCValueIndex.argtypes = powrprof.PowerReadACValueIndex.argtypes
    powrprof.PowerReadDCValueIndex.restype = wintypes.DWORD
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    kernel32.GetSystemPowerStatus.argtypes = [ctypes.POINTER(_SystemPowerStatus)]
    kernel32.GetSystemPowerStatus.restype = wintypes.BOOL

    scheme = ctypes.POINTER(_Guid)()
    result = powrprof.PowerGetActiveScheme(None, ctypes.byref(scheme))
    if result != ERROR_SUCCESS:
        raise OSError(result, "PowerGetActiveScheme failed")
    try:
        ac_timeout = wintypes.DWORD()
        dc_timeout = wintypes.DWORD()
        result = powrprof.PowerReadACValueIndex(
            None,
            scheme,
            ctypes.byref(GUID_SLEEP_SUBGROUP),
            ctypes.byref(GUID_STANDBYIDLE),
            ctypes.byref(ac_timeout),
        )
        if result != ERROR_SUCCESS:
            raise OSError(result, "PowerReadACValueIndex for sleep timeout failed")
        result = powrprof.PowerReadDCValueIndex(
            None,
            scheme,
            ctypes.byref(GUID_SLEEP_SUBGROUP),
            ctypes.byref(GUID_STANDBYIDLE),
            ctypes.byref(dc_timeout),
        )
        if result != ERROR_SUCCESS:
            raise OSError(result, "PowerReadDCValueIndex for sleep timeout failed")
    finally:
        kernel32.LocalFree(ctypes.cast(scheme, ctypes.c_void_p))

    power_status = _SystemPowerStatus()
    if not kernel32.GetSystemPowerStatus(ctypes.byref(power_status)):
        raise ctypes.WinError(ctypes.get_last_error())
    if power_status.ac_line_status == AC_LINE_ONLINE:
        on_ac_power: bool | None = True
    elif power_status.ac_line_status == AC_LINE_OFFLINE:
        on_ac_power = False
    elif power_status.ac_line_status == AC_LINE_UNKNOWN:
        on_ac_power = None
    else:
        on_ac_power = None
    return SleepTimeoutInfo(ac_timeout.value, dc_timeout.value, on_ac_power)


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
