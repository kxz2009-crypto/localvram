param(
  [string]$ComDomain = "https://localvram.com",
  [string]$CnDomain = "https://localvram.cn",
  [string[]]$ExpectedHreflangLocales = @()
)

$ErrorActionPreference = "Stop"

function Get-HeadMeta {
  param([string]$Url)
  $raw = curl.exe -s -I $Url
  $statusLine = ($raw | Select-String -Pattern '^HTTP/' | Select-Object -Last 1).Line
  $locationLine = ($raw | Select-String -Pattern '^Location:' | Select-Object -First 1).Line
  $statusCode = ""
  if ($statusLine -match '^HTTP/\S+\s+(\d{3})') {
    $statusCode = $Matches[1]
  }
  $location = ""
  if ($locationLine) {
    $location = ($locationLine -replace '^Location:\s*', '').Trim()
  }
  return [pscustomobject]@{
    url = $Url
    status = $statusCode
    location = $location
    status_line = $statusLine
  }
}

function Normalize-AbsoluteLocation {
  param(
    [string]$BaseDomain,
    [string]$Location
  )
  if (-not $Location) {
    return ""
  }
  if ($Location.StartsWith("http://") -or $Location.StartsWith("https://")) {
    return $Location
  }
  if ($Location.StartsWith("/")) {
    return "$BaseDomain$Location"
  }
  return "$BaseDomain/$Location"
}

$locales = @("en", "es", "pt", "fr", "de", "ru", "ja", "ko", "ar", "hi", "id")
$results = @()

foreach ($locale in $locales) {
  $url = "$ComDomain/$locale/"
  $head = Get-HeadMeta -Url $url
  $ok = $head.status -eq "200"
  $results += [pscustomobject]@{
    check = "/$locale/"
    status = $head.status
    location = $head.location
    ok = if ($ok) { "OK" } else { "FAIL" }
  }
}

$zhChecks = @(
  @{ from = "/zh/"; to = "$CnDomain/zh/" },
  @{ from = "/zh/guides/best-coding-models/?ref=qa"; to = "$CnDomain/zh/guides/best-coding-models/?ref=qa" }
)

foreach ($row in $zhChecks) {
  $url = "$ComDomain$($row.from)"
  $head = Get-HeadMeta -Url $url
  $actual = Normalize-AbsoluteLocation -BaseDomain $ComDomain -Location $head.location
  $ok = ($head.status -eq "301") -and ($actual -eq $row.to)
  $results += [pscustomobject]@{
    check = $row.from
    status = $head.status
    location = $actual
    ok = if ($ok) { "OK" } else { "FAIL" }
  }
}

$enHtml = curl.exe -s "$ComDomain/en/"
$rolloutConfigPath = Join-Path $PSScriptRoot "..\src\data\i18n-rollout.json"
if ($ExpectedHreflangLocales.Count -eq 0 -and (Test-Path $rolloutConfigPath)) {
  $rawConfig = Get-Content $rolloutConfigPath -Raw | ConvertFrom-Json
  if ($rawConfig.hreflang_rollout_locales) {
    $ExpectedHreflangLocales = @($rawConfig.hreflang_rollout_locales)
  }
}
if ($ExpectedHreflangLocales.Count -eq 0) {
  $ExpectedHreflangLocales = @("en", "es", "pt", "ja")
}

$expectedSet = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
foreach ($item in $ExpectedHreflangLocales) {
  if ($item) {
    [void]$expectedSet.Add($item.Trim())
  }
}
[void]$expectedSet.Add("en")

foreach ($tag in $locales) {
  $pattern = "hrefLang=""$tag"""
  $present = $enHtml -match [regex]::Escape($pattern)
  $shouldPresent = $expectedSet.Contains($tag)
  $ok = ($present -and $shouldPresent) -or ((-not $present) -and (-not $shouldPresent))
  $results += [pscustomobject]@{
    check = "hreflang:$tag"
    status = if ($present) { "present" } else { "missing" }
    location = ""
    ok = if ($ok) { "OK" } else { "FAIL" }
  }
}

$xDefaultPresent = $enHtml -match [regex]::Escape('hrefLang="x-default"')
$results += [pscustomobject]@{
  check = "hreflang:x-default"
  status = if ($xDefaultPresent) { "present" } else { "missing" }
  location = ""
  ok = if ($xDefaultPresent) { "OK" } else { "FAIL" }
}

$zhHreflangPresent = $enHtml -match "hrefLang=""zh-CN"""
$results += [pscustomobject]@{
  check = "hreflang:zh-CN"
  status = if ($zhHreflangPresent) { "present" } else { "absent" }
  location = ""
  ok = if (-not $zhHreflangPresent) { "OK" } else { "FAIL" }
}

Write-Host "i18n production verification"
Write-Host "com=$ComDomain cn=$CnDomain"
Write-Host ""
$results | Format-Table -AutoSize

$failed = @($results | Where-Object { $_.ok -ne "OK" })
if ($failed.Count -gt 0) {
  Write-Host ""
  Write-Host "FAILED checks:" -ForegroundColor Red
  $failed | Format-Table -AutoSize
  exit 1
}

Write-Host ""
Write-Host "All checks passed." -ForegroundColor Green
exit 0
