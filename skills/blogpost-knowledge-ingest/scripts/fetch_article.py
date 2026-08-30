#!/usr/bin/env python3
"""
fetch_article.py - dependency-free article fetcher, extractor, and deep-linker.

Standard library only (Python 3.8+). No pip install, no readability, no bs4.

WHY THIS EXISTS
    A YouTube transcript hands you `?t=742` for free: every claim is traceable
    to the second it was said. Prose has no such coordinate. This script
    manufactures one.

    For every block of the article it emits a deep link, choosing the most
    durable form available:

      1. `url#heading-id`      - when the page's own HTML gives the enclosing
                                 heading an id. Stable, survives edits.
      2. `url#:~:text=a,b`     - a W3C text fragment built from the block's own
                                 first and last words. Chrome/Edge/Safari scroll
                                 to it and highlight it. Breaks only if the
                                 author rewrites that sentence, which is exactly
                                 when you want to know.

    Every block also carries a paragraph ordinal (P12) so a citation still
    means something after both mechanisms rot.

USAGE
    python3 fetch_article.py <url> [options]

    --json PATH    write the full structured record as JSON
    --md PATH      write the readable article as markdown
    --min-words N  drop candidate containers below N words (default 120)
    --raw          skip main-content detection, convert the whole body
    --debug        report extraction decisions and scores
    --quiet        suppress the stderr summary

    With neither --json nor --md, the markdown goes to stdout.

OUTPUT (JSON)
    {
      "url", "canonical_url", "title", "author", "site_name",
      "published", "modified", "retrieved", "description",
      "word_count", "reading_minutes", "paywall_suspected", "js_shell_suspected",
      "headings":  [{"level","text","id","block"}],
      "blocks":    [{"n","kind","section","section_id","text","code_lang",
                     "url","anchor_kind"}],
      "outbound_links": [{"text","href","block"}]
    }

EXIT CODES
    0 ok   1 bad input / network   2 fetched but no article text found
"""

import argparse
import datetime as _dt
import gzip
import html as _html
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zlib
from html.parser import HTMLParser

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

DEBUG = []


def note(msg):
    DEBUG.append(msg)


# ---------------------------------------------------------------- fetching

def fetch(url, timeout=30):
    if not re.match(r"^https?://", url):
        url = "https://" + url
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        enc = (r.headers.get("Content-Encoding") or "").lower()
        final_url = r.geturl()
        ctype = r.headers.get("Content-Type") or ""
    if "gzip" in enc:
        raw = gzip.decompress(raw)
    elif "deflate" in enc:
        try:
            raw = zlib.decompress(raw)
        except zlib.error:
            raw = zlib.decompress(raw, -zlib.MAX_WBITS)
    note("fetched %s (%d bytes, %s)" % (final_url, len(raw), ctype))
    return raw, final_url, ctype


def decode_html(raw, ctype):
    charset = "utf-8"
    m = re.search(r"charset=([\w-]+)", ctype, re.I)
    if m:
        charset = m.group(1)
    else:
        m = re.search(rb'charset=["\']?([\w-]+)', raw[:4096], re.I)
        if m:
            charset = m.group(1).decode("ascii", "ignore")
    return raw.decode(charset, "replace")


# ---------------------------------------------------------------- tiny DOM

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr"}
DROP = {"script", "style", "noscript", "svg", "canvas", "iframe", "form",
        "button", "select", "textarea", "nav", "footer", "header", "aside",
        "template", "video", "audio"}
# Class/id substrings that mark furniture rather than article prose.
JUNK = re.compile(
    r"(^|[-_ ])(nav|menu|sidebar|side-bar|footer|header|masthead|comment|"
    r"disqus|share|sharing|social|subscribe|newsletter|signup|promo|banner|"
    r"advert|\bad\b|ads|sponsor|related|recirc|recommend|popular|trending|"
    r"breadcrumb|pagination|paginate|cookie|consent|modal|popup|toolbar|"
    r"author-bio|bio-box|tags?-list|meta-info|skip-link|toc|table-of-contents)"
    r"([-_ ]|$)", re.I)


class Node:
    __slots__ = ("tag", "attrs", "children", "parent", "text")

    def __init__(self, tag, attrs=None, parent=None):
        self.tag = tag
        self.attrs = attrs or {}
        self.children = []
        self.parent = parent
        self.text = ""

    def is_text(self):
        return self.tag == "#text"

    def inner_text(self):
        if self.is_text():
            return self.text
        return "".join(c.inner_text() for c in self.children)

    def find_all(self, tags):
        out = []
        for c in self.children:
            if c.tag in tags:
                out.append(c)
            out.extend(c.find_all(tags))
        return out


