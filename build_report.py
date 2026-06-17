#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Convert the femtech feasibility report Markdown into a single elegant, academic HTML page."""
import re, html, sys, io

SRC = "/Users/yuanzhidian/Desktop/project/电极贴片/女性健康电刺激产品_立项调研报告.md"
OUT = "/Users/yuanzhidian/Desktop/project/电极贴片/女性健康电刺激产品_立项调研报告.html"

with open(SRC, encoding="utf-8") as f:
    raw = f.read().replace("\r\n", "\n")
lines = raw.split("\n")

# ---------- footnote numbering (by first in-text reference) ----------
fn_order = {}          # label -> number
fn_seen_ref = set()    # labels whose first fnref id has been emitted
def_re = re.compile(r"^\[\^([A-Za-z0-9_]+)\]:\s")
ref_re = re.compile(r"\[\^([A-Za-z0-9_]+)\]")
for ln in lines:
    if def_re.match(ln):
        continue
    for m in ref_re.finditer(ln):
        lab = m.group(1)
        if lab not in fn_order:
            fn_order[lab] = len(fn_order) + 1
# any label only defined but never referenced still needs a number
def_labels = []
for ln in lines:
    m = def_re.match(ln)
    if m:
        lab = m.group(1)
        def_labels.append(lab)
        if lab not in fn_order:
            fn_order[lab] = len(fn_order) + 1

