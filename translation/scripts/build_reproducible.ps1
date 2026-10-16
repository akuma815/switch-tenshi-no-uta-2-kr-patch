param(
    [Parameter(Mandatory=$true)][string]$SourcePaks,
    [Parameter(Mandatory=$true)][string]$RetocPath,
    [Parameter(Mandatory=$true)][string]$RepakPath,
    [Parameter(Mandatory=$true)][string]$XdeltaPath,
    [string]$ReleaseArchive = ''
)
$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$root = Split-Path (Split-Path $PSScriptRoot)
$inputs = Get-Content -LiteralPath (Join-Path $root 'config/rebuild_inputs.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$prepare = @('--source-paks', $SourcePaks, '--retoc', $RetocPath, '--repak', $RepakPath, '--xdelta', $XdeltaPath)
if ($ReleaseArchive) { $prepare += @('--release-archive', $ReleaseArchive) }
& python -X utf8 (Join-Path $PSScriptRoot 'prepare_build_inputs.py') @prepare
if ($LASTEXITCODE -ne 0) { throw 'Build input restoration failed' }
$builder = if ($inputs.game_number -eq 1) { 'build_patch.ps1' } else { 'build_patch2.ps1' }
& (Join-Path $PSScriptRoot $builder) -SourcePaks $SourcePaks -RetocPath $RetocPath -RepakPath $RepakPath
& python -X utf8 (Join-Path $PSScriptRoot 'verify_rebuild.py') --retoc $RetocPath --repak $RepakPath
if ($LASTEXITCODE -ne 0) { throw 'Rebuilt release payload verification failed' }