class DOM(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root")
        self.cur = self.root
        self.skip_depth = 0
        self.skip_tag = None

    def handle_starttag(self, tag, attrs):
        if self.skip_depth:
            if tag == self.skip_tag and tag not in VOID:
                self.skip_depth += 1
            return
        if tag in DROP:
            if tag not in VOID:
                self.skip_depth = 1
                self.skip_tag = tag
            return
        node = Node(tag, dict(attrs), self.cur)
        self.cur.children.append(node)
        if tag not in VOID:
            self.cur = node

    def handle_startendtag(self, tag, attrs):
        if self.skip_depth or tag in DROP:
            return
        self.cur.children.append(Node(tag, dict(attrs), self.cur))

    def handle_endtag(self, tag):
        if self.skip_depth:
            if tag == self.skip_tag:
                self.skip_depth -= 1
                if not self.skip_depth:
                    self.skip_tag = None
            return
        if tag in VOID:
            return
        n = self.cur
        while n is not self.root:
            if n.tag == tag:
                self.cur = n.parent
                return
            n = n.parent
        # stray close tag: ignore

    def handle_data(self, data):
        if self.skip_depth or not data.strip():
            return
        t = Node("#text", parent=self.cur)
        t.text = data
        self.cur.children.append(t)


# ---------------------------------------------------------------- metadata

def meta_map(doc):
    out = {}
    for m in doc.find_all({"meta"}):
        key = (m.attrs.get("property") or m.attrs.get("name")
               or m.attrs.get("itemprop") or "").lower()
        val = m.attrs.get("content")
        if key and val and key not in out:
            out[key] = _html.unescape(val).strip()
    return out


def json_ld(page_html):
    """Pull author/date out of JSON-LD, which most CMSes emit."""
    found = {}
    for m in re.finditer(
            r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            page_html, re.S | re.I):
        try:
            data = json.loads(m.group(1).strip())
        except Exception:
            continue
        stack = [data]
        while stack:
            d = stack.pop()
            if isinstance(d, list):
                stack.extend(d)
                continue
            if not isinstance(d, dict):
                continue
            stack.extend(v for v in d.values() if isinstance(v, (dict, list)))
            a = d.get("author")
            if a and "author" not in found:
                if isinstance(a, list):
                    a = a[0]
                if isinstance(a, dict):
                    a = a.get("name")
                if isinstance(a, str):
                    found["author"] = a.strip()
            for src, dst in (("datePublished", "published"),
                             ("dateModified", "modified")):
                if d.get(src) and dst not in found and isinstance(d[src], str):
                    found[dst] = d[src].strip()
            if d.get("headline") and "title" not in found and isinstance(d["headline"], str):
                found["title"] = d["headline"].strip()
    return found


def pick_title(doc, meta, ld):
    for k in ("og:title", "twitter:title"):
        if meta.get(k):
            return meta[k]
    if ld.get("title"):
        return ld["title"]
    for h in doc.find_all({"h1"}):
        t = norm(h.inner_text())
        if t:
            return t
    for t in doc.find_all({"title"}):
        return norm(t.inner_text())
    return ""


def pick_author(doc, meta, ld):
    for k in ("author", "article:author", "byl", "parsely-author"):
        v = meta.get(k)
        if v and not v.startswith("http"):
            return v
    if ld.get("author"):
        return ld["author"]
    if meta.get("twitter:creator"):
        return meta["twitter:creator"]
    for n in doc.find_all({"a", "span", "div", "p"}):
        blob = " ".join([n.attrs.get("class", ""), n.attrs.get("id", ""),
                         n.attrs.get("rel", "")])
        if re.search(r"(^|[-_ ])(author|byline|byl)([-_ ]|$)", blob, re.I):
            t = norm(n.inner_text())
            t = re.sub(r"^(by|written by|posted by)\s+", "", t, flags=re.I)
            if 2 < len(t) < 80:
                return t
    return ""


# ---------------------------------------------------------------- scoring

def norm(s):
    return re.sub(r"\s+", " ", _html.unescape(s or "")).strip()


def words(s):
    return len(s.split())


def junky(node):
    blob = " ".join([node.attrs.get("class", ""), node.attrs.get("id", ""),
                     node.attrs.get("role", "")])
    return bool(JUNK.search(blob))


def score(node):
    """Reward containers dense in real paragraph prose, penalise link farms."""
    paras = node.find_all({"p"})
    body = sum(words(norm(p.inner_text())) for p in paras)
    if body == 0:
        return 0.0
    link_words = sum(words(norm(a.inner_text())) for a in node.find_all({"a"}))
    total = words(norm(node.inner_text())) or 1
    link_density = min(link_words / total, 1.0)
    s = body * (1.0 - 0.8 * link_density)
    blob = " ".join([node.attrs.get("class", ""), node.attrs.get("id", ""),
                     node.attrs.get("itemprop", "")])
    if re.search(r"(article|post|entry|content|story|markdown|prose|blog|"
                 r"main|body-?text|rich-?text)", blob, re.I):
        s *= 1.35
    if junky(node):
        s *= 0.25
    if node.tag == "article":
        s *= 1.5
    if node.tag == "main":
        s *= 1.25
    return s


def pick_main(doc, min_words, debug=False):
    cands = doc.find_all({"article", "main", "div", "section", "td"})
    ranked = []
    for c in cands:
        sc = score(c)
        if sc >= min_words:
            ranked.append((sc, c))
    if not ranked:
        return None
    ranked.sort(key=lambda x: -x[0])
    best_score, best = ranked[0]
    # Prefer the deepest node keeping >=88% of the winner's score: avoids
    # returning a wrapper that drags in sibling furniture.
    for sc, c in ranked:
        if sc >= 0.88 * best_score:
            d1 = depth(c)
            if d1 > depth(best):
                best, best_score = c, sc
    if debug:
        for sc, c in ranked[:6]:
            note("candidate <%s class=%r> score=%.0f" %
                 (c.tag, c.attrs.get("class", "")[:40], sc))
    return best


def depth(n):
    d = 0
    while n.parent:
        d += 1
        n = n.parent
    return d


# ---------------------------------------------------------------- inline md

def inline(node, links, block_n, base_url):
    if node.is_text():
        return re.sub(r"\s+", " ", _html.unescape(node.text))
    t = node.tag
    inner = "".join(inline(c, links, block_n, base_url) for c in node.children)
    if t in ("strong", "b"):
        return "**%s**" % inner.strip() if inner.strip() else ""
    if t in ("em", "i"):
        return "*%s*" % inner.strip() if inner.strip() else ""
    if t == "code":
        return "`%s`" % inner.strip() if inner.strip() else ""
    if t == "br":
        return " "
    if t == "a":
        href = node.attrs.get("href", "")
        txt = inner.strip()
        if href and txt and not href.startswith(("#", "javascript:", "mailto:")):
            absolute = urllib.parse.urljoin(base_url, href)
            links.append({"text": txt, "href": absolute, "block": block_n})
            return "[%s](%s)" % (txt, absolute)
        return txt
    if t == "img":
        alt = norm(node.attrs.get("alt", ""))
        return "![%s]" % alt if alt else ""
    return inner


# ---------------------------------------------------------------- deep links

def frag(base, text):
    """W3C text fragment: #:~:text=start,end - escaping -,& per the spec."""
    def enc(s):
        return urllib.parse.quote(s, safe="").replace("-", "%2D").replace("&", "%26")
    w = text.split()
    if len(w) < 8:
        return base + "#:~:text=" + enc(" ".join(w))
    return base + "#:~:text=" + enc(" ".join(w[:6])) + "," + enc(" ".join(w[-4:]))


def slug(s):
    s = re.sub(r"[^\w\s-]", "", s.lower()).strip()
    return re.sub(r"[\s_]+", "-", s)[:60]


# ---------------------------------------------------------------- extraction

BLOCK_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6", "p", "ul", "ol", "pre",
              "blockquote", "table", "dl", "figcaption", "hr"}


