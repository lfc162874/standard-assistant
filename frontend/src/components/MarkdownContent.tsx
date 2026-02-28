function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function sanitizeUrl(url: string): string {
  const trimmed = url.trim();
  if (/^https?:\/\//i.test(trimmed)) return trimmed;
  if (trimmed.startsWith("/")) return trimmed;
  return "#";
}

function formatInline(text: string): string {
  let escaped = escapeHtml(text);

  escaped = escaped.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_, label: string, url: string) => {
    const safeUrl = sanitizeUrl(url);
    return `<a href="${escapeHtml(safeUrl)}" target="_blank" rel="noreferrer">${label}</a>`;
  });
  escaped = escaped.replace(/`([^`]+)`/g, "<code>$1</code>");
  escaped = escaped.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  escaped = escaped.replace(/\*([^*]+)\*/g, "<em>$1</em>");
  escaped = escaped.replace(/~~([^~]+)~~/g, "<del>$1</del>");

  return escaped;
}

function isSpecialLine(line: string): boolean {
  const trimmed = line.trim();
  if (!trimmed) return true;
  if (/^```/.test(trimmed)) return true;
  if (/^#{1,4}\s+/.test(trimmed)) return true;
  if (/^>\s?/.test(trimmed)) return true;
  if (/^[-*+]\s+/.test(trimmed)) return true;
  if (/^\d+\.\s+/.test(trimmed)) return true;
  if (/^[-*_]{3,}$/.test(trimmed)) return true;
  return false;
}

function parseTableRow(line: string): string[] {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => formatInline(cell.trim()));
}

function renderMarkdownToHtml(markdown: string): string {
  const lines = markdown.replace(/\r\n/g, "\n").split("\n");
  const html: string[] = [];
  const paragraphBuffer: string[] = [];
  let i = 0;

  const flushParagraph = () => {
    if (!paragraphBuffer.length) return;
    html.push(`<p>${formatInline(paragraphBuffer.join(" ").trim())}</p>`);
    paragraphBuffer.length = 0;
  };

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();

    if (!trimmed) {
      flushParagraph();
      i += 1;
      continue;
    }

    if (/^```/.test(trimmed)) {
      flushParagraph();
      const language = trimmed.slice(3).trim();
      i += 1;
      const code: string[] = [];

      while (i < lines.length && !/^```/.test(lines[i].trim())) {
        code.push(lines[i]);
        i += 1;
      }

      if (i < lines.length) i += 1;

      const langClass = language ? ` class="language-${escapeHtml(language)}"` : "";
      html.push(`<pre><code${langClass}>${escapeHtml(code.join("\n"))}</code></pre>`);
      continue;
    }

    const heading = trimmed.match(/^(#{1,4})\s+(.*)$/);
    if (heading) {
      flushParagraph();
      const level = heading[1].length;
      html.push(`<h${level}>${formatInline(heading[2])}</h${level}>`);
      i += 1;
      continue;
    }

    if (/^[-*_]{3,}$/.test(trimmed)) {
      flushParagraph();
      html.push("<hr />");
      i += 1;
      continue;
    }

    if (/^>\s?/.test(trimmed)) {
      flushParagraph();
      const quoteLines: string[] = [];
      while (i < lines.length && /^>\s?/.test(lines[i].trim())) {
        quoteLines.push(lines[i].trim().replace(/^>\s?/, ""));
        i += 1;
      }
      html.push(`<blockquote>${formatInline(quoteLines.join("\n"))}</blockquote>`);
      continue;
    }

    if (/^\|?.+\|.+\|?$/.test(trimmed) && i + 1 < lines.length && /^[\s|:-]+$/.test(lines[i + 1].trim())) {
      flushParagraph();
      const headerCells = parseTableRow(lines[i]);
      i += 2;
      const rows: string[][] = [];

      while (i < lines.length && /\|/.test(lines[i])) {
        rows.push(parseTableRow(lines[i]));
        i += 1;
      }

      const thead = `<thead><tr>${headerCells.map((cell) => `<th>${cell}</th>`).join("")}</tr></thead>`;
      const tbodyRows = rows
        .map((row) => `<tr>${row.map((cell) => `<td>${cell}</td>`).join("")}</tr>`)
        .join("");
      html.push(`<table>${thead}<tbody>${tbodyRows}</tbody></table>`);
      continue;
    }

    if (/^[-*+]\s+/.test(trimmed)) {
      flushParagraph();
      const items: string[] = [];
      while (i < lines.length && /^[-*+]\s+/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^[-*+]\s+/, ""));
        i += 1;
      }
      html.push(`<ul>${items.map((item) => `<li>${formatInline(item)}</li>`).join("")}</ul>`);
      continue;
    }

    if (/^\d+\.\s+/.test(trimmed)) {
      flushParagraph();
      const items: string[] = [];
      while (i < lines.length && /^\d+\.\s+/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^\d+\.\s+/, ""));
        i += 1;
      }
      html.push(`<ol>${items.map((item) => `<li>${formatInline(item)}</li>`).join("")}</ol>`);
      continue;
    }

    paragraphBuffer.push(line.trim());

    if (i + 1 < lines.length && isSpecialLine(lines[i + 1])) {
      flushParagraph();
    }
    i += 1;
  }

  flushParagraph();
  return html.join("");
}

interface MarkdownContentProps {
  markdown: string;
}

export default function MarkdownContent({ markdown }: MarkdownContentProps) {
  const html = renderMarkdownToHtml(markdown);
  return <div dangerouslySetInnerHTML={{ __html: html }} />;
}
