param(
  [Parameter(Mandatory = $true)]
  [ValidateSet("Archive", "Restore")]
  [string]$Mode,

  [Parameter(Mandatory = $true)]
  [string[]]$Models,

  [string]$HotRoot = "D:\Ollama",
  [string]$ColdRoot = "E:\Ollama-cold",

  [switch]$Apply,
  [switch]$DeleteSource,
  [switch]$Force
)

<# 
Examples:

Dry-run archive candidates from D:\Ollama to E:\Ollama-cold:
  powershell -ExecutionPolicy Bypass -File scripts\ollama-cold-storage.ps1 `
    -Mode Archive `
    -Models 'qwen3.5:122b','antangelmed/ling-flash-2.0:100b','llama3.3:70b-instruct-q4_k_m' `
    -HotRoot 'D:\Ollama' `
    -ColdRoot 'E:\Ollama-cold'

Copy to cold storage, keep the hot source:
  powershell -ExecutionPolicy Bypass -File scripts\ollama-cold-storage.ps1 `
    -Mode Archive `
    -Models 'qwen3.5:122b','antangelmed/ling-flash-2.0:100b','llama3.3:70b-instruct-q4_k_m' `
    -Apply

After confirming Ollama still works for the models you kept, delete archived source files:
  powershell -ExecutionPolicy Bypass -File scripts\ollama-cold-storage.ps1 `
    -Mode Archive `
    -Models 'qwen3.5:122b','antangelmed/ling-flash-2.0:100b','llama3.3:70b-instruct-q4_k_m' `
    -Apply `
    -DeleteSource

Restore a model back to D:\Ollama:
  powershell -ExecutionPolicy Bypass -File scripts\ollama-cold-storage.ps1 `
    -Mode Restore `
    -Models 'qwen3.5:122b' `
    -Apply
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Convert-DigestToBlobName {
  param([Parameter(Mandatory = $true)][string]$Digest)
  return $Digest.Trim() -replace ":", "-"
}

function Split-ModelSpec {
  param([Parameter(Mandatory = $true)][string]$Model)

  $tagIndex = $Model.LastIndexOf(":")
  if ($tagIndex -lt 1 -or $tagIndex -eq ($Model.Length - 1)) {
    throw "Model must include an explicit tag, for example qwen3.5:122b or llama4:latest. Got: $Model"
  }

  $name = $Model.Substring(0, $tagIndex)
  $tag = $Model.Substring($tagIndex + 1)
  $parts = $name -split "/"

  if ($parts.Count -eq 1) {
    return @{
      Registry = "registry.ollama.ai"
      Namespace = "library"
      Name = $parts[0]
      Tag = $tag
    }
  }

  if ($parts.Count -eq 2) {
    return @{
      Registry = "registry.ollama.ai"
      Namespace = $parts[0]
      Name = $parts[1]
      Tag = $tag
    }
  }

  if ($parts.Count -eq 3) {
    return @{
      Registry = $parts[0]
      Namespace = $parts[1]
      Name = $parts[2]
      Tag = $tag
    }
  }

  throw "Unsupported model format: $Model"
}

function Get-ManifestPath {
  param(
    [Parameter(Mandatory = $true)][string]$Root,
    [Parameter(Mandatory = $true)][hashtable]$Spec
  )

  return Join-Path $Root ("manifests\{0}\{1}\{2}\{3}" -f $Spec.Registry, $Spec.Namespace, $Spec.Name, $Spec.Tag)
}

function Get-BlobPath {
  param(
    [Parameter(Mandatory = $true)][string]$Root,
    [Parameter(Mandatory = $true)][string]$Digest
  )

  return Join-Path $Root ("blobs\{0}" -f (Convert-DigestToBlobName $Digest))
}

function Get-ManifestDigests {
  param([Parameter(Mandatory = $true)][string]$ManifestPath)

  $manifest = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json
  $digests = New-Object System.Collections.Generic.List[string]

  if ($manifest.config -and $manifest.config.digest) {
    $digests.Add([string]$manifest.config.digest)
  }

  if ($manifest.layers) {
    foreach ($layer in $manifest.layers) {
      if ($layer.digest) {
        $digests.Add([string]$layer.digest)
      }
    }
  }

  return $digests | Sort-Object -Unique
}

