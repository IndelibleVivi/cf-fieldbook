import test from "node:test";
import assert from "node:assert/strict";
import worker from "./index.mjs";

const call = (path, init = {}) => worker.fetch(
  new Request(`https://example.com${path}`, init));

test("GET health has a fixed schema and is not cacheable", async () => {
  const response = await call("/health");
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), { ok: true, schema: "health/1" });
  assert.equal(response.headers.get("cache-control"), "no-store");
  assert.equal(response.headers.get("x-content-type-options"), "nosniff");
});

test("HEAD returns headers without a body", async () => {
  const response = await call("/health", { method: "HEAD" });
  assert.equal(response.status, 200);
  assert.equal(await response.text(), "");
});

test("Unsupported methods do not create an action", async () => {
  for (const method of ["POST", "PUT", "PATCH", "DELETE", "OPTIONS"]) {
    const response = await call("/health", { method });
    assert.equal(response.status, 405);
    assert.equal(response.headers.get("allow"), "GET, HEAD");
  }
});

test("Unknown paths and encoded lookalikes return 404", async () => {
  for (const path of ["/", "/missing", "/health/", "/%68ealth"]) {
    const response = await call(path);
    assert.equal(response.status, 404);
  }
});

test("HEAD on an unknown path has no body", async () => {
  const response = await call("/missing", { method: "HEAD" });
  assert.equal(response.status, 404);
  assert.equal(await response.text(), "");
});

test("Caller supplied metadata is not reflected", async () => {
  const response = await call("/health?secret=synthetic-only", {
    headers: { authorization: "Bearer synthetic-only", "x-private": "synthetic-only" },
  });
  assert.equal((await response.text()).includes("synthetic-only"), false);
});
