export interface EditorAction {
  id: string;
  label: string;
  math?: boolean;
  wrap?: [string, string];
  insert?: string;
  select?: [number, number];
  title?: string;
}

export interface EditorGroup {
  name: string;
  actions: EditorAction[];
}

export const TOOLBAR: EditorGroup[] = [
  {
    name: "Structure",
    actions: [
      { id: "h1", label: "H1", insert: "# ", title: "Title heading (Ctrl+1)" },
      { id: "h2", label: "H2", insert: "## ", title: "Section heading (Ctrl+2)" },
      { id: "h3", label: "H3", insert: "### ", title: "Heading 3 (Ctrl+3)" },
      { id: "h4", label: "H4", insert: "#### ", title: "Heading 4 (Ctrl+4)" },
      { id: "h5", label: "H5", insert: "##### ", title: "Heading 5 (Ctrl+5)" },
      { id: "h6", label: "H6", insert: "###### ", title: "Heading 6 (Ctrl+6)" },
      { id: "bullet", label: "• list", insert: "- ", title: "Bullet" },
      { id: "numbered", label: "1. list", insert: "1. ", title: "Numbered list" },
      { id: "quote", label: "> quote", insert: "> ", title: "Blockquote" },
      {
        id: "table",
        label: "table",
        insert: "| Concept | Formula |\n| --- | --- |\n|  |  |\n",
        title: "Table",
      },
      {
        id: "template",
        label: "skeleton",
        insert: "## Section\n\nWrite here — inline math like $r = \\frac{D_1}{P_0} + g$ and display math:\n\n$$E(R_p) = \\sum_{i=1}^{n} w_i E(R_i)$$\n\n- key point\n",
        select: [3, 10],
        title: "Insert a section skeleton",
      },
    ],
  },
  {
    name: "Markdown",
    actions: [
      { id: "bold", label: "B", wrap: ["**", "**"], title: "Bold (⌘/Ctrl+B)" },
      { id: "italic", label: "I", wrap: ["*", "*"], title: "Italic (⌘/Ctrl+I)" },
      { id: "link", label: "link", wrap: ["[", "](https://)"], title: "Link" },
      { id: "codeblock", label: "code block", wrap: ["```\n", "\n```"], title: "Code block" },
      { id: "code", label: "code", wrap: ["`", "`"], title: "Inline code" },
      { id: "inline", label: "$x$", wrap: ["$", "$"], title: "Inline math" },
      { id: "display", label: "$$", wrap: ["$$\n", "\n$$"], title: "Display math" },
    ],
  },
  {
    name: "Math",
    actions: [
      { id: "frac", label: "$\\frac{a}{b}$", math: true, insert: "\\frac{a}{b}", select: [6, 7], title: "Fraction" },
      { id: "sqrt", label: "$\\sqrt{x}$", math: true, insert: "\\sqrt{x}", select: [6, 7], title: "Square root" },
      { id: "sub", label: "$x_i$", math: true, insert: "x_{i}", select: [3, 4], title: "Subscript" },
      { id: "sup", label: "$x^2$", math: true, insert: "x^{2}", select: [3, 4], title: "Superscript" },
      { id: "sum", label: "$\\sum_{i=1}^{n}$", math: true, insert: "\\sum_{i=1}^{n} ", title: "Summation" },
      { id: "bar", label: "$\\bar{x}$", math: true, insert: "\\bar{x}", select: [5, 6], title: "Overline / mean" },
      { id: "hat", label: "$\\hat{y}$", math: true, insert: "\\hat{y}", select: [5, 6], title: "Estimator" },
    ],
  },
  {
    name: "Greek",
    actions: [
      { id: "alpha", label: "$\\alpha$", math: true, insert: "$\\alpha$" },
      { id: "beta", label: "$\\beta$", math: true, insert: "$\\beta$" },
      { id: "delta", label: "$\\delta$", math: true, insert: "$\\delta$" },
      { id: "Delta", label: "$\\Delta$", math: true, insert: "$\\Delta$" },
      { id: "theta", label: "$\\theta$", math: true, insert: "$\\theta$" },
      { id: "lambda", label: "$\\lambda$", math: true, insert: "$\\lambda$" },
      { id: "mu", label: "$\\mu$", math: true, insert: "$\\mu$" },
      { id: "pi", label: "$\\pi$", math: true, insert: "$\\pi$" },
      { id: "rho", label: "$\\rho$", math: true, insert: "$\\rho$" },
      { id: "sigma", label: "$\\sigma$", math: true, insert: "$\\sigma$" },
      { id: "Sigma", label: "$\\Sigma$", math: true, insert: "$\\Sigma$" },
      { id: "omega", label: "$\\omega$", math: true, insert: "$\\omega$" },
    ],
  },
  {
    name: "Symbols",
    actions: [
      { id: "approx", label: "$\\approx$", math: true, insert: "$\\approx$" },
      { id: "neq", label: "$\\neq$", math: true, insert: "$\\neq$" },
      { id: "leq", label: "$\\leq$", math: true, insert: "$\\leq$" },
      { id: "geq", label: "$\\geq$", math: true, insert: "$\\geq$" },
      { id: "times", label: "$\\times$", math: true, insert: "$\\times$" },
      { id: "cdot", label: "$\\cdot$", math: true, insert: "$\\cdot$" },
      { id: "pm", label: "$\\pm$", math: true, insert: "$\\pm$" },
      { id: "to", label: "$\\to$", math: true, insert: "$\\to$" },
      { id: "impl", label: "$\\Rightarrow$", math: true, insert: "$\\Rightarrow$" },
      { id: "inf", label: "$\\infty$", math: true, insert: "$\\infty$" },
    ],
  },
];

export function applyAction(
  text: string,
  start: number,
  end: number,
  action: EditorAction,
): { text: string; start: number; end: number } {
  if (/^h[1-6]$/.test(action.id)) {
    const lineStart = start === 0 ? 0 : text.lastIndexOf("\n", start - 1) + 1;
    const existing = text.slice(lineStart).match(/^#{1,6}\s+/)?.[0] ?? "";
    const prefix = action.insert ?? "";
    const next = text.slice(0, lineStart) + prefix + text.slice(lineStart + existing.length);
    const translate = (position: number) => position < lineStart + existing.length ? lineStart + prefix.length : position + prefix.length - existing.length;
    return { text: next, start: translate(start), end: translate(end) };
  }
  if (action.wrap) {
    const [prefix, suffix] = action.wrap;
    const selected = text.slice(start, end);
    const next = text.slice(0, start) + prefix + selected + suffix + text.slice(end);
    const s = start + prefix.length;
    return { text: next, start: s, end: s + selected.length };
  }
  const ins = action.insert ?? "";
  const next = text.slice(0, start) + ins + text.slice(end);
  if (action.select) {
    const [a, b] = action.select;
    return { text: next, start: start + a, end: start + b };
  }
  const p = start + ins.length;
  return { text: next, start: p, end: p };
}

// Only Ctrl+1–6: leave Command+number available for macOS/browser shortcuts.
export function headingShortcut(e: Pick<KeyboardEvent, "ctrlKey" | "metaKey" | "altKey" | "shiftKey" | "key" | "code">): string | null {
  if (!e.ctrlKey || e.metaKey || e.altKey || e.shiftKey) return null;
  const key = /^Digit[1-6]$/.test(e.code) ? e.code.slice(-1) : e.key;
  return /^[1-6]$/.test(key) ? `h${key}` : null;
}
