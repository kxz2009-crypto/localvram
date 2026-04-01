# Ollama Upgrade Runbook (WSL)

## Benchmark runner port note

For the `3090-WSL2-V2` self-hosted GitHub Actions runner, keep the WSL-managed Ollama instance on:

- `http://127.0.0.1:11435`

Do not point weekly benchmark or smoke-check workflows at `11434` on that machine. In this environment, `11434` may be occupied by a Windows-side Ollama/localhost forward that is reachable from WSL but does not appear as a local `ollama serve` process, causing workflow preflight to fail with `ollama_instance_unmanaged`.
This runbook is for the failure pattern:

- `ollama run qwen3.5:35b` -> `500 ... unable to load model ... sha256-...`
- `ollama pull qwen3.5:35b` -> `412 ... requires a newer version of Ollama`

## 1) What this means

- `ollama list` showing `qwen3.5:35b` only proves a tag/manifest exists.
- It does **not** prove the model is runnable.
- Your current Ollama binary is too old for this model manifest, and/or local blobs are incomplete/corrupted.

## 2) Stop port conflicts first (Windows + WSL)

In WSL:

```bash
powershell.exe -NoProfile -Command "Get-Process ollama -ErrorAction SilentlyContinue | Stop-Process -Force"
sudo systemctl stop ollama || true
sudo pkill -f "ollama serve" || true
sleep 2
sudo ss -ltnp | grep 11434 || echo "port 11434 is free"
```

## 3) Upgrade Ollama in WSL

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama -v
```

If `pull qwen3.5:35b` still returns `412`, install a newer pre-release from:

- https://github.com/ollama/ollama/releases

Then verify again:

```bash
ollama -v
```

## 4) Start single managed instance (systemd)

```bash
sudo systemctl daemon-reload
sudo systemctl reset-failed ollama
sudo systemctl restart ollama
systemctl status ollama --no-pager -l | head -n 30
curl -s http://127.0.0.1:11434/api/version
```

Expected:

- service is `active (running)`
- endpoint returns a valid version JSON

## 5) Repair and re-pull qwen3.5:35b

```bash
ollama rm qwen3.5:35b || true
ollama pull qwen3.5:35b
ollama run qwen3.5:35b "Reply only: OK"
```

If `unable to load model ... sha256-...` persists, remove only the broken blob and pull again:

```bash
# replace with the exact sha from the error
rm -f /mnt/d/Ollama/blobs/sha256-REPLACE_WITH_SHA
ollama pull qwen3.5:35b
```

## 6) Pipeline re-validation

After model is runnable, run:

1. `Runner Smoke Check`
2. `Weekly Benchmark`
3. `Publish Benchmark Artifact`

Recommended one-shot wrapper:

```powershell
python scripts/run-weekly-publish-pipeline.py `
  --gh-path "C:\Program Files\GitHub CLI\gh.exe" `
  --repo kxz2009-crypto/localvram `
  --retry-weekly-after-smoke true
```

## 7) Confirm qwen3.5 moved from estimated -> measured

After publish succeeds:

```powershell
python scripts/quality-gate.py
rg -n "qwen3\\.5|qwen35" src/data/benchmark-results.json
```

If no qwen3.5 measured row appears, fetch weekly failed logs and check model runtime errors for qwen3.5 specifically.