def walk_blocks(node, out):
    for c in node.children:
        if c.is_text():
            continue
        if c.tag in BLOCK_TAGS:
            out.append(c)
        elif c.tag == "li":
            continue
        else:
            walk_blocks(c, out)


def code_lang(node):
    blob = node.attrs.get("class", "")
    for c in node.find_all({"code"}):
        blob += " " + c.attrs.get("class", "")
    m = re.search(r"(?:language|lang|highlight)[-_]([\w+#]+)", blob, re.I)
    return m.group(1).lower() if m else ""


def extract(main, base_url):
    raw = []
    walk_blocks(main, raw)
    blocks, headings, links = [], [], []
    section, section_id, n = "", "", 0

    for el in raw:
        t = el.tag
        if t == "hr":
            continue
        if t == "pre":
            text = el.inner_text().rstrip()
            if not text.strip():
                continue
            n += 1
            blocks.append({"n": n, "kind": "code", "section": section,
                           "section_id": section_id, "text": text,
                           "plain": text, "code_lang": code_lang(el)})
            continue

        if t in ("ul", "ol"):
            items, plains = [], []
            for i, li in enumerate(c for c in el.children if c.tag == "li"):
                s = norm(inline(li, links, n + 1, base_url))
                if s:
                    items.append(("%d. %s" % (i + 1, s)) if t == "ol" else "- " + s)
                    plains.append(norm(li.inner_text()))
            if not items:
                continue
            n += 1
            for l in links:
                if l["block"] == n + 1:
                    l["block"] = n
            blocks.append({"n": n, "kind": "list", "section": section,
                           "section_id": section_id, "text": "\n".join(items),
                           "plain": " ".join(plains), "code_lang": ""})
            continue

        text = norm(inline(el, links, n + 1, base_url))
        plain = norm(el.inner_text())
        if not text:
            continue
        n += 1
        for l in links:
            if l["block"] == n + 1:
                l["block"] = n

        if t in ("h1", "h2", "h3", "h4", "h5", "h6"):
            hid = el.attrs.get("id", "")
            if not hid:
                for a in el.find_all({"a"}):
                    if a.attrs.get("id"):
                        hid = a.attrs["id"]
                        break
                    href = a.attrs.get("href", "")
                    if href.startswith("#") and slug(plain).startswith(slug(href[1:])[:8]):
                        hid = href[1:]
                        break
            section, section_id = plain, hid
            headings.append({"level": int(t[1]), "text": plain,
                             "id": hid, "block": n})
            blocks.append({"n": n, "kind": "heading", "level": int(t[1]),
                           "section": plain, "section_id": hid,
                           "text": plain, "plain": plain, "code_lang": ""})
            continue

        kind = {"blockquote": "quote", "table": "table",
                "figcaption": "caption"}.get(t, "para")
        blocks.append({"n": n, "kind": kind, "section": section,
                       "section_id": section_id, "text": text,
                       "plain": plain, "code_lang": ""})

    # Attach a deep link to every block.
    for b in blocks:
        if b["kind"] == "heading" and b["section_id"]:
            b["url"] = base_url + "#" + b["section_id"]
            b["anchor_kind"] = "heading-id"
        elif b["kind"] in ("code", "table"):
            if b["section_id"]:
                b["url"] = base_url + "#" + b["section_id"]
                b["anchor_kind"] = "section-id"
            else:
                b["url"] = base_url
                b["anchor_kind"] = "page"
        else:
            b["url"] = frag(base_url, b.get("plain") or b["text"])
            b["anchor_kind"] = "text-fragment"
    return blocks, headings, links


