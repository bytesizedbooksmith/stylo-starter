"""Standalone, escaped HTML reading views; no network or third-party dependencies."""
from html import escape
import re
from .guide_style import STYLE
ALIAS = {}
def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def rewrite_link(url):
    if re.match(r"(?i)^(javascript|data|vbscript):", url.strip()):
        return "#"
    if url.startswith(("http://", "https://", "#", "mailto:")):
        return url
    tail = url.split("/")[-1]
    name = tail.split("#")[0]
    anchor = tail[len(name):] if "#" in tail else ""
    if name in ALIAS:
        return ALIAS[name] + anchor
    return url  # leave other relative links (rare) as-is

def inline_basic(s):
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)   # bold (may contain italic)
    s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", s)
    return s

def inline(text):
    stash = {}
    def keep(html):
        k = f"\x00{len(stash)}\x00"
        stash[k] = html
        return k
    # code spans
    text = re.sub(r"`([^`]+)`", lambda m: keep("<code>" + esc(m.group(1)) + "</code>"), text)
    # links
    def link(m):
        label, url = m.group(1), m.group(2)
        return keep('<a href="' + esc(rewrite_link(url)) + '">' + inline_basic(label) + "</a>")
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, text)
    # escape the rest, then bold/italic
    text = esc(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)   # bold (may contain italic)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    # restore placeholders — loop to resolve nesting (e.g. a code span inside a link label)
    for _ in range(6):
        if "\x00" not in text:
            break
        for k, v in stash.items():
            text = text.replace(k, v)
    return text

def split_row(line):
    line = line.strip()
    if line.startswith("|"): line = line[1:]
    if line.endswith("|"): line = line[:-1]
    return [c.strip() for c in line.split("|")]

def render_table(header, rows):
    out = ["<table>", "<thead><tr>"]
    out += [f"<th>{inline(c)}</th>" for c in header]
    out.append("</tr></thead><tbody>")
    for r in rows:
        out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>")
    out.append("</tbody></table>")
    return "".join(out)

def indent_of(s):
    return len(s) - len(s.lstrip())

def render_list(block):
    def parse(lines, idx, indent):
        ordered = bool(re.match(r"^\s*\d+\.\s", lines[idx]))
        tag = "ol" if ordered else "ul"
        items = []
        while idx < len(lines):
            ln = lines[idx]
            if ln.strip() == "":
                idx += 1; continue
            ci = indent_of(ln)
            if ci < indent:
                break
            if ci == indent and re.match(r"^\s*([-*]|\d+\.)\s+", ln):
                content = re.sub(r"^\s*([-*]|\d+\.)\s+", "", ln).strip()
                # collect deeper-indented lines as nested
                nested = []
                j = idx + 1
                while j < len(lines):
                    if lines[j].strip() == "":
                        nested.append(lines[j]); j += 1; continue
                    if indent_of(lines[j]) > indent:
                        nested.append(lines[j]); j += 1
                    else:
                        break
                li = "<li>" + inline(content)
                real_nested = [x for x in nested if x.strip()]
                if real_nested:
                    inner, _ = parse(real_nested, 0, indent_of(real_nested[0]))
                    li += inner
                li += "</li>"
                items.append(li)
                idx = j
            else:
                break
        return f"<{tag}>" + "".join(items) + f"</{tag}>", idx
    html, _ = parse(block, 0, indent_of(block[0]))
    return html

def is_block_start(line):
    s = line.strip()
    return (line.lstrip().startswith("```") or s.startswith("#")
            or re.match(r"^\s*([-*]|\d+\.)\s+", line) or s.startswith(">")
            or re.match(r"^\s*(---|\*\*\*)\s*$", line) or s == "")

