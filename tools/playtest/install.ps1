# Draws playtest.ico, compiles playtest.exe from launcher.cs and adds a shortcut to it to the Start menu,
# where the dev pins it to the taskbar. Run it in the main checkout, so the pin follows main.
param([string]$ShortcutFolder = [Environment]::GetFolderPath('Programs'))
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$icon = Join-Path $PSScriptRoot 'playtest.ico'
$exe = Join-Path $PSScriptRoot 'playtest.exe'

function New-Glyph([int]$size) {
  $bitmap = New-Object Drawing.Bitmap $size, $size
  $g = [Drawing.Graphics]::FromImage($bitmap)
  $g.SmoothingMode = 'AntiAlias'
  $g.ScaleTransform($size / 100, $size / 100)
  $teeth = 9
  $gear = for ($i = 0; $i -lt $teeth * 4; $i++) {
    $angle = 2 * [math]::PI * ([math]::Floor($i / 4) + (0, 0.12, 0.42, 0.54)[$i % 4]) / $teeth
    $radius = (40, 48, 48, 40)[$i % 4]
    New-Object Drawing.PointF ([float](50 + $radius * [math]::Sin($angle))), ([float](50 - $radius * [math]::Cos($angle)))
  }
  $body = New-Object Drawing.Drawing2D.GraphicsPath
  $body.AddPolygon([Drawing.PointF[]]$gear)
  $body.AddEllipse(35, 35, 30, 30)
  $brass = New-Object Drawing.Drawing2D.LinearGradientBrush ([Drawing.PointF]::new(10, 5)), ([Drawing.PointF]::new(90, 95)),
    ([Drawing.Color]::FromArgb(242, 196, 92)), ([Drawing.Color]::FromArgb(122, 76, 22))
  $g.FillPath($brass, $body)
  $g.DrawPath((New-Object Drawing.Pen ([Drawing.Color]::FromArgb(64, 38, 10)), 2.5), $body)
  $dark = New-Object Drawing.SolidBrush ([Drawing.Color]::FromArgb(40, 28, 20))
  $steel = New-Object Drawing.Drawing2D.LinearGradientBrush ([Drawing.PointF]::new(44, 0)), ([Drawing.PointF]::new(56, 0)),
    ([Drawing.Color]::FromArgb(250, 250, 255)), ([Drawing.Color]::FromArgb(130, 140, 155))
  $blade = [Drawing.PointF[]]@((New-Object Drawing.PointF 50, 4), (New-Object Drawing.PointF 56, 13),
    (New-Object Drawing.PointF 56, 66), (New-Object Drawing.PointF 44, 66), (New-Object Drawing.PointF 44, 13))
  $g.FillPolygon($steel, $blade)
  $g.DrawPolygon((New-Object Drawing.Pen ([Drawing.Color]::FromArgb(40, 44, 52)), 2), $blade)
  $g.FillRectangle($dark, 29, 64, 42, 9)
  $g.FillRectangle($dark, 45, 72, 10, 17)
  $g.FillEllipse($dark, 42, 86, 16, 12)
  $g.Dispose()
  $bitmap
}

function Get-IconImage([int]$size) {
  $bitmap = New-Glyph $size
  $data = $bitmap.LockBits((New-Object Drawing.Rectangle 0, 0, $size, $size), 'ReadOnly', 'Format32bppArgb')
  $pixels = New-Object byte[] ($size * $size * 4)
  [Runtime.InteropServices.Marshal]::Copy($data.Scan0, $pixels, 0, $pixels.Length)
  $bitmap.UnlockBits($data)
  $stream = New-Object IO.MemoryStream
  $writer = New-Object IO.BinaryWriter $stream
  foreach ($value in 40, $size, (2 * $size)) { $writer.Write([int32]$value) }
  $writer.Write([uint16]1); $writer.Write([uint16]32); $writer.Write((New-Object byte[] 24))
  for ($y = $size - 1; $y -ge 0; $y--) { $writer.Write($pixels, $y * $size * 4, $size * 4) }
  $writer.Write((New-Object byte[] ([math]::Ceiling($size / 32) * 4 * $size)))
  $writer.Flush()
  , $stream.ToArray()
}

function Save-Icon([string]$path, [int[]]$sizes) {
  $images = foreach ($size in $sizes) { , (Get-IconImage $size) }
  $writer = New-Object IO.BinaryWriter ([IO.File]::Create($path))
  $writer.Write([uint16]0); $writer.Write([uint16]1); $writer.Write([uint16]$sizes.Count)
  $offset = 6 + 16 * $sizes.Count
  for ($i = 0; $i -lt $sizes.Count; $i++) {
    $writer.Write([byte]($sizes[$i] % 256)); $writer.Write([byte]($sizes[$i] % 256)); $writer.Write([uint16]0)
    $writer.Write([uint16]1); $writer.Write([uint16]32); $writer.Write([uint32]$images[$i].Length); $writer.Write([uint32]$offset)
    $offset += $images[$i].Length
  }
  foreach ($image in $images) { $writer.Write($image) }
  $writer.Close()
}

Save-Icon $icon 16, 20, 24, 32, 40, 48, 64, 256
$csc = Join-Path ([Runtime.InteropServices.RuntimeEnvironment]::GetRuntimeDirectory()) 'csc.exe'
& $csc /nologo /target:winexe "/win32icon:$icon" "/out:$exe" (Join-Path $PSScriptRoot 'launcher.cs')
if ($LASTEXITCODE -ne 0) { throw "csc failed with exit code $LASTEXITCODE" }
$shortcut = (New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $ShortcutFolder 'Clockwork Knight playtest.lnk'))
$shortcut.TargetPath = $exe
$shortcut.WorkingDirectory = $PSScriptRoot
$shortcut.IconLocation = "$exe,0"
$shortcut.Description = 'Play the main checkout or a worktree'
$shortcut.Save()
"Shortcut: $($shortcut.FullName)"
