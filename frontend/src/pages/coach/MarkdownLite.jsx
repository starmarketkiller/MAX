// Markdown helpers (h1-h3, bold, inline-code, lists, paragraphs).
// Intentionally tiny — pull in a real lib (react-markdown) if requirements grow.

function inline(s) {
  const parts = s.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return parts.map((p, i) => {
    const k = `${i}-${p.slice(0, 8)}`;
    if (p.startsWith("**") && p.endsWith("**"))
      return <strong key={`b-${k}`}>{p.slice(2, -2)}</strong>;
    if (p.startsWith("`") && p.endsWith("`"))
      return <code key={`c-${k}`} className="px-1 py-0.5 rounded bg-secondary text-[0.85em]">{p.slice(1, -1)}</code>;
    return <span key={`s-${k}`}>{p}</span>;
  });
}

function headingClass(level) {
  if (level === 1) return "text-lg font-bold mt-3 mb-2";
  if (level === 2) return "text-base font-bold mt-3 mb-2 text-sky-600 dark:text-sky-400";
  return "text-sm font-semibold mt-2 mb-1";
}

export default function MarkdownLite({ text }) {
  const lines = (text || "").split("\n");
  const blocks = [];
  let buf = [];
  let listBuf = [];

  const flushPara = () => {
    if (!buf.length) return;
    blocks.push(
      <p key={blocks.length} className="my-2 leading-relaxed whitespace-pre-wrap">
        {inline(buf.join("\n"))}
      </p>
    );
    buf = [];
  };
  const flushList = () => {
    if (!listBuf.length) return;
    blocks.push(
      <ul key={`ul-${blocks.length}`} className="my-2 ml-5 list-disc space-y-1">
        {listBuf.map((li, i) => (
          <li key={`li-${i}-${li.slice(0, 12)}`} className="leading-relaxed">
            {inline(li)}
          </li>
        ))}
      </ul>
    );
    listBuf = [];
  };

  for (const raw of lines) {
    const l = raw.replace(/\r/g, "");
    if (/^#{1,3}\s/.test(l)) {
      flushPara(); flushList();
      const lvl = l.match(/^#+/)[0].length;
      const txt = l.replace(/^#+\s/, "");
      blocks.push(
        <div key={blocks.length} className={headingClass(lvl)}>{inline(txt)}</div>
      );
    } else if (/^\s*[-*]\s/.test(l)) {
      flushPara();
      listBuf.push(l.replace(/^\s*[-*]\s/, ""));
    } else if (l.trim() === "" || l.trim() === "---") {
      flushPara(); flushList();
    } else {
      flushList();
      buf.push(l);
    }
  }
  flushPara(); flushList();
  return <div>{blocks}</div>;
}
