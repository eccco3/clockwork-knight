"""A face script, build_faces.py or another, run in the background: in Blender without a window, its output
in a log, and ended with the process that started it, however that ends (a Windows job object), so a
closed tool leaves no render running behind it."""
import ctypes, os, subprocess
from ctypes import wintypes

from .files import HERE

BLENDER = os.path.join("toolchain", "blender", "blender.exe")
KILL_ON_JOB_CLOSE, EXTENDED_LIMITS = 0x2000, 9
SET_QUOTA, TERMINATE = 0x0100, 0x0001

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
kernel32.CreateJobObjectW.restype = wintypes.HANDLE
kernel32.CreateJobObjectW.argtypes = [wintypes.LPVOID, wintypes.LPCWSTR]
kernel32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]


class Limits(ctypes.Structure):
    """JOBOBJECT_EXTENDED_LIMIT_INFORMATION."""
    _fields_ = [("times", ctypes.c_int64 * 2), ("flags", wintypes.DWORD), ("working_set", ctypes.c_size_t * 2),
                ("processes", wintypes.DWORD), ("affinity", ctypes.c_size_t), ("classes", wintypes.DWORD * 2),
                ("io", ctypes.c_uint64 * 6), ("memory", ctypes.c_size_t * 4)]


def job():
    """A job whose processes end when this process does: the system closes its only handle then."""
    handle = kernel32.CreateJobObjectW(None, None)
    limits = Limits(flags=KILL_ON_JOB_CLOSE)
    if not (handle and kernel32.SetInformationJobObject(handle, EXTENDED_LIMITS, ctypes.byref(limits),
                                                        ctypes.sizeof(limits))):
        raise ctypes.WinError(ctypes.get_last_error())
    return handle


JOB = job()


def blender():
    """The toolchain's Blender, in the project or, from a worktree, a folder above it."""
    folder = os.path.dirname(os.path.dirname(HERE))
    while not os.path.exists(os.path.join(folder, BLENDER)):
        if os.path.dirname(folder) == folder:
            raise FileNotFoundError(BLENDER)
        folder = os.path.dirname(folder)
    return os.path.join(folder, BLENDER)


class Build:
    """One run of the script, build_faces.py unless named, with these arguments, writing its output to `log`."""

    def __init__(self, arguments, log, script=os.path.join(HERE, "build_faces.py")):
        self.log = log
        with open(log, "w", encoding="utf-8") as out:
            self.process = subprocess.Popen(
                [blender(), "--background", "--python-exit-code", "1", "--python", script, "--"] + arguments, stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW)
        process = kernel32.OpenProcess(SET_QUOTA | TERMINATE, False, self.process.pid)
        joined = process and kernel32.AssignProcessToJobObject(JOB, process)
        error = ctypes.get_last_error()
        if process:
            kernel32.CloseHandle(process)
        if not joined:
            self.process.kill()
            raise ctypes.WinError(error)

    def running(self):
        return self.process.poll() is None

    def stop(self):
        """Ends the run, its work no longer wanted."""
        self.process.kill()
        self.process.wait()

    def failure(self):
        """Why it failed, the last line it wrote; "" while it runs or once it has succeeded."""
        if self.running() or self.process.returncode == 0:
            return ""
        with open(self.log, encoding="utf-8", errors="replace") as f:
            lines = [line.strip() for line in f if line.strip()]
        return lines[-1] if lines else "Blender exited with %d" % self.process.returncode