# ---------- inline formatting ----------
CODE_TOKEN = "\x00CODE%d\x00"
def inline(text):
    codes = []
    def stash(m):
        codes.append(m.group(1))
        return CODE_TOKEN % (len(codes) - 1)
    text = re.sub(r"`([^`]+)`", stash, text)
    text = html.escape(text, quote=False)
    # footnote references -> superscript links
    def fnref(m):
        lab = m.group(1)
        num = fn_order.get(lab, "?")
        if lab not in fn_seen_ref:
            fn_seen_ref.add(lab)
            anchor = f' id="fnref-{lab}"'
        else:
            anchor = ""
        return (f'<sup class="fnref"><a{anchor} href="#fn-{lab}" '
                f'aria-label="参考文献 {num}">{num}</a></sup>')
    text = ref_re.sub(fnref, text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", text)
    for i, c in enumerate(codes):
        text = text.replace(CODE_TOKEN % i, "<code>" + html.escape(c, quote=False) + "</code>")
    return text

# ---------- signal-light cell decoration ----------
def deco_cell(cellhtml):
    raw = cellhtml
    for emo, cls, label in (("🟢","g","绿"),("🟡","y","黄"),("🔴","r","红")):
        if emo in raw:
            txt = raw.replace(emo, "").strip()
            return f'<span class="sig sig-{cls}"><span class="dot"></span>{txt}</span>'
    if cellhtml.strip() in ("★ <strong>首发主打</strong>", "★ <strong>首发主打</strong>".strip()):
        pass
    return cellhtml

# ---------- cover extraction ----------
i = 0
title = ""
fm = {}
while i < len(lines):
    ln = lines[i]
    if ln.startswith("# ") and not title:
        title = ln[2:].strip()
        i += 1
        continue
    if ln.startswith(">"):
        body = ln.lstrip(">").strip()
        mm = re.match(r"\*\*(.+?):\*\*\s*(.*)", body) or re.match(r"\*\*(.+?):?\*\*[:：]?\s*(.*)", body)
        if mm:
            key = mm.group(1).strip().rstrip(":：")
            fm[key] = mm.group(2).strip()
        i += 1
        continue
    if ln.strip() == "---":
        i += 1
        break
    if ln.strip() == "":
        i += 1
        continue
    i += 1
rest = lines[i:]

# ---------- block parser for the remainder ----------
out = []
toc = []
sec_n = 0
in_section = False
def close_section():
    global in_section
    if in_section:
        out.append("</section>")
        in_section = False

def is_table_sep(s):
    s = s.strip()
    if "|" not in s:
        return False
    inner = s.strip("|")
    cells = inner.split("|")
    return all(re.fullmatch(r"\s*:?-{2,}:?\s*", c) for c in cells)

n = 0
N = len(rest)
hr_count = 0
while n < N:
    ln = rest[n]
    s = ln.strip()

    if s == "":
        n += 1
        continue

    # horizontal rule
    if re.fullmatch(r"-{3,}", s):
        # ignore divider rules between chapters (sections already separate visually)
        n += 1
        continue

    # heading
    hm = re.match(r"^(#{2,6})\s+(.*)$", ln)
    if hm:
        level = len(hm.group(1))
        htext = hm.group(2).strip()
        if level == 2:
            close_section()
            sec_n += 1
            sid = f"sec-{sec_n}"
            toc.append((sid, htext))
            out.append(f'<section class="chapter" id="{sid}">')
            in_section = True
            out.append(f'<h2 class="ch-head"><span class="ch-rule" aria-hidden="true"></span>{inline(htext)}</h2>')
        else:
            tag = f"h{level}"
            out.append(f'<{tag}>{inline(htext)}</{tag}>')
        n += 1
        continue

    # footnote definition (reference entry)
    dm = def_re.match(ln)
    if dm:
        lab = dm.group(1)
        num = fn_order.get(lab, "?")
        bodytext = ln[dm.end():].strip()
        out.append(
            f'<div class="ref-entry" id="fn-{lab}">'
            f'<span class="ref-num">{num}</span>'
            f'<div class="ref-body">{inline(bodytext)} '
            f'<a class="fn-back" href="#fnref-{lab}" aria-label="返回正文">↩</a></div>'
            f'</div>'
        )
        n += 1
        continue

    # table
    if "|" in s and n + 1 < N and is_table_sep(rest[n + 1]):
        header = [c.strip() for c in s.strip("|").split("|")]
        n += 2
        rows = []
        while n < N and "|" in rest[n].strip() and rest[n].strip():
            rows.append([c.strip() for c in rest[n].strip().strip("|").split("|")])
            n += 1
        thead = "".join(f"<th>{inline(c)}</th>" for c in header)
        body_html = []
        for r in rows:
            while len(r) < len(header):
                r.append("")
            tds = "".join(f"<td>{deco_cell(inline(c))}</td>" for c in r)
            body_html.append(f"<tr>{tds}</tr>")
        out.append(
            '<div class="table-wrap"><table>'
            f"<thead><tr>{thead}</tr></thead>"
            f'<tbody>{"".join(body_html)}</tbody>'
            "</table></div>"
        )
        continue

    # blockquote (callout)
    if s.startswith(">"):
        buf = []
        while n < N and rest[n].strip().startswith(">"):
            buf.append(rest[n].strip().lstrip(">").strip())
            n += 1
        inner = " ".join(b for b in buf if b)
        out.append(f'<aside class="note"><div class="note-mark" aria-hidden="true"></div>'
                   f'<p>{inline(inner)}</p></aside>')
        continue

    # ordered list
    if re.match(r"^\d+\.\s", s):
        items = []
        while n < N and re.match(r"^\d+\.\s", rest[n].strip()):
            items.append(re.sub(r"^\d+\.\s", "", rest[n].strip()))
            n += 1
        lis = "".join(f"<li>{inline(it)}</li>" for it in items)
        out.append(f"<ol>{lis}</ol>")
        continue

    # unordered list
    if re.match(r"^[-*]\s", s):
        items = []
        while n < N and re.match(r"^[-*]\s", rest[n].strip()) and not re.fullmatch(r"-{3,}", rest[n].strip()):
            items.append(re.sub(r"^[-*]\s", "", rest[n].strip()))
            n += 1
        lis = "".join(f"<li>{inline(it)}</li>" for it in items)
        out.append(f"<ul>{lis}</ul>")
        continue

    # paragraph (gather consecutive plain lines)
    buf = [s]
    n += 1
    while n < N:
        nx = rest[n].strip()
        if (nx == "" or nx.startswith(("#", ">", "|", "-", "*"))
                or re.match(r"^\d+\.\s", nx) or def_re.match(rest[n])):
            break
        buf.append(nx)
        n += 1
    para = " ".join(buf)
    cls = ""
    if para.startswith("*") and para.endswith("*") and "报告完" in para:
        out.append(f'<p class="endmark">{inline(para.strip("*"))}</p>')
    elif para.startswith("*") and para.endswith("*"):
        out.append(f'<p class="fineprint">{inline(para)}</p>')
    else:
        out.append(f"<p>{inline(para)}</p>")

close_section()
content = "\n".join(out)

# ---------- cover pieces ----------
subtitle = fm.get("副标题", "")
position = fm.get("定位", "")
keywords = fm.get("关键词", "")
kw_chips = ""
if keywords:
    parts = [p.strip() for p in re.split(r"\s*·\s*", keywords) if p.strip()]
    kw_chips = "".join(f'<li>{inline(p)}</li>' for p in parts)

toc_html = "".join(
    f'<li><a href="#{sid}" data-target="{sid}">{inline(t)}</a></li>' for sid, t in toc
)

CSS = r"""
:root{
  --bg:#ffffff;
  --surface:#faf7f5;
  --surface-2:#f5efec;
  --ink:#231d1b;
  --ink-soft:#4f4744;
  --muted:#6a615d;
  --rule:#e8e1dc;
  --rule-soft:#f0ebe7;
  --accent:#a32a45;
  --accent-deep:#7c1d33;
  --accent-tint:#fbeef1;
  --accent-soft:#f6e2e7;
  --g:#2f8f5b; --y:#c8881b; --r:#bb2d3b;
  --maxw:44rem;
  --serif:"Newsreader","Songti SC","STSong","Noto Serif SC","Source Han Serif SC",Georgia,serif;
  --sans:"PingFang SC","Hiragino Sans GB","Microsoft YaHei",-apple-system,system-ui,"Segoe UI",sans-serif;
  --z-toc:10; --z-bar:20;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
body{
  margin:0;background:var(--bg);color:var(--ink);
  font-family:var(--sans);font-size:17px;line-height:1.9;
  -webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility;
  font-feature-settings:"kern" 1;
}
::selection{background:var(--accent-soft);color:var(--accent-deep)}

/* reading progress bar */
.progress{position:fixed;top:0;left:0;height:2px;width:0;background:var(--accent);z-index:var(--z-bar);transition:width .1s linear}
@media (prefers-reduced-motion:reduce){.progress{transition:none}}

a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline;text-underline-offset:3px;text-decoration-thickness:1px}

/* ---------- COVER ---------- */
.cover{max-width:52rem;margin:0 auto;padding:clamp(3.5rem,8vw,6.5rem) 1.5rem clamp(2rem,4vw,3rem)}
.kicker{display:inline-flex;align-items:center;gap:.6em;font-size:.74rem;letter-spacing:.18em;
  text-transform:uppercase;color:var(--accent);font-weight:600;margin-bottom:1.6rem}
.kicker::before{content:"";width:1.6rem;height:1px;background:var(--accent)}
.cover h1{
  font-family:var(--serif);font-weight:600;
  font-size:clamp(2rem,5.2vw,3.5rem);line-height:1.12;letter-spacing:-.01em;
  margin:0 0 1.2rem;color:var(--ink);text-wrap:balance;max-width:20ch;
}
.cover .subtitle{font-size:clamp(1.02rem,2.2vw,1.22rem);color:var(--ink-soft);
  line-height:1.6;max-width:46ch;margin:0 0 2rem;font-weight:400}
.cover .subtitle em{font-style:normal;color:var(--accent-deep)}
.meta-row{display:flex;flex-wrap:wrap;gap:.7rem 1.4rem;align-items:center;
  padding-top:1.4rem;border-top:1px solid var(--rule);font-size:.86rem;color:var(--muted)}
.badge{display:inline-flex;align-items:center;gap:.45em;padding:.28em .8em;border-radius:999px;
  background:var(--accent-tint);color:var(--accent-deep);font-weight:600;font-size:.78rem;letter-spacing:.02em}
.badge .dot{width:.5em;height:.5em;border-radius:50%;background:var(--accent)}
.kw{list-style:none;display:flex;flex-wrap:wrap;gap:.5rem;padding:0;margin:1.6rem 0 0}
.kw li{font-size:.78rem;color:var(--ink-soft);padding:.3em .8em;border:1px solid var(--rule);
  border-radius:6px;background:var(--surface)}

/* ---------- LAYOUT ---------- */
.layout{max-width:74rem;margin:0 auto;padding:0 1.5rem 5rem;
  display:grid;grid-template-columns:1fr;gap:2.5rem}
@media (min-width:1080px){
  .layout{grid-template-columns:15rem minmax(0,1fr);gap:4rem;align-items:start}
}

/* ---------- TOC ---------- */
.toc{font-size:.85rem}
.toc .toc-title{font-size:.72rem;letter-spacing:.16em;text-transform:uppercase;
  color:var(--muted);font-weight:600;margin:0 0 1rem;padding-bottom:.7rem;border-bottom:1px solid var(--rule)}
.toc ol{list-style:none;margin:0;padding:0;counter-reset:toc}
.toc li{margin:0}
.toc a{display:block;color:var(--ink-soft);padding:.42em 0 .42em .9rem;
  border-left:1px solid var(--rule-soft);line-height:1.4;transition:color .18s,border-color .18s}
.toc a:hover{color:var(--ink);text-decoration:none;border-left-color:var(--accent-soft)}
.toc a.active{color:var(--accent-deep);font-weight:600;border-left-color:var(--accent)}
@media (min-width:1080px){
  .toc{position:sticky;top:2.2rem;max-height:calc(100vh - 4rem);overflow-y:auto;
    padding-right:.4rem;-webkit-overflow-scrolling:touch}
  .toc::-webkit-scrollbar{width:5px}
  .toc::-webkit-scrollbar-thumb{background:var(--rule);border-radius:3px}
}
@media (max-width:1079px){
  .toc{background:var(--surface);border:1px solid var(--rule);border-radius:12px;padding:1.2rem 1.3rem}
}

/* ---------- PROSE ---------- */
.prose{max-width:var(--maxw);min-width:0}
.chapter{padding-top:1rem;margin-bottom:2.4rem}
.chapter+.chapter{border-top:1px solid var(--rule-soft);margin-top:1rem;padding-top:2.8rem}
.ch-head{font-family:var(--serif);font-weight:600;font-size:clamp(1.5rem,3.4vw,2.1rem);
  line-height:1.22;letter-spacing:-.005em;color:var(--ink);margin:0 0 1.4rem;
  scroll-margin-top:1.5rem;text-wrap:balance;display:flex;align-items:baseline;gap:.7rem}
.ch-rule{flex:0 0 auto;width:.4rem;height:.4rem;border-radius:50%;background:var(--accent);
  transform:translateY(-.18em)}
h3{font-family:var(--serif);font-weight:600;font-size:1.28rem;line-height:1.35;
  color:var(--ink);margin:2.4rem 0 .9rem;letter-spacing:-.003em;scroll-margin-top:1.5rem}
h4{font-weight:700;font-size:1.02rem;color:var(--accent-deep);margin:1.8rem 0 .7rem;letter-spacing:.01em}
.prose p{margin:0 0 1.1rem;color:var(--ink-soft);text-wrap:pretty}
.prose strong{color:var(--ink);font-weight:700}
.prose em{color:var(--ink);font-style:italic}
.prose>section p{hyphens:none}

/* lists */
.prose ul,.prose ol{margin:0 0 1.3rem;padding-left:0;color:var(--ink-soft)}
.prose ul{list-style:none}
.prose ul li{position:relative;padding-left:1.5rem;margin:.5em 0}
.prose ul li::before{content:"";position:absolute;left:.2rem;top:.72em;width:.42rem;height:.42rem;
  border-radius:50%;border:1.5px solid var(--accent);background:transparent}
.prose ol{list-style:none;counter-reset:li}
.prose ol li{position:relative;padding-left:2.1rem;margin:.7em 0;counter-increment:li}
.prose ol li::before{content:counter(li);position:absolute;left:0;top:.05em;
  width:1.5rem;height:1.5rem;display:grid;place-items:center;font-family:var(--serif);
  font-size:.82rem;font-weight:600;color:var(--accent-deep);background:var(--accent-tint);border-radius:50%}
.prose li strong:first-child{color:var(--ink)}

/* code */
code{font-family:"SF Mono",ui-monospace,"JetBrains Mono",Menlo,monospace;font-size:.85em;
  background:var(--surface-2);padding:.12em .4em;border-radius:4px;color:var(--accent-deep)}

/* ---------- NOTE / CALLOUT ---------- */
.note{position:relative;background:var(--surface);border:1px solid var(--rule);border-radius:12px;
  padding:1.1rem 1.3rem 1.1rem 2.5rem;margin:1.5rem 0;font-size:.96rem}
.note .note-mark{position:absolute;left:1rem;top:1.25rem;width:1rem;height:1rem;border-radius:50%;
  background:var(--accent-tint)}
.note .note-mark::after{content:"i";position:absolute;inset:0;display:grid;place-items:center;
  font-family:var(--serif);font-style:italic;font-size:.7rem;font-weight:600;color:var(--accent-deep)}
.note p{margin:0;color:var(--ink-soft)}
.note strong{color:var(--accent-deep)}

/* ---------- TABLES ---------- */
.table-wrap{margin:1.6rem 0;overflow-x:auto;border-radius:10px;-webkit-overflow-scrolling:touch}
table{width:100%;border-collapse:collapse;font-size:.92rem;line-height:1.55;min-width:30rem}
thead th{text-align:left;font-weight:700;color:var(--ink);padding:.85em 1em;
  background:var(--surface);border-bottom:2px solid var(--accent);white-space:nowrap;vertical-align:bottom}
tbody td{padding:.8em 1em;border-bottom:1px solid var(--rule);color:var(--ink-soft);vertical-align:top}
tbody tr:last-child td{border-bottom:1px solid var(--rule)}
tbody tr:hover td{background:var(--surface)}
table strong{color:var(--ink)}
td:first-child{color:var(--ink)}

/* signal lights */
.sig{display:inline-flex;align-items:center;gap:.5em;font-weight:600;white-space:nowrap}
.sig .dot{width:.7em;height:.7em;border-radius:50%;flex:0 0 auto;box-shadow:0 0 0 3px rgba(0,0,0,.04)}
.sig-g{color:var(--g)} .sig-g .dot{background:var(--g)}
.sig-y{color:var(--y)} .sig-y .dot{background:var(--y)}
.sig-r{color:var(--r)} .sig-r .dot{background:var(--r)}

/* ---------- footnotes / references ---------- */
.fnref{font-feature-settings:"sups";line-height:0}
.fnref a{font-size:.72em;font-weight:600;padding:0 .15em;color:var(--accent);
  text-decoration:none;vertical-align:super}
.fnref a:hover{text-decoration:underline}
#sec-%REFSEC% .ref-entry{display:grid;grid-template-columns:2rem 1fr;gap:.7rem;
  padding:.85rem 0;border-bottom:1px solid var(--rule-soft);font-size:.86rem;line-height:1.65;
  scroll-margin-top:2rem}
.ref-entry{display:grid;grid-template-columns:2rem 1fr;gap:.7rem;
  padding:.85rem 0;border-bottom:1px solid var(--rule-soft);font-size:.86rem;line-height:1.65;
  scroll-margin-top:2rem;color:var(--muted)}
.ref-entry:target{background:var(--accent-tint);border-radius:8px;
  padding-left:.7rem;padding-right:.7rem;margin:0 -.7rem}
.ref-num{font-family:var(--serif);font-weight:600;color:var(--accent-deep);text-align:right;
  font-size:.9rem;padding-top:.05em}
.ref-body{color:var(--muted)}
.ref-body em{color:var(--ink-soft);font-style:italic}
.ref-body strong{color:var(--ink-soft)}
.fn-back{font-size:.85em;margin-left:.2em;text-decoration:none;opacity:.7}
.fn-back:hover{opacity:1}

.fineprint{font-size:.82rem;color:var(--muted);font-style:italic;line-height:1.7}
.endmark{text-align:center;font-family:var(--serif);font-style:italic;color:var(--muted);
  margin:2.5rem 0 1rem;letter-spacing:.05em}

/* footer */
.foot{max-width:74rem;margin:0 auto;padding:2.5rem 1.5rem 4rem;border-top:1px solid var(--rule);
  color:var(--muted);font-size:.8rem;line-height:1.7}
.foot strong{color:var(--ink-soft)}

/* reveal */
.chapter{opacity:1}
.reveal{opacity:0;transform:translateY(14px)}
.reveal.shown{opacity:1;transform:none;transition:opacity .7s cubic-bezier(.16,1,.3,1),transform .7s cubic-bezier(.16,1,.3,1)}
@media (prefers-reduced-motion:reduce){
  .reveal,.reveal.shown{opacity:1;transform:none;transition:none}
}

@media (max-width:600px){
  body{font-size:16px}
  .cover{padding-top:3rem}
  .note{padding-left:2.3rem}
}
"""

# patch reference section number into CSS (#sec-N target highlight not critical; replace placeholder)
ref_secnum = sec_n  # references is the last h2
CSS = CSS.replace("%REFSEC%", str(ref_secnum))

JS = r"""
(function(){
  var bar=document.querySelector('.progress');
  function onScroll(){
    var h=document.documentElement;
    var sc=h.scrollTop||document.body.scrollTop;
    var max=h.scrollHeight-h.clientHeight;
    if(bar)bar.style.width=(max>0?(sc/max*100):0)+'%';
  }
  document.addEventListener('scroll',onScroll,{passive:true});onScroll();

  var links=[].slice.call(document.querySelectorAll('.toc a'));
  var map={};links.forEach(function(a){map[a.dataset.target]=a;});
  var secs=[].slice.call(document.querySelectorAll('section.chapter'));

  if('IntersectionObserver' in window){
    var spy=new IntersectionObserver(function(es){
      es.forEach(function(e){
        if(e.isIntersecting){
          links.forEach(function(a){a.classList.remove('active');});
          var a=map[e.target.id];if(a)a.classList.add('active');
        }
      });
    },{rootMargin:'-15% 0px -70% 0px',threshold:0});
    secs.forEach(function(s){spy.observe(s);});

    var reduce=window.matchMedia('(prefers-reduced-motion:reduce)').matches;
    if(!reduce){
      secs.forEach(function(s){s.classList.add('reveal');});
      var rev=new IntersectionObserver(function(es){
        es.forEach(function(e){
          if(e.isIntersecting){e.target.classList.add('shown');rev.unobserve(e.target);}
        });
      },{rootMargin:'0px 0px -8% 0px',threshold:.06});
      secs.forEach(function(s){rev.observe(s);});
      // safety: never leave a section hidden (non-scrolling renderers, hidden tabs)
      setTimeout(function(){secs.forEach(function(s){s.classList.add('shown');});},1400);
    }
  }
})();
"""

doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(subtitle)}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400;1,6..72,500&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
<div class="progress" aria-hidden="true"></div>

