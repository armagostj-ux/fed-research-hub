#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Federal Reserve Research Hub - weekly refresh.

Fetches the latest titles from official Fed RSS feeds + the RePEc/IDEAS research
index, rebuilds page_data.json, and injects it into template.html to produce
fed-research-hub.html (ready to publish to the Claude artifact).

Run:  python -I refresh_fed_hub.py
Then publish fed-research-hub.html to artifact URL:
      https://claude.ai/artifact/PECaNiv1o9cMUHGhvxvkv5
"""
import re, html, json, os, datetime, ssl, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
MAXN = 7
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
CTX = ssl.create_default_context()

def fetch(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
            return r.read()
    except Exception as e:
        print("  ! fetch failed:", url, "->", e)
        return b""

def decode(raw):
    try: return raw.decode("utf-8")
    except UnicodeDecodeError: return raw.decode("cp1252", "replace")

def clean(s):
    if s is None: return ""
    s = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", s, flags=re.S)
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()

MONTHS = {m:i for i,m in enumerate(
    ["jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"],1)}
INV = {v:k for k,v in MONTHS.items()}

def norm_date(raw):
    if not raw: return ("", "")
    m = re.search(r"(\d{1,2})\s+([A-Za-z]{3})[a-z]*\s+(\d{4})", raw)
    if m:
        d, mon, y = int(m.group(1)), m.group(2).lower()[:3], int(m.group(3))
        if mon in MONTHS: return (f"{y}-{MONTHS[mon]:02d}-{d:02d}", f"{mon.capitalize()} {d}, {y}")
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", raw)
    if m:
        y, mo, d = map(int, m.groups())
        return (f"{y}-{mo:02d}-{d:02d}", f"{INV[mo].capitalize()} {d}, {y}")
    return ("", raw[:20])

def label_year(label):
    label = label or ""
    m = re.search(r"\b(19|20)(\d{2})\b", label)
    if m: y = m.group(1)+m.group(2)
    else:
        m = re.search(r"\b(\d{2})-\d+\b", label)
        if not m: return ""
        y = "20"+m.group(1)
    try:
        if 1990 <= int(y) <= 2035: return y
    except ValueError: pass
    return ""

def parse_rss(raw, maxn=MAXN):
    txt = decode(raw).lstrip("﻿")
    items = []
    for block in re.findall(r"<item[ >].*?</item>", txt, flags=re.S|re.I):
        t = re.search(r"<title>(.*?)</title>", block, re.S|re.I)
        l = re.search(r"<link>(.*?)</link>", block, re.S|re.I) or re.search(r'<link[^>]*href="([^"]+)"', block, re.I)
        d = re.search(r"<pubDate>(.*?)</pubDate>", block, re.S|re.I) or re.search(r"<dc:date>(.*?)</dc:date>", block, re.S|re.I)
        title = clean(t.group(1)) if t else ""
        link = clean(l.group(1)) if l else ""
        _, disp = norm_date(d.group(1) if d else "")
        if title and link:
            items.append({"t": title, "u": link, "d": disp})
        if len(items) >= maxn: break
    return items

def parse_ideas(raw, handle, maxn=MAXN):
    txt = decode(raw)
    items = []
    pat = re.compile(r'<B>\s*([^<]*?)\s*<A HREF="(/p/fip/%s/[^"]+)">(.*?)</A>' % re.escape(handle), re.I|re.S)
    for m in pat.finditer(txt):
        title = clean(m.group(3))
        if not title or title.lower() in ("by citations","by downloads","by date","by authors"): continue
        items.append({"t": title, "u": "https://ideas.repec.org"+m.group(2), "d": label_year(clean(m.group(1)))})
        if len(items) >= maxn: break
    return items

RSS = "rss"; IDEAS = "ideas"
# bank: list of (type, label, kind, url_or_(url,handle))
SOURCES = {
 "BoG": [
   ("research","Working Papers (FEDS)", RSS, "https://www.federalreserve.gov/feeds/feds.xml"),
   ("research","Working Papers (IFDP)", RSS, "https://www.federalreserve.gov/feeds/ifdp.xml"),
   ("blog","FEDS Notes", RSS, "https://www.federalreserve.gov/feeds/feds_notes.xml"),
   ("news","Monetary Policy Press", RSS, "https://www.federalreserve.gov/feeds/press_monetary.xml"),
   ("news","Speeches & Testimony", RSS, "https://www.federalreserve.gov/feeds/speeches.xml"),
 ],
 "Boston": [("research","Working Papers", IDEAS, ("https://ideas.repec.org/s/fip/fedbwp.html","fedbwp"))],
 "New York": [
   ("research","Staff Reports", IDEAS, ("https://ideas.repec.org/s/fip/fednsr.html","fednsr")),
   ("blog","Liberty Street Economics", RSS, "https://libertystreeteconomics.newyorkfed.org/feed/"),
 ],
 "Philadelphia": [("research","Working Papers", IDEAS, ("https://ideas.repec.org/s/fip/fedpwp.html","fedpwp"))],
 "Cleveland": [("research","Working Papers", IDEAS, ("https://ideas.repec.org/s/fip/fedcwq.html","fedcwq"))],
 "Richmond": [
   ("research","Working Papers", RSS, "https://www.richmondfed.org/publications/research/working_papers?cc_view=rss"),
   ("publications","Economic Brief", RSS, "https://www.richmondfed.org/publications/research/economic_brief?cc_view=rss"),
   ("news","Press Room", RSS, "https://www.richmondfed.org/press_room?cc_view=rss"),
 ],
 "Atlanta": [
   ("research","Working Papers", IDEAS, ("https://ideas.repec.org/s/fip/fedawp.html","fedawp")),
   ("blog","macroblog", RSS, "https://www.atlantafed.org/rss/macroblog"),
 ],
 "Chicago": [("research","Working Papers", IDEAS, ("https://ideas.repec.org/s/fip/fedhwp.html","fedhwp"))],
 "St. Louis": [("research","Working Papers", IDEAS, ("https://ideas.repec.org/s/fip/fedlwp.html","fedlwp"))],
 "Minneapolis": [("research","Working Papers", IDEAS, ("https://ideas.repec.org/s/fip/fedmwp.html","fedmwp"))],
 "Kansas City": [("research","Research Working Papers", IDEAS, ("https://ideas.repec.org/s/fip/fedkrw.html","fedkrw"))],
 "Dallas": [("research","Working Papers", IDEAS, ("https://ideas.repec.org/s/fip/feddwp.html","feddwp"))],
 "San Francisco": [
   ("research","Working Papers", IDEAS, ("https://ideas.repec.org/s/fip/fedfwp.html","fedfwp")),
   ("publications","Economic Letter", IDEAS, ("https://ideas.repec.org/s/fip/fedfel.html","fedfel")),
 ],
}
META = {
 "BoG":(0,"","Washington, D.C. · System-wide","https://www.federalreserve.gov"),
 "Boston":(1,"A","First District · New England","https://www.bostonfed.org"),
 "New York":(2,"B","Second District · NY, northern NJ","https://www.newyorkfed.org"),
 "Philadelphia":(3,"C","Third District · eastern PA, NJ, DE","https://www.philadelphiafed.org"),
 "Cleveland":(4,"D","Fourth District · OH, western PA","https://www.clevelandfed.org"),
 "Richmond":(5,"E","Fifth District · VA, NC, SC, MD, WV, D.C.","https://www.richmondfed.org"),
 "Atlanta":(6,"F","Sixth District · Southeast","https://www.atlantafed.org"),
 "Chicago":(7,"G","Seventh District · Midwest","https://www.chicagofed.org"),
 "St. Louis":(8,"H","Eighth District · mid-South","https://www.stlouisfed.org"),
 "Minneapolis":(9,"I","Ninth District · Upper Midwest","https://www.minneapolisfed.org"),
 "Kansas City":(10,"J","Tenth District · Great Plains, Rockies","https://www.kansascityfed.org"),
 "Dallas":(11,"K","Eleventh District · TX, northern LA, southern NM","https://www.dallasfed.org"),
 "San Francisco":(12,"L","Twelfth District · the West","https://www.frbsf.org"),
}
HUBS = {
 ("BoG","Working Papers (FEDS)"):"https://www.federalreserve.gov/econres/feds/index.htm",
 ("BoG","Working Papers (IFDP)"):"https://www.federalreserve.gov/econres/ifdp/index.htm",
 ("BoG","FEDS Notes"):"https://www.federalreserve.gov/econres/notes/feds-notes/default.htm",
 ("BoG","Monetary Policy Press"):"https://www.federalreserve.gov/newsevents/pressreleases.htm",
 ("BoG","Speeches & Testimony"):"https://www.federalreserve.gov/newsevents/speeches.htm",
 ("Boston","Working Papers"):"https://www.bostonfed.org/publications/research-department-working-paper.aspx",
 ("New York","Staff Reports"):"https://www.newyorkfed.org/research/staff_reports/index.html",
 ("New York","Liberty Street Economics"):"https://libertystreeteconomics.newyorkfed.org",
 ("Philadelphia","Working Papers"):"https://www.philadelphiafed.org/search-results/working-papers",
 ("Cleveland","Working Papers"):"https://www.clevelandfed.org/publications/working-paper",
 ("Richmond","Working Papers"):"https://www.richmondfed.org/publications/research/working_papers",
 ("Richmond","Economic Brief"):"https://www.richmondfed.org/publications/research/economic_brief",
 ("Richmond","Press Room"):"https://www.richmondfed.org/press_room",
 ("Atlanta","Working Papers"):"https://www.atlantafed.org/research/publications/wp",
 ("Atlanta","macroblog"):"https://www.atlantafed.org/blogs/macroblog",
 ("Chicago","Working Papers"):"https://www.chicagofed.org/publications/working-papers/index",
 ("St. Louis","Working Papers"):"https://research.stlouisfed.org/wp/",
 ("Minneapolis","Working Papers"):"https://www.minneapolisfed.org/research/working-papers",
 ("Kansas City","Research Working Papers"):"https://www.kansascityfed.org/research/research-working-papers/",
 ("Dallas","Working Papers"):"https://www.dallasfed.org/research/papers",
 ("San Francisco","Working Papers"):"https://www.frbsf.org/research-and-insights/publications/working-papers/",
 ("San Francisco","Economic Letter"):"https://www.frbsf.org/research-and-insights/publications/economic-letter/",
}
TYPE_ORDER = {"research":0,"publications":1,"blog":2,"news":3}

def build():
    banks = []
    for bank, srcs in SOURCES.items():
        print("*", bank)
        secs = []
        for typ, label, kind, arg in srcs:
            if kind == RSS:
                items = parse_rss(fetch(arg))
            else:
                url, handle = arg
                items = parse_ideas(fetch(url), handle)
            print(f"    [{typ}] {label}: {len(items)}")
            if items:
                secs.append({"type": typ, "label": label, "items": items,
                             "hub": HUBS.get((bank, label), META[bank][3])})
        secs.sort(key=lambda s: TYPE_ORDER.get(s["type"], 9))
        num, ltr, city, home = META[bank]
        banks.append({"key": bank, "num": num, "ltr": ltr,
            "name": bank if bank=="BoG" else ("Federal Reserve Bank of "+bank),
            "short": "Board of Governors" if bank=="BoG" else bank,
            "city": city, "home": home, "sys": bank=="BoG", "sections": secs})
    page = {"generated": datetime.date.today().isoformat(), "banks": banks}
    data = json.dumps(page, ensure_ascii=False, separators=(",",":"))
    open(os.path.join(HERE,"page_data.json"),"w",encoding="utf-8").write(data)

    tpl = open(os.path.join(HERE,"template.html"),encoding="utf-8").read()
    out = tpl.replace("/*DATA*/", data.replace("</script>","<\\/script>"))
    open(os.path.join(HERE,"fed-research-hub.html"),"w",encoding="utf-8").write(out)
    total = sum(len(s["items"]) for b in banks for s in b["sections"])
    print(f"\nDone: {total} articles across {len(banks)} banks -> fed-research-hub.html ({len(out)} bytes)")

if __name__ == "__main__":
    build()
