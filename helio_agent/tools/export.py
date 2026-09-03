"""Self-hosted HTML export: templated markdown without unmarkdown.com hosting.

Converts markdown through the unmarkdown API (template styles arrive fully
inlined) and wraps the result in a standalone page that renders Mermaid,
KaTeX, and Chart.js blocks client-side — the pieces the convert API leaves
as raw code. The output file works from any host or the local filesystem.
See skills/tools/analysis_notes.md.
"""

from __future__ import annotations

import json
import os

from helio_agent.registry import tool
from helio_agent.workspace import output_path

_API = "https://api.unmarkdown.com/v1/convert"

# Rendering libraries: CDN versions pinned WITH SRI hashes (sha384 of the
# exact files, verified 2026-09-02) so a compromised CDN cannot alter the
# page. With embed_assets the same files are downloaded (through the shared
# HTTP cache), hash-VERIFIED against these pins, and inlined for offline use.
_ASSETS = [
    ("script", "https://cdnjs.cloudflare.com/ajax/libs/mermaid/11.12.1/mermaid.min.js",
     "sha384-LlKSgo4Eo5GuF/ZrstLti44dE+GC5XAJ7TSu0Nw9Q3vIZF2QMnkRcK7BUoLabYLF"),
    ("script", "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.5.1/chart.umd.min.js",
     "sha384-jb8JQMbMoBUzgWatfe6COACi2ljcDdZQ2OxczGA3bGNeWe+6DChMTBJemed7ZnvJ"),
    ("style", "https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.18/katex.min.css",
     "sha384-veTAhWILPOotXm+kbR5uY7dRamYLJf58I7P+hJhjeuc7hsMAkJHTsPahAl0hBST0"),
    ("script", "https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.18/katex.min.js",
     "sha384-v6mkHYHfY/4BWq54f7lQAdtIsoZZIByznQ3ZqN38OL4KCsrxo31SLlPiak7cj/Mg"),
    ("script", "https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.18/contrib/auto-render.min.js",
     "sha384-hCXGrW6PitJEwbkoStFjeJxv+fSOOQKOPbJxSfM6G5sWZjAyWhXiTIIAmQqnlLlh"),
]


def _asset_tags_cdn() -> str:
    tags = []
    for kind, url, sri in _ASSETS:
        if kind == "style":
            tags.append(f'<link rel="stylesheet" href="{url}" integrity="{sri}" '
                        'crossorigin="anonymous">')
        else:
            tags.append(f'<script src="{url}" integrity="{sri}" '
                        'crossorigin="anonymous"></script>')
    return "\n".join(tags)


def _asset_tags_embedded() -> str:
    """Download each pinned asset (shared HTTP cache), verify its sha384
    against the SRI pin, and inline it. Raises on any hash mismatch."""
    import base64
    import hashlib

    from helio_agent.http import cached_get

    tags = []
    for kind, url, sri in _ASSETS:
        r = cached_get(url, timeout=120)
        r.raise_for_status()
        digest = "sha384-" + base64.b64encode(
            hashlib.sha384(r.content).digest()).decode()
        if digest != sri:
            raise RuntimeError(f"integrity mismatch for {url}: got {digest}")
        body = r.content.decode("utf-8")
        if kind == "style":
            # KaTeX css references fonts/... relatively; point them at the CDN
            # so online viewers get real fonts (offline falls back gracefully).
            body = body.replace("url(fonts/",
                                "url(https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.18/fonts/")
            tags.append(f"<style>\n{body}\n</style>")
        else:
            tags.append(f"<script>\n{body}\n</script>")
    return "\n".join(tags)


# Local publication stylesheet for engine="local" (no unmarkdown.com at
# all). Our own look, cousin to the 'research' template: DM Sans if the
# viewer has it / webfont when online, honest system fallbacks otherwise.
_LOCAL_CSS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=DM+Mono&display=swap">
<style>
main { font-family: "DM Sans", -apple-system, "Segoe UI", sans-serif;
       font-size: 16px; line-height: 1.65; }
