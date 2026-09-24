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

test("history follows renames, and a reused old path is a new file", async () => {
  // newest first, as the GitHub API returns them
  const cs = [
    { sha: "c5", author: "dave" },  // new file created at the old path
    { sha: "c4", author: "carol" }, // mid.js -> new.js + edit
    { sha: "c3", author: "bob" },   // old.js -> mid.js
    { sha: "c2", author: "bob" },   // edit old.js
    { sha: "c1", author: "alice" }, // create old.js
  ];
  const files = {
    c5: [{ filename: "old.js", status: "added" }],
    c4: [{ filename: "new.js", previous_filename: "mid.js", status: "renamed" }],
    c3: [{ filename: "mid.js", previous_filename: "old.js", status: "renamed" }],
    c2: [{ filename: "old.js", status: "modified" }],
    c1: [{ filename: "old.js", status: "added" }],
  };
  // Resolve fetches out of order to prove ordering doesn't depend on timing.
  const delay = { c1: 5, c2: 1, c3: 4, c4: 0, c5: 3 };
  globalThis.fetch = async (url) => {
    const sha = url.split("/").pop();
    await new Promise((r) => setTimeout(r, delay[sha]));
    return ok({ files: files[sha] });
  };
  const r = await buildChurn("o", "r", cs, null, 10);
  assert.deepEqual(r.churn, { "new.js": 4, "old.js": 1 });
  assert.deepEqual(r.authors["new.js"].sort(), ["alice", "bob", "carol"]);
  assert.deepEqual(r.authors["old.js"], ["dave"]);
});
