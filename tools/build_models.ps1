# Rebuilds the git-ignored models (assets/models/*.glb) from source, imports them into Godot and
# bakes the hall's lightmap (assets/lightmaps/). The bake runs the Godot editor on a hidden desktop for a few minutes.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$blender = Join-Path $root 'toolchain\blender\blender.exe'
$python = Join-Path $root 'toolchain\blender\4.5\python\bin\python.exe'
$godot = Join-Path $root 'toolchain\godot\Godot_v4.7.2-stable_win64_console.exe'

function Invoke-Step([string]$name, [string]$exe, [string[]]$arguments) {
  $started = Get-Date
  $ErrorActionPreference = 'Continue' # Godot prints harmless errors on exit; only the exit code counts
  & $exe @arguments | Out-Host
  if ($LASTEXITCODE -ne 0) { throw "$name failed with exit code $LASTEXITCODE" }
  '{0,-8} {1,5:N0} s' -f $name, ((Get-Date) - $started).TotalSeconds
}

Push-Location $root
try {
  Invoke-Step 'hall' $blender @('--background', '--python-exit-code', '1', '--python', 'tools/build_hall.py')
  Invoke-Step 'knight' $blender @('--background', '--python-exit-code', '1', '--python', 'tools/knight/build_knight.py',
    '--', '--out', 'assets/models/knight.glb')
  Invoke-Step 'grinner' $blender @('--background', '--python-exit-code', '1', '--python', 'tools/grinner/build_grinner.py',
    '--', '--out', 'assets/models/grinner.glb')
  Invoke-Step 'scuttler' $blender @('--background', '--python-exit-code', '1', '--python', 'tools/grinner/build_grinner.py',
    '--', '--kind', 'scuttler', '--out', 'assets/models/scuttler.glb')
  Invoke-Step 'rosalyn' $blender @('--background', '--python-exit-code', '1', '--python', 'tools/rosalyn/build_rosalyn.py',
    '--', '--out', 'assets/models/rosalyn.glb')
  foreach ($model in 'hall', 'knight', 'grinner', 'scuttler', 'rosalyn') {
    if (-not (Test-Path "assets\models\$model.glb")) { throw "$model.glb was not written" }
  }
  Invoke-Step 'import' $godot @('--path', '.', '--headless', '--import')
  Invoke-Step 'lightmap' $python @('-I', 'dev/quiet.py', '--path', '.', '--editor', 'res://scenes/hall.tscn', '--', 'bake-lightmaps')
  if (-not (Test-Path 'assets\lightmaps\hall.exr')) { throw 'the hall lightmap was not written' }
} finally {
  Pop-Location
}
