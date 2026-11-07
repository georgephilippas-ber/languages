import { lint } from "markdownlint/sync";
import { applyFixes, type Configuration, type LintError } from "markdownlint";
import { findMathSpans } from "./bookMathSpans";

const CONFIG: Configuration = {
  default: true,
  MD013: false,
  MD033: false,
  MD034: false,
  MD004: { style: "dash" },
  MD009: { br_spaces: 0 },
  MD024: { siblings_only: true },
  MD049: { style: "asterisk" },
  MD050: { style: "asterisk" },
};

const AUTO_FIX = new Set([
  "MD004", "MD005", "MD007", "MD009", "MD010", "MD011", "MD012", "MD018", "MD019",
  "MD020", "MD021", "MD022", "MD023", "MD027", "MD030", "MD031", "MD032", "MD037",
  "MD038", "MD039", "MD047", "MD049", "MD050", "MD058", "MD060",
]);

const OPEN = "";
const CLOSE = "";
const PLACEHOLDER = /(\d+)/g;

export interface LintIssue {
  line: number;
  rule: string;
  description: string;
  detail?: string;
}

export interface LintOutcome {
  text: string;
  fixed: number;
  issues: LintIssue[];
  mathGuard?: string;
}

function maskMath(text: string): { masked: string; pieces: string[] } {
  const pieces: string[] = [];
  let masked = "";
  let pos = 0;
  for (const span of findMathSpans(text)) {
    masked += text.slice(pos, span.start);
    masked += text
      .slice(span.start, span.end)
      .split("\n")
      .map((line) => `${OPEN}${pieces.push(line) - 1}${CLOSE}`)
      .join("\n");
    pos = span.end;
  }
  return { masked: masked + text.slice(pos), pieces };
}

function unmaskMath(masked: string, pieces: string[]): string | null {
  const seen = new Array<number>(pieces.length).fill(0);
  const text = masked.replace(PLACEHOLDER, (_, id: string) => {
    const n = Number(id);
    if (n < pieces.length) seen[n]++;
    return pieces[n] ?? "";
  });
  if (seen.some((count) => count !== 1) || text.includes(OPEN) || text.includes(CLOSE)) return null;
  return text;
}

const mathSources = (text: string): string[] => findMathSpans(text).map((s) => text.slice(s.start, s.end));

function sameMath(before: string, after: string): boolean {
  const a = mathSources(before);
  const b = mathSources(after);
  return a.length === b.length && a.every((src, k) => src === b[k]);
}

function lintMasked(masked: string): LintError[] {
  return lint({ strings: { note: masked }, config: CONFIG }).note ?? [];
}

const toIssue = (e: LintError): LintIssue => ({
  line: e.lineNumber,
  rule: e.ruleNames[0],
  description: e.ruleDescription,
  detail: e.errorDetail ?? undefined,
});

export function lintMarkdown(text: string): LintOutcome {
  if (text.includes(OPEN) || text.includes(CLOSE)) {
    return { text, fixed: 0, issues: [], mathGuard: "The note contains private-use characters the linter relies on; nothing was changed." };
  }

  let current = text;
  let fixed = 0;
  for (let pass = 0; pass < 3; pass++) {
    const { masked, pieces } = maskMath(current);
    const fixable = lintMasked(masked).filter((e) => e.fixInfo && AUTO_FIX.has(e.ruleNames[0]));
    if (fixable.length === 0) break;
    const next = unmaskMath(applyFixes(masked, fixable), pieces);
    if (next === null || !sameMath(text, next)) {
      const { masked: original } = maskMath(text);
      return {
        text,
        fixed: 0,
        issues: lintMasked(original).map(toIssue),
        mathGuard: "Automatic fixes were discarded because they would have changed a formula.",
      };
    }
    fixed += fixable.length;
    current = next;
  }

  const { masked } = maskMath(current);
  const issues = lintMasked(masked)
    .map(toIssue)
    .sort((a, b) => a.line - b.line);
  return { text: current, fixed, issues };
}
