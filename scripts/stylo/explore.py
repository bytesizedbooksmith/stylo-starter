"""Measure one or two passages without a registry, corpus, profile, or network."""
from datetime import datetime, timezone
from pathlib import Path
from html import escape
import hashlib, json
from .segment import make_document
from .features import measure
from .html_report import page

VERSION = "1.0"
MEASURES = (
    ("sent_mean","Average sentence length","words"),
    ("sent_median","Middle sentence length","words"),
    ("para_mean_words","Average paragraph length","words"),
    ("dialogue_word_pct","Words inside quotation marks","%"),
    ("para_one_sentence_pct","One-sentence paragraphs","%"),
    ("narr_emdash_per_1k","Em dashes in narration","per 1,000 narration words"),
)
def read_sample(path):
    path=Path(path)
    if path.suffix.lower() not in (".md",".txt"):
        raise ValueError(f"{path.name}: please use a Markdown or plain-text copy (.md or .txt). Keep the original document.")
    text=path.read_text(encoding="utf-8-sig")
    document=make_document(text,title=path.stem)
    if not document.paragraphs or not document.word_count:
        raise ValueError(f"{path.name}: no prose was found. Try a passage with ordinary paragraphs.")
    values=measure(document.paragraphs,document.proper_names())
    return {"source":path.name,"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
            "words":document.word_count,"paragraph_count":len(document.paragraphs),
            "paragraphs":[p.text for p in document.paragraphs],
            "measurements":{k:values[k] for k,_,_ in MEASURES}}

def display(key,value):
    return f"{value:.1f}"

def observations(samples):
    a=samples[0]["measurements"]
    if len(samples)==1:
        return [
            f"In this sample, a sentence averages {a['sent_mean']:.1f} words.",
            f"Paragraphs average {a['para_mean_words']:.1f} words.",
            f"{a['dialogue_word_pct']:.1f}% of the counted words are inside recognized quotation marks.",
        ]
    b=samples[1]["measurements"]; result=[]
    for key,label,unit in [
        ("sent_mean","Sentences average","words"),
        ("para_mean_words","Paragraphs average","words"),
        ("dialogue_word_pct","Words inside recognized quotation marks account for","%"),
    ]:
        suffix="" if unit=="%" else " "
        result.append(f"{label} {a[key]:.1f}{suffix}{unit} in sample A and {b[key]:.1f}{suffix}{unit} in sample B.")
    return result

def create_result(paths, *, demo=False):
    if not 1 <= len(paths) <= 2:
        raise ValueError("Choose one passage, or two passages to compare.")
    samples=[read_sample(p) for p in paths]
    return {"schema":"stylo-exploration/1","tool_version":VERSION,
            "generated_utc":datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "demo":demo,"mode":"comparison" if len(samples)==2 else "single passage",
            "samples":samples,"observations":observations(samples),
            "limits":[
                "These are descriptions of the supplied passages, not a stable author profile or a quality score.",
                "Short samples change easily. The demonstration is intentionally short so you can see what changes.",
                "Sentence boundaries and quotation handling follow the toolkit's English-oriented rules. Unusual dialogue formatting can affect results.",
                "Quoted words are an estimate of dialogue: a quoted letter or thought can be counted too.",
                "Subject, scene purpose and editing stage can explain a difference. A difference need not be repaired.",
            ]}

def result_markdown(result):
    lines=["# Stylo exploration","",
           f"- Mode: {result['mode']}",f"- Measured at: {result['generated_utc']}",
           f"- Tool version: {result['tool_version']}",
           "- Status: measured observations; author interpretation pending","",
           "## Inputs"]
    for i,s in enumerate(result["samples"]):
        lines += [f"- Sample {'AB'[i]}: {s['source']}; {s['words']} words; SHA-256 {s['sha256']}"]
    lines += ["","## Observations"]+["- "+s for s in result["observations"]]
    lines += ["","## Measurements","| Measure | Sample A |"+(" Sample B |" if len(result["samples"])==2 else ""),
              "|---|---:|"+("---:|" if len(result["samples"])==2 else "")]
    for key,label,unit in MEASURES:
        lines.append("| "+label+" ("+unit+") | "+" | ".join(display(key,s["measurements"][key]) for s in result["samples"])+" |")
    lines += ["","## Limits"]+["- "+x for x in result["limits"]]
    lines += ["","## Author choices","Pending. Ask what they notice or prefer. Do not infer preferences from numbers.","",
              "## Next step","Offer one small, optional experiment. Do not rewrite source files or call this an author fingerprint."]
    return "\n".join(lines)+"\n"

