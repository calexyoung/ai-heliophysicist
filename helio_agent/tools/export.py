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

# Client-side wiring for the three block types the convert API passes through
# as code. CDN versions pinned WITH SRI hashes (sha384 of the exact files,
# verified 2026-09-02) so a compromised CDN cannot alter the page.
_RUNTIME = """
<script src="https://cdnjs.cloudflare.com/ajax/libs/mermaid/11.12.1/mermaid.min.js" integrity="sha384-LlKSgo4Eo5GuF/ZrstLti44dE+GC5XAJ7TSu0Nw9Q3vIZF2QMnkRcK7BUoLabYLF" crossorigin="anonymous"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.5.1/chart.umd.min.js" integrity="sha384-jb8JQMbMoBUzgWatfe6COACi2ljcDdZQ2OxczGA3bGNeWe+6DChMTBJemed7ZnvJ" crossorigin="anonymous"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.18/katex.min.css" integrity="sha384-veTAhWILPOotXm+kbR5uY7dRamYLJf58I7P+hJhjeuc7hsMAkJHTsPahAl0hBST0" crossorigin="anonymous">
<script src="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.18/katex.min.js" integrity="sha384-v6mkHYHfY/4BWq54f7lQAdtIsoZZIByznQ3ZqN38OL4KCsrxo31SLlPiak7cj/Mg" crossorigin="anonymous"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.18/contrib/auto-render.min.js" integrity="sha384-hCXGrW6PitJEwbkoStFjeJxv+fSOOQKOPbJxSfM6G5sWZjAyWhXiTIIAmQqnlLlh" crossorigin="anonymous"></script>
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
                out_name: str | None = None) -> dict:
    """Export a markdown file as a standalone, self-hostable HTML page.

    Applies an unmarkdown visual template (default: 'research', the
    analysis-note standard — see skills/tools/analysis_notes.md) with all
    styles inlined, and wires Mermaid, KaTeX, and Chart.js to render
    client-side. The file needs no unmarkdown.com hosting: serve it from any
    web server or open it locally (external CDN scripts require network).

    Requires UNMARKDOWN_API_KEY in the environment/.env; refuses without it.
    """
    import re

    import requests

    key = os.environ.get("UNMARKDOWN_API_KEY")
    if not key:
        return {"status": "error",
                "error": "refusing: UNMARKDOWN_API_KEY not set (.env); "
                         "the template conversion runs through the unmarkdown API"}
    try:
        md = open(markdown_file).read()
    except OSError as exc:
        return {"status": "error", "error": f"refusing: cannot read {markdown_file}: {exc}"}

    r = requests.post(_API, timeout=120,
                      headers={"Authorization": f"Bearer {key}",
                               "Content-Type": "application/json"},
                      json={"markdown": md, "template_id": template_id,
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
        f"{_RUNTIME}\n</head>\n<body>\n<main>\n{body}\n</main>\n</body>\n</html>\n"
    )
    fname = out_name or markdown_file.rsplit("/", 1)[-1].replace(".md", "") + ".html"
    if not fname.endswith(".html"):
        fname += ".html"
    fpath = output_path(fname)
    fpath.write_text(page)
    n_mermaid = len(re.findall(r"```mermaid", md))
    n_charts = len(re.findall(r"```chart", md))
    return {"file": str(fpath), "template_id": template_id,
            "theme_mode": theme_mode, "bytes": len(page),
            "client_rendered": {"mermaid_blocks": n_mermaid,
                                "chart_blocks": n_charts,
                                "katex": "$...$ auto-render"},
            "note": "self-hosted page; CDN scripts need network at view time",
            "artifacts": [str(fpath)]}
