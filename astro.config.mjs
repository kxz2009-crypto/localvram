import { defineConfig } from "astro/config";

export default defineConfig({
  site: "https://localvram.com",
  output: "static",
  vite: {
    cacheDir: ".cache/vite"
  },
  build: {
    format: "directory"
  }
});
