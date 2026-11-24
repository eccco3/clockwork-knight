# Picks the main checkout or a worktree, readies it and starts the game windowed. -DryRun prints the
# picker's entries and the steps it would take for -Pick (a branch or folder; main by default).
param([switch]$DryRun, [string]$Pick)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch {}

$script:Report = { param($line) Write-Host $line }
$script:Notes = 0

function Write-Report([string]$line) { & $script:Report $line }
function Write-Note([string]$line) { $script:Notes++; Write-Report "Note: $line" }

function Invoke-Step([string]$text, [scriptblock]$action) {
  if ($DryRun) { Write-Report "Would $text" } else { Write-Report "$text..."; & $action }
}

function Invoke-Git([string]$dir, [string[]]$arguments) {
  $ErrorActionPreference = 'Continue'
  $output = & git -c core.quotePath=false -C $dir @arguments 2>&1 | ForEach-Object { "$_" }
  if ($LASTEXITCODE -ne 0) { throw "git $arguments failed in ${dir}: $($output -join ' ')" }
  $output
}

function Invoke-Hidden([string]$exe, [string[]]$arguments) {
  $info = New-Object Diagnostics.ProcessStartInfo $exe, (($arguments | ForEach-Object { "`"$_`"" }) -join ' ')
  $info.UseShellExecute = $false
  $info.CreateNoWindow = $true
  $info.RedirectStandardOutput = $true
  $info.RedirectStandardError = $true
  $process = [Diagnostics.Process]::Start($info)
  $output = $process.StandardOutput.ReadToEndAsync()
  $errors = $process.StandardError.ReadToEndAsync()
  while (-not $process.WaitForExit(50)) { [Windows.Forms.Application]::DoEvents() }
  $process.WaitForExit()
  if ($process.ExitCode -ne 0) {
    $tail = ($output.Result + $errors.Result) -split '\r?\n' | Where-Object { $_ } | Select-Object -Last 12
    throw "$(Split-Path -Leaf $exe) exited with code $($process.ExitCode):`r`n$($tail -join "`r`n")"
  }
}

function Format-Age([datetime]$time) {
  $span = (Get-Date) - $time
  if ($span.TotalHours -lt 1) { '{0} min' -f [math]::Floor($span.TotalMinutes) }
  elseif ($span.TotalDays -lt 2) { '{0} h' -f [math]::Floor($span.TotalHours) }
  else { '{0} days' -f [math]::Floor($span.TotalDays) }
}

function Get-Checkouts {
  $blocks = (Invoke-Git $PSScriptRoot @('worktree', 'list', '--porcelain')) -join "`n" -split "`n`n" | Where-Object { $_ }
  for ($i = 0; $i -lt @($blocks).Count; $i++) {
    $fields = @{}
    foreach ($line in $blocks[$i] -split "`n") { $key, $value = $line -split ' ', 2; $fields[$key] = $value }
    $path = $fields.worktree -replace '/', '\'
    if (-not (Test-Path -LiteralPath (Join-Path $path 'project.godot'))) { continue }
    $time, $subject = (Invoke-Git $path @('log', '-1', '--format=%ct%x1f%s')) -split [char]0x1f, 2
    [pscustomobject]@{
      Branch = if ($fields.branch) { $fields.branch -replace '^refs/heads/' } else { "detached $($fields.HEAD.Substring(0, 7))" }
      Subject = $subject
      Time = [DateTimeOffset]::FromUnixTimeSeconds($time).LocalDateTime
      Path = $path
      IsMain = $i -eq 0
    }
  }
}

function Update-Checkout([string]$dir) {
  Invoke-Git $dir @('fetch', '--quiet') | Out-Null
  $upstream = Invoke-Git $dir @('rev-parse', '--abbrev-ref', '@{upstream}')
  $ahead, $behind = (Invoke-Git $dir @('rev-list', '--left-right', '--count', 'HEAD...@{upstream}')) -split '\s+'
  if ($behind -eq '0') { Write-Report "Up to date with $upstream." }
  elseif ($ahead -ne '0') { Write-Note "not updated: $ahead local and $behind $upstream commits have diverged." }
  elseif (Invoke-Git $dir @('status', '--porcelain', '--untracked-files=no')) { Write-Note "not updated from ${upstream}: uncommitted changes." }
  else { Invoke-Step "fast-forward $behind commits from $upstream" { Invoke-Git $dir @('merge', '--ff-only', '--quiet', '@{upstream}') | Out-Null } }
}

function Copy-MissingAssets([string]$from, [string]$to) {
  $missing = @(Invoke-Git $from @('ls-files', '--others', '--ignored', '--exclude-standard', '--', 'assets') |
    Where-Object { -not (Test-Path -LiteralPath (Join-Path $to $_)) })
  if ($missing) {
    Invoke-Step "copy $($missing.Count) built or downloaded assets from $from" {
      foreach ($file in $missing) {
        $target = Join-Path $to $file
        New-Item -ItemType Directory -Force (Split-Path $target) | Out-Null
        Copy-Item -LiteralPath (Join-Path $from $file) $target
      }
    }
  }
}

function Get-ImportReason([string]$dir) {
  $classes = Get-Item -LiteralPath (Join-Path $dir '.godot\global_script_class_cache.cfg') -ErrorAction SilentlyContinue
  if (-not $classes) { return 'no import cache' }
  $files = Get-ChildItem -LiteralPath $dir -Directory |
    Where-Object { -not $_.Name.StartsWith('.') -and -not (Test-Path (Join-Path $_.FullName '.gdignore')) } |
    Get-ChildItem -Recurse -File | Where-Object Extension -in '.gd', '.import'
  foreach ($file in $files) {
    $name = $file.FullName.Substring($dir.Length + 1)
    if ($file.Extension -eq '.gd') {
      if ($file.LastWriteTimeUtc -gt $classes.LastWriteTimeUtc) { return "$name changed" }
      continue
    }
    $source = Get-Item -LiteralPath ($file.FullName -replace '\.import$') -ErrorAction SilentlyContinue
    if (-not $source) { continue }
    $dests = Select-String -LiteralPath $file.FullName -Pattern '^dest_files=' | ForEach-Object { [regex]::Matches($_.Line, 'res://([^"]+)') }
    foreach ($dest in $dests) {
      $imported = Get-Item -LiteralPath (Join-Path $dir $dest.Groups[1].Value) -ErrorAction SilentlyContinue
      if (-not $imported) { return "$($source.Name) is not imported" }
      if ($source.LastWriteTimeUtc -le $imported.LastWriteTimeUtc) { continue }
      $md5 = Get-Content -Raw -LiteralPath ($imported.FullName -replace '(-[0-9a-f]{32})\..*$', '$1.md5') -ErrorAction SilentlyContinue
      $hash = (Get-FileHash -LiteralPath $source.FullName -Algorithm MD5).Hash
      if ("$md5" -notmatch "source_md5=`"$hash`"") { return "$($source.Name) changed" }
    }
  }
}

function Start-Playtest($checkout, $main) {
  $godot = Join-Path $main.Path 'toolchain\godot\Godot_v4.7.2-stable_win64.exe'
  $console = Join-Path $main.Path 'toolchain\godot\Godot_v4.7.2-stable_win64_console.exe'
  foreach ($exe in $godot, $console) { if (-not (Test-Path $exe)) { throw "Missing toolchain: $exe" } }
  Write-Report "$($checkout.Branch) in $($checkout.Path)"
  if ($checkout.IsMain) {
    try { Update-Checkout $checkout.Path } catch { Write-Note "not updated: $_" }
  }
  Copy-MissingAssets $main.Path $checkout.Path
  $reason = Get-ImportReason $checkout.Path
  if ($reason) { Invoke-Step "import ($reason)" { Invoke-Hidden $console @('--headless', '--path', $checkout.Path, '--import') } }
  $arguments = @('--path', "`"$($checkout.Path)`"")
  Invoke-Step "run $godot $arguments" { Start-Process $godot -ArgumentList $arguments -WorkingDirectory $checkout.Path }
}

function Show-Picker {
  Add-Type -Name Dpi -Namespace Playtest -MemberDefinition '[DllImport("user32.dll")] public static extern bool SetProcessDPIAware();'
  [Playtest.Dpi]::SetProcessDPIAware() | Out-Null
  [Windows.Forms.Application]::EnableVisualStyles()
  $form = New-Object Windows.Forms.Form -Property @{
    Text = 'Clockwork Knight playtest'; ClientSize = '900, 440'; StartPosition = 'CenterScreen'
    Font = New-Object Drawing.Font 'Segoe UI', 10; AutoScaleMode = 'Dpi'; KeyPreview = $true
  }
  $iconPath = Join-Path $PSScriptRoot 'playtest.ico'
  if (Test-Path $iconPath) { $form.Icon = New-Object Drawing.Icon $iconPath }
  $list = New-Object Windows.Forms.ListView -Property @{
    View = 'Details'; FullRowSelect = $true; MultiSelect = $false; HideSelection = $false; Dock = 'Fill'
  }
  foreach ($column in @('Branch', 310), @('Commit', 480), @('Age', 80)) { $list.Columns.Add($column[0], $column[1]) | Out-Null }
  $log = New-Object Windows.Forms.TextBox -Property @{
    Multiline = $true; ReadOnly = $true; ScrollBars = 'Vertical'; Dock = 'Bottom'; Height = 110
  }
  $play = New-Object Windows.Forms.Button -Property @{ Text = 'Play'; Dock = 'Right'; Width = 110 }
  $bar = New-Object Windows.Forms.Panel -Property @{ Dock = 'Bottom'; Height = 36; Padding = '4, 4, 4, 4' }
  $bar.Controls.Add($play)
  $form.Controls.AddRange(@($list, $log, $bar))
  $form.AcceptButton = $play
  $form.Add_KeyDown({ if ($_.KeyCode -eq 'Escape') { $form.Close() } })
  $script:Report = { param($line) $log.AppendText("$line`r`n"); [Windows.Forms.Application]::DoEvents() }.GetNewClosure()

  try {
    $checkouts = @(Get-Checkouts | Sort-Object Time -Descending)
    $main = $checkouts | Where-Object IsMain
    foreach ($checkout in $checkouts) {
      $item = New-Object Windows.Forms.ListViewItem (, [string[]]@($checkout.Branch, $checkout.Subject, (Format-Age $checkout.Time)))
      $item.Tag = $checkout
      $list.Items.Add($item) | Out-Null
      if ($checkout.IsMain) { $item.Selected = $item.Focused = $true }
    }
  } catch { Write-Report "Failed: $_" }

  $play.Add_Click({
    if (-not $list.SelectedItems.Count) { return }
    $list.Enabled = $play.Enabled = $false
    $script:Notes = 0
    try {
      Start-Playtest $list.SelectedItems[0].Tag $main
      if ($script:Notes) { Write-Report 'Game started.' } else { $form.Close() }
    } catch { Write-Report "Failed: $_" }
    $list.Enabled = $play.Enabled = $true
  })
  $list.Add_DoubleClick({ $play.PerformClick() })
  $form.Add_Shown({ if ($list.SelectedItems.Count) { $list.SelectedItems[0].EnsureVisible() }; $list.Focus() })
  $form.ShowDialog() | Out-Null
}

if ($DryRun) {
  $checkouts = @(Get-Checkouts | Sort-Object Time -Descending)
  $main = $checkouts | Where-Object IsMain
  $checkouts | Format-Table @{ n = ' '; e = { if ($_.IsMain) { '>' } } }, Branch, @{ n = 'Age'; e = { Format-Age $_.Time } }, Subject |
    Out-String -Width 200 | Write-Host
  $checkout = if ($Pick) { $checkouts | Where-Object { $Pick -in $_.Branch, $_.Path } | Select-Object -First 1 } else { $main }
  if (-not $checkout) { throw "No checkout matches $Pick" }
  Start-Playtest $checkout $main
} else {
  Show-Picker
}
