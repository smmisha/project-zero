import { test } from "node:test";
import assert from "node:assert/strict";
import { isExcluded, parseExclude } from "../src/filters.js";

test("plain name excludes a directory at any depth", () => {
  assert.ok(isExcluded("tests/test_app.py", ["tests"]));
  assert.ok(isExcluded("pkg/tests/x.py", ["tests/"]));
  assert.ok(!isExcluded("src/tests_helper.py", ["tests"]));
  assert.ok(!isExcluded("src/tests", ["tests"]));
});

test("path prefix and globs", () => {
  assert.ok(isExcluded("docs/api/x.py", ["docs/api"]));
  assert.ok(!isExcluded("src/docs/api/x.py", ["docs/api"]));
  assert.ok(isExcluded("static/app.min.js", ["*.min.js"]));
  assert.ok(isExcluded("docs/conf.py", ["docs/*"]));
  assert.ok(!isExcluded("src/app.js", ["*.min.js"]));
  assert.ok(isExcluded("a.c", ["[ab].c"]));
});

test("parseExclude splits commas and drops blanks", () => {
  assert.deepEqual(parseExclude(" tests, ,*.min.js "), ["tests", "*.min.js"]);
  assert.deepEqual(parseExclude(undefined), []);
  assert.deepEqual(parseExclude(["a", " b "]), ["a", "b"]);
});
