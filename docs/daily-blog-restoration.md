# Daily blog restoration

Chinese article titles previously used the first Markdown heading of any level. Translations starting with `## 快速结论` therefore shared that section name as their title. Only an explicit H1 can now override source metadata; model-specific historical titles remain distinct. Translation comments are removed before extracting previews.

Homepage and updates pages now render published articles from the content collection, including a substantive excerpt and full-article link. Operational logs remain in a collapsed section on updates pages. Historical posts and URLs are preserved; this does not retrospectively certify their benchmark or recommendation claims.

The daily job still ranks and reviews topics, but invokes publishing with `--min-publish 0`. Empty approved queues no longer produce a forced rotating benchmark article. The publisher default is also zero; an explicitly requested nonzero minimum remains available for manual use. Same-day publishing merges article links rather than overwriting earlier publications. Actual daily publication depends on reviewed substantive topics, not a quota. Old topic sources and previously generated generic drafts still require editorial scrutiny; this repair does not turn a template generator into an autonomous researcher.

A new English/Chinese Qwen3.8 workload-cost guide provides practical, explicitly hypothetical calculations without asserting unmeasured hardware performance.

CN production now follows a successful Daily Content Agent run on main via workflow_run, matching the existing COM refresh path. Automatic CN refresh does not submit Baidu URLs. Manual CN deployment remains available.
