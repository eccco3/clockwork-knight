# Downloads the third-party files this project builds from: Poly Haven's CC0 surface scans and sky HDRI, and ICT-FaceKit.
# Re-runnable: skips files that already exist.
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$root = Split-Path -Parent $PSScriptRoot
$ua = @{ 'User-Agent' = 'scene-builder/1.0' }
$res = '2k'

$textures = @(
  # character
  'fine_grained_wood','rosewood_veneer1','oak_veneer_01','dark_wood','brown_leather',
  # hall: floor / walls / stone
  'dark_wooden_planks','wood_floor_worn','plank_flooring_04','plastered_wall_04','beige_wall_001',
  'painted_plaster_wall','medieval_blocks_03','rustic_stone_wall_02','castle_wall_slates',
  'monastery_stone_floor',
  # hall: timber and furniture
  'rough_wood','weathered_brown_planks','brown_planks_03','wood_cabinet_worn_long','wood_table_001',
  'wood_table_worn','planks_brown_10','bark_brown_02',
  # hall: soft goods and props
  'velour_velvet','fabric_pattern_07','floral_jacquard','quatrefoil_jacquard_fabric','rough_linen',
  'wool_boucle','hessian_230','book_pattern','leather_red_02','rusty_metal_02','metal_plate',
  # hall: extra plain stone / plaster / roof boards
  'rock_surface','sandstone_cracks','white_rough_plaster','white_plaster_rough_01','roof_planks','rough_concrete','leather_red_03',
  # outdoors: bare earth and its mossy patches
  'brown_mud_02','forrest_ground_01'
)
$maps = [ordered]@{ Diffuse = 'albedo'; nor_gl = 'normal'; arm = 'arm'; Displacement = 'height' }

foreach ($id in $textures) {
  $dir = Join-Path $root "assets\textures\$id"
  New-Item -ItemType Directory -Force $dir | Out-Null
  $files = $null
  foreach ($m in $maps.Keys) {
    $out = Join-Path $dir "$($maps[$m]).jpg"
    if (Test-Path $out) { continue }
    if ($null -eq $files) { $files = Invoke-RestMethod -Uri "https://api.polyhaven.com/files/$id" -Headers $ua }
    $entry = $files.$m
    if ($null -eq $entry -or $null -eq $entry.$res -or $null -eq $entry.$res.jpg) { continue }
    Invoke-WebRequest -Uri $entry.$res.jpg.url -OutFile $out -Headers $ua
  }
  "{0,-28} {1}" -f $id, ((Get-ChildItem $dir -File | ForEach-Object { $_.Name }) -join ' ')
}

$hdris = @('kloppenheim_06_puresky')
$hdir = Join-Path $root 'assets\hdri'
New-Item -ItemType Directory -Force $hdir | Out-Null
foreach ($id in $hdris) {
  $out = Join-Path $hdir "$id.hdr"
  if (-not (Test-Path $out)) {
    $files = Invoke-RestMethod -Uri "https://api.polyhaven.com/files/$id" -Headers $ua
    Invoke-WebRequest -Uri $files.hdri.$res.hdr.url -OutFile $out -Headers $ua
  }
  "{0,-28} {1:N1} MB" -f $id, ((Get-Item $out).Length / 1MB)
}

# ICT-FaceKit (MIT): the generic head and its 100 identity modes, which tools/faces builds the face model from.
$kit = 'https://raw.githubusercontent.com/USC-ICT/ICT-FaceKit/da5f95a607f5e6b37755b38d3385d7f2853732e5'
$kdir = Join-Path $root 'tools\downloads\ict_facekit'
New-Item -ItemType Directory -Force $kdir | Out-Null
$shapes = @('generic_neutral_mesh') + (0..99 | ForEach-Object { 'identity{0:d3}' -f $_ })
foreach ($file in @('LICENSE') + ($shapes | ForEach-Object { "FaceXModel/$_.obj" })) {
  $out = Join-Path $kdir (Split-Path -Leaf $file)
  if (Test-Path $out) { continue }
  Invoke-WebRequest -Uri "$kit/$file" -OutFile "$out.part" -Headers $ua
  Move-Item "$out.part" $out
}
"{0,-28} {1:N0} MB" -f 'ict_facekit', ((Get-ChildItem $kdir -File | Measure-Object Length -Sum).Sum / 1MB)
