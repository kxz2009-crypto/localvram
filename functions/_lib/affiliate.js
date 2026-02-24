const DEFAULT_RUNPOD_REF = "kzc9gtvv";
const DEFAULT_VAST_REF_ID = "415258";

const AMAZON_RECOMMENDATIONS = {
  "rtx-3090-24gb": {
    keyword: "RTX 3090 24GB graphics card",
    label: "RTX 3090 24GB",
    envKey: "AMAZON_3090_URL",
    directUrl: "https://amzn.to/4sdISrb"
  },
  "rtx-4090-24gb": {
    keyword: "RTX 4090 24GB graphics card",
    label: "RTX 4090 24GB",
    envKey: "AMAZON_4090_URL",
    directUrl: "https://amzn.to/3N1JaCr"
  },
  "atx3-1000w-psu": {
    keyword: "ATX 3.0 1000W PSU",
    label: "ATX 3.0 1000W PSU",
    envKey: "AMAZON_PSU_URL",
    directUrl: "https://amzn.to/4ryN84q"
  },
  "high-airflow-case": {
    keyword: "high airflow mid tower case",
    label: "CORSAIR 4000D Mid-Tower",
    envKey: "AMAZON_CASE_URL",
    directUrl: "https://amzn.to/4ryVBEN"
  }
};

function withSharedTrackingParams(targetUrl, requestUrl, channel) {
  const target = new URL(targetUrl);
  const source = new URL(requestUrl);
  for (const [key, value] of source.searchParams.entries()) {
    if (!target.searchParams.has(key)) {
      target.searchParams.set(key, value);
    }
  }
  if (!target.searchParams.has("utm_source")) {
    target.searchParams.set("utm_source", "localvram");
  }
  if (!target.searchParams.has("utm_medium")) {
    target.searchParams.set("utm_medium", "affiliate_redirect");
  }
  if (!target.searchParams.has("utm_campaign")) {
    target.searchParams.set("utm_campaign", channel);
  }
  return target.toString();
}

function buildAmazonTarget(slug, env) {
  const entry = AMAZON_RECOMMENDATIONS[slug];
  if (!entry) {
    return null;
  }
  const envUrl = entry.envKey ? String(env[entry.envKey] || "").trim() : "";
  const directUrl = envUrl || entry.directUrl || "";
  if (directUrl) {
    return {
      provider: "amazon",
      label: entry.label,
      url: directUrl
    };
  }
  const url = new URL("https://www.amazon.com/s");
  url.searchParams.set("k", entry.keyword);
  if (env.AMAZON_TAG) {
    url.searchParams.set("tag", env.AMAZON_TAG);
  }
  return {
    provider: "amazon",
    label: entry.label,
    url: url.toString()
  };
}

function buildProviderTarget(provider, env) {
  if (provider === "runpod") {
    return {
      provider: "runpod",
      label: "RunPod",
      url: `https://runpod.io?ref=${encodeURIComponent(env.RUNPOD_REF || DEFAULT_RUNPOD_REF)}`
    };
  }
  if (provider === "vast") {
    return {
      provider: "vast",
      label: "Vast.ai",
      url: `https://cloud.vast.ai/?ref_id=${encodeURIComponent(env.VAST_REF_ID || DEFAULT_VAST_REF_ID)}`
    };
  }
  return null;
}

function redirectResponse(url) {
  return new Response(null, {
    status: 302,
    headers: {
      Location: url,
      "Cache-Control": "no-store, max-age=0",
      "X-Robots-Tag": "noindex, nofollow"
    }
  });
}

async function persistClickEvent(context, event) {
  try {
    if (context.env.AFFILIATE_EVENTS) {
      const key = `click:${Date.now()}:${crypto.randomUUID()}`;
      await context.env.AFFILIATE_EVENTS.put(key, JSON.stringify(event), {
        expirationTtl: 60 * 60 * 24 * 30
      });
    }
  } catch (error) {
    console.log("affiliate_event_store_error", String(error));
  }
  console.log("affiliate_click", JSON.stringify(event));
}

function trackClick(context, details) {
  const cf = context.request.cf || {};
  const event = {
    ts: new Date().toISOString(),
    path: context.request.url,
    provider: details.provider,
    route: details.route,
    destination: details.destination,
    referer: context.request.headers.get("referer") || "",
    userAgent: context.request.headers.get("user-agent") || "",
    ip: context.request.headers.get("cf-connecting-ip") || "",
    country: cf.country || "",
    colo: cf.colo || ""
  };
  context.waitUntil(persistClickEvent(context, event));
}

export {
  AMAZON_RECOMMENDATIONS,
  buildAmazonTarget,
  buildProviderTarget,
  redirectResponse,
  trackClick,
  withSharedTrackingParams
};