# ---------------------------------------------------------------- PDF path

# Producers that mean "this text layer came out of OCR, so it is approximate".
OCR_PRODUCERS = re.compile(
    r"(paper capture|ocr|tesseract|abbyy|finereader|scansnap|readiris|"
    r"omnipage|acrobat capture)", re.I)


def dupe_rate(t):
    """Fraction of adjacent word pairs that are identical.

    OCR'd PDFs frequently carry a doubled text layer (the recognised text is
    stamped over the scanned glyphs, and some extractors emit both). On this
    corpus the discriminator is stark: a doubled layer scores 0.26-0.36, a
    clean one scores under 0.01. Cheap, and it catches a failure that would
    otherwise poison every quote in the ingest.
    """
    w = re.findall(r"[A-Za-z']{3,}", t.lower())
    if len(w) < 20:
        return 0.0
    return sum(1 for a, b in zip(w, w[1:]) if a == b) / len(w)


def pdf_pages_pypdf(path):
    import pypdf
    r = pypdf.PdfReader(path)
    return [(pg.extract_text() or "") for pg in r.pages]


def pdf_pages_pymupdf(path):
    import fitz
    with fitz.open(path) as d:
        return [pg.get_text() for pg in d]


def pdf_pages_poppler(path, layout=False):
    cmd = ["pdftotext"] + (["-layout"] if layout else []) + ["-enc", "UTF-8",
                                                             path, "-"]
    out = subprocess.run(cmd, capture_output=True, timeout=180).stdout
    return out.decode("utf-8", "replace").split("\f")


# Ordered by observed quality, but the choice is made by SCORE, not by order:
# on OCR'd files poppler wins the race and loses the result.
PDF_EXTRACTORS = [
    ("pypdf", pdf_pages_pypdf),
    ("pymupdf", pdf_pages_pymupdf),
    ("pdftotext", lambda p: pdf_pages_poppler(p, layout=False)),
    ("pdftotext -layout", lambda p: pdf_pages_poppler(p, layout=True)),
]


