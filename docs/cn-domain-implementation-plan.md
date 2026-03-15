# localvram.cn 中文站实施规划（v4）

> 创建日期：2026-03-09  
> 最后更新：2026-03-12  
> 状态：待实施（已吸收架构优化建议）

> 备案状态（2026-03-11）：ICP 已通过（京ICP备2026009936号，审核通过日期 2026-03-09）；公安备案进行中（不阻断代码上线）。

---

## 一、最终决策（本版）

1. `.cn` 采用根路径中文站：`https://localvram.cn/*`，不再保留冗余 `/zh/` 前缀作为主路径。
2. `.com` 继续保留 `/zh*` 入口，但仅做 301 跳转到 `.cn` 根路径同构 URL。
3. 跨域 hreflang 建立双向映射：`.com(en+10)` 与 `.cn(zh-CN)` 互相声明语言替代关系。
4. CN 站采用 Astro 单配置多目标构建（`BUILD_TARGET` + `SITE_URL`），不使用后处理“切包”修补 canonical。
5. Cloudflare 跳转规则必须落在仓库 `public/_redirects`，禁止在 Cloudflare 面板临时配置 Page Rules/Redirect Rules。
6. `.cn` 正式对外前必须完成 ICP 备案并展示备案信息；公安联网备案可并行推进，但需纳入上线后跟踪。

---

## 二、URL 策略（去 `/zh/`）

## 2.1 目标 URL

| 场景 | 旧目标 | 新目标 |
|---|---|---|
| CN 首页 | `https://localvram.cn/zh/` | `https://localvram.cn/` |
| CN 工具页 | `https://localvram.cn/zh/tools/vram-calculator/` | `https://localvram.cn/tools/vram-calculator/` |
| COM 跳转 | `/zh/* -> .cn/zh/*` | `/zh/* -> .cn/*` |

## 2.2 映射规则

1. `https://localvram.com/zh` -> `https://localvram.cn/`
2. `https://localvram.com/zh/` -> `https://localvram.cn/`
3. `https://localvram.com/zh/<path>` -> `https://localvram.cn/<path>`
4. 查询参数必须保留（如 `?ref=qa`）。

---

## 三、SEO 策略（跨域语言集群）

## 3.1 核心原则

1. `.com` 与 `.cn` 部署独立，但在搜索引擎语义上属于同一多语言站点。
2. canonical 始终自指向本域当前页面。
3. hreflang 允许跨域，建立双向映射。

## 3.2 页面级要求

1. `.com` 英文页面增加：
   - `<link rel="alternate" hreflang="zh-CN" href="https://localvram.cn/<mapped-path>" />`
2. `.cn` 中文页面增加：
   - `<link rel="alternate" hreflang="en" href="https://localvram.com/en/<mapped-path>" />`
   - 可选补充：与 `.com` 保持一致的其余语言项（按实施成本决定）。
3. `x-default` 仍指向 `.com` 英文页面。

说明：

- 这会与现有“`.com` 不含 `zh-CN` hreflang”的旧门禁冲突，需要同步更新验证脚本和验收文档。

---

## 四、合规与搜索引擎迁移

## 4.1 备案与展示（上线前阻断）

1. `.cn` 接入腾讯云 CDN 前，需完成工信部 ICP 备案。
2. 公安联网备案可在上线后并行推进，但需记录责任人和完成截止日期。
3. ICP 备案号在 `.cn` Footer 底部展示，并链接工信部备案查询页面。
   - 当前备案号：`京ICP备2026009936号`
   - 审核通过日期：`2026-03-09`
4. 备案号建议通过环境变量注入，避免硬编码多环境漂移。
   - `BUILD_TARGET=cn`（仅 CN 构建显示备案信息）
   - `CN_ICP_NUMBER=京ICP备2026009936号`
   - `CN_ICP_URL=https://beian.miit.gov.cn/`
   - `CN_PUBLIC_SECURITY_STATUS=pending|active`（默认 `pending`）
   - `CN_PUBLIC_SECURITY_RECORD=公安备案办理中`（公安备案通过后替换为正式编号）
   - `CN_PUBLIC_SECURITY_URL=<公安备案官方查询链接>`（可选）
