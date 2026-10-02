const HEADERS = {
  "content-type": "application/json; charset=utf-8",
  "cache-control": "no-store",
  "x-content-type-options": "nosniff",
};

function reply(body, status, head = false, extra = {}) {
  return new Response(head ? null : JSON.stringify(body), {
    status,
    headers: { ...HEADERS, ...extra },
  });
}

export default {
  async fetch(request) {
    const head = request.method === "HEAD";
    const path = new URL(request.url).pathname;
    if (path !== "/health") {
      return reply({ error: "not_found" }, 404, head);
    }
    if (request.method !== "GET" && !head) {
      return reply({ error: "method_not_allowed" }, 405,
        false, { allow: "GET, HEAD" });
    }
    return reply({ ok: true, schema: "health/1" }, 200, head);
  },
};
