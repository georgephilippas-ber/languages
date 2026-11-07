interface MathEnd {
  end: number;
  closeLen: number;
}

function findDollarEnd(text: string, start: number, display: boolean): MathEnd | null {
  if (start >= text.length) return null;
  if (!display && /\s/.test(text[start])) return null;

  let j = start;
  while (j < text.length) {
    const ch = text[j];
    if (ch === "\\") {
      j += 2;
      continue;
    }
    if (display) {
      if (ch === "$" && text[j + 1] === "$") return { end: j, closeLen: 2 };
    } else {
      if (ch === "\n") return null;
      if (ch === "$") {
        if (/\s/.test(text[j - 1])) return null;
        const after = text[j + 1];
        if (after && /[0-9]/.test(after)) return null;
        return { end: j, closeLen: 1 };
      }
    }
    j += 1;
  }
  return null;
}

export interface MathSpan {
  start: number;
  end: number;
  tex: string;
  display: boolean;
}

export function findMathSpans(text: string): MathSpan[] {
  const spans: MathSpan[] = [];
  let i = 0;

  while (i < text.length) {
    const ch = text[i];
    const next = text[i + 1];

    if (ch === "\\") {
      if (next === "$") {
        i += 2;
        continue;
      }
      if (next === "(" || next === "[") {
        const close = next === "(" ? "\\)" : "\\]";
        const end = text.indexOf(close, i + 2);
        if (end !== -1) {
          spans.push({ start: i, end: end + 2, tex: text.slice(i + 2, end), display: next === "[" });
          i = end + 2;
          continue;
        }
      }
      i += 1;
      continue;
    }

    if (ch === "$") {
      const display = next === "$";
      const start = i + (display ? 2 : 1);
      const found = findDollarEnd(text, start, display);
      const tex = found ? text.slice(start, found.end).trim() : "";
      if (found && tex) {
        spans.push({ start: i, end: found.end + found.closeLen, tex, display });
        i = found.end + found.closeLen;
        continue;
      }
    }

    i += 1;
  }

  return spans;
}

