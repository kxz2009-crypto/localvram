param(
  [string]$CnDomain = "https://localvram.cn",
  [string]$ExpectedSitemapUrl = "https://localvram.cn/sitemap-cn.xml",
  [string[]]$KeyPaths = @("/", "/tools/vram-calculator/", "/guides/best-coding-models/"),
  [switch]$SkipLegacyZhRedirectChecks,
  [switch]$SkipContentChecks,
  [string]$ComDomain = "https://localvram.com",
  [string]$RequiredIcpNumber = $(if ([string]::IsNullOrWhiteSpace($env:CN_ICP_NUMBER)) { "京ICP备2026009936号" } else { $env:CN_ICP_NUMBER }),
  [string]$RequiredPublicSecurityRecord = $(if ([string]::IsNullOrWhiteSpace($env:CN_PUBLIC_SECURITY_RECORD)) { "公安备案办理中" } else { $env:CN_PUBLIC_SECURITY_RECORD }),
  [ValidateSet("pending", "active")]
  [string]$RequiredPublicSecurityStatus = $(if ([string]::IsNullOrWhiteSpace($env:CN_PUBLIC_SECURITY_STATUS)) { "pending" } else { $env:CN_PUBLIC_SECURITY_STATUS.ToLowerInvariant() })
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

function Normalize-Path {
  param([string]$Path)
  $cleaned = [string]$Path
  if ([string]::IsNullOrWhiteSpace($cleaned)) {
    return "/"
  }
  if (-not $cleaned.StartsWith("/")) {
    $cleaned = "/$cleaned"
  }
  if ($cleaned -eq "/") {
    return "/"
  }
  if (-not $cleaned.EndsWith("/")) {
    $cleaned = "$cleaned/"
  }
  return $cleaned
}

function Get-CanonicalHref {
  param([string]$Html)
  $match = [regex]::Match(
    $Html,
    '<link\b[^>]*rel=["'']canonical["''][^>]*href=["''](?<href>[^"''>]+)["'']',
    [System.Text.RegularExpressions.RegexOptions]::IgnoreCase
  )
  if ($match.Success) {
    return $match.Groups["href"].Value.Trim()
  }
  return ""
}

function Get-AlternateHref {
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

function Is-RedirectStatus {
  param([string]$StatusCode)
  return @("301", "302", "307", "308") -contains ([string]$StatusCode).Trim()
}

$results = @()
$contentChecksEnabled = -not $SkipContentChecks

foreach ($path in $KeyPaths) {
  $normalizedPath = Normalize-Path -Path $path
  $url = "$CnDomain$normalizedPath"
  $head = Get-HeadMeta -Url $url

  $canonicalHref = ""
  $canonicalHost = ""
  $canonicalPath = ""
  $canonicalOk = $false
  $alternateZhCn = ""
  $alternateEn = ""
  $alternateDefault = ""
  $alternateZhOk = $false
  $alternateEnOk = $false
  $alternateDefaultOk = $false
  $icpOk = $true
  $publicSecurityOk = $true

  if (($head.status -eq "200") -and $contentChecksEnabled) {
    $html = Get-Body -Url $url
    if ($null -eq $html) {
      $html = ""
    }
    $canonicalHref = Get-CanonicalHref -Html $html
    $alternateZhCn = Get-AlternateHref -Html $html -HrefLang "zh-CN"
    $alternateEn = Get-AlternateHref -Html $html -HrefLang "en"
    $alternateDefault = Get-AlternateHref -Html $html -HrefLang "x-default"
    $expectedZhCn = "$CnDomain$normalizedPath"
    $expectedEn = if ($normalizedPath -eq "/legal/") { "$ComDomain/legal/" } else { "$ComDomain/en$normalizedPath" }
    $alternateZhOk = ($alternateZhCn -eq $expectedZhCn)
    $alternateEnOk = ($alternateEn -eq $expectedEn)
    $alternateDefaultOk = ($alternateDefault -eq $expectedEn)

    if (-not [string]::IsNullOrWhiteSpace($RequiredIcpNumber)) {
      $icpOk = ([string]$html).Contains($RequiredIcpNumber)
    }
    if ($RequiredPublicSecurityStatus -eq "active") {
      $publicSecurityOk = ([string]$html).Contains($RequiredPublicSecurityRecord) -and -not ([string]$html).Contains("公安备案办理中")
    } else {
      $publicSecurityOk = ([string]$html).Contains($RequiredPublicSecurityRecord)
    }
    if ($canonicalHref) {
      try {
        $canonicalUri = [uri]$canonicalHref
        $expectedUri = [uri]("$CnDomain$normalizedPath")
        $canonicalHost = $canonicalUri.Host
        $canonicalPath = Normalize-Path -Path $canonicalUri.AbsolutePath
        $expectedPath = Normalize-Path -Path $expectedUri.AbsolutePath
        $canonicalOk = ($canonicalUri.Scheme -eq $expectedUri.Scheme) -and ($canonicalUri.Host -eq $expectedUri.Host) -and ($canonicalPath -eq $expectedPath)
      } catch {
        $canonicalOk = $false
      }
    }
  }

  $results += [pscustomobject]@{
    check = "cn-page:$normalizedPath"
    status = $head.status
    location = if ($contentChecksEnabled) { if ($canonicalHref) { $canonicalHref } else { "(missing canonical)" } } else { "(content checks skipped)" }
    ok = if ($contentChecksEnabled) { if (($head.status -eq "200") -and $canonicalOk) { "OK" } else { "FAIL" } } else { if ($head.status -eq "200") { "OK" } else { "FAIL" } }
  }

  if ($contentChecksEnabled) {
    $results += [pscustomobject]@{
      check = "cn-hreflang:zh-CN:$normalizedPath"
      status = $head.status
      location = if ($alternateZhCn) { $alternateZhCn } else { "(missing zh-CN alternate)" }
      ok = if (($head.status -eq "200") -and $alternateZhOk) { "OK" } else { "FAIL" }
    }
    $results += [pscustomobject]@{
      check = "cn-hreflang:en:$normalizedPath"
      status = $head.status
      location = if ($alternateEn) { $alternateEn } else { "(missing en alternate)" }
      ok = if (($head.status -eq "200") -and $alternateEnOk) { "OK" } else { "FAIL" }
    }
    $results += [pscustomobject]@{
      check = "cn-hreflang:x-default:$normalizedPath"
      status = $head.status
      location = if ($alternateDefault) { $alternateDefault } else { "(missing x-default alternate)" }
      ok = if (($head.status -eq "200") -and $alternateDefaultOk) { "OK" } else { "FAIL" }
    }
  }

  if ($contentChecksEnabled -and -not [string]::IsNullOrWhiteSpace($RequiredIcpNumber)) {
    $results += [pscustomobject]@{
      check = "cn-footer:icp:$normalizedPath"
      status = $head.status
      location = $RequiredIcpNumber
      ok = if (($head.status -eq "200") -and $icpOk) { "OK" } else { "FAIL" }
    }
  }
  if ($contentChecksEnabled) {
    $results += [pscustomobject]@{
      check = "cn-footer:public-security:$normalizedPath"
      status = $head.status
      location = $RequiredPublicSecurityRecord
      ok = if (($head.status -eq "200") -and $publicSecurityOk) { "OK" } else { "FAIL" }
    }
  }
}

$robotsUrl = "$CnDomain/robots.txt"
$robotsHead = Get-HeadMeta -Url $robotsUrl
$robotsBody = ""
$robotsHasSitemap = $false
if ($robotsHead.status -eq "200") {
  if ($contentChecksEnabled) {
    $robotsBody = Get-Body -Url $robotsUrl
    $robotsHasSitemap = $robotsBody -match [regex]::Escape("Sitemap: $ExpectedSitemapUrl")
  } else {
    $robotsHasSitemap = $true
  }
}
$results += [pscustomobject]@{
  check = "cn-robots:sitemap-line"
  status = $robotsHead.status
  location = "expect=Sitemap: $ExpectedSitemapUrl"
  ok = if (($robotsHead.status -eq "200") -and $robotsHasSitemap) { "OK" } else { "FAIL" }
}

$sitemapHead = Get-HeadMeta -Url $ExpectedSitemapUrl
$sitemapBody = ""
$sitemapXmlOk = $false
if ($sitemapHead.status -eq "200") {
  if ($contentChecksEnabled) {
    $sitemapBody = Get-Body -Url $ExpectedSitemapUrl
    $sitemapXmlOk = ($sitemapBody -match "<urlset") -or ($sitemapBody -match "<sitemapindex")
  } else {
    $sitemapXmlOk = $true
  }
}
$results += [pscustomobject]@{
  check = "cn-sitemap:accessible"
  status = $sitemapHead.status
  location = $ExpectedSitemapUrl
  ok = if (($sitemapHead.status -eq "200") -and $sitemapXmlOk) { "OK" } else { "FAIL" }
}

if (-not $SkipLegacyZhRedirectChecks) {
  $legacyChecks = @(
    @{ from = "/zh"; to = "$CnDomain/" },
    @{ from = "/zh/"; to = "$CnDomain/" },
    @{ from = "/zh/tools/vram-calculator/?ref=qa"; to = "$CnDomain/tools/vram-calculator/?ref=qa" }
  )

  foreach ($row in $legacyChecks) {
    $url = "$CnDomain$($row.from)"
    $head = Get-HeadMeta -Url $url
    $actual = Normalize-AbsoluteLocation -BaseDomain $CnDomain -Location $head.location
    $targetHead = if ($actual) { Get-HeadMeta -Url $actual } else { [pscustomobject]@{ status = ""; location = "" } }
    $singleHop = -not (Is-RedirectStatus -StatusCode $targetHead.status)
    $ok = ($head.status -eq "301") -and ($actual -eq $row.to) -and $singleHop

    $results += [pscustomobject]@{
      check = "cn-legacy:$($row.from)"
      status = "$($head.status)->$($targetHead.status)"
      location = $actual
      ok = if ($ok) { "OK" } else { "FAIL" }
    }
  }
}

$enCompatChecks = @(
  @{ from = "/en"; to = "$CnDomain/" },
  @{ from = "/en/"; to = "$CnDomain/" },
  @{ from = "/en/tools/vram-calculator/?ref=qa"; to = "$CnDomain/tools/vram-calculator/?ref=qa" }
)

foreach ($row in $enCompatChecks) {
  $url = "$CnDomain$($row.from)"
  $head = Get-HeadMeta -Url $url
  $actual = Normalize-AbsoluteLocation -BaseDomain $CnDomain -Location $head.location
  $targetHead = if ($actual) { Get-HeadMeta -Url $actual } else { [pscustomobject]@{ status = ""; location = "" } }
  $singleHop = -not (Is-RedirectStatus -StatusCode $targetHead.status)
  $ok = ($head.status -eq "301") -and ($actual -eq $row.to) -and $singleHop

  $results += [pscustomobject]@{
    check = "cn-en-compat:$($row.from)"
    status = "$($head.status)->$($targetHead.status)"
    location = $actual
    ok = if ($ok) { "OK" } else { "FAIL" }
  }
}

Write-Host "cn domain verification"
Write-Host "cn=$CnDomain"
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
