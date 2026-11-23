# Rebuilds the git-ignored models (assets/models/*.glb) from source and imports them into Godot.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$blender = Join-Path $root 'toolchain\blender\blender.exe'
$godot = Join-Path $root 'toolchain\godot\Godot_v4.7.2-stable_win64_console.exe'

function Invoke-Step([string]$name, [string]$exe, [string[]]$arguments) {
  $started = Get-Date
  & $exe @arguments | Out-Host
  if ($LASTEXITCODE -ne 0) { throw "$name failed with exit code $LASTEXITCODE" }
  '{0,-8} {1,5:N0} s' -f $name, ((Get-Date) - $started).TotalSeconds
}

Push-Location $root
try {
  Invoke-Step 'hall' $blender @('--background', '--python-exit-code', '1', '--python', 'tools/build_hall.py')
  Invoke-Step 'knight' $blender @('--background', '--python-exit-code', '1', '--python', 'tools/knight/build_knight.py',
    '--', '--out', 'assets/models/knight.glb')
  foreach ($model in 'hall', 'knight') {
    if (-not (Test-Path "assets\models\$model.glb")) { throw "$model.glb was not written" }
  }
  Invoke-Step 'import' $godot @('--path', '.', '--headless', '--import')
} finally {
  Pop-Location
}