def convert(md):
    lines = md.split("\n")
    out, i, n = [], 0, len(lines)
    while i < n:
        line = lines[i]
        if line.lstrip().startswith("```"):
            i += 1; buf = []
            while i < n and not lines[i].lstrip().startswith("```"):
                buf.append(lines[i]); i += 1
            i += 1
            out.append("<pre><code>" + esc("\n".join(buf)) + "</code></pre>")
            continue
        if line.strip() == "":
            i += 1; continue
        if re.match(r"^\s*(---|\*\*\*)\s*$", line):
            out.append("<hr>"); i += 1; continue
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            lvl = len(m.group(1))
            out.append(f"<h{lvl}>{inline(m.group(2).strip())}</h{lvl}>"); i += 1; continue
        if "|" in line and i + 1 < n and re.match(r"^\s*\|?[\s:|-]*-[\s:|-]*\|?\s*$", lines[i + 1]) and "|" in lines[i + 1]:
            header = split_row(line); i += 2; rows = []
            while i < n and "|" in lines[i] and lines[i].strip():
                rows.append(split_row(lines[i])); i += 1
            out.append(render_table(header, rows)); continue
        if re.match(r"^\s*>", line):
            buf = []
            while i < n and re.match(r"^\s*>", lines[i]):
                buf.append(re.sub(r"^\s*>\s?", "", lines[i])); i += 1
            out.append("<blockquote>" + convert("\n".join(buf)) + "</blockquote>"); continue
        if re.match(r"^\s*([-*]|\d+\.)\s+", line):
            block = []
            while i < n and (re.match(r"^\s*([-*]|\d+\.)\s+", lines[i]) or
                             (lines[i].startswith("  ") and lines[i].strip())):
                block.append(lines[i]); i += 1
            out.append(render_list(block)); continue
        buf = [line]; i += 1
        while i < n and not is_block_start(lines[i]):
            buf.append(lines[i]); i += 1
        out.append("<p>" + inline(" ".join(b.strip() for b in buf)) + "</p>")
    return "\n".join(out)

# ---------------------------------------------------------------------------
# Page shell + navigation
# ---------------------------------------------------------------------------



def markdown_html(text):
    # Frontmatter is metadata for AI, not part of the human reading experience.
    text = re.sub(r"\A---\s*\n.*?\n---\s*\n", "", text, count=1, flags=re.S)
    return convert(text).replace("<table>", '<div class="table-scroll"><table>').replace("</table>", "</table></div>")

def page(title, body):
    extra = """
    body{display:block}.content{max-width:1040px;margin:auto}
    .table-scroll{overflow:auto;max-width:100%}
    .reading p{font-family:Georgia,serif}
    .facts{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px}
    .fact{padding:18px;background:var(--pale);border-radius:10px}.fact strong{display:block;font-size:25px}
    .metric-note{font:13px/1.55 system-ui,sans-serif;color:var(--muted)}
    """
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+escape(title)+' · Stylo</title><style>'+STYLE+extra+'</style></head><body><main class="content" id="main">'+body+'<footer class="pagefoot">Stylo Starter · Angie Hartwell / Byte-Sized Booksmith<br>Counts describe these samples. Your reading and creative choices matter.</footer></main></body></html>'

def markdown_page(title,text):
    return page(title,markdown_html(text))


def audit_page(result, profile):
    body='<p class="eyebrow">Optional profile comparison</p><h1>A few differences to explore.</h1>'
    body+='<p class="lede">This passage was compared with '+escape(profile.name)+'. A difference may be intentional; there is no requirement to make every measurement match.</p>'
    body+='<p>'+str(result.words)+' words · '+str(result.paragraphs)+' paragraphs. This is a structural comparison, not a judgment of the scene.</p>'
    if result.warnings:
        body+='<details open><summary>Context for this comparison</summary><ul>'+''.join('<li>'+escape(w)+'</li>' for w in result.warnings)+'</ul></details>'
    body+='<h2>Places to look, if useful</h2>'
    if not result.drifts:
        body+='<p>No differences were flagged by these settings. That does not establish writing quality or authorship.</p>'
    from .features import REGISTRY
    for drift in result.drifts[:3]:
        metric=REGISTRY[drift.key]
        body+='<div class="welcome"><h3>'+escape(drift.label)+'</h3><p>This passage: '+escape(metric.format(drift.draft))+'. Reference middle range: '+escape(metric.format(drift.lane_low))+'–'+escape(metric.format(drift.lane_high))+'.</p><p>Consider whether the scene calls for this difference before changing anything.</p></div>'
    if result.locations:
        body+='<details><summary>Passages to look at</summary><ul>'+''.join('<li>'+escape((x.where or "Throughout")+": "+x.detail)+'</li>' for x in result.locations)+'</ul></details>'
    body+='<details><summary>All flagged measurements</summary><div class="table-scroll"><table><thead><tr><th>Measure</th><th>This passage</th><th>Reference middle range</th><th>Method</th></tr></thead><tbody>'
    for d in result.drifts:
        m=REGISTRY[d.key]
        body+='<tr><td>'+escape(d.label)+'</td><td>'+escape(m.format(d.draft))+'</td><td>'+escape(m.format(d.lane_low)+'–'+m.format(d.lane_high))+'</td><td>'+escape(d.reliability)+'</td></tr>'
    body+='</tbody></table></div></details><p>You can keep the original, try one change on a copy, or stop here. The detailed AI report contains possible experiments, not approved edits.</p>'
    return page("Profile comparison",body)
