"""Literature: NASA ADS search and arXiv retrieval.

ADS needs an API token in the ADS_API_TOKEN environment variable
(free from https://ui.adsabs.harvard.edu/user/settings/token).
arXiv needs nothing.
"""

from __future__ import annotations

import os
import re

from helio_agent.http import cached_get, cached_request
from helio_agent.registry import tool
from helio_agent.workspace import data_path

_UA = {"User-Agent": "helio-agent/0.1 (AI Heliophysicist)"}


@tool(family="literature")
def search_ads(query: str, max_results: int = 10, sort: str = "citation_count desc") -> dict:
    """Search NASA ADS. query uses ADS syntax, e.g.
    'GX 339-4 outburst', 'author:"Gopalswamy" year:2004-2006 CME',
    'full:"superposed epoch" abs:"solar wind"'.
    """
    token = os.environ.get("ADS_API_TOKEN")
    if not token:
        return {"status": "error",
                "error": "ADS_API_TOKEN not set; get a free token at "
                         "https://ui.adsabs.harvard.edu/user/settings/token"}
    r = cached_get("https://api.adsabs.harvard.edu/v1/search/query",
                   params={"q": query, "rows": max_results, "sort": sort,
                           "fl": "bibcode,title,author,year,pub,citation_count,abstract,identifier"},
                   headers={"Authorization": f"Bearer {token}"}, timeout=60)
    r.raise_for_status()
    docs = r.json()["response"]["docs"]
    papers = []
    for d in docs:
        arxiv = next((i.split(":")[-1] for i in d.get("identifier", [])
                      if i.startswith("arXiv:")), None)
        papers.append({"bibcode": d.get("bibcode"),
                       "title": (d.get("title") or [""])[0],
                       "first_author": (d.get("author") or [""])[0],
                       "year": d.get("year"), "pub": d.get("pub"),
                       "citations": d.get("citation_count"),
                       "arxiv_id": arxiv,
                       "abstract": (d.get("abstract") or "")[:600]})
    return {"n_results": len(papers), "papers": papers}


@tool(family="literature")
def get_bibtex(bibcodes: list[str]) -> dict:
    """Fetch BibTeX entries from ADS for a list of bibcodes."""
    token = os.environ.get("ADS_API_TOKEN")
    if not token:
        return {"status": "error", "error": "ADS_API_TOKEN not set"}
    r = cached_request(
        "POST", "https://api.adsabs.harvard.edu/v1/export/bibtex",
        json_body={"bibcode": bibcodes},
        headers={**_UA, "Authorization": f"Bearer {token}"}, timeout=60)
    r.raise_for_status()
    return {"bibtex": r.json()["export"]}


@tool(family="literature")
def search_arxiv(query: str, max_results: int = 10, category: str = "astro-ph.SR") -> dict:
    """Search arXiv (no key needed). category astro-ph.SR = solar/stellar;
    physics.space-ph = space physics."""
    import defusedxml.ElementTree as ET
    q = f"cat:{category} AND all:{query}" if category else f"all:{query}"
    r = cached_get("https://export.arxiv.org/api/query",
                     params={"search_query": q, "max_results": max_results,
                             "sortBy": "relevance"}, timeout=60)
    r.raise_for_status()
    ns = {"a": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(r.text)
    papers = []
    for entry in root.findall("a:entry", ns):
        aid = entry.findtext("a:id", "", ns).rsplit("/abs/", 1)[-1]
        papers.append({
            "arxiv_id": aid,
            "title": re.sub(r"\s+", " ", entry.findtext("a:title", "", ns)).strip(),
            "first_author": entry.findtext("a:author/a:name", "", ns),
            "published": entry.findtext("a:published", "", ns)[:10],
            "summary": re.sub(r"\s+", " ", entry.findtext("a:summary", "", ns)).strip()[:600],
        })
    return {"n_results": len(papers), "papers": papers}


@tool(family="literature")
def fetch_arxiv_pdf(arxiv_id: str) -> dict:
    """Download an arXiv paper PDF into the workspace for reading."""
    r = cached_get(f"https://arxiv.org/pdf/{arxiv_id}", timeout=120)
    r.raise_for_status()
    fpath = data_path(f"arxiv_{arxiv_id.replace('/', '_')}.pdf")
    fpath.write_bytes(r.content)
    return {"file": str(fpath), "bytes": len(r.content), "artifacts": [str(fpath)]}