def voice_notes(result):
    # Deliberately not a fabricated measured author profile.
    return """# Voice notes — provisional
Status: author review needed
Source: report.md from this exploration

## Observations
"""+'\n'.join('- '+x for x in result["observations"])+"""

## Preferences the author has actually confirmed
None yet. Ask; do not turn an observed number into a preferred target.

## Intentional differences
Not yet discussed.

## What to try, if the author wants
One small change on a separate copy. Preserve mixed emotions, intentional rhythm and the author's right to prefer the original.

These samples do not establish stable author-wide ranges.
"""

def result_html(result):
    samples=result["samples"]
    body='<p class="eyebrow">A small experiment · no score to chase</p><h1>What do you notice?</h1>'
    body+='<p class="lede">Here are a few patterns in these passages. You get to decide whether any of them matter.</p>'
    if result["demo"]:
        body+='<div class="welcome"><p><strong>These are original teaching samples written for this kit.</strong> They are two treatments of the same moment, not models of a real author’s voice. Neither is the right answer.</p></div>'
    body+='<div class="facts">'
    for i,s in enumerate(samples):
        body+=f'<div class="fact">Sample {"AB"[i]}<strong>{s["words"]} words</strong>{s["paragraph_count"]} paragraphs</div>'
    body+='</div><h2>Three things we can count</h2><ul>'+''.join('<li>'+escape(x)+'</li>' for x in result["observations"])+'</ul>'
    body+='<h2>What those numbers leave open</h2><p>Shorter sentences may feel brisk, hesitant, emphatic—or something else in context. More quoted words do not automatically mean better dialogue. Read the passages before deciding what a difference means.</p>'
    for i,s in enumerate(samples):
        body+=f'<details open><summary>Read sample {"AB"[i]} · {escape(s["source"])}</summary><div class="reading">'
        body+=''.join('<p>'+escape(p)+'</p>' for p in s["paragraphs"])+'</div></details>'
    body+='<div class="welcome"><h2>One question is enough.</h2><p>Which passage—or which part of either passage—feels closer to what you want today?</p><p>“A bit of both,” “neither,” and “I’m not sure” are useful answers. You can keep a difference on purpose.</p></div>'
    body+='<h2>If you feel like experimenting</h2><p>Try changing one paragraph on a copy, then compare again. Stop when you have learned something useful; you do not need to make the numbers match.</p>'
    body+='<details><summary>The measurements, if you are curious</summary><div class="table-scroll"><table><thead><tr><th>Measure</th>'
    body+=''.join('<th>Sample '+ 'AB'[i] +'</th>' for i in range(len(samples)))+'</tr></thead><tbody>'
    for key,label,unit in MEASURES:
        body+='<tr><td>'+escape(label)+'<br><span class="metric-note">'+escape(unit)+'</span></td>'
        body+=''.join('<td>'+display(key,s["measurements"][key])+'</td>' for s in samples)+'</tr>'
    body+='</tbody></table></div></details>'
    body+='<details><summary>How to read this fairly</summary><ul>'+''.join('<li>'+escape(x)+'</li>' for x in result["limits"])+'</ul>'
    body+='<p>Measured locally at '+escape(result["generated_utc"])+'. Tool version '+escape(result["tool_version"])+'. Input fingerprints are recorded in the Markdown and structured report.</p></details>'
    return page("Your prose exploration",body)

def write_result(result, output):
    output=Path(output)
    # Do not overwrite a previous result or any source directory.
    output.mkdir(parents=True,exist_ok=False)
    (output/"report.html").write_text(result_html(result),encoding="utf-8")
    (output/"report.md").write_text(result_markdown(result),encoding="utf-8")
    (output/"voice-notes.md").write_text(voice_notes(result),encoding="utf-8")
    from .html_report import markdown_page
    (output/"voice-notes.html").write_text(markdown_page("Provisional voice notes",voice_notes(result)),encoding="utf-8")
    # Raw paragraphs stay in the local HTML reading view; structured counts need not duplicate them.
    structured={**result,"samples":[{k:v for k,v in s.items() if k!="paragraphs"} for s in result["samples"]]}
    (output/"measurements.json").write_text(json.dumps(structured,indent=2,ensure_ascii=False),encoding="utf-8")
    return output/"report.html"
