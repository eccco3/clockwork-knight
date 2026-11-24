using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;

static class Launcher
{
    // The taskbar click lets this process take the foreground; pass that on, or the picker opens behind other windows.
    [DllImport("user32.dll")]
    static extern bool AllowSetForegroundWindow(int processId);

    static void Main()
    {
        string script = Path.Combine(Path.GetDirectoryName(typeof(Launcher).Assembly.Location), "playtest.ps1");
        Process picker = Process.Start(new ProcessStartInfo("powershell.exe", "-NoProfile -ExecutionPolicy Bypass -STA -File \"" + script + "\"")
        {
            UseShellExecute = false,
            CreateNoWindow = true
        });
        AllowSetForegroundWindow(picker.Id);
    }
}
