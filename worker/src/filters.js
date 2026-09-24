// Path filtering for exclude patterns — JS port of git_hotspots/filters.py.
//
// A pattern with glob characters (*, ?, [) is matched against the full path
// (like Python's fnmatch: * also matches "/"). A plain pattern like "tests"
// or "tests/" excludes that directory at any depth, or that exact file.

function globToRegExp(glob) {
  let re = "";
  for (let i = 0; i < glob.length; i++) {
    const ch = glob[i];
    if (ch === "*") re += ".*";
    else if (ch === "?") re += ".";
    else if (ch === "[") {
      const end = glob.indexOf("]", i + 1);
      if (end === -1) {
        re += "\\[";
      } else {
        let body = glob.slice(i + 1, end).replace(/\\/g, "\\\\");
        if (body.startsWith("!")) body = "^" + body.slice(1);
        re += `[${body}]`;
        i = end;
      }
    } else re += ch.replace(/[.+^${}()|\\/]/g, "\\$&");
  }
  return new RegExp(`^${re}$`);
}

export function isExcluded(path, patterns) {
  if (!patterns || patterns.length === 0) return false;
  path = path.replace(/\\/g, "/");
  const parts = path.split("/");
  for (let pattern of patterns) {
    pattern = (pattern || "").trim().replace(/\\/g, "/");
    if (!pattern) continue;
    if (/[*?[]/.test(pattern)) {
      if (globToRegExp(pattern).test(path)) return true;
      continue;
    }
    pattern = pattern.replace(/^\/+|\/+$/g, "");
    if (path === pattern || path.startsWith(pattern + "/")) return true;
    if (!pattern.includes("/") && parts.slice(0, -1).includes(pattern)) return true;
  }
  return false;
}

export function parseExclude(raw) {
  const list = Array.isArray(raw) ? raw : String(raw || "").split(",");
  return list.map((p) => String(p).trim()).filter(Boolean).slice(0, 20);
}