def best_pdf_text(path, debug=False):
    """Run every available extractor and keep the cleanest output.

    Returns (name, pages) or (None, None) when nothing produced usable text.
    """
    results = []
    for name, fn in PDF_EXTRACTORS:
        try:
            pages = fn(path)
        except ImportError:
            note("%s: not installed" % name)
            continue
        except FileNotFoundError:
            note("%s: binary not on PATH" % name)
            continue
        except Exception as e:
            note("%s: failed (%s)" % (name, type(e).__name__))
            continue
        joined = "\n".join(pages)
        wc = len(joined.split())
        d = dupe_rate(joined)
        # Penalise doubled layers hard; prefer more text among clean results.
        quality = wc * (1.0 - min(d * 3.0, 0.95))
        results.append((quality, wc, d, name, pages))
        note("%-18s words=%-6d dupe=%.3f quality=%.0f" % (name, wc, d, quality))
    if not results:
        return None, None
    results.sort(key=lambda r: -r[0])
    quality, wc, d, name, pages = results[0]
    if d > 0.15:
        note("WARNING: best extractor still shows a doubled text layer")
    return name, pages


def pdf_meta(path):
    """Title/author/dates/producer from the /Info dict, plus page count."""
    out = {"page_count": 0, "producer": "", "title": "", "author": "",
           "created": "", "modified": ""}
    try:
        import pypdf
        r = pypdf.PdfReader(path)
        out["page_count"] = len(r.pages)
        info = r.metadata or {}

        def g(k):
            v = info.get(k)
            return str(v).strip() if v else ""
        out["title"] = g("/Title")
        out["author"] = g("/Author")
        out["producer"] = (g("/Producer") + " " + g("/Creator")).strip()
        out["created"] = pdf_date(g("/CreationDate"))
        out["modified"] = pdf_date(g("/ModDate"))
    except Exception as e:
        note("metadata read failed (%s)" % type(e).__name__)
    return out


def pdf_date(s):
    """D:20250603193645-07'00'  ->  2025-06-03"""
    m = re.match(r"D:(\d{4})(\d{2})(\d{2})", s or "")
    return "-".join(m.groups()) if m else ""


def pdf_outline(path):
    """Bookmarks as headings — but only when they are real titles.

    Export pipelines often emit one bookmark per page named after the source
    file with a sequence number ('Report-name-01', '-02', ...). Those are
    artifacts, not structure, and treating them as headings would invent an
    outline the document does not have.
    """
    try:
        import pypdf
        r = pypdf.PdfReader(path)
        items, stack = [], list(r.outline or [])
        while stack:
            it = stack.pop(0)
            if isinstance(it, list):
                stack = it + stack
                continue
            title = str(it.get("/Title", "")).strip()
            if not title:
                continue
            try:
                page = r.get_destination_page_number(it) + 1
            except Exception:
                page = None
            items.append({"text": title, "page": page})
        if not items:
            return []
        seq = sum(1 for i in items if re.search(r"[-_ ]\d{1,3}$", i["text"]))
        if seq >= 0.6 * len(items):
            note("outline looks auto-generated (%d/%d sequence-numbered) - ignored"
                 % (seq, len(items)))
            OUTLINE_STEM.append(outline_stem([i["text"] for i in items]))
            return []
        return items
    except Exception:
        return []


OUTLINE_STEM = []


def outline_stem(titles):
    """'Report-name-01', 'Report-name-02' -> 'Report name'.

    An export pipeline that numbers one bookmark per page throws away the
    outline as structure but preserves the document's name in every entry.
    Recover it - a PDF whose /Info carries no title usually still has one here.
    """
    stems = {re.sub(r"[-_ ]\d{1,3}$", "", t) for t in titles}
    if len(stems) != 1:
        return ""
    return re.sub(r"[-_]+", " ", stems.pop()).strip()


def pdf_blocks(pages, base_url, headings):
    """Split each page into paragraph blocks with a #page=N deep link.

    Line-joining signals, in priority order:
      * U+2028 LINE SEPARATOR - a designed soft break. Ends a run.
      * trailing whitespace    - a wrapped line; join to the next.
      * no sentence-final punctuation + next line starts lowercase - join.
    """
    blocks, n = [], 0
    hd_by_page = {}
    for h in headings:
        hd_by_page.setdefault(h.get("page"), h["text"])

    for pi, raw in enumerate(pages, start=1):
        if not raw or not raw.strip():
            continue
        raw = raw.replace("\u2029", "\n\n").replace("\u2028", "\n\x00")
        lines = raw.split("\n")
        paras, cur = [], ""
        for ln in lines:
            hard = ln.endswith("\x00")
            ln = ln.replace("\x00", "")
            if not ln.strip():
                if cur.strip():
                    paras.append(cur.strip())
                cur = ""
                continue
            wrapped = ln != ln.rstrip()
            cur = (cur + " " + ln.strip()).strip() if cur else ln.strip()
            ends_sentence = bool(re.search(r'[.!?:;"\u201d\u2019)]\s*$', cur))
            if hard or (not wrapped and ends_sentence):
                paras.append(cur.strip())
                cur = ""
        if cur.strip():
            paras.append(cur.strip())

        section = hd_by_page.get(pi, "")
        for j, ptxt in enumerate(paras):
            ptxt = re.sub(r"\s+", " ", ptxt).strip()
            if not ptxt:
                continue
            n += 1
            # A short, unpunctuated line followed by prose reads as a subhead.
            is_head = (len(ptxt) < 70
                       and not re.search(r"[.!?;,]$", ptxt)
                       and j + 1 < len(paras)
                       and len(paras[j + 1]) > 80)
            if is_head:
                section = ptxt
            blocks.append({
                "n": n, "page": pi,
                "kind": "subhead" if is_head else "para",
                "section": section, "section_id": "",
                "text": ptxt, "plain": ptxt, "code_lang": "",
                "url": "%s#page=%d" % (base_url, pi),
                "anchor_kind": "pdf-page",
            })
    return blocks


