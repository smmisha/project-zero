// Language-agnostic complexity heuristics — JS port of complexity.py.
// Computes a 0-100 complexity score from branch density, function count,
// and max nesting depth. No parsing, just regex heuristics.

const BRANCH_KEYWORDS = {
  python: [/\bif\b/g, /\belif\b/g, /\bfor\b/g, /\bwhile\b/g, /\bexcept\b/g, /\bwith\b/g, /\band\b/g, /\bor\b/g, /\bassert\b/g, /\blambda\b/g],
  js_ts: [/\bif\b/g, /\belse\b/g, /\bfor\b/g, /\bwhile\b/g, /\bswitch\b/g, /\bcase\b/g, /\bcatch\b/g, /\?\./g, /\?\?/g, /\?\s*:/g],
  java_kotlin: [/\bif\b/g, /\bfor\b/g, /\bwhile\b/g, /\bswitch\b/g, /\bcase\b/g, /\bcatch\b/g, /\bthrow\b/g, /\binstanceof\b/g],
  go: [/\bif\b/g, /\bfor\b/g, /\bswitch\b/g, /\bcase\b/g, /\bselect\b/g, /\bdefer\b/g, /\bgo\b/g],
  rust: [/\bif\b/g, /\bfor\b/g, /\bwhile\b/g, /\bmatch\b/g, /\bunwrap\b/g, /\bexpect\b/g],
  c_cpp: [/\bif\b/g, /\bfor\b/g, /\bwhile\b/g, /\bswitch\b/g, /\bcase\b/g, /\bgoto\b/g],
  generic: [/\bif\b/g, /\bfor\b/g, /\bwhile\b/g, /\bswitch\b/g, /\bcase\b/g, /\bcatch\b/g],
};

const FUNCTION_PATTERNS = {
  python: [/^\s*def\s+\w+/gm, /^\s*async\s+def\s+\w+/gm],
  js_ts: [/function\s+\w+\s*\(/g, /^\s*\w+\s*:\s*(?:async\s+)?\(/gm, /=>\s*[{(]/g, /^\s*(?:async\s+)?(?:get|set)\s+\w+/gm],
  java_kotlin: [/(?:public|private|protected|internal|override)\s+(?:\w+\s+)+\w+\s*\(/g, /^\s*fun\s+\w+/gm],
  go: [/^\s*func\s+(?:\(\w+\s+\*?\w+\)\s+)?\w+/gm],
  rust: [/^\s*(?:pub\s+)?fn\s+\w+/gm],
  c_cpp: [/^\s*\w[\w\s*]+\s+\w+\s*\(/gm],
  generic: [/^\s*(?:def|func|function)\s+\w+/gm],
};

const EXTENSION_MAP = {
  py: "python",
  js: "js_ts", jsx: "js_ts", ts: "js_ts", tsx: "js_ts", mjs: "js_ts", cjs: "js_ts",
  java: "java_kotlin", kt: "java_kotlin", kts: "java_kotlin", scala: "java_kotlin", cs: "java_kotlin",
  go: "go",
  rs: "rust",
  c: "c_cpp", cpp: "c_cpp", cc: "c_cpp", h: "c_cpp", hpp: "c_cpp",
  rb: "generic", php: "generic", swift: "generic",
  dart: "js_ts",
};

export const SUPPORTED_EXTENSIONS = new Set(Object.keys(EXTENSION_MAP));

export function detectLanguage(path) {
  const dot = path.lastIndexOf(".");
  if (dot === -1) return null;
  const ext = path.slice(dot + 1).toLowerCase();
  return EXTENSION_MAP[ext] || null;
}

export function isSourceFile(path) {
  return detectLanguage(path) !== null;
}

function countMatches(text, patterns) {
  let n = 0;
  for (const re of patterns) {
    const m = text.match(re);
    if (m) n += m.length;
  }
  return n;
}

// Analyze a file's source text. Returns metrics or null if unusable.
export function analyzeContent(path, content) {
  const lang = detectLanguage(path);
  if (!lang) return null;
  if (!content || content.length > 500000) return null;

  const lines = content.split("\n");
  if (lines.length === 0) return null;

  const codeLines = [];
  for (const line of lines) {
    const s = line.trim();
    if (s && !/^(#|\/\/|\*|\/\*|\*\/|')/.test(s)) {
      codeLines.push(line);
    }
  }
  const loc = codeLines.length;
  if (loc === 0) return null;

  const codeText = codeLines.join("\n");
  const branchCount = countMatches(codeText, BRANCH_KEYWORDS[lang] || BRANCH_KEYWORDS.generic);
  const funcCount = countMatches(content, FUNCTION_PATTERNS[lang] || FUNCTION_PATTERNS.generic);

  let maxDepth = 0;
  for (const line of codeLines) {
    if (!line.trim()) continue;
    const leading = line.length - line.trimStart().length;
    const depth = line[0] === "\t" ? leading : Math.floor(leading / 4);
    if (depth > maxDepth) maxDepth = depth;
  }

  const rawComplexity = branchCount + funcCount * 2 + maxDepth * 1.5;
  const complexityScore = Math.min(100, (rawComplexity / Math.max(loc, 1)) * 100);

  return {
    loc,
    branch_count: branchCount,
    function_count: funcCount,
    max_depth: maxDepth,
    complexity_score: Math.round(complexityScore * 100) / 100,
    language: lang,
  };
}
