#!/usr/bin/env python3
"""
Inject transits.json into index.html to produce the self-contained
graha-transits.html (double-clickable, no server needed).

index.html normally fetches transits.json at runtime; this bakes the data into
its #embedded-data <script> so the output opens straight from disk, offline.

Usage:
  python3 build_site.py            # uses transits.json + index.html
  python3 build_site.py --data transits.json --template index.html --out graha-transits.html
"""
import argparse

ap = argparse.ArgumentParser()
ap.add_argument("--data", default="transits.json")
ap.add_argument("--template", default="index.html")
ap.add_argument("--out", default="graha-transits.html")
args = ap.parse_args()

with open(args.template, encoding="utf-8") as f:
    tpl = f.read()
if "__DATA__" not in tpl:
    raise SystemExit(f"{args.template} has no __DATA__ placeholder to inject into.")
with open(args.data, encoding="utf-8") as f:
    data = f.read()

# guard against a literal </script> inside the JSON breaking the tag
data = data.replace("</", "<\\/")

with open(args.out, "w", encoding="utf-8") as f:
    f.write(tpl.replace("__DATA__", data))

print(f"Wrote {args.out}")
