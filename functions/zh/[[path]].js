const COM_HOSTS = new Set(["localvram.com", "www.localvram.com"]);
const CN_ORIGIN = "https://localvram.cn";
const REDIRECT_DISABLE_FLAGS = new Set(["0", "false", "no", "off"]);

export async function onRequest(context) {
  const cutoverRaw = String(context.env?.LV_ZH_CN_CUTOVER || "").trim().toLowerCase();
  // Default-on cutover: disable only when explicitly set to a falsey flag.
  if (REDIRECT_DISABLE_FLAGS.has(cutoverRaw)) {
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
