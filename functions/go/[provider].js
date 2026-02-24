import {
  buildProviderTarget,
  redirectResponse,
  trackClick,
  withSharedTrackingParams
} from "../_lib/affiliate.js";

export async function onRequest(context) {
  const provider = String(context.params.provider || "").toLowerCase();
  const target = buildProviderTarget(provider, context.env);
  if (!target) {
    return Response.redirect("https://localvram.com/en/affiliate/cloud-gpu/?invalid_provider=1", 302);
  }

  const destination = withSharedTrackingParams(target.url, context.request.url, `go-${provider}`);
  trackClick(context, {
    provider: target.provider,
    route: `/go/${provider}`,
    destination
  });
  return redirectResponse(destination);
}
