#!/usr/bin/env python3
"""A no-download first measurement. Run --demo, or pass one or two .md/.txt copies."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, sys, uuid
from stylo.explore import create_result, write_result
ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("samples",nargs="*",help="One passage, or two to compare. UTF-8 .md/.txt copies.")
    parser.add_argument("--demo",action="store_true",help="Use the included teaching samples; no downloads.")
    parser.add_argument("--output",type=Path,help="A NEW report folder. Existing folders are never overwritten.")
    args=parser.parse_args()
    if args.demo and args.samples:
        parser.error("Use --demo by itself, or supply your own samples.")
    paths=[ROOT/"examples"/name for name in ["sample-a.md","sample-b.md"]] if args.demo else [Path(p) for p in args.samples]
    output=args.output or ROOT/"reports"/("exploration-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")+"-"+uuid.uuid4().hex[:6])
    try:
        result=create_result(paths,demo=args.demo)
        report=write_result(result,output)
    except (OSError,UnicodeError,ValueError) as error:
        parser.exit(2,f"Let's fix one thing: {error}\nYour source passages were not changed. Use a new output folder for each run.\n")
    print(f"Your reading page: {report.resolve()}")
    print("Measurements describe these samples. There is no pass/fail result.")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