function Copy-FileChecked {
  param(
    [Parameter(Mandatory = $true)][string]$Source,
    [Parameter(Mandatory = $true)][string]$Destination,
    [Parameter(Mandatory = $true)][bool]$ApplyChanges,
    [Parameter(Mandatory = $true)][bool]$Overwrite
  )

  if (!(Test-Path -LiteralPath $Source -PathType Leaf)) {
    throw "Missing source file: $Source"
  }

  $sourceInfo = Get-Item -LiteralPath $Source
  $exists = Test-Path -LiteralPath $Destination -PathType Leaf
  if ($exists -and !$Overwrite) {
    $destInfo = Get-Item -LiteralPath $Destination
    if ($destInfo.Length -eq $sourceInfo.Length) {
      return @{
        Path = $Destination
        Bytes = $sourceInfo.Length
        Action = "skip-existing"
      }
    }
    throw "Destination exists with different size. Use -Force to overwrite: $Destination"
  }

  if ($ApplyChanges) {
    $parent = Split-Path -Parent $Destination
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    Copy-Item -LiteralPath $Source -Destination $Destination -Force:$Overwrite

    $destInfoAfter = Get-Item -LiteralPath $Destination
    if ($destInfoAfter.Length -ne $sourceInfo.Length) {
      throw "Copy verification failed for $Source -> $Destination"
    }
  }

  return @{
    Path = $Destination
    Bytes = $sourceInfo.Length
    Action = $(if ($ApplyChanges) { "copied" } else { "would-copy" })
  }
}

function Remove-FileChecked {
  param(
    [Parameter(Mandatory = $true)][string]$Path,
    [Parameter(Mandatory = $true)][bool]$ApplyChanges
  )

  if (!(Test-Path -LiteralPath $Path -PathType Leaf)) {
    return "missing"
  }

  if ($ApplyChanges) {
    Remove-Item -LiteralPath $Path -Force
    return "deleted"
  }

  return "would-delete"
}

function Format-Bytes {
  param([Parameter(Mandatory = $true)][Int64]$Bytes)

  if ($Bytes -ge 1TB) {
    return "{0:N2} TB" -f ($Bytes / 1TB)
  }
  if ($Bytes -ge 1GB) {
    return "{0:N2} GB" -f ($Bytes / 1GB)
  }
  if ($Bytes -ge 1MB) {
    return "{0:N2} MB" -f ($Bytes / 1MB)
  }
  return "$Bytes B"
}

$sourceRoot = if ($Mode -eq "Archive") { $HotRoot } else { $ColdRoot }
$targetRoot = if ($Mode -eq "Archive") { $ColdRoot } else { $HotRoot }

if ($DeleteSource -and !$Apply) {
  throw "-DeleteSource requires -Apply."
}

$Models = @(
  foreach ($model in $Models) {
    foreach ($part in ($model -split ",")) {
      $trimmed = $part.Trim()
      if ($trimmed) {
        $trimmed
      }
    }
  }
)

$totalBytes = [Int64]0
$copiedFiles = 0
$deletedFiles = 0

foreach ($model in $Models) {
  $spec = Split-ModelSpec $model
  $sourceManifest = Get-ManifestPath -Root $sourceRoot -Spec $spec
  $targetManifest = Get-ManifestPath -Root $targetRoot -Spec $spec

  Write-Host ""
  Write-Host "== $Mode $model =="
  Write-Host "source manifest: $sourceManifest"
  Write-Host "target manifest: $targetManifest"

  if (!(Test-Path -LiteralPath $sourceManifest -PathType Leaf)) {
    Write-Warning "Manifest not found, skipping: $sourceManifest"
    continue
  }

  $digests = @(Get-ManifestDigests -ManifestPath $sourceManifest)
  $files = New-Object System.Collections.Generic.List[object]
  $files.Add(@{
      Source = $sourceManifest
      Destination = $targetManifest
      Kind = "manifest"
    })

  foreach ($digest in $digests) {
    $files.Add(@{
        Source = Get-BlobPath -Root $sourceRoot -Digest $digest
        Destination = Get-BlobPath -Root $targetRoot -Digest $digest
        Kind = "blob"
      })
  }

  $modelBytes = [Int64]0
  foreach ($file in $files) {
    $result = Copy-FileChecked -Source $file.Source -Destination $file.Destination -ApplyChanges:$Apply.IsPresent -Overwrite:$Force.IsPresent
    $modelBytes += [Int64]$result.Bytes
    if ($result.Action -eq "copied" -or $result.Action -eq "would-copy") {
      $copiedFiles++
    }
  }

  $totalBytes += $modelBytes
  Write-Host ("files: {0}; referenced size: {1}" -f $files.Count, (Format-Bytes $modelBytes))

  if ($DeleteSource) {
    Write-Host "deleting source files after verified copy..."
    foreach ($file in $files) {
      $deleteAction = Remove-FileChecked -Path $file.Source -ApplyChanges:$Apply.IsPresent
      if ($deleteAction -eq "deleted" -or $deleteAction -eq "would-delete") {
        $deletedFiles++
      }
    }
  }
}

Write-Host ""
Write-Host "Summary"
Write-Host ("mode: {0}" -f $Mode)
Write-Host ("apply: {0}" -f $Apply.IsPresent)
Write-Host ("delete source: {0}" -f $DeleteSource.IsPresent)
Write-Host ("referenced bytes: {0}" -f (Format-Bytes $totalBytes))
Write-Host ("copy actions: {0}" -f $copiedFiles)
Write-Host ("delete actions: {0}" -f $deletedFiles)

if (!$Apply) {
  Write-Host ""
  Write-Host "Dry-run only. Re-run with -Apply to copy files."
}
