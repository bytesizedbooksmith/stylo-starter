"""Integration checks for first-use exploration and optional profile HTML."""
from pathlib import Path
import csv, hashlib, json, os, subprocess, sys, tempfile, unittest
from stylo.explore import create_result, write_result, result_html
ROOT=Path(__file__).resolve().parents[1]
class ExplorationTests(unittest.TestCase):
    def test_counts_and_source_preservation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);a=root/"a.md";b=root/"b.txt"
            a.write_text("# Heading\n\nShe came. He left.\n\nShe waited.",encoding="utf-8")
            b.write_text("She came and he left while she waited.",encoding="utf-8")
            before={p:p.read_bytes() for p in (a,b)}
            r=create_result([a,b]);self.assertEqual(r["samples"][0]["words"],6)
            self.assertEqual(r["samples"][0]["measurements"]["sent_mean"],2)
            self.assertEqual(r["samples"][0]["paragraph_count"],2)
            output=root/"new-report";write_result(r,output)
            self.assertTrue((output/"report.html").exists())
            self.assertTrue((output/"voice-notes.html").exists())
            structured=json.loads((output/"measurements.json").read_text(encoding="utf-8"))
            self.assertNotIn("paragraphs",structured["samples"][0])
            with self.assertRaises(FileExistsError):write_result(r,output)
            for p,original in before.items():self.assertEqual(p.read_bytes(),original)
    def test_escape_and_untrusted_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"sample.md";p.write_text('She read <script>alert("x")</script> and waited.',encoding="utf-8")
            html=result_html(create_result([p]))
            self.assertNotIn('<script>alert',html);self.assertIn('&lt;script&gt;',html)
    def test_bad_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"blank.md";p.write_text("# Heading\n",encoding="utf-8")
            with self.assertRaises(ValueError):create_result([p])
            with self.assertRaises(ValueError):create_result([])
            with self.assertRaises(ValueError):create_result([p,p,p])
            p=Path(tmp)/"a.docx";p.write_bytes(b"not prose")
            with self.assertRaises(ValueError):create_result([p])
    def test_cli_without_corpus_and_repeat(self):
        with tempfile.TemporaryDirectory() as tmp:
            env={**os.environ,"STYLO_DATA_ROOT":str(Path(tmp)/"no-corpus"),"PYTHONDONTWRITEBYTECODE":"1"}
            out=Path(tmp)/"demo"
            cmd=[sys.executable,str(ROOT/"scripts/stylo_explore.py"),"--demo","--output",str(out)]
            run=subprocess.run(cmd,env=env,capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr)
            report=json.loads((out/"measurements.json").read_text(encoding="utf-8"))
            self.assertEqual(len(report["samples"]),2)
            again=subprocess.run(cmd,env=env,capture_output=True,text=True)
            self.assertEqual(again.returncode,2);self.assertIn("not changed",again.stderr)
            missing=subprocess.run([sys.executable,str(ROOT/"scripts/stylo_explore.py"),str(Path(tmp)/"missing.md")],env=env,capture_output=True,text=True)
            self.assertEqual(missing.returncode,2);self.assertNotIn("Traceback",missing.stderr)
    def test_full_profiles_and_audit_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            data=Path(tmp);rows=[];registry={}
            # Artificial fixtures exercise the plumbing, not author recognition quality.
            for slug,sample in [("sample-a","sample-a.md"),("sample-b","sample-b.md")]:
                work=data/"authors"/slug/"works"/"fixture.md";work.parent.mkdir(parents=True)
                prose=(ROOT/"examples"/sample).read_text(encoding="utf-8").split("\n",1)[1]
                work.write_text((prose+"\n")*32,encoding="utf-8")
                registry[slug]={"slug":slug,"name":slug,"short":slug,"genre":"test fixture","period":"test"}
                rows.append({"author":slug,"author_folder":"authors/"+slug,"title":"Fixture","original_publication_year":"2026","markdown_path":work.relative_to(data).as_posix(),"work_type":"novel"})
            (data/"registry.json").write_text(json.dumps(registry),encoding="utf-8")
            with (data/"catalog.csv").open("w",newline="",encoding="utf-8") as f:
                w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
            env={**os.environ,"STYLO_DATA_ROOT":str(data),"PYTHONDONTWRITEBYTECODE":"1"}
            run=subprocess.run([sys.executable,str(ROOT/"scripts/build_stylo_profiles.py")],env=env,capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr)
            for slug in registry:
                p=data/"authors"/slug/"profile"
                self.assertTrue((p/(slug+"-stylometry-report.html")).is_file())
                self.assertTrue((p/(slug+"-style-card.html")).is_file())
            out=data/"audit"
            run=subprocess.run([sys.executable,str(ROOT/"scripts/stylo_check.py"),str(ROOT/"examples/sample-a.md"),"--author","sample-a","--output-dir",str(out)],env=env,capture_output=True,text=True)
            self.assertIn(run.returncode,(0,1),run.stderr)
            self.assertTrue((out/"report.html").is_file())
            self.assertTrue((out/"report.md").is_file())
            self.assertTrue(list((data/"stylometry").glob("*.html")))
    def test_missing_profile_sources_are_explained(self):
        with tempfile.TemporaryDirectory() as tmp:
            env={**os.environ,"STYLO_DATA_ROOT":str(Path(tmp)/"unconfigured"),"PYTHONDONTWRITEBYTECODE":"1"}
            run=subprocess.run([sys.executable,str(ROOT/"scripts/build_stylo_profiles.py")],capture_output=True,text=True,env=env)
        self.assertEqual(run.returncode,2)
        self.assertIn("stylo_explore.py --demo",run.stderr)
        self.assertNotIn("Traceback",run.stderr)
if __name__=="__main__":
    unittest.main(verbosity=2)