def build_pdf_record(path, canonical, final_url, debug=False):
    meta = pdf_meta(path)
    name, pages = best_pdf_text(path, debug)
    if pages is None:
        return None, meta, None
    heads = pdf_outline(path)
    blocks = pdf_blocks(pages, canonical, heads)
    wc = sum(len(b["text"].split()) for b in blocks)
    is_ocr = bool(OCR_PRODUCERS.search(meta["producer"]))
    headings = [{"level": 2, "text": h["text"], "id": "",
                 "block": next((b["n"] for b in blocks
                                if b["page"] == h.get("page")), None)}
                for h in heads]
    headings += [{"level": 3, "text": b["text"], "id": "", "block": b["n"]}
                 for b in blocks if b["kind"] == "subhead"]
    rec = {
        "url": final_url, "canonical_url": canonical,
        "format": "pdf", "extractor": name,
        "title": meta["title"] or "",
        "author": meta["author"], "site_name": urllib.parse.urlsplit(canonical).netloc,
        "published": meta["created"], "modified": meta["modified"],
        "retrieved": _dt.date.today().isoformat(),
        "description": "",
        "page_count": meta["page_count"],
        "pages_with_text": len({b["page"] for b in blocks}),
        "text_is_ocr": is_ocr, "producer": meta["producer"],
        "word_count": wc, "reading_minutes": max(1, round(wc / 230)),
        "paywall_suspected": False,
        "js_shell_suspected": False,
        "headings": headings, "blocks": blocks, "outbound_links": [],
    }
    return rec, meta, blocks


# ---------------------------------------------------------------- rendering

def to_markdown(rec):
    L = ["# " + rec["title"], ""]
    meta = []
    if rec["author"]:
        meta.append("**Author:** " + rec["author"])
    if rec["site_name"]:
        meta.append("**Site:** " + rec["site_name"])
    if rec["published"]:
        meta.append("**Published:** " + rec["published"])
    if rec["modified"]:
        meta.append("**Updated:** " + rec["modified"])
    meta.append("**Retrieved:** " + rec["retrieved"])
    meta.append("**Canonical:** " + rec["canonical_url"])
    meta.append("**Length:** %d words (~%d min read) · %d blocks"
                % (rec["word_count"], rec["reading_minutes"], len(rec["blocks"])))
    if rec.get("format") == "pdf":
        meta.append("**PDF:** %d pages (%d with text) · extractor: %s"
                    % (rec["page_count"], rec["pages_with_text"], rec["extractor"]))
    L += meta + [""]
    if rec.get("text_is_ocr"):
        L += ["> ⚠️ **OCR text layer** (producer: %s). Wording is approximate — "
              "treat it as evidence of what was written, not as a printed quote. "
              "Cite quotes as `**Verbatim (OCR, p.N)**`."
              % rec["producer"], ""]
    if rec["paywall_suspected"]:
        L += ["> ⚠️ Possible paywall or truncated body — verify before extracting.", ""]
    if rec["js_shell_suspected"]:
        L += ["> ⚠️ Very little text for a page this size — likely client-rendered.", ""]
    if rec.get("format") != "pdf":
        L += ["---", ""]
    cur_page = None
    for b in rec["blocks"]:
        if rec.get("format") == "pdf" and b.get("page") != cur_page:
            cur_page = b["page"]
            L += ["", "---", "", "### page %d  <!-- %s#page=%d -->"
                  % (cur_page, rec["canonical_url"], cur_page), ""]
        tag = "`P%d`" % b["n"]
        if rec.get("format") == "pdf":
            tag = "`p%d.%d`" % (b["page"], b["n"])
        if b["kind"] == "subhead":
            L += ["", "**%s**  %s" % (b["text"], tag), ""]
            continue
        if b["kind"] == "heading":
            L += ["", "%s %s  <!-- %s → %s -->" % ("#" * min(b.get("level", 2) + 1, 6),
                                                   b["text"], tag, b["url"]), ""]
        elif b["kind"] == "code":
            L += ["%s [¶](%s)" % (tag, b["url"]), "```" + b["code_lang"],
                  b["text"], "```", ""]
        elif b["kind"] == "quote":
            L += ["%s [¶](%s)" % (tag, b["url"]),
                  "\n".join("> " + x for x in b["text"].split("\n")), ""]
        elif b["kind"] == "list":
            L += ["%s [¶](%s)" % (tag, b["url"]), b["text"], ""]
        else:
            L += ["%s [¶](%s)  %s" % (tag, b["url"], b["text"]), ""]
    return "\n".join(L).rstrip() + "\n"


