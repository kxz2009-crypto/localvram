param(
  [string]$OutputDir = "docs/seo-ops",
  [switch]$Force
)

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$targetDir = Join-Path $repoRoot $OutputDir
New-Item -ItemType Directory -Path $targetDir -Force | Out-Null

$dailyCsv = @'
check_date,owner,step_id,check_item,status,notes,next_action,due_date
2026-02-26,ops,A1,Confirm date and exposure pool version,TODO,,,
2026-02-26,ops,A2,Pick 8 URLs (5 latest + 2 older + 1 fallback),TODO,,,
2026-02-26,ops,A3,Put qwen3.5:35b page at slot 1,TODO,,,
2026-02-26,seo,B1,Each page has unique conclusion block,TODO,,,
2026-02-26,seo,B2,Each page has measured/estimated plus timestamp,TODO,,,
2026-02-26,ops,C1,Publish 8 URLs in daily updates,TODO,,,
2026-02-26,ops,D1,Indexing API pushes <= 2 today,TODO,,,
2026-02-26,ops,E1,Record discovered/crawled/indexed for yesterday URLs,TODO,,,
'@

$weeklyCsv = @'
week_start,owner,step_id,check_item,status,metric_value,target,notes,next_action,due_date
2026-02-24,seo,F1,Weekly index rate,TODO,,>=70%,,,
2026-02-24,seo,F2,Latest-model index latency days,TODO,,<=5,,,
2026-02-24,seo,F3,Older-model index latency days,TODO,,<=14,,,
2026-02-24,seo,F4,Tool-page CTR,TODO,,>=4%,,,
2026-02-24,seo,F5,Discovered-not-indexed ratio,TODO,,<25%,,,
2026-02-24,ops,G1,Red alerts assigned with owners and due dates,TODO,,,,
2026-02-24,ops,H1,Next 14-day exposure pool updated,TODO,,,,
'@

$exposureCsv = @'
date,slot,priority_bucket,page_url,page_type,model_tag,is_newest,is_older_than_30d,score,status_24h,status_72h,replace_if_no_progress,notes
2026-02-26,1,latest,https://localvram.com/en/models/qwen35-35b-q4/,model,qwen3.5:35b,1,0,4,planned,,,no,fixed first slot
2026-02-26,2,latest,https://localvram.com/en/models/qwen35-122b-q4/,model,qwen3.5:122b,1,0,4,planned,,,yes,
2026-02-26,3,latest,https://localvram.com/en/models/ministral-3-14b-q4/,model,ministral-3:14b,1,0,4,planned,,,yes,
2026-02-26,4,latest,https://localvram.com/en/models/qwen3-vl-32b-q4/,model,qwen3-vl:32b,1,0,4,planned,,,yes,
2026-02-26,5,latest,https://localvram.com/en/models/qwen3-vl-30b-q4/,model,qwen3-vl:30b,1,0,4,planned,,,yes,
2026-02-26,6,older_than_30d,https://localvram.com/en/models/qwen2.5-14b-q4/,model,qwen2.5:14b,0,1,4,planned,,,yes,
2026-02-26,7,older_than_30d,https://localvram.com/en/models/qwen3-8b-q4/,model,qwen3:8b,0,1,4,planned,,,yes,
2026-02-26,8,fallback,https://localvram.com/en/tools/vram-calculator/,tool,,0,0,5,planned,,,no,fallback high-value page
'@

$localeKpiCsv = @'
date,domain,locale,owner,indexed_urls,discovered_urls,index_rate_pct,impressions,clicks,ctr_pct,avg_position,notes,next_action
2026-02-27,localvram.com,en,seo-en,0,0,0,0,0,0,0,baseline row,fill from Search Console
2026-02-27,localvram.com,es,seo-es,0,0,0,0,0,0,0,baseline row,build locale keyword seed list
2026-02-27,localvram.com,pt,seo-pt,0,0,0,0,0,0,0,baseline row,build locale keyword seed list
2026-02-27,localvram.com,fr,seo-fr,0,0,0,0,0,0,0,baseline row,build locale keyword seed list
2026-02-27,localvram.com,de,seo-de,0,0,0,0,0,0,0,baseline row,build locale keyword seed list
2026-02-27,localvram.com,ru,seo-ru,0,0,0,0,0,0,0,baseline row,build locale keyword seed list
2026-02-27,localvram.com,ja,seo-ja,0,0,0,0,0,0,0,baseline row,build locale keyword seed list
2026-02-27,localvram.com,ko,seo-ko,0,0,0,0,0,0,0,baseline row,build locale keyword seed list
2026-02-27,localvram.com,ar,seo-ar,0,0,0,0,0,0,0,baseline row,build locale keyword seed list
2026-02-27,localvram.com,hi,seo-hi,0,0,0,0,0,0,0,baseline row,build locale keyword seed list
2026-02-27,localvram.com,id,seo-id,0,0,0,0,0,0,0,baseline row,build locale keyword seed list
2026-02-27,localvram.cn,zh-CN,seo-zh,0,0,0,0,0,0,0,baseline row,fill from Baidu tools
'@

$localeContentPlanCsv = @'
week_start,domain,locale,owner,target_urls,new_pages,refresh_pages,priority_topic_cluster,status,notes
2026-02-23,localvram.com,en,content-en,8,3,5,model fit + vram planning,active,existing production lane
2026-02-23,localvram.com,es,content-es,3,2,1,local llm cost + gpu choice,planned,launch locale briefs
2026-02-23,localvram.com,pt,content-pt,3,2,1,local llm cost + gpu choice,planned,launch locale briefs
2026-02-23,localvram.com,fr,content-fr,3,2,1,ollama setup + hardware tiers,planned,launch locale briefs
2026-02-23,localvram.com,de,content-de,3,2,1,benchmark stability + thermals,planned,launch locale briefs
2026-02-23,localvram.com,ru,content-ru,3,2,1,local deployment + gpu sizing,planned,launch locale briefs
2026-02-23,localvram.com,ja,content-ja,3,2,1,local inference speed + memory,planned,launch locale briefs
2026-02-23,localvram.com,ko,content-ko,3,2,1,llm setup + benchmark comparisons,planned,launch locale briefs
2026-02-23,localvram.com,ar,content-ar,3,2,1,cloud vs local decision pages,planned,launch locale briefs
2026-02-23,localvram.com,hi,content-hi,3,2,1,beginner setup + hardware guides,planned,launch locale briefs
2026-02-23,localvram.com,id,content-id,3,2,1,budget gpu + practical deployment,planned,launch locale briefs
2026-02-23,localvram.cn,zh-CN,content-zh,8,4,4,model picks + deployment guides,active,cn independent operation
'@

$files = @(
  @{ Name = "daily-checklist.csv"; Content = $dailyCsv },
  @{ Name = "weekly-checklist.csv"; Content = $weeklyCsv },
  @{ Name = "exposure-pool.csv"; Content = $exposureCsv },
  @{ Name = "locale-kpi-tracker.csv"; Content = $localeKpiCsv },
  @{ Name = "locale-content-plan.csv"; Content = $localeContentPlanCsv }
)

foreach ($file in $files) {
  $path = Join-Path $targetDir $file.Name
  if ((Test-Path $path) -and -not $Force) {
    Write-Host "skip (exists): $path"
    continue
  }
  Set-Content -Path $path -Value $file.Content -Encoding UTF8
  Write-Host "written: $path"
}

Write-Host "done: $targetDir"
