"""Runs Godot on a hidden Windows desktop, so its windows never appear on the visible one.

    toolchain\\blender\\4.5\\python\\bin\\python.exe -I dev\\quiet.py <godot arguments>

Output and the exit code pass through. Works from a worktree: Godot is found in a parent folder.
"""
import ctypes
import subprocess
import sys
from ctypes import wintypes
from pathlib import Path

DESKTOP = 'ClockworkQuiet'
GODOT = 'toolchain/godot/Godot_v4.7.2-stable_win64_console.exe'

user32 = ctypes.WinDLL('user32', use_last_error=True)
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
user32.CreateDesktopW.restype = wintypes.HANDLE
user32.CreateDesktopW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPVOID, wintypes.DWORD,
                                  wintypes.DWORD, wintypes.LPVOID]
kernel32.GetStdHandle.restype = wintypes.HANDLE
kernel32.SetHandleInformation.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD]
kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]


class StartupInfo(ctypes.Structure):
    _fields_ = [('cb', wintypes.DWORD), ('lpReserved', wintypes.LPWSTR), ('lpDesktop', wintypes.LPWSTR),
                ('lpTitle', wintypes.LPWSTR), ('dwX', wintypes.DWORD), ('dwY', wintypes.DWORD),
                ('dwXSize', wintypes.DWORD), ('dwYSize', wintypes.DWORD), ('dwXCountChars', wintypes.DWORD),
                ('dwYCountChars', wintypes.DWORD), ('dwFillAttribute', wintypes.DWORD), ('dwFlags', wintypes.DWORD),
                ('wShowWindow', wintypes.WORD), ('cbReserved2', wintypes.WORD), ('lpReserved2', wintypes.LPVOID),
                ('hStdInput', wintypes.HANDLE), ('hStdOutput', wintypes.HANDLE), ('hStdError', wintypes.HANDLE)]


class ProcessInformation(ctypes.Structure):
    _fields_ = [('hProcess', wintypes.HANDLE), ('hThread', wintypes.HANDLE),
                ('dwProcessId', wintypes.DWORD), ('dwThreadId', wintypes.DWORD)]


kernel32.CreateProcessW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.LPVOID, wintypes.LPVOID,
                                    wintypes.BOOL, wintypes.DWORD, wintypes.LPVOID, wintypes.LPCWSTR,
                                    ctypes.POINTER(StartupInfo), ctypes.POINTER(ProcessInformation)]


def find_godot() -> Path:
    for folder in Path(__file__).resolve().parents:
        if (folder / GODOT).exists():
            return folder / GODOT
    sys.exit('quiet: Godot not found in any parent folder')


def main() -> int:
    if not user32.CreateDesktopW(DESKTOP, None, None, 0, 0x10000000, None):
        sys.exit(f'quiet: CreateDesktop failed ({ctypes.get_last_error()})')
    si = StartupInfo()
    si.cb = ctypes.sizeof(si)
    si.lpDesktop = 'WinSta0\\' + DESKTOP
    si.dwFlags = 0x100
    handles = [kernel32.GetStdHandle(n) for n in (-10, -11, -12)]
    for h in handles:
        if h:
            kernel32.SetHandleInformation(h, 1, 1)
    si.hStdInput, si.hStdOutput, si.hStdError = handles
    pi = ProcessInformation()
    line = ctypes.create_unicode_buffer(subprocess.list2cmdline([str(find_godot())] + sys.argv[1:]))
    if not kernel32.CreateProcessW(None, line, None, None, True, 0, None, None, ctypes.byref(si), ctypes.byref(pi)):
        sys.exit(f'quiet: CreateProcess failed ({ctypes.get_last_error()})')
    kernel32.WaitForSingleObject(pi.hProcess, 0xFFFFFFFF)
    code = wintypes.DWORD()
    kernel32.GetExitCodeProcess(pi.hProcess, ctypes.byref(code))
    return code.value


if __name__ == '__main__':
    sys.exit(main())
