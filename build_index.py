#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a single, self-contained index.html that embeds both report HTML files
via <iframe srcdoc>.

Why srcdoc and not src=: when index.html is opened directly as a local file
(file://), browsers block loading sibling local .html files into <iframe src>,
so the frames render blank — tabs look dead and there is nothing to scroll.
srcdoc renders the embedded markup in an isolated, same-origin document with no
file access required, so it works offline/locally while keeping each report's
own CSS fully isolated."""
import html, os

BASE = os.path.dirname(os.path.abspath(__file__))

# (frame id, tab main label, tab sub label, source html file, iframe title)
REPORTS = [
    ("frame-report", "主报告 · 原发性痛经", "非药物镇痛贴片 · 立项调研",
     "女性健康电刺激产品_立项调研报告.html", "原发性痛经立项调研报告"),
    ("frame-oab", "候选场景 · OAB / TTNS", "急迫性尿失禁 · 经皮胫神经刺激",
     "候选场景立项简版_急迫尿失禁OAB_经皮胫神经刺激TTNS.html", "OAB / TTNS 候选场景立项简版"),
]


# Injected into every embedded report. In an <iframe srcdoc> the document's
# base URL is inherited from the parent, so a bare in-page link like
# href="#sec-12" resolves against index.html and *navigates the frame away*
# (blanking the report). Intercepting same-page anchor clicks and scrolling
# in-document keeps TOC links, footnote refs and back-links working when
# embedded, and is harmless when the report is opened standalone.
ANCHOR_SHIM = """<script>
(function(){
  document.addEventListener('click',function(e){
    var a=e.target.closest?e.target.closest('a[href^="#"]'):null;
    if(!a)return;
    var raw=a.getAttribute('href');
    if(!raw||raw==='#')return;
    var id=raw.slice(1);
    var t=document.getElementById(id)||document.getElementById(decodeURIComponent(id));
    if(!t)return;
    e.preventDefault();
    var reduce=window.matchMedia&&window.matchMedia('(prefers-reduced-motion:reduce)').matches;
    t.scrollIntoView({behavior:reduce?'auto':'smooth',block:'start'});
  },false);
})();
</script>"""


def inject_shim(doc):
    """Insert the anchor shim just before the report's closing </body>."""
    idx = doc.rfind("</body>")
    if idx == -1:
        return doc + ANCHOR_SHIM
    return doc[:idx] + ANCHOR_SHIM + "\n" + doc[idx:]


def load(fn):
    with open(os.path.join(BASE, fn), encoding="utf-8") as f:
        return f.read()


tabs, frames, links = [], [], []
for i, (fid, main, sub, fn, title) in enumerate(REPORTS):
    active = " active" if i == 0 else ""
    sel = "true" if i == 0 else "false"
    tabs.append(
        f'    <button class="tab{active}" id="tab-{i}" role="tab" aria-selected="{sel}"\n'
        f'      aria-controls="{fid}" tabindex="{0 if i == 0 else -1}" data-target="{fid}">\n'
        f'      <span class="t-main">{html.escape(main)}</span>\n'
        f'      <span class="t-sub">{html.escape(sub)}</span>\n'
        f'    </button>'
    )
    srcdoc = html.escape(inject_shim(load(fn)), quote=True)
    frames.append(
        f'  <iframe id="{fid}" class="{("active" if i == 0 else "").strip() or "frame"}" '
        f'title="{html.escape(title)}"\n          role="tabpanel" aria-labelledby="tab-{i}"'
        f'\n          srcdoc="{srcdoc}"></iframe>'
    )
    links.append(f'<a href="{html.escape(fn)}">{html.escape(main)}</a>')

tabs_html = "\n".join(tabs)
frames_html = "\n".join(frames)
links_html = " · \n      ".join(links)

CSS = r"""
:root{
  --bg:#ffffff; --surface:#faf7f5; --surface-2:#f5efec;
  --ink:#231d1b; --ink-soft:#4f4744; --muted:#6a615d;
  --rule:#e8e1dc; --rule-soft:#f0ebe7;
  --accent:#a32a45; --accent-deep:#7c1d33; --accent-tint:#fbeef1; --accent-soft:#f6e2e7;
  --serif:"Newsreader","Songti SC","STSong","Noto Serif SC",Georgia,serif;
  --sans:"PingFang SC","Hiragino Sans GB","Microsoft YaHei",-apple-system,system-ui,"Segoe UI",sans-serif;
}
*{box-sizing:border-box}
html{height:100%}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);
  height:100vh;height:100dvh;display:flex;flex-direction:column;-webkit-font-smoothing:antialiased}

/* ---------- app bar ---------- */
.appbar{flex:0 0 auto;background:var(--bg);border-bottom:1px solid var(--rule);
  padding:.85rem clamp(1rem,3vw,2rem) 0;position:relative;z-index:5}
.brand{display:flex;align-items:baseline;gap:.7rem;flex-wrap:wrap;margin-bottom:.7rem}
.brand .mark{width:.5rem;height:.5rem;border-radius:50%;background:var(--accent);transform:translateY(-.1em)}
.brand h1{font-family:var(--serif);font-weight:600;font-size:clamp(1rem,2.4vw,1.28rem);
  letter-spacing:-.01em;color:var(--ink);margin:0;line-height:1.2}
.brand .kicker{font-size:.66rem;letter-spacing:.18em;text-transform:uppercase;
  color:var(--accent);font-weight:600;margin-left:auto;align-self:center}

.tabs{display:flex;gap:.3rem;flex-wrap:wrap}
.tab{appearance:none;border:0;background:transparent;cursor:pointer;font-family:var(--sans);
  font-size:.92rem;color:var(--muted);padding:.6rem .95rem;border-radius:9px 9px 0 0;
  position:relative;line-height:1.3;transition:color .18s,background .18s;display:flex;
  flex-direction:column;gap:.1rem;min-width:0}
.tab .t-main{font-weight:600;color:inherit}
.tab .t-sub{font-size:.72rem;color:var(--muted);font-weight:400;letter-spacing:.01em}
.tab:hover{color:var(--ink-soft);background:var(--surface)}
.tab.active{color:var(--accent-deep);background:var(--surface)}
.tab.active .t-sub{color:var(--accent)}
.tab.active::after{content:"";position:absolute;left:.6rem;right:.6rem;bottom:-1px;height:2px;
  background:var(--accent);border-radius:2px}

/* ---------- frames ---------- */
/* Inactive frames stay laid out (visibility, not display:none) so each report's
   inner responsive JS reads the real viewport width — a display:none iframe
   reports ~0px and would wrongly collapse the OAB report's <details> TOC. */
.frames{flex:1 1 auto;position:relative;background:var(--bg)}
.frames iframe{position:absolute;inset:0;width:100%;height:100%;border:0;visibility:hidden;z-index:0}
.frames iframe.active{visibility:visible;z-index:1}

.fallback{position:absolute;left:0;right:0;bottom:0;padding:.5rem 1rem;text-align:center;
  color:var(--muted);font-size:.78rem;line-height:1.6;background:var(--bg);
  border-top:1px solid var(--rule-soft)}
.fallback a{color:var(--accent);font-weight:600}

@media (max-width:560px){
  .appbar{padding:.55rem .9rem 0}
  .brand{margin-bottom:.5rem;gap:.5rem}
  .brand .kicker{display:none}
  .brand h1{font-size:.95rem}
  .tabs{gap:.25rem}
  .tab{flex:1 1 0;align-items:center;justify-content:center;text-align:center;
    padding:.7rem .4rem;min-height:46px}
  .tab .t-sub{display:none}
  .tab .t-main{font-size:.84rem}
  .tab.active::after{left:.4rem;right:.4rem}
}
"""

doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>女性健康可穿戴电刺激产品 · 立项材料集</title>
<meta name="description" content="痛经主报告与 OAB/TTNS 候选场景立项材料 · 分页切换">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
<header class="appbar">
  <div class="brand">
    <span class="mark" aria-hidden="true"></span>
    <h1>女性健康可穿戴电刺激产品 · 立项材料集</h1>
    <span class="kicker">机密 · 内部立项决策材料</span>
  </div>
  <nav class="tabs" role="tablist" aria-label="报告切换">
{tabs_html}
  </nav>
</header>

<div class="frames">
{frames_html}
  <div class="fallback">独立打开:
      {links_html}</div>
</div>

<script>
(function(){{
  var tabs=[].slice.call(document.querySelectorAll('.tab'));
  var frames=[].slice.call(document.querySelectorAll('.frames iframe'));
  function activate(id,focus){{
    tabs.forEach(function(t){{
      var on=t.dataset.target===id;
      t.classList.toggle('active',on);
      t.setAttribute('aria-selected',on?'true':'false');
      t.tabIndex=on?0:-1;
      if(on&&focus)t.focus();
    }});
    frames.forEach(function(f){{f.classList.toggle('active',f.id===id);}});
    try{{history.replaceState(null,'',id==='frame-oab'?'#oab':'#report');}}catch(e){{}}
  }}
  tabs.forEach(function(t,i){{
    t.addEventListener('click',function(){{activate(t.dataset.target);}});
    t.addEventListener('keydown',function(e){{
      var d=0;
      if(e.key==='ArrowRight'||e.key==='ArrowDown')d=1;
      else if(e.key==='ArrowLeft'||e.key==='ArrowUp')d=-1;
      else if(e.key==='Home'){{e.preventDefault();return activate(tabs[0].dataset.target,true);}}
      else if(e.key==='End'){{e.preventDefault();return activate(tabs[tabs.length-1].dataset.target,true);}}
      else return;
      e.preventDefault();
      activate(tabs[(i+d+tabs.length)%tabs.length].dataset.target,true);
    }});
  }});
  if(location.hash==='#oab')activate('frame-oab');
}})();
</script>
</body>
</html>
"""

OUT = os.path.join(BASE, "index.html")
with open(OUT, "w", encoding="utf-8") as f:
    f.write(doc)
print("wrote", OUT, "|", round(len(doc) / 1024), "KB |", len(REPORTS), "reports embedded")
