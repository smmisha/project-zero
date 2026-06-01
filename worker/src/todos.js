// Scan already-fetched file contents for TODO/FIXME debt.
// Note: no git blame in the Worker, so we report file:line + text but not
// per-line author/age (that needs git history we don't fetch line-by-line).

const TODO_RE = /\b(TODO|FIXME|HACK|XXX|NOTE|BUG|KLUDGE|OPTIMIZE)\b[\s:]*(.{0,100})/i;

export function findTodos(contents, limitFiles) {
  const results = [];
  const paths = Object.keys(contents).slice(0, limitFiles || Object.keys(contents).length);
  for (const path of paths) {
    const lines = contents[path].split("\n");
    for (let i = 0; i < lines.length; i++) {
      const m = lines[i].match(TODO_RE);
      if (m) {
        results.push({
          file: path,
          line: i + 1,
          kind: m[1].toUpperCase(),
          text: (m[2] || "").trim(),
        });
      }
    }
  }
  return results;
}
