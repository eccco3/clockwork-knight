# Speaks a figure's lines in Windows' own voice (System.Speech), until she has a recorded one. Each line of
# <folder>\lines.json becomes <key>.wav and <key>.json: when the voice reaches each of SAPI's 22 visemes, in
# seconds, which scripts/mouth.gd times her lips to.
#   tools\voice.ps1 assets\voices\rosalyn
param([Parameter(Mandatory)] [string]$Folder)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
Add-Type -ReferencedAssemblies System.Speech -TypeDefinition @'
using System.Collections.Generic;
using System.Speech.Synthesis;

public static class Voicing {
    // Each viseme the synthesizer reports as it speaks: where in the audio it starts, which, how long it lasts,
    // and its place in the report.
    public static List<double[]> Speak(SpeechSynthesizer voice, string text) {
        var heard = new List<double[]>();
        System.EventHandler<VisemeReachedEventArgs> note = (sender, e) =>
            heard.Add(new double[] { e.AudioPosition.TotalSeconds, e.Viseme, e.Duration.TotalSeconds, heard.Count });
        voice.VisemeReached += note;
        voice.Speak(text);
        voice.VisemeReached -= note;
        return heard;
    }
}
'@

$spec = Get-Content (Join-Path $Folder 'lines.json') -Raw | ConvertFrom-Json
$voice = New-Object System.Speech.Synthesis.SpeechSynthesizer
$voice.SelectVoice($spec.voice)
$voice.Rate = $spec.rate
# At 16 kHz the reported positions match the audio; at other rates they drift.
$format = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000,
  [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
$plain = New-Object System.Text.UTF8Encoding($false)
try {
  foreach ($line in $spec.lines.PSObject.Properties) {
    $wav = [System.IO.Path]::GetFullPath((Join-Path $Folder "$($line.Name).wav"))
    $voice.SetOutputToWaveFile($wav, $format)
    $heard = [Voicing]::Speak($voice, $line.Value)
    $voice.SetOutputToNull()
    # A diphthong's two visemes share a start: the second follows the first.
    $marks = @()
    $start, $at, $lasts = -1.0, -1.0, 0.0
    foreach ($mark in ($heard | Sort-Object { $_[0] }, { $_[3] })) {
      $at = if ($mark[0] -gt $start) { $mark[0] } else { $at + $lasts }
      $start, $lasts = $mark[0], $mark[2]
      $marks += '[{0:0.000}, {1}]' -f $at, [int]$mark[1]
    }
    $json = "{`"visemes`": [" + ($marks -join ', ') + "]}`n"
    [System.IO.File]::WriteAllText([System.IO.Path]::ChangeExtension($wav, '.json'), $json, $plain)
    '{0,-10} {1,5:N2} s  {2} visemes' -f $line.Name, $heard[$heard.Count - 1][0], $marks.Count
  }
} finally {
  $voice.Dispose()
}
