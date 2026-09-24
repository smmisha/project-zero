import { test, afterEach } from "node:test";
import assert from "node:assert/strict";
import { buildChurn, listCommits, GitHubError, SubrequestBudget } from "../src/github.js";

const realFetch = globalThis.fetch;
afterEach(() => { globalThis.fetch = realFetch; });

const commits = Array.from({ length: 150 }, (_, i) => ({ sha: `s${i}`, author: `dev${i % 3}` }));
const ok = (body) => new Response(JSON.stringify(body), { status: 200 });
const rateLimited = () =>
  new Response("{}", { status: 403, headers: { "x-ratelimit-remaining": "0" } });

test("rate limit mid-way is reported, not hidden (regression)", async () => {
  let n = 0;
  globalThis.fetch = async () => (++n > 40 ? rateLimited() : ok({ files: [{ filename: "a.js" }] }));
  const r = await buildChurn("o", "r", commits, null, 150);
  assert.equal(r.analyzed, 40);          // used to claim 150 of 150
  assert.equal(r.churn["a.js"], 40);
  assert.equal(r.total, 150);
  assert.equal(r.rateLimited, true);
  assert.ok(n < 60, `stops issuing requests after the limit (made ${n})`);
});

test("rate limit before any commit is fetched throws", async () => {
  globalThis.fetch = async () => rateLimited();
  await assert.rejects(buildChurn("o", "r", commits, null, 10), (e) => e instanceof GitHubError && e.status === 429);
});

test("listCommits stops at the subrequest budget and says it truncated", async () => {
  let calls = 0;
  globalThis.fetch = async () => {
    calls++;
    return ok(Array.from({ length: 100 }, (_, i) => ({ sha: `x${calls}-${i}`, commit: { author: { name: "a", date: "2026-01-01T00:00:00Z" } } })));
  };
  const budget = new SubrequestBudget(2);
  const r = await listCommits("o", "r", "2025-01-01T00:00:00Z", null, 8, budget);
  assert.equal(calls, 2);
  assert.equal(r.commits.length, 200);
  assert.equal(r.truncated, true);
  assert.equal(budget.left, 0);
});
