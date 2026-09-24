import { test } from "node:test";
import assert from "node:assert/strict";
import { analyzeContent, normalizeComplexity } from "../src/complexity.js";
import { calculateHotspots, getSummaryStats } from "../src/hotspots.js";
import { findTodos } from "../src/todos.js";

test("bigger file outranks a small file with the same code style", () => {
  const block = (n) => `def f${n}(x):\n    if x:\n        return 1\n    return 0\n`;
  const complexity = {
    "small.py": analyzeContent("small.py", block(0)),
    "big.py": analyzeContent("big.py", Array.from({ length: 100 }, (_, i) => block(i)).join("")),
  };
  normalizeComplexity(complexity);
  assert.equal(complexity["big.py"].complexity_score, 100);
  assert.ok(complexity["small.py"].complexity_score < 5);
});

test("summary stats report real commits, not file changes", () => {
  const churn = { "a.py": 3, "b.py": 3 };
  const cx = { "a.py": { complexity_score: 50, loc: 10 } };
  const stats = getSummaryStats(calculateHotspots(churn, cx, {}), churn, cx, 3);
  assert.equal(stats.total_commits_analyzed, 3);
  assert.equal(stats.total_file_changes, 6);
});

test("TODO scan ignores NOTE and lowercase prose", () => {
  const todos = findTodos({
    "a.py": "# TODO: fix\n# NOTE: docs\n# the todo list\n# FIXME later\n",
  });
  assert.deepEqual(todos.map((t) => [t.kind, t.line]), [["TODO", 1], ["FIXME", 4]]);
});
