param(
  [string]$HostName = "120.53.243.14",
  [string]$UserName = "root",
  [string]$SshKeyPath = "$env:USERPROFILE\.ssh\tinyworld_vps"
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir "..")
Set-Location $repoRoot

$sshExe = "C:\Windows\System32\OpenSSH\ssh.exe"
$scpExe = "C:\Windows\System32\OpenSSH\scp.exe"
if (-not (Test-Path $sshExe)) { throw "ssh.exe not found: $sshExe" }
if (-not (Test-Path $scpExe)) { throw "scp.exe not found: $scpExe" }
if (-not (Test-Path $SshKeyPath)) { throw "SSH private key not found: $SshKeyPath" }

Write-Host "[1/5] Build CN artifact..."
npm.cmd run build:cn

$requiredPaths = @(
  "dist-cn/index.html",
  "dist-cn/tools/index.html",
  "dist-cn/guides/index.html",
  "dist-cn/tools/vram-calculator/index.html",
  "dist-cn/guides/best-coding-models/index.html"
)

Write-Host "[2/5] Validate required artifact files..."
foreach ($path in $requiredPaths) {
  if (-not (Test-Path $path)) {
    throw "Missing artifact file: $path"
  }
}

Write-Host "[3/5] Package and upload dist-cn..."
tar -czf dist-cn.tar.gz -C . dist-cn
& $scpExe `
  -i $SshKeyPath `
  -o BatchMode=yes `
  -o StrictHostKeyChecking=accept-new `
  .\dist-cn.tar.gz `
  "${UserName}@${HostName}:/root/"
if ($LASTEXITCODE -ne 0) { throw "scp upload failed (exit=$LASTEXITCODE)" }

$remoteScript = @'
set -euo pipefail

TS=$(date +%Y%m%d%H%M%S)
REL=/var/www/localvram-cn/releases/$TS

mkdir -p "$REL"
tar -xzf /root/dist-cn.tar.gz -C "$REL" --strip-components=1

# Safety overlay for entry index pages
[ -f "$REL/zh/tools/index.html" ] && mkdir -p "$REL/tools" && cp -f "$REL/zh/tools/index.html" "$REL/tools/index.html"
[ -f "$REL/zh/guides/index.html" ] && mkdir -p "$REL/guides" && cp -f "$REL/zh/guides/index.html" "$REL/guides/index.html"

ln -sfn "$REL" /var/www/localvram-cn/current
chown -R nginx:nginx /var/www/localvram-cn
nginx -t && systemctl reload nginx

echo "==== verify home ===="
curl -sL --compressed https://localvram.cn/ | grep -E "60 秒选对适合你显卡的本地模型|开始显存计算|数据状态"

echo "==== verify tools ===="
curl -sL --compressed https://localvram.cn/tools/ | grep -E "中文工具中心|开始显存计算|打开量化盲测|ROI 成本计算器"

echo "==== verify guides ===="
curl -sL --compressed https://localvram.cn/guides/ | grep -E "中文指南中心|编程模型推荐|RAG 模型推荐|成本对比指南"

echo "==== verify lang ===="
curl -sL --compressed https://localvram.cn/guides/ | grep -o '<html lang="[^"]*"' | head -n1
'@

$tmpRemote = Join-Path $env:TEMP "deploy-cn-remote.sh"
Set-Content -Path $tmpRemote -Value $remoteScript -Encoding UTF8

Write-Host "[4/5] Deploy on remote and verify..."
Get-Content $tmpRemote -Raw | & $sshExe `
  -i $SshKeyPath `
  -o BatchMode=yes `
  -o StrictHostKeyChecking=accept-new `
  "$UserName@$HostName" `
  "bash -s"
if ($LASTEXITCODE -ne 0) { throw "remote deploy failed (exit=$LASTEXITCODE)" }

Remove-Item $tmpRemote -ErrorAction SilentlyContinue

Write-Host "[5/5] Done."
