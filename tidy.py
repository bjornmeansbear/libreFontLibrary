#!/usr/bin/env python3
"""Put the repo in the shape the manifest describes. Dry run unless --apply.

  delete  the X11 font-server index files committed by accident
  delete  loose files of any family that isn't libre (license personal-use-only)
  delete  loose 2019 files whose family has been fetched fresh into Families/
  move    every other loose file into Unsorted/<Family>/ — kept, but not
          installed, until its family is fetched with its license

Reads audit/claims.json (which file belongs to which family), written by
build_manifest.py — run that after fetch.py and before this. Uses git rm and
git mv, so every change is in history and can be undone.
"""
import argparse, json, re, shutil, subprocess, time, tomllib
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
JUNK = ["fonts.dir", "fonts.scale", "fonts.list", "encodings.dir"]
NOT_LIBRE = {"personal-use-only"}
KEEP_DIRS = {".git", "Families", "Unsorted", "audit"}
FONT = (".otf", ".ttf", ".woff", ".woff2")
safe = lambda n: re.sub(r"[^A-Za-z0-9._-]+", "-", n).strip("-")


def git(*a):
    """Retry when another git process holds the index — an editor refreshing
    the repo mid-run is enough to fail one of hundreds of calls."""
    for attempt in range(20):
        r = subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True)
        if r.returncode == 0 or "index.lock" not in r.stderr:
            return r
        time.sleep(0.5)
    return r


def remove(path):
    """git rm, or a plain delete for a file git doesn't track."""
    r = git("rm", "-q", path)
    if r.returncode and "did not match any files" in r.stderr:
        (ROOT / path).unlink()
    elif r.returncode:
        raise RuntimeError(f"git rm {path}: {r.stderr.strip()}")


def move(path, dest):
    """git mv, or a plain move for a file git doesn't track."""
    (ROOT / dest).parent.mkdir(parents=True, exist_ok=True)
    r = git("mv", path, dest)
    if r.returncode and "not under version control" in r.stderr:
        shutil.move(ROOT / path, ROOT / dest)
    elif r.returncode:
        raise RuntimeError(f"git mv {path}: {r.stderr.strip()}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="make the changes (default: just report)")
    args = ap.parse_args()

    claims = json.loads((ROOT / "audit/claims.json").read_text())
    fams = {f["name"]: f for f in tomllib.loads((ROOT / "fonts.toml").read_text())["family"]}
    plan = defaultdict(list)      # reason -> [(path, destination or None)]

    for j in JUNK:
        if (ROOT / j).exists():
            plan["delete — X11 index junk"].append((j, None))

    dir_action = {}               # top-level family folder -> what its fonts got
    for path, name in sorted(claims.items()):
        if not (ROOT / path).exists() or path.startswith("Unsorted/"):
            continue                          # gone already, or already sorted
        f = fams.get(name, {})
        if f.get("license") in NOT_LIBRE:
            reason, dest = "delete — not libre", None
        elif f.get("fetched"):
            reason, dest = "delete — fetched fresh into Families/", None
        else:
            reason, dest = "move — to Unsorted/, not fetched yet", f"Unsorted/{safe(name)}/{Path(path).name}"
        plan[reason].append((path, dest))
        parts = Path(path).parts
        if len(parts) > 1:
            dir_action[parts[0]] = (reason, f"Unsorted/{safe(name)}" if dest else None)

    # a family folder's license and readme files follow its fonts
    for d, (reason, dest_dir) in dir_action.items():
        for p in (ROOT / d).rglob("*"):
            rel = str(p.relative_to(ROOT))
            if p.is_file() and not p.name.lower().endswith(FONT) and rel not in claims:
                plan[reason].append((rel, f"{dest_dir}/{p.name}" if dest_dir else None))

    for reason, items in sorted(plan.items()):
        mb = sum((ROOT / p).stat().st_size for p, _ in items) / 1e6
        print(f"{reason}: {len(items)} files, {mb:.1f} MB")
    moved = sorted({d.split("/")[1] for items in plan.values() for _, d in items if d})
    print(f"\nUnsorted/ would hold {len(moved)} families: {', '.join(moved)}")
    gone = sorted({claims[p] for r, items in plan.items() if 'not libre' in r for p, _ in items if p in claims})
    if gone:
        print(f"not libre, deleted: {', '.join(gone)}")

    if not args.apply:
        print("\ndry run — nothing changed. Re-run with --apply to do it.")
        return
    for reason, items in plan.items():
        for path, dest in items:
            if not (ROOT / path).exists():
                continue                      # a resumed run: already done
            move(path, dest) if dest else remove(path)
    for p in sorted(ROOT.rglob("*"), key=lambda p: -len(p.parts)):
        if p.is_dir() and not KEEP_DIRS & set(p.relative_to(ROOT).parts) and not any(p.iterdir()):
            p.rmdir()
    print("\napplied. Review with `git status`, then commit.")


if __name__ == "__main__":
    main()
