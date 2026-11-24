using System.Diagnostics;
using System.IO;

static class Launcher
{
    static void Main()
    {
        string script = Path.Combine(Path.GetDirectoryName(typeof(Launcher).Assembly.Location), "playtest.ps1");
        Process.Start(new ProcessStartInfo("powershell.exe", "-NoProfile -ExecutionPolicy Bypass -STA -File \"" + script + "\"")
        {
            UseShellExecute = false,
            CreateNoWindow = true
        });
    }
}
