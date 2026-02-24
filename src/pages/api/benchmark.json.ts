import benchmarkResults from "../../data/benchmark-results.json";

export const prerender = true;

export async function GET() {
  return new Response(JSON.stringify(benchmarkResults), {
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "public, max-age=300",
    },
  });
}