# ---------------------------------------------------------------- main

def run_pdf(a, raw, final_url, local):
    """PDF branch: cache bytes to disk, extract, emit the same record shape."""
    canonical = final_url
    if canonical.startswith("http"):
        parts = urllib.parse.urlsplit(canonical)
        q = [(k, v) for k, v in urllib.parse.parse_qsl(parts.query)
             if not re.match(r"^(utm_|fbclid|gclid|mc_|ref|source|si)$", k, re.I)]
        canonical = urllib.parse.urlunsplit(
            (parts.scheme, parts.netloc, parts.path, urllib.parse.urlencode(q), ""))

    if local:
        path = local
        tmp = None
    else:
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        tmp.write(raw)
        tmp.close()
        path = tmp.name

    try:
        rec, meta, blocks = build_pdf_record(path, canonical, final_url, a.debug)
    finally:
        pass  # keep the temp file; --debug users want to open it

    if rec is None or rec["word_count"] < 60:
        print("NO EXTRACTABLE TEXT LAYER in this PDF (%d pages).\n"
              % (meta.get("page_count", 0)), file=sys.stderr)
        print("This is normal for scanned documents without OCR, and for\n"
              "slide decks that are exported as flat images.\n\n"
              "Do NOT guess the contents. Instead:\n"
              "  1. Read the pages directly with the Read tool, which renders\n"
              "     each page visually - pass `pages: \"1-20\"` (max 20 per call).\n"
              "     The file is at: %s\n"
              "  2. Cite with the same #page=N deep links this script would have\n"
              "     produced, and mark bodies **Verbatim (page image, p.N)**.\n"
              "  3. Steps 2-6 of the skill are unchanged." % path, file=sys.stderr)
        if a.debug:
            print("\n".join("  · " + d for d in DEBUG), file=sys.stderr)
        return 2

    if not rec["title"] and OUTLINE_STEM and OUTLINE_STEM[0]:
        rec["title"] = OUTLINE_STEM[0]
        note("title recovered from auto-generated outline stem")
    if not rec["title"]:
        # Last resort: the first short block on page 1. Flag it, because a
        # cover page often runs the title straight into the standfirst.
        for b in rec["blocks"]:
            if b["page"] == 1 and 8 < len(b["text"]) < 120:
                rec["title"] = b["text"]
                note("title guessed from page 1 - verify before using")
                break

    md = to_markdown(rec)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False, indent=2)
    if a.md:
        with open(a.md, "w", encoding="utf-8") as f:
            f.write(md)
    if not a.json and not a.md:
        sys.stdout.write(md)

    if a.debug:
        print("\n".join("  · " + d for d in DEBUG), file=sys.stderr)
    if not a.quiet:
        print("%s — PDF, %d pages (%d with text), %d words, %d blocks [%s]"
              % (rec["title"][:55] or "(untitled)", rec["page_count"],
                 rec["pages_with_text"], rec["word_count"], len(rec["blocks"]),
                 rec["extractor"]), file=sys.stderr)
        if rec["text_is_ocr"]:
            print("  ⚠️ OCR text layer (%s) — wording is approximate"
                  % rec["producer"][:60], file=sys.stderr)
        if not local:
            print("  cached at %s (read pages visually if a quote looks wrong)"
                  % path, file=sys.stderr)
    return 0


