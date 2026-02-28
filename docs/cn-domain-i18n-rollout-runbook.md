# CN Domain i18n Rollout Runbook

Goal:

- Global: `localvram.com` (`en/es/pt/fr/de/ru/ja/ko/ar/hi/id` independent locale operations)
- Chinese: `localvram.cn` (`zh-CN` primary for Baidu/WeChat/ByteDance ecosystem)
- Alias only: `zh.localvram.com` -> 301 redirect to `localvram.cn`

## 1) Cloudflare redirect rules (copy/paste)

Use **301 permanent** redirects and keep both path + query.

### Rule A: zh subdomain -> cn root

Condition:

```txt
(http.host eq "zh.localvram.com")
```

Action:

```txt
Dynamic redirect
Status code: 301
URL: concat("https://localvram.cn", http.request.uri.path, if(len(http.request.uri.query) > 0, concat("?", http.request.uri.query), ""))
```

### Rule B (enable only after ICP approval): lock old `/zh/...` path on .com -> `.cn/zh/...`

Condition:

```txt
(http.host eq "localvram.com" and (http.request.uri.path eq "/zh" or starts_with(http.request.uri.path, "/zh/")))
```

Action:

```txt
Dynamic redirect
Status code: 301
URL: if(http.request.uri.path eq "/zh", concat("https://localvram.cn/zh", if(len(http.request.uri.query) > 0, concat("?", http.request.uri.query), "")), concat("https://localvram.cn/zh", substring(http.request.uri.path, 3), if(len(http.request.uri.query) > 0, concat("?", http.request.uri.query), "")))
```

Notes:

- Keep Rule A above Rule B.
- Enable only when `localvram.cn` is live and healthy.
- This rule keeps `/zh/...` path structure on `.cn` and hard-locks Chinese traffic away from `.com`.

### Code fallback (recommended for Pages project-level enforcement)

If dashboard rules are delayed or not applied yet, keep a Pages Function route:

- `functions/zh/[[path]].js`
- Behavior: when host is `localvram.com` or `www.localvram.com`, return `301` to `https://localvram.cn/zh/...` (preserve query)
- For `localvram.cn` host, continue normal request handling (no redirect)
- Safety switch: set Pages environment variable `LV_ZH_CN_CUTOVER=false` (or `0/off/no`) to disable redirect.
- Default behavior with empty flag: redirect enabled (`.com/zh/...` -> `.cn/zh/...`).
- Canonical/hreflang switch: set `PUBLIC_ZH_SITE_ORIGIN=https://localvram.cn` at cutover time.

## 2) Canonical + hreflang policy

Single-language pages should point to their own primary domain:

- English canonical: `https://localvram.com/...`
- Chinese canonical: `https://localvram.cn/...`

Cross-domain alternates:

- `en`: `https://localvram.com/...`
- `zh-CN`: `https://localvram.cn/...`
- `x-default`: `https://localvram.com/`

## 3) Astro template (drop-in pattern)

Use this when rendering pages/layout props:

```ts
const enUrl = `https://localvram.com${enPath}`;
const zhUrl = `https://localvram.cn${zhPath}`;

const canonical = locale === "zh" ? zhUrl : enUrl;
const alternates = [
  { hrefLang: "en", href: enUrl },
  { hrefLang: "zh-CN", href: zhUrl },
  { hrefLang: "x-default", href: "https://localvram.com/" }
];
```

Then in layout:

```astro
<link rel="canonical" href={canonical} />
{alternates.map((item) => (
  <link rel="alternate" hrefLang={item.hrefLang} href={item.href} />
))}
```

## 4) Sitemaps

Keep separate sitemaps:

- `https://localvram.com/sitemap.xml` -> English URLs only
- `https://localvram.cn/sitemap-cn.xml` -> Chinese URLs only

Do not include `zh.localvram.com` URLs in sitemap.

## 5) Verification checklist

After cutover:

1. `curl -I https://zh.localvram.com/` returns `301` to `https://localvram.cn/`
2. `curl -I https://zh.localvram.com/models/qwen35-35b-q4/?x=1` keeps path/query
3. Chinese pages output canonical on `.cn`
4. Chinese pages contain `hreflang=zh-CN` + cross-domain `en`
5. Baidu receives `.cn` sitemap only

## 6) Chinese SEO channels (ops note)

Primary indexing traffic:

- Baidu organic + Baidu push

Discovery/support channels:

- WeChat 搜一搜
- 抖音搜索
- 豆包 / Kimi / DeepSeek / 元宝 (content citation + brand recall)

These channels are content distribution + brand mention oriented, not pure crawler-only SEO.
