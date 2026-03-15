param(
  [string]$ComDomain = "https://localvram.com",
  [string]$CnDomain = "https://localvram.cn",
  [string[]]$ExpectedHreflangLocales = @(),
  [ValidateSet("absent", "present", "skip")]
  [string]$ZhHreflangExpectation = "present",
  [switch]$SkipContentChecks
)

$ErrorActionPreference = "Stop"

function Get-CurlExecutable {
  $candidates = @("curl.exe", "curl")
  foreach ($name in $candidates) {
    $cmd = Get-Command $name -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($cmd -and $cmd.Source) {
      return $cmd.Source
    }
  }
  return $null
}

$script:CurlExecutable = Get-CurlExecutable

function Get-HeadMeta {
  param([string]$Url)
  $raw = @()
  if ($script:CurlExecutable) {
    try {
      $raw = & $script:CurlExecutable -s -I $Url 2>$null
    } catch {
      $raw = @()
    }
  }
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
  if ([string]::IsNullOrWhiteSpace($statusCode)) {
    try {
      $resp = Invoke-WebRequest -Uri $Url -Method Head -MaximumRedirection 0 -ErrorAction Stop
      $statusCode = [string]$resp.StatusCode
      $statusLine = "HTTP/$($resp.BaseResponse.ProtocolVersion) $statusCode"
      $location = [string]$resp.Headers["Location"]
    } catch {
      $response = $_.Exception.Response
      if ($response) {
        try {
          $statusCode = [string][int]$response.StatusCode
          $statusLine = "HTTP/$($response.ProtocolVersion) $statusCode"
          $location = [string]$response.Headers["Location"]
        } catch {
          # keep empty values if response parsing fails
        }
      }
    }
  }
  return [pscustomobject]@{
    url = $Url
    status = $statusCode
    location = $location
    status_line = $statusLine
  }
}

function Get-Body {
  param([string]$Url)
  $body = ""
  if ($script:CurlExecutable) {
    try {
      $body = (& $script:CurlExecutable -s $Url 2>$null)
    } catch {
      $body = ""
    }
  }
  if (-not [string]::IsNullOrWhiteSpace([string]$body)) {
    return [string]$body
  }
  try {
    $resp = Invoke-WebRequest -Uri $Url -Method Get -ErrorAction Stop
    return [string]$resp.Content
  } catch {
    return ""
  }
}

function Get-HreflangHref {
  param(
    [string]$Html,
    [string]$HrefLang
  )
  if ([string]::IsNullOrWhiteSpace($Html) -or [string]::IsNullOrWhiteSpace($HrefLang)) {
    return ""
  }
  $escapedLang = [regex]::Escape($HrefLang)
  $pattern = "<link\b(?=[^>]*rel=[""']alternate[""'])(?=[^>]*hrefLang=[""']$escapedLang[""'])[^>]*href=[""'](?<href>[^""'>]+)[""']"
  $match = [regex]::Match(
    $Html,
    $pattern,
    [System.Text.RegularExpressions.RegexOptions]::IgnoreCase
  )
  if ($match.Success) {
    return $match.Groups["href"].Value.Trim()
  }
  return ""
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

function Is-RedirectStatus {
  param([string]$StatusCode)
  return @("301", "302", "307", "308") -contains ([string]$StatusCode).Trim()
}

$locales = @("en", "es", "pt", "fr", "de", "ru", "ja", "ko", "ar", "hi", "id")
$results = @()

$rootHead = Get-HeadMeta -Url "$ComDomain/"
$rootLocation = Normalize-AbsoluteLocation -BaseDomain $ComDomain -Location $rootHead.location
$rootOk = ($rootHead.status -eq "301") -and ($rootLocation -eq "$ComDomain/en/")
$results += [pscustomobject]@{
  check = "/"
  status = $rootHead.status
  location = $rootLocation
  ok = if ($rootOk) { "OK" } else { "FAIL" }
}

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
  @{ from = "/zh"; to = "$CnDomain/" },
  @{ from = "/zh/"; to = "$CnDomain/" },
  @{ from = "/zh/tools/vram-calculator/"; to = "$CnDomain/tools/vram-calculator/" },
  @{ from = "/zh/guides/best-coding-models/?ref=qa"; to = "$CnDomain/guides/best-coding-models/?ref=qa" }
)

foreach ($row in $zhChecks) {
  $url = "$ComDomain$($row.from)"
  $head = Get-HeadMeta -Url $url
  $actual = Normalize-AbsoluteLocation -BaseDomain $ComDomain -Location $head.location
  $targetHead = if ($actual) { Get-HeadMeta -Url $actual } else { [pscustomobject]@{ status = ""; location = "" } }
  $singleHop = -not (Is-RedirectStatus -StatusCode $targetHead.status)
  $ok = ($head.status -eq "301") -and ($actual -eq $row.to) -and $singleHop
  $results += [pscustomobject]@{
    check = $row.from
    status = "$($head.status)->$($targetHead.status)"
    location = $actual
    ok = if ($ok) { "OK" } else { "FAIL" }
  }
}

$contentChecksEnabled = -not $SkipContentChecks
$enHtml = if ($contentChecksEnabled) { Get-Body -Url "$ComDomain/en/" } else { "" }
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

if ($contentChecksEnabled) {
  foreach ($tag in $locales) {
    $href = Get-HreflangHref -Html $enHtml -HrefLang $tag
    $present = -not [string]::IsNullOrWhiteSpace($href)
    $shouldPresent = $expectedSet.Contains($tag)
    $ok = ($present -and $shouldPresent) -or ((-not $present) -and (-not $shouldPresent))
    $results += [pscustomobject]@{
      check = "hreflang:$tag"
      status = if ($present) { "present" } else { "missing" }
      location = $href
      ok = if ($ok) { "OK" } else { "FAIL" }
    }
  }

  $xDefaultHref = Get-HreflangHref -Html $enHtml -HrefLang "x-default"
  $xDefaultPresent = -not [string]::IsNullOrWhiteSpace($xDefaultHref)
  $results += [pscustomobject]@{
    check = "hreflang:x-default"
    status = if ($xDefaultPresent) { "present" } else { "missing" }
    location = $xDefaultHref
    ok = if ($xDefaultPresent) { "OK" } else { "FAIL" }
  }

  $zhHreflangHref = Get-HreflangHref -Html $enHtml -HrefLang "zh-CN"
  $zhHreflangPresent = -not [string]::IsNullOrWhiteSpace($zhHreflangHref)
  $zhExpect = $ZhHreflangExpectation.Trim().ToLowerInvariant()
  $zhHreflangOk = $true
  if ($zhExpect -eq "present") {
    $zhHreflangOk = $zhHreflangPresent -and $zhHreflangHref.StartsWith("$CnDomain/")
  } elseif ($zhExpect -eq "absent") {
    $zhHreflangOk = -not $zhHreflangPresent
  }
  $results += [pscustomobject]@{
    check = "hreflang:zh-CN"
    status = if ($zhHreflangPresent) { "present" } else { "absent" }
    location = "expect=$zhExpect href=$zhHreflangHref"
    ok = if ($zhHreflangOk) { "OK" } else { "FAIL" }
  }
} else {
  $results += [pscustomobject]@{
    check = "hreflang:content-checks"
    status = "skipped"
    location = ""
    ok = "OK"
  }
}

Write-Host "i18n production verification"
Write-Host "com=$ComDomain cn=$CnDomain"
Write-Host "content_checks=$contentChecksEnabled"
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