5. 公安备案“占位位”固定保留在 CN Footer，与 ICP 并列展示：
   - `pending` 阶段展示 `公安备案办理中`（无链接也可发布）。
   - `active` 阶段必须替换为正式公安备案号；若仍出现 `公安备案办理中`，视为发布阻断。
   - 切换到 `active` 的同次发布必须同步更新 `CN_PUBLIC_SECURITY_RECORD`（及 `CN_PUBLIC_SECURITY_URL` 如已可用）并重新跑 `scripts/verify-cn-domain.ps1`。

## 4.2 搜索引擎迁移声明（阶段 1 与阶段 2 之间）

1. 在 Google Search Console 执行站点迁移/地址变更相关操作。
2. 在百度搜索资源平台执行站点改版（目录/站点迁移）申报。
3. 提交迁移映射说明：`/zh/* -> https://localvram.cn/*`。
4. 保留 301 长期稳定，不在迁移窗口频繁改规则。

---

## 五、构建方案（Astro 单配置多目标）

## 5.1 为什么不用后处理切包

1. 后处理脚本容易遗漏 hash 静态资源依赖（`_astro/*`）。
2. canonical/og/url/结构化数据 URL 的根源在构建时配置，不是打包后能安全修补的问题。

## 5.2 构建要求

1. 仅使用一个 `astro.config.mjs`，通过环境变量动态切换目标，避免 `.com/.cn` 配置漂移。
2. 推荐配置：

```js
import { defineConfig } from "astro/config";

const isCN = process.env.BUILD_TARGET === "cn";

export default defineConfig({
  site: isCN ? "https://localvram.cn" : (process.env.SITE_URL ?? "https://localvram.com"),
  outDir: isCN ? "dist-cn" : "dist",
  output: "static",
  build: { format: "directory" },
});
```

3. CI 分开构建：
   - `.com`：`SITE_URL=https://localvram.com pnpm build`
   - `.cn`：`pnpm build:cn`（内部统一执行 `BUILD_TARGET=cn` + CN 产物校验）

PowerShell 示例：

```powershell
pnpm build:cn
```

---

## 六、路由落地位置（防复发红线）

## 6.1 必须写入仓库文件

`public/_redirects`（由 Cloudflare Pages 解析）：

```text
/zh https://localvram.cn/ 301
/zh/ https://localvram.cn/ 301
/zh/* https://localvram.cn/:splat 301
/en / 301
/en/ / 301
/en/* /:splat 301
```

## 6.2 明确禁止

1. 不在 Cloudflare 控制台新增临时 Page Rules/Redirect Rules 来处理 `/zh*`。
2. 不允许同一跳转在“仓库规则 + 面板规则 + Nginx”三处同时定义。

---

## 七、阶段顺序（消除裸奔窗口）

## 阶段 0：预置占位页（先于切流）

1. 先在 `.cn` 部署可用占位页（首页 200，不跳回 `.com`）。
2. 最低标准：`/` 返回 200，含 canonical 基础头。
3. 占位页必须添加：`<meta name="robots" content="noindex, nofollow">`，防止空页被收录。

## 阶段 1：切换 `.com/zh*` 跳转

1. 合并 `_redirects` 新规则并发布 `.com`。
2. 验证：`.com/zh*` 一跳到 `.cn/*`。

## 阶段 1.5：提交搜索引擎迁移声明

1. 在 GSC 提交站点迁移/地址变更操作。
2. 在百度搜索资源平台提交站点改版。
3. 验证迁移样本 URL 在平台可抓取并返回 301/200 预期。

## 阶段 2：发布 CN 正式内容