h1 { font-size: 1.9em; font-weight: 700; line-height: 1.25; margin: 0.8em 0 0.4em; }
h2 { font-size: 1.35em; font-weight: 700; margin: 1.6em 0 0.5em; }
h3 { font-size: 1.1em; font-weight: 700; margin: 1.3em 0 0.4em; }
p, li { margin: 0 0 0.9em; }
a { color: #0072B2; text-underline-offset: 2px; }
code { font-family: "DM Mono", ui-monospace, monospace; font-size: 0.875em;
       background: rgba(2,132,199,0.08); padding: 0.12em 0.35em; border-radius: 4px; }
pre { background: #0f172a; color: #e2e8f0; padding: 1em; border-radius: 8px;
      overflow-x: auto; }
pre code { background: none; padding: 0; color: inherit; }
blockquote { border-left: 4px solid #0072B2; margin: 1em 0; padding: 0.2em 1em;
             color: inherit; opacity: 0.9; background: rgba(2,132,199,0.05); }
table { border-collapse: collapse; width: 100%; margin: 1.2em 0; font-size: 0.95em; }
th, td { border: 1px solid rgba(100,116,139,0.4); padding: 0.55em 0.7em;
         text-align: left; }
th { font-weight: 700; }
hr { border: none; border-top: 1px solid rgba(100,116,139,0.4); margin: 2em 0; }
</style>
"""


def _local_convert(md: str) -> str:
    """Markdown -> HTML entirely locally (markdown-it-py, CommonMark+GFM
    tables/strikethrough). Fenced blocks keep language-<x> classes so the
    client runtime can render mermaid/chart blocks."""
    from markdown_it import MarkdownIt

    parser = MarkdownIt("commonmark", {"html": False, "linkify": False})
    parser.enable(["table", "strikethrough"])
    return parser.render(md)


_RUNTIME = """
<script>
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll("code").forEach(function (code) {
    var lang = (code.className.match(/language-([\\w.]+)/) || [])[1];
    var pre = code.closest("pre");
    if (!pre || !lang) return;
    var src = code.textContent;
    if (lang === "mermaid") {
      var d = document.createElement("pre");
      d.className = "mermaid";
      d.textContent = src;
      d.style.background = "transparent";
      pre.replaceWith(d);
    } else if (lang === "chart" || lang === "chartjs" || lang === "chart.js") {
      try {
        var cfg = JSON.parse(src);
        var wrap = document.createElement("div");
        wrap.style.maxWidth = "760px";
        wrap.style.margin = "1.5em auto";
        var canvas = document.createElement("canvas");
        wrap.appendChild(canvas);
        pre.replaceWith(wrap);
        new Chart(canvas, cfg);
      } catch (e) { /* leave the code block visible on bad JSON */ }
    }
  });
  if (window.mermaid) mermaid.initialize({ startOnLoad: true, theme: "neutral" });
  if (window.renderMathInElement) renderMathInElement(document.body, {
    delimiters: [{left: "$$", right: "$$", display: true},
                 {left: "$", right: "$", display: false}]
  });
});
</script>
"""


@tool(family="report")
def export_html(markdown_file: str, template_id: str = "research",
                theme_mode: str = "light", title: str | None = None,
                embed_assets: bool = False, engine: str = "unmarkdown",
                out_name: str | None = None) -> dict:
    """Export a markdown file as a standalone, self-hostable HTML page.

    Applies an unmarkdown visual template (default: 'research', the
    analysis-note standard — see skills/tools/analysis_notes.md) with all
    styles inlined, and wires Mermaid, KaTeX, and Chart.js to render
    client-side. The file needs no unmarkdown.com hosting: serve it from any
    web server or open it locally.

    embed_assets=False (default): rendering libraries load from SRI-pinned
    CDNs — small file, network needed at view time. embed_assets=True:
    the libraries are downloaded once (shared HTTP cache), each verified
    against its pinned sha384, and inlined — a ~4 MB fully-offline page
    (KaTeX fonts still prefer the CDN when online; offline math falls back
    to system fonts).

    engine: "unmarkdown" (default) applies a hosted visual template via the
    unmarkdown convert API (needs UNMARKDOWN_API_KEY); "local" converts
    entirely on this machine (markdown-it-py + the built-in publication
    stylesheet) — no unmarkdown.com involvement, no key, works offline
    end-to-end when combined with embed_assets=True. template_id is ignored
    for engine="local".
    """
    import re

    if engine not in ("unmarkdown", "local"):
        return {"status": "error",
                "error": "refusing: engine must be 'unmarkdown' or 'local'"}
    try:
        md = open(markdown_file).read()
    except OSError as exc:
        return {"status": "error", "error": f"refusing: cannot read {markdown_file}: {exc}"}

    local_css = ""
    if engine == "local":
        body = _local_convert(md)
        local_css = _LOCAL_CSS
        template_id = "local"
    else:
        key = os.environ.get("UNMARKDOWN_API_KEY")
        if not key:
            return {"status": "error",
                    "error": "refusing: UNMARKDOWN_API_KEY not set (.env); "
                             "use engine='local' for key-free offline conversion"}
        from helio_agent.http import cached_request
        r = cached_request(
            "POST", _API, timeout=120,
            headers={"Authorization": f"Bearer {key}",
                     "Content-Type": "application/json"},
            json_body={"markdown": md, "template_id": template_id,
                       "theme_mode": theme_mode, "destination": "generic"})
        if r.status_code != 200:
            return {"status": "error",
                    "error": f"unmarkdown convert failed ({r.status_code}): {r.text[:200]}"}
        body = r.json()["html"]

    if title is None:
        m = re.search(r"^#\s+(.+)$", md, re.MULTILINE)
        title = m.group(1).strip() if m else markdown_file.rsplit("/", 1)[-1]
    bg = "#0b1120" if theme_mode == "dark" else "#ffffff"
    fg = "#e2e8f0" if theme_mode == "dark" else "#0f172a"
    page = (
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        f"<title>{title}</title>\n"
        f"<style>body{{margin:0;background:{bg};color:{fg};}}"
        "main{max-width:860px;margin:0 auto;padding:2.5rem 1.25rem;}"
        "img{max-width:100%;}</style>\n"
        f"{local_css}"
        f"{_asset_tags_embedded() if embed_assets else _asset_tags_cdn()}\n"
        f"{_RUNTIME}\n</head>\n<body>\n<main>\n{body}\n</main>\n</body>\n</html>\n"
    )
    fname = out_name or markdown_file.rsplit("/", 1)[-1].replace(".md", "") + ".html"
    if not fname.endswith(".html"):
        fname += ".html"
    fpath = output_path(fname)
    fpath.write_text(page)
    n_mermaid = len(re.findall(r"```mermaid", md))
    n_charts = len(re.findall(r"```chart", md))
    return {"file": str(fpath), "engine": engine, "template_id": template_id,
            "theme_mode": theme_mode, "bytes": len(page),
            "assets": "embedded (offline-capable, hash-verified)"
                      if embed_assets else "CDN (SRI-pinned, network at view time)",
            "client_rendered": {"mermaid_blocks": n_mermaid,
                                "chart_blocks": n_charts,
                                "katex": "$...$ auto-render"},
            "note": ("fully self-contained page" if embed_assets else
                     "self-hosted page; CDN scripts need network at view time"),
            "artifacts": [str(fpath)]}