def main():
    ap = argparse.ArgumentParser(description="Fetch a blog post as deep-linkable blocks.")
    ap.add_argument("url")
    ap.add_argument("--json")
    ap.add_argument("--md")
    ap.add_argument("--min-words", type=int, default=120)
    ap.add_argument("--raw", action="store_true")
    ap.add_argument("--debug", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    # Local files are a first-class input: PDFs often arrive as downloads.
    local = None
    if os.path.exists(a.url):
        local = os.path.abspath(a.url)
        raw, final_url, ctype = open(local, "rb").read(), "file://" + local, ""
        note("read local file %s (%d bytes)" % (local, len(raw)))
    else:
        try:
            raw, final_url, ctype = fetch(a.url)
        except urllib.error.HTTPError as e:
            code = e.code
            print("FETCH FAILED: HTTP %s for %s\n" % (code, a.url), file=sys.stderr)
            if code in (401, 402, 403, 429):
                print("This looks like a block or a paywall. Options:\n"
                      "  1. Open it with the browser tools (preview_start + get_page_text)\n"
                      "     — that uses a real browser and the user's own session.\n"
                      "  2. Ask the user to paste the article text.\n"
                      "  3. Try the publisher's RSS/Atom feed, which often carries full text.\n"
                      "Do NOT reconstruct the post from its title or an excerpt.",
                      file=sys.stderr)
            return 1
        except Exception as e:
            print("FETCH FAILED: %s" % e, file=sys.stderr)
            return 1

    # ---- format dispatch -------------------------------------------------
    is_pdf = (raw[:5] == b"%PDF-" or "application/pdf" in ctype.lower()
              or a.url.lower().split("?")[0].endswith(".pdf"))
    if is_pdf:
        return run_pdf(a, raw, final_url, local)

    page = decode_html(raw, ctype)

    dom = DOM()
    dom.feed(page)
    doc = dom.root
    meta = meta_map(doc)
    ld = json_ld(page)

    canonical = ""
    for link in doc.find_all({"link"}):
        if (link.attrs.get("rel") or "").lower() == "canonical" and link.attrs.get("href"):
            canonical = urllib.parse.urljoin(final_url, link.attrs["href"])
            break
    canonical = canonical or meta.get("og:url") or final_url
    # Strip tracking noise so Source groups cleanly.
    parts = urllib.parse.urlsplit(canonical)
    q = [(k, v) for k, v in urllib.parse.parse_qsl(parts.query)
         if not re.match(r"^(utm_|fbclid|gclid|mc_|ref|source|si)$", k, re.I)]
    canonical = urllib.parse.urlunsplit(
        (parts.scheme, parts.netloc, parts.path,
         urllib.parse.urlencode(q), ""))

    main_node = doc if a.raw else pick_main(doc, a.min_words, a.debug)
    if main_node is None:
        body = [n for n in doc.find_all({"body"})]
        main_node = body[0] if body else doc
        note("no strong candidate; fell back to <body>")

    blocks, headings, links = extract(main_node, canonical)
    prose = " ".join(b["text"] for b in blocks if b["kind"] in ("para", "list", "quote"))
    wc = words(prose)

    rec = {
        "url": final_url,
        "canonical_url": canonical,
        "title": pick_title(doc, meta, ld),
        "author": pick_author(doc, meta, ld),
        "site_name": meta.get("og:site_name", "") or urllib.parse.urlsplit(canonical).netloc,
        "published": (meta.get("article:published_time") or ld.get("published")
                      or meta.get("date") or meta.get("parsely-pub-date") or ""),
        "modified": meta.get("article:modified_time") or ld.get("modified") or "",
        "retrieved": _dt.date.today().isoformat(),
        "description": meta.get("og:description") or meta.get("description") or "",
        "word_count": wc,
        "reading_minutes": max(1, round(wc / 230)),
        "paywall_suspected": bool(
            re.search(r"(paywall|subscriber-only|premium-content|meteredContent|"
                      r"subscribe to (?:keep )?read|for subscribers)", page, re.I)
            and wc < 900),
        "js_shell_suspected": wc < 150 and len(page) > 40000,
        "headings": headings,
        "blocks": blocks,
        "outbound_links": links,
    }

    md = to_markdown(rec)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False, indent=2)
    if a.md:
        with open(a.md, "w", encoding="utf-8") as f:
            f.write(md)
    if not a.json and not a.md:
        sys.stdout.write(md)

    if a.debug:
        print("\n".join("  · " + d for d in DEBUG), file=sys.stderr)
    if not a.quiet:
        print("%s — %d words, %d blocks, %d headings, %d links"
              % (rec["title"][:60] or "(untitled)", wc, len(blocks),
                 len(headings), len(links)), file=sys.stderr)
        if rec["paywall_suspected"]:
            print("  ⚠️ paywall suspected — body may be truncated", file=sys.stderr)
        if rec["js_shell_suspected"]:
            print("  ⚠️ client-rendered shell — use the browser tools instead",
                  file=sys.stderr)

    if wc < 60:
        print("NO ARTICLE TEXT FOUND. Try --raw, or fetch with the browser tools "
              "(preview_start + get_page_text), or ask the user to paste it.",
              file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