1. 部署 `dist-cn` 正式版本。
2. 完成 canonical/hreflang/sitemap-cn/robots 校验。
3. Footer 展示 ICP 备案信息（`京ICP备2026009936号`，含跳转链接）并人工验收；公安备案状态在运维清单中持续跟踪。
4. 每日新增英文博客必须同步 CN 中文稿：`src/content/blog-i18n/zh/<slug>.md`；可先执行 `npm run i18n:blog-body:auto-fill:zh` 生成机翻草稿，再人工校对。

## 阶段 3：开启跨域 hreflang

1. 发布 `.com` 与 `.cn` 头部 alternates 双向声明。
2. 同步更新验证脚本与门禁断言。

---

## 八、Nginx 生产配置（含 www 443 与安全头）

```nginx
server {
    listen 80;
    server_name localvram.cn www.localvram.cn;
    return 301 https://localvram.cn$request_uri;
}

server {
    listen 443 ssl http2;
    server_name www.localvram.cn;
    return 301 https://localvram.cn$request_uri;
}

server {
    listen 443 ssl http2;
    server_name localvram.cn;

    root /var/www/localvram-cn/current;
    index index.html;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    location ~ ^/baidu_verify_ {
        try_files $uri =404;
    }

    location /_astro/ {
        expires 30d;
        add_header Cache-Control "public, max-age=2592000, immutable";
        try_files $uri =404;
    }

    # 兼容旧链接：/zh/* -> /*
    location = /zh {
        return 301 /$is_args$args;
    }
    location ~ ^/zh/(.*)$ {
        return 301 /$1$is_args$args;
    }

    location / {
        # CN 构建产物已实体化根路径页面，直接按根目录命中
        try_files $uri $uri/ /index.html;
    }
}
```

---

## 九、CI/CD 与验证脚本改造

## 9.1 需新增

1. `.github/workflows/deploy-cn-site.yml`（已落地，2026-03-11）
2. `scripts/verify-cn-domain.ps1`
3. `scripts/check-cn-artifact-integrity.py`（资源白名单/完整性校验）
4. `scripts/build-cn-site.py`（CN 构建编排：astro build + sitemap/robots 产出 + 完整性校验）
5. `scripts/rewrite-cn-html-links.py`（CN 产物链接归一：仅做根相对 `/en/* -> /*`，避免误改跨域 hreflang）
6. `scripts/check-cn-blog-sync.py`（博客同步门禁：校验 EN 新发布文章必须有 `src/content/blog-i18n/zh/<slug>.md` 中文稿）

## 9.2 需修改

1. `scripts/verify-production-i18n.ps1`
   - 跳转目标改为 `.cn` 根路径
   - 增加“只允许一跳 301”断言
   - 增加可配置的 `zh-CN hreflang` 断言（旧版为必须 absent）
2. `docs/i18n/release-acceptance-checklist.md`
   - `/zh*` 目标路径更新为 `.cn/*`
   - hreflang 验收口径更新为跨域版本
3. `public/_redirects`
   - 按新映射更新三条 `/zh` 规则
   - 增加 `/en* -> /*` 301 规则，彻底去除 `.cn` 冗余 `/en/` 入口

## 9.3 deploy-cn-site 工作流运行约束（新增）

1. 触发方式：GitHub Actions 手动触发 `Deploy CN Site`（`workflow_dispatch`）。
2. 默认门禁：
   - `python scripts/quality-gate.py`
   - `npm run build:cn`（内部包含 CN 产物完整性校验）
3. 部署凭据（非 dry-run 必填）：
   - `CF_API_TOKEN`（GitHub Secret）
   - `CF_ACCOUNT_ID`（GitHub Secret）
   - `CN_ICP_NUMBER`（GitHub Repository Variable，建议配置；未配置时使用默认值 `京ICP备2026009936号`）
   - `CN_ICP_URL`（GitHub Repository Variable，可选；默认 `https://beian.miit.gov.cn/`）
   - `CN_PUBLIC_SECURITY_STATUS`（GitHub Repository Variable，可选；`pending|active`，默认 `pending`）
   - `CN_PUBLIC_SECURITY_RECORD`（GitHub Repository Variable，可选；默认 `公安备案办理中`）
   - `CN_PUBLIC_SECURITY_URL`（GitHub Repository Variable，可选）
