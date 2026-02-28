const COM_HOSTS = new Set(["localvram.com", "www.localvram.com"]);
const CN_ORIGIN = "https://localvram.cn";

export async function onRequest(context) {
  const url = new URL(context.request.url);
  const host = (url.hostname || "").toLowerCase();

  if (!COM_HOSTS.has(host)) {
    return context.next();
  }

  let path = url.pathname || "/zh/";
  if (!path.startsWith("/zh")) {
    path = `/zh${path.startsWith("/") ? path : `/${path}`}`;
  }
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