<header class="cover">
  <div class="kicker">机密 · 内部立项决策材料</div>
  <h1>{inline(title)}</h1>
  <p class="subtitle">{inline(subtitle)}</p>
  <ul class="kw">{kw_chips}</ul>
  <div class="meta-row">
    <span class="badge"><span class="dot"></span>{inline(position)}</span>
    <span>经皮电刺激 · 非药物镇痛 · 女性健康</span>
  </div>
</header>

<div class="layout">
  <nav class="toc" aria-label="目录">
    <p class="toc-title">目录</p>
    <ol>{toc_html}</ol>
  </nav>
  <main class="prose">
{content}
  </main>
</div>

<footer class="foot">
  <p><strong>免责声明 ·</strong> 本报告为内部立项决策材料。所引研究多以 TENS / 电针 / 成人或术后人群为对象,可作机理与方向支持,不可直接等同于本产品形态的临床效果;迁移须以自有验证数据为准。所有功效宣称须以最终取得的医疗器械注册资质及获批适应症为限,法规分类与注册路径以专业法规顾问意见为准。</p>
</footer>

<script>{JS}</script>
</body>
</html>
"""

with open(OUT, "w", encoding="utf-8") as f:
    f.write(doc)
print("wrote", OUT, "| sections:", sec_n, "| footnotes:", len(fn_order))
