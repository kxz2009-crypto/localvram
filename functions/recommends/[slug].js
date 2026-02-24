import {
  buildAmazonTarget,
  redirectResponse,
  trackClick,
  withSharedTrackingParams
} from "../_lib/affiliate.js";

export async function onRequest(context) {
  const slug = String(context.params.slug || "").toLowerCase();
  const target = buildAmazonTarget(slug, context.env);
  if (!target) {
    return Response.redirect("https://localvram.com/en/affiliate/hardware-upgrade/?invalid_slug=1", 302);
  }

  const destination = withSharedTrackingParams(target.url, context.request.url, `recommends-${slug}`);
  trackClick(context, {
    provider: target.provider,
    route: `/recommends/${slug}`,
    destination
  });
  return redirectResponse(destination);
}
