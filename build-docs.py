"""Build the standalone Stylo guide and its measured demonstration."""
from pathlib import Path
from html import escape
import re, json, sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/"scripts"))
from stylo.guide_style import STYLE, SCRIPT
from stylo.html_report import markdown_html, markdown_page
from stylo.explore import create_result, result_html, result_markdown, voice_notes
PAGES=[
("overview","index","Welcome","Start small"),
("demo","demo","See the example","Start small"),
("start-here","start-here","Try it with your AI","Start small"),
("setup","setup","Setup help","Start small"),
("reading-results","reading-results","Read the results","Start small"),
("help","help","When you're stuck","Start small"),
("customize","customize","Change one thing","Start small"),
("modules","modules","Module menu","Optional modules"),
("profiles","profiles","Personal profiles","Optional modules"),
("pen-names","pen-names","Pen names & periods","Optional modules"),
("dialogue","dialogue","Dialogue & narration","Optional modules"),
("advanced","advanced","Advanced comparisons","Optional modules"),
("longer-work","longer-work","Longer work","Optional modules"),
("book-machine","book-machine","Book Machine connection","Optional modules"),
("credits","credits","Credits & thanks","Explore later"),
("maintain","maintain","Adapt your copy","Explore later"),
]
def nav(current,prefix=""):
    s='<a class="skip" href="#main">Skip to content</a><nav class="sidebar" aria-label="Guide"><a class="brand" href="'+prefix+'index.html">Stylo Starter</a><p class="tag">A Byte-Sized Booksmith starter kit</p>'
    for group in ("Start small","Optional modules","Explore later"):
        items=[(out,label) for _,out,label,g in PAGES if g==group]
        if group=="Start small":s+='<span class="navlabel">Start small</span>'
        else:s+='<details'+(' open' if current in [out for out,_ in items] else '')+'><summary>'+group+'</summary>'
        s+='<ul>'
        for out,label in items:
            s+='<li><a href="'+prefix+out+'.html"'+(' aria-current="page"' if current==out else '')+'>'+escape(label)+'</a></li>'
        s+='</ul>'
        if group!="Start small":s+='</details>'
    return s+'</nav>'
def shell(title,body,current,prefix=""):
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+escape(title)+' · Stylo</title><link rel="stylesheet" href="'+prefix+'style.css"><script defer src="'+prefix+'guide.js"></script></head><body>'+nav(current,prefix)+'<main class="content" id="main">'+body+'<footer class="pagefoot">Stylo Starter · Angie Hartwell / Byte-Sized Booksmith<br><a href="'+prefix+'credits.html">Credits &amp; thanks</a> · <a href="'+prefix+'license.html">License</a> · September 2026</footer></main></body></html>'
def build():
    guide=ROOT/"guide";guide.mkdir(exist_ok=True)
    css=STYLE+"\n.table-scroll{overflow:auto;max-width:100%}.facts{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px}.fact{padding:16px;background:var(--pale);border-radius:8px}.fact strong{display:block;font-size:24px}.metric-note{font:12px/1.5 system-ui,sans-serif}\n"
    (guide/"style.css").write_text(css,encoding="utf-8")
    (guide/"guide.js").write_text(SCRIPT,encoding="utf-8")
    demo=create_result([ROOT/"examples/sample-a.md",ROOT/"examples/sample-b.md"],demo=True)
    results=ROOT/"examples/results";results.mkdir(exist_ok=True)
    prior=results/"measurements.json"
    if prior.exists():
        old=json.loads(prior.read_text(encoding="utf-8"))
        if old.get("tool_version")==demo["tool_version"] and [s["sha256"] for s in old.get("samples",[])]==[s["sha256"] for s in demo["samples"]]:
            demo["generated_utc"]=old["generated_utc"]
    (results/"report.html").write_text(result_html(demo),encoding="utf-8")
    (results/"report.md").write_text(result_markdown(demo),encoding="utf-8")
    (results/"voice-notes.md").write_text(voice_notes(demo),encoding="utf-8")
    (results/"voice-notes.html").write_text(markdown_page("Provisional voice notes",voice_notes(demo)),encoding="utf-8")
    structured={**demo,"samples":[{k:v for k,v in s.items() if k!="paragraphs"} for s in demo["samples"]]}
    prior.write_text(json.dumps(structured,indent=2,ensure_ascii=False),encoding="utf-8")
    demo_body=re.search(r'<main class="content" id="main">(.*?)<footer',result_html(demo),re.S).group(1)
    # The surrounding guide already supplies the page title and introduction.
    demo_body=re.sub(r'^.*?</h1>', '', demo_body, count=1, flags=re.S)
    for src,out,label,_ in PAGES:
        body=(ROOT/"docs-src"/(src+".html")).read_text(encoding="utf-8")
        body=body.replace("<!--DEMO-->",demo_body)
        (guide/(out+".html")).write_text(shell(label,body,out),encoding="utf-8")
    license_body='<h1>MIT License</h1><p>Keep this copyright and permission notice with copies or substantial portions of the software.</p>'+''.join('<p>'+escape(p)+'</p>' for p in (ROOT/"LICENSE").read_text(encoding="utf-8").split('\n\n'))
    (guide/"license.html").write_text(shell("License",license_body,"license"),encoding="utf-8")
    welcome=(ROOT/"docs-src/overview.html").read_text(encoding="utf-8")
    welcome=re.sub(r'href="(?!https?:|#)([^"]+)"',r'href="guide/\1"',welcome)
    (ROOT/"START-HERE.html").write_text(shell("Welcome",welcome,"index","guide/"),encoding="utf-8")
    print(f"Built {len(PAGES)+2} guide pages and the measured demo.")
if __name__=="__main__":
    build()
