import { defineConfig } from "astro/config";

const buildTarget = String(process.env.BUILD_TARGET || "").trim().toLowerCase();
const isCnBuild = buildTarget === "cn";
const defaultSite = isCnBuild ? "https://localvram.cn" : "https://localvram.com";
const resolvedSite = String(process.env.SITE_URL || defaultSite).trim().replace(/\/$/, "");

export default defineConfig({
  site: resolvedSite || defaultSite,
  output: "static",
  outDir: isCnBuild ? "dist-cn" : "dist",
  vite: {
    cacheDir: ".cache/vite"
  },
  build: {
    format: "directory"
  }
});
