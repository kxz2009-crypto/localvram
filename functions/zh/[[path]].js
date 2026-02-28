const COM_HOSTS = new Set(["localvram.com", "www.localvram.com"]);
const CN_ORIGIN = "https://localvram.cn";
const REDIRECT_ENABLE_FLAGS = new Set(["1", "true", "yes", "on"]);

export async function onRequest(context) {
  const cutoverRaw = String(context.env?.LV_ZH_CN_CUTOVER || "").trim().toLowerCase();
  // Safety-first: keep redirect disabled unless explicitly enabled.
  if (!REDIRECT_ENABLE_FLAGS.has(cutoverRaw)) {
    return context.next();
  }

  const url = new URL(context.request.url);
  const host = (url.hostname || "").toLowerCase();
  if (!COM_HOSTS.has(host)) {
    return context.next();
  }

  let path = url.pathname || "/zh/";
  if (path === "/zh") {
    path = "/zh/";
  }
  const destination = new URL(path, CN_ORIGIN);
  if (url.search) {
    destination.search = url.search;
  }

  return new Response(null, {
    status: 301,
    headers: {
      Location: destination.toString(),
      "Cache-Control": "public, max-age=3600"
    }
  });
}