4. 关键输入项：
   - `pages_project_name`（默认 `localvram-cn`）
   - `pages_branch`（默认 `main`）
   - `cn_domain`（默认 `https://localvram.cn`）
   - `expected_sitemap_url`（默认 `https://localvram.cn/sitemap-cn.xml`）
   - `skip_content_checks`（默认 `false`；仅在受限网络/TLS 环境下启用，跳过 canonical/hreflang/footer/robots 内容断言）
   - `push_baidu_urls`（默认 `true`，部署后推送百度）
   - `baidu_push_required`（默认 `false`，缺 token 是否阻断）
   - `baidu_site`（默认 `https://localvram.cn`）
   - `baidu_sitemap_url`（默认 `https://localvram.cn/sitemap-cn.xml`）
   - `baidu_push_limit`（默认 `5000`）
5. 部署后验证：
   - 自动执行 `scripts/verify-cn-domain.ps1`
   - 默认包含 legacy `/zh` 兼容跳转检查、`/en* -> /*` 收口检查（单跳+query 保留）与线上 canonical/robots/sitemap 校验
   - 额外校验跨域 hreflang（`zh-CN` 指向 `.cn`，`en/x-default` 指向 `.com/en`）与 Footer 备案文案（ICP / 公安备案状态）
   - 可选自动执行 `scripts/push-baidu-urls.py` 推送 `sitemap-cn.xml`
   - 失败自动创建/更新 `[OPS-ALERT] Deploy CN Site: deploy_cn_failed`

---

## 十、CN 站运维要求

1. SSL 续签必须文档化并自动化（`certbot renew` + reload hook）。
2. 发布采用原子切换：
   - `/var/www/localvram-cn/releases/<timestamp>`
   - `current` 软链接切换
3. 建议接入腾讯云 CDN（至少缓存 `/_astro/*`）优化大陆访问与 CWV。
4. 配置 GA4（或同类工具）跨域追踪：`localvram.com` 与 `localvram.cn` 纳入同一数据流跨域白名单。
5. 切换器跳转链路保留统计参数并验证 `_gl` 参数可透传。

---

## 十一、发布阻断项（Go/No-Go）

1. `.com/zh*` 到 `.cn/*` 映射正确，且仅一跳 301（含 query 保留断言）。
2. `.cn` 首页与关键路径均 200，无静态资源 404。
3. `.cn` canonical 全部自指向 `localvram.cn`。
4. 跨域 hreflang 双向声明可被采样页面验证通过。
5. `robots.txt` 指向 `https://localvram.cn/sitemap-cn.xml`。
6. 百度推送脚本可读取并推送 `sitemap-cn.xml` URL 列表。
7. ICP 备案信息（`京ICP备2026009936号`）在线可见且备案链接可访问；公安备案事项已登记并持续跟踪。
8. 每日新增英文博客（按 `pubDate`）必须同步存在 CN 中文稿，否则阻断发布流水线。

---

## 十二、风险与缓解

| 风险 | 影响 | 缓解 |
|---|---|---|
| 新旧 hreflang 门禁冲突 | CI 红灯 | 先改脚本断言，再发 hreflang |
| 旧 `/zh/` 外链仍在传播 | 404 或重复页 | Nginx 保留 `/zh/* -> /*` 长期 301 |
| 手工配置漂移 | 循环或二跳 | 全部规则版本化到仓库 + 自动验证 |
| 证书过期 | 全站不可访问 | 自动续签 + 监控告警 |
| CN 首屏慢 | 跳出率高 | CDN 缓存 `_astro` 与静态资源 |

---

## 十三、相关文档

1. `docs/i18n/release-acceptance-checklist.md`
2. `docs/i18n/seo-field-matrix.md`
3. `docs/i18n/translation-pack-workflow.md`
4. `README.md`
