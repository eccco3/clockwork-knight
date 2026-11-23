"""Runs Godot on a hidden Windows desktop, so its windows never appear on the visible one.

    toolchain\\blender\\4.5\\python\\bin\\python.exe -I dev\\quiet.py [--timing] <godot arguments>

Output and the exit code pass through. Works from a worktree: Godot is found in a parent folder.

--timing makes the run exclusive across every worktree: it waits until no other Godot or Blender is
running, and other quiet.py launches wait until it ends.
"""
import ctypes
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path

DESKTOP = 'ClockworkQuiet'
GODOT = 'toolchain/godot/Godot_v4.7.2-stable_win64_console.exe'
TIMING_LOCK = 'Local\\ClockworkGpuTiming'
GPU_USERS = ('godot', 'blender')

user32 = ctypes.WinDLL('user32', use_last_error=True)
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
user32.CreateDesktopW.restype = wintypes.HANDLE
user32.CreateDesktopW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPVOID, wintypes.DWORD,
                                  wintypes.DWORD, wintypes.LPVOID]
kernel32.GetStdHandle.restype = wintypes.HANDLE
kernel32.SetHandleInformation.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD]
kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
kernel32.CreateMutexW.restype = wintypes.HANDLE
kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.ReleaseMutex.argtypes = [wintypes.HANDLE]
INFINITE = 0xFFFFFFFF


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


def gpu_users() -> list[str]:
    listing = subprocess.run(['tasklist', '/fo', 'csv', '/nh'], capture_output=True, text=True).stdout
    names = (line.split(',')[0].strip('"') for line in listing.splitlines() if line)
    return sorted({name for name in names if name.lower().startswith(GPU_USERS)})


def wait_until_alone() -> None:
    reported = None
    while busy := gpu_users():
        if busy != reported:
            print(f'quiet: timing run waiting for {", ".join(busy)}', file=sys.stderr, flush=True)
            reported = busy
        time.sleep(2)


def main() -> int:
    args = sys.argv[1:]
    timing = '--timing' in args
    if timing:
        args.remove('--timing')
    lock = kernel32.CreateMutexW(None, False, TIMING_LOCK)
    kernel32.WaitForSingleObject(lock, INFINITE)
    try:
        if timing:
            wait_until_alone()
        process = launch(args)
    finally:
        if not timing:
            kernel32.ReleaseMutex(lock)
    kernel32.WaitForSingleObject(process, INFINITE)
    code = wintypes.DWORD()
    kernel32.GetExitCodeProcess(process, ctypes.byref(code))
    return code.value


def launch(args: list[str]) -> wintypes.HANDLE:
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
    line = ctypes.create_unicode_buffer(subprocess.list2cmdline([str(find_godot())] + args))
    if not kernel32.CreateProcessW(None, line, None, None, True, 0, None, None, ctypes.byref(si), ctypes.byref(pi)):
        sys.exit(f'quiet: CreateProcess failed ({ctypes.get_last_error()})')
    return pi.hProcess


if __name__ == '__main__':
    sys.exit(main())
