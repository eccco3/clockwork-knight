# Picks the main checkout or a worktree and one of its playable scenes or dev tools, readies the checkout
# (an import shows Godot's progress, one launcher at a time) and starts the scene windowed. A scene is playable when its root node has metadata/playable, the title
# listed here, and a dev tool when it has metadata/dev_tool; a checkout without any offers its main scene. The scene last played is remembered per user.
# -DryRun prints the picker's entries and the steps it would take for -Pick (a branch or folder; main
# by default) and -Scene (a title or res:// path; the remembered one by default).
param([switch]$DryRun, [string]$Pick, [string]$Scene)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch {}

$script:Report = { param($line) Write-Host $line }
$script:Progress = { param($text, $percent) }      # a long step's progress: text, or none once done; percent, or -1 if unknown
$script:Notes = 0
$script:LastScene = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'Clockwork Knight\playtest scene.txt'

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

function Invoke-Hidden([string]$exe, [string[]]$arguments, [scriptblock]$onLine = {}) {
  $info = New-Object Diagnostics.ProcessStartInfo $exe, (($arguments | ForEach-Object { "`"$_`"" }) -join ' ')
  $info.UseShellExecute = $false
  $info.CreateNoWindow = $true
  $info.RedirectStandardOutput = $true
  $info.RedirectStandardError = $true
  $process = [Diagnostics.Process]::Start($info)
  $errors = $process.StandardError.ReadToEndAsync()
  $lines = New-Object Collections.Generic.List[string]
  $next = $process.StandardOutput.ReadLineAsync()
  while ($true) {                                   # each line as it comes, the window kept responsive between them
    if ($next.Wait(50)) {
      if ($null -eq $next.Result) { break }
      $lines.Add($next.Result); & $onLine $next.Result
      $next = $process.StandardOutput.ReadLineAsync()
    } else { & $onLine $null }
    [Windows.Forms.Application]::DoEvents()
  }
  $process.WaitForExit()
  if ($process.ExitCode -ne 0) {
    $tail = @($lines) + ($errors.Result -split '\r?\n') | Where-Object { $_ } | Select-Object -Last 12
    throw "$(Split-Path -Leaf $exe) exited with code $($process.ExitCode):`r`n$($tail -join "`r`n")"
  }
}

# Godot's import reports each task's progress as "[ 25% ] task | item", coloured for a terminal.
function Read-GodotProgress([string]$line) {
  if (($line -replace '\x1b\[[0-9;]*m') -match '^\[\s*(\d+)% \]\s+(\S+)\s+\|\s*(.*)$') {
    [pscustomobject]@{ Percent = [int]$Matches[1]; Task = $Matches[2]; Item = $Matches[3].Trim() }
  }
}

# Imports a checkout, showing Godot's progress and the time taken. Only one launcher imports a checkout at
# a time: another waits for it, then imports only if something is still out of date.
function Wait-Lock([Threading.Mutex]$lock, [int]$ms) {
  try { $lock.WaitOne($ms) } catch [Threading.AbandonedMutexException] { $true }   # its last holder was killed
}

function Invoke-Import($console, [string]$dir) {
  $lock = New-Object Threading.Mutex $false, ('Local\ClockworkKnightImport_' + [BitConverter]::ToString(
    [Security.Cryptography.MD5]::Create().ComputeHash([Text.Encoding]::UTF8.GetBytes($dir.ToLowerInvariant()))).Replace('-', ''))
  $started = Get-Date
  $held = $false
  try {
    $held = Wait-Lock $lock 0
    if (-not $held) {
      Write-Report 'Another launcher is importing this checkout; waiting for it...'
      while (-not $held) {
        $held = Wait-Lock $lock 50
        & $script:Progress ('Waiting for the other import, {0:m\:ss}' -f ((Get-Date) - $started)) -1
        [Windows.Forms.Application]::DoEvents()
      }
    }
    $reason = Get-ImportReason $dir
    if (-not $reason) { return }
    Write-Report "import ($reason)..."
    $state = @{ Text = 'Starting Godot'; Percent = -1 }
    Invoke-Hidden $console @('--headless', '--path', $dir, '--import') {
      param($line)
      $step = if ($line) { Read-GodotProgress $line }
      if ($step) { $state.Text = if ($step.Item) { "$($step.Task): $($step.Item)" } else { $step.Task }; $state.Percent = $step.Percent }
      & $script:Progress ('Importing, {0:m\:ss}  {1}' -f ((Get-Date) - $started), $state.Text) $state.Percent
    }
    Write-Report ('Imported in {0:m\:ss}.' -f ((Get-Date) - $started))
  } finally {
    if ($held) { $lock.ReleaseMutex() }
    $lock.Dispose()
    & $script:Progress $null 0
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

function Get-ProjectFiles([string]$dir) {
  Get-ChildItem -LiteralPath $dir -Directory |
    Where-Object { -not $_.Name.StartsWith('.') -and -not (Test-Path (Join-Path $_.FullName '.gdignore')) } |
    Get-ChildItem -Recurse -File
}

function Get-PlayableTitle([string]$scene) {
  $root = [regex]::Match([IO.File]::ReadAllText($scene), '(?ms)^\[node .*?(?=^\[|\z)').Value
  if ($root -match '(?m)^metadata/playable = "(.*)"\r?$') { $Matches[1] }
  elseif ($root -match '(?m)^metadata/dev_tool = "(.*)"\r?$') { "Tool: $($Matches[1])" }
}

function New-Scene([string]$title, [string]$path, [string]$main) {
  [pscustomobject]@{ Title = $title; Path = $path; IsMain = $path -eq $main }
}

function Get-Scenes([string]$dir) {
  $main = if ((Get-Content -Raw -LiteralPath (Join-Path $dir 'project.godot')) -match '(?m)^run/main_scene="(.*)"') { $Matches[1] }
  $scenes = foreach ($file in Get-ProjectFiles $dir | Where-Object Extension -eq '.tscn') {
    $title = Get-PlayableTitle $file.FullName
    if ($title) { New-Scene $title ('res://' + $file.FullName.Substring($dir.Length + 1).Replace('\', '/')) $main }
  }
  if (-not $scenes) { $scenes = New-Scene ([IO.Path]::GetFileNameWithoutExtension($main)) $main $main }
  @($scenes) | Sort-Object @{ e = 'IsMain'; Descending = $true }, Title
}

function Find-Scene($scenes, [string]$name) {
  $scenes | Where-Object { $name -in $_.Title, $_.Path } | Select-Object -First 1
}

function Get-DefaultScene($scenes, [string]$wanted) {
  $found = Find-Scene $scenes $wanted
  if ($found) { $found } else { @($scenes)[0] }
}

function Get-LastScene { Get-Content -LiteralPath $script:LastScene -TotalCount 1 -ErrorAction SilentlyContinue }

function Save-LastScene($scene) {
  New-Item -ItemType Directory -Force (Split-Path $script:LastScene) | Out-Null
  Set-Content -LiteralPath $script:LastScene $scene.Path
}

function Get-ImportReason([string]$dir) {
  $classes = Get-Item -LiteralPath (Join-Path $dir '.godot\global_script_class_cache.cfg') -ErrorAction SilentlyContinue
  if (-not $classes) { return 'no import cache' }
  $files = Get-ProjectFiles $dir | Where-Object Extension -in '.gd', '.import'
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

function Start-Playtest($checkout, $main, $scene) {
  $godot = Join-Path $main.Path 'toolchain\godot\Godot_v4.7.2-stable_win64.exe'
  $console = Join-Path $main.Path 'toolchain\godot\Godot_v4.7.2-stable_win64_console.exe'
  foreach ($exe in $godot, $console) { if (-not (Test-Path $exe)) { throw "Missing toolchain: $exe" } }
  Write-Report "$($scene.Title) from $($checkout.Branch) in $($checkout.Path)"
  if ($checkout.IsMain) {
    try { Update-Checkout $checkout.Path } catch { Write-Note "not updated: $_" }
  }
  Copy-MissingAssets $main.Path $checkout.Path
  if ($DryRun) {
    $reason = Get-ImportReason $checkout.Path
    if ($reason) { Write-Report "Would import ($reason)" }
  } else { Invoke-Import $console $checkout.Path }
  $arguments = @('--path', "`"$($checkout.Path)`"", "`"$($scene.Path)`"")
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
  $label = New-Object Windows.Forms.Label -Property @{ Text = '&Scene'; AutoSize = $true; Anchor = 'None'; TabIndex = 0 }
  $sceneBox = New-Object Windows.Forms.ComboBox -Property @{ DropDownStyle = 'DropDownList'; Width = 240; Anchor = 'None'; TabIndex = 1 }
  $play = New-Object Windows.Forms.Button -Property @{ Text = 'Play'; Width = 110; Height = 30; TabIndex = 2 }
  $bar = New-Object Windows.Forms.FlowLayoutPanel -Property @{ Dock = 'Bottom'; Height = 40; FlowDirection = 'RightToLeft'; Padding = '2, 2, 2, 2' }
  $bar.Controls.AddRange(@($play, $sceneBox, $label))
  $progress = New-Object Windows.Forms.ProgressBar -Property @{ Dock = 'Bottom'; Height = 18; Maximum = 100; Visible = $false }
  $status = New-Object Windows.Forms.Label -Property @{ Dock = 'Bottom'; Height = 22; AutoEllipsis = $true; Visible = $false }
  $form.Controls.AddRange(@($list, $status, $progress, $log, $bar))
  $form.AcceptButton = $play
  $form.Add_KeyDown({ if ($_.KeyCode -eq 'Escape') { $form.Close() } })
  $script:Report = { param($line) $log.AppendText("$line`r`n"); [Windows.Forms.Application]::DoEvents() }.GetNewClosure()
  $script:Progress = {
    param($text, $percent)
    $progress.Visible = $status.Visible = [bool]$text
    if (-not $text) { return }
    if ($status.Text -ne $text) { $status.Text = $text }
    if ($percent -lt 0) { $progress.Style = 'Marquee' } else { $progress.Style = 'Continuous'; $progress.Value = [math]::Min(100, $percent) }
  }.GetNewClosure()

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

  $sceneCache = @{}
  $wanted = @{ Path = Get-LastScene }
  $showScenes = {
    if (-not $list.SelectedItems.Count) { return }
    try {
      $path = $list.SelectedItems[0].Tag.Path
      if (-not $sceneCache[$path]) { $sceneCache[$path] = @(Get-Scenes $path) }
      $scenes = $sceneCache[$path]
      $chosen = Get-DefaultScene $scenes $wanted.Path
      $sceneBox.Items.Clear()
      $sceneBox.Items.AddRange([object[]]$scenes.Title)
      $sceneBox.Tag = $scenes
      $sceneBox.SelectedIndex = [array]::IndexOf([object[]]$scenes.Path, $chosen.Path)
    } catch { Write-Report "Failed: $_" }
  }
  $list.Add_SelectedIndexChanged($showScenes)
  $sceneBox.Add_SelectionChangeCommitted({ $wanted.Path = $sceneBox.Tag[$sceneBox.SelectedIndex].Path })
  & $showScenes

  $play.Add_Click({
    if (-not $list.SelectedItems.Count -or $sceneBox.SelectedIndex -lt 0) { return }
    $scene = $sceneBox.Tag[$sceneBox.SelectedIndex]
    $list.Enabled = $sceneBox.Enabled = $play.Enabled = $false
    $script:Notes = 0
    try {
      Start-Playtest $list.SelectedItems[0].Tag $main $scene
      Save-LastScene $scene
      if ($script:Notes) { Write-Report 'Game started.' } else { $form.Close() }
    } catch { Write-Report "Failed: $_" }
    $list.Enabled = $sceneBox.Enabled = $play.Enabled = $true
  })
  $list.Add_DoubleClick({ $play.PerformClick() })
  # The picker takes seconds to list the checkouts, by which time Windows may keep it behind the window in front.
  $form.Add_Shown({
    $form.TopMost = $true; $form.TopMost = $false; $form.Activate()
    if ($list.SelectedItems.Count) { $list.SelectedItems[0].EnsureVisible() }; $list.Focus()
  })
  $form.ShowDialog() | Out-Null
}

if ($DryRun) {
  $checkouts = @(Get-Checkouts | Sort-Object Time -Descending)
  $main = $checkouts | Where-Object IsMain
  $checkouts | Format-Table @{ n = ' '; e = { if ($_.IsMain) { '>' } } }, Branch, @{ n = 'Age'; e = { Format-Age $_.Time } }, Subject |
    Out-String -Width 200 | Write-Host
  $checkout = if ($Pick) { $checkouts | Where-Object { $Pick -in $_.Branch, $_.Path } | Select-Object -First 1 } else { $main }
  if (-not $checkout) { throw "No checkout matches $Pick" }
  $scenes = @(Get-Scenes $checkout.Path)
  $default = Get-DefaultScene $scenes (Get-LastScene)
  $scenes | Format-Table @{ n = ' '; e = { if ($_.Path -eq $default.Path) { '>' } } }, Title, Path |
    Out-String -Width 200 | Write-Host
  $chosen = if ($Scene) { Find-Scene $scenes $Scene } else { $default }
  if (-not $chosen) { throw "No playable scene in $($checkout.Branch) matches $Scene" }
  Start-Playtest $checkout $main $chosen
} else {
  Show-Picker
}
