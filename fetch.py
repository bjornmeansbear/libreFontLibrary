#!/usr/bin/env python3
"""Pull each family's current binaries, with its license, into Families/<Name>/.

Reads fonts.toml.

  github   the repo archive, keeping the binaries meant for installing. Many font
           repos don't commit binaries, or are too big to download whole; then
           the latest release assets instead — one per package, since some
           repos (IBM Plex) release each family separately.
  gitlab   the repo archive
  google   file by file from the google/fonts repo, per METADATA.pb
  web      a .zip download found on the upstream page. Its license is usually
           unverified in the manifest, so the license file that ships inside
           decides: written only if that text reads as redistributable.

  python3 fetch.py --dry-run          what would be fetched; writes nothing
  python3 fetch.py --only Inter Jost  just these families
  python3 fetch.py --no-web           repos and Google only
  python3 fetch.py                    everything not already fetched

A family with no license file is never written: the license travelling with
the font is the point. Doesn't touch the loose 2019 files — see tidy.py.
"""
import argparse, html, io, json, os, re, tarfile, tempfile, tomllib, urllib.error, urllib.parse, urllib.request, zipfile
from datetime import date
from pathlib import Path

from licenses import REDISTRIBUTABLE, classify

ROOT = Path(__file__).resolve().parent
norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())
OUT = ROOT / "Families"
UA = {"User-Agent": "libreFontLibrary-fetch"}
BROWSER = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
GH_API = {**UA, "Accept": "application/vnd.github+json"}
if os.environ.get("GITHUB_TOKEN"):
    GH_API["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
NEVER = {"personal-use-only", "unclear", "google-dir-not-found"}
FONT = (".otf", ".ttf")
ARCHIVE = re.compile(r"\.(zip|tar\.gz|tgz|tar\.bz2|tar\.xz)$", re.I)
LICENSE = re.compile(r"(^|/)[-_]?(OFL|LICEN[CS]E|COPYING|COPYRIGHT)[^/]*$", re.I)   # Cooper Hewitt ships "-OFL.txt"
TEXT = {"", ".txt", ".md", ".markdown", ".rst"}
# a license is a text file: a UFO's copyright.glif is a drawing of the © sign
is_license = lambda n: bool(LICENSE.search(n)) and Path(n).suffix.lower() in TEXT
_gf = ROOT / "audit/google-fonts.json"
GOOGLE = {norm(g["family"]): g["family"] for g in (json.loads(_gf.read_text()) if _gf.exists() else [])}
NOT_SHIPPED = re.compile(r"/(sources?|src|tests?|testdata|proofs?|docs?|old|archive|specimens?|scripts|"
                         r"tools|ufos?|masters?|glyphs|web|webfonts?|woff2?)/", re.I)
SHIPPED = re.compile(r"/(fonts?|binaries|products|release|dist|output|otf|ttf|variable)/", re.I)


class TooBig(RuntimeError):
    pass


def download(url, limit_mb, headers=UA):
    """Stream to a temp file, giving up past limit_mb — some font repos carry gigabytes of source."""
    tmp = tempfile.TemporaryFile()
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=300) as r:
        size = 0
        while chunk := r.read(1 << 20):
            size += len(chunk)
            if size > limit_mb << 20:
                raise TooBig(f"archive over {limit_mb} MB")
            tmp.write(chunk)
    tmp.seek(0)
    return tmp


def open_archive(tmp):
    """Names and a reader for a zip or any tarball."""
    if zipfile.is_zipfile(tmp):
        tmp.seek(0)
        z = zipfile.ZipFile(tmp)
        return [n for n in z.namelist() if not n.endswith("/")], z.read
    tmp.seek(0)
    t = tarfile.open(fileobj=tmp, mode="r:*")
    members = {m.name: m for m in t.getmembers() if m.isfile()}
    return list(members), lambda n: t.extractfile(members[n]).read()


def pick_fonts(paths):
    """From every .otf/.ttf in an archive, keep the binaries meant for installing:
    not sources or web builds, the newest of a file kept in several versions,
    and the OTF where a style ships as both OTF and TTF."""
    fonts = [p for p in paths if p.lower().endswith(FONT) and not NOT_SHIPPED.search("/" + p)
             and "webfont" not in Path(p).name.lower()]
    fonts = [p for p in fonts if SHIPPED.search("/" + p)] or fonts
    best = {}
    for p in fonts:
        stem = Path(p).stem.lower()
        m = re.search(r"[\s_-]*v(\d{2,5})(?:[\s_-]?([a-z]))?$", stem)     # "v0049", "v0050 a"
        base, ver = (stem[:m.start()], (int(m.group(1)), m.group(2) or "")) if m else (stem, (-1, ""))
        cur = best.get(base)
        if cur is None or ver > cur[1] or (ver == cur[1] and p.lower().endswith(".otf")):
            best[base] = (p, ver)
    return sorted(p for p, _ in best.values())


def from_archive(url, limit_mb, headers=UA):
    names, read = open_archive(download(url, limit_mb, headers))
    names = [n for n in names if "__MACOSX" not in n]
    firsts = {n.split("/")[0] for n in names}
    top = (next(iter(firsts)) + "/") if len(firsts) == 1 and all("/" in n for n in names) else ""
    rel = [n[len(top):] for n in names]
    fonts = pick_fonts(rel)
    lic = [n for n in rel if is_license(n) and "/" not in n]                      # archive root first
    lic = lic or [n for n in rel if is_license(n)][:2]
    outer = lambda n: read(top + n)
    if not fonts:                        # some repos ship their fonts as a zip committed inside the repo
        inner = [n for n in rel if n.lower().endswith(".zip") and not NOT_SHIPPED.search("/" + n)
                 and not re.search(r"web|woff|src|source|ufo", n, re.I)][:3]
        parts = []
        for n in inner:
            zz = zipfile.ZipFile(io.BytesIO(outer(n)))
            names2 = [m for m in zz.namelist() if not m.endswith("/") and "__MACOSX" not in m]
            parts.append((pick_fonts(names2), [m for m in names2 if is_license(m)][:2], zz.read))
        if any(f for f, _, _ in parts):
            return combine(parts + [([], lic, outer)])
    return fonts, lic, outer


def combine(parts):
    """Several archives' fonts and licenses behind one reader, keyed '<i>/<path>'."""
    fonts, lic, readers = [], [], []
    for i, (f, l, r) in enumerate(parts):
        fonts += [f"{i}/{n}" for n in f]
        lic += [f"{i}/{n}" for n in l]
        readers.append(r)

    def read(key):
        i, n = key.split("/", 1)
        return readers[int(i)](n)

    def unique(keys):
        seen, out = set(), []
        for k in keys:
            if Path(k).name.lower() not in seen:
                seen.add(Path(k).name.lower())
                out.append(k)
        return out
    return unique(fonts), unique(lic), read


def from_release(slug, limit_mb):
    """The newest release of each package in the repo, best asset of each."""
    req = urllib.request.Request(f"https://api.github.com/repos/{slug}/releases?per_page=40", headers=GH_API)
    with urllib.request.urlopen(req, timeout=60) as r:
        releases = [x for x in json.load(r) if not x.get("draft") and not x.get("prerelease")]
    newest = {}
    for x in releases:                       # newest first; "@ibm/plex-sans@1.1.0" -> "@ibm/plex-sans"
        newest.setdefault(re.sub(r"@?v?\d[\w.+-]*$", "", x["tag_name"]), x)
    parts = []
    for x in list(newest.values())[:20]:
        assets = [a for a in x.get("assets", []) if ARCHIVE.search(a["name"])]
        score = lambda a: (any(w in a["name"].lower() for w in ("otf", "ttf", "desktop", "font"))
                           - any(w in a["name"].lower() for w in ("web", "woff", "src", "source", "ufo", "glyphs")))
        for a in sorted(assets, key=score, reverse=True)[:1]:
            try:
                parts.append(from_archive(a["browser_download_url"], limit_mb))
            except TooBig:
                pass
    if not parts or not any(p[0] for p in parts):
        raise RuntimeError("no binaries in the repo, and no release assets with any")
    return combine(parts)


def from_web(url, limit_mb):
    page = urllib.request.urlopen(urllib.request.Request(url, headers=BROWSER), timeout=60).read().decode("utf-8", "replace")
    zips = list(dict.fromkeys(urllib.parse.urljoin(url, html.unescape(m))
                              for m in re.findall(r"""href=['"]([^'"]+?\.zip(?:\?[^'"]*)?)['"]""", page, re.I)))
    if not zips:
        raise RuntimeError("no .zip download on the page — fetch by hand")
    return from_archive(zips[0], limit_mb, BROWSER)


def from_google(name):
    for folder in ("ofl", "apache", "ufl", "cc-by-sa"):
        base = f"https://raw.githubusercontent.com/google/fonts/main/{folder}/{norm(name)}/"
        try:
            meta = urllib.request.urlopen(urllib.request.Request(base + "METADATA.pb", headers=UA)).read().decode()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue
            raise
        fonts = sorted(set(re.findall(r'^\s*filename:\s*"([^"]+)"', meta, re.M)))
        lic = []
        for cand in ("OFL.txt", "LICENSE.txt", "UFL.txt", "LICENCE.txt"):
            try:
                urllib.request.urlopen(urllib.request.Request(base + cand, headers=UA, method="HEAD"))
                lic.append(cand)
            except urllib.error.HTTPError:
                pass
        read = lambda n, b=base: urllib.request.urlopen(urllib.request.Request(b + n, headers=UA)).read()
        return fonts, lic, read
    raise RuntimeError("not found in google/fonts under ofl/, apache/, ufl/ or cc-by-sa/")


def from_github(up, limit_mb):
    slug = re.search(r"github\.com/([^/]+/[^/?#\s]+)", up).group(1)
    try:
        fonts, lic, read = from_archive(f"{up}/archive/HEAD.zip", limit_mb)
    except TooBig:
        fonts, lic, read = [], [], None
    if fonts:
        return fonts, lic, read
    rf, rl, rr = from_release(slug, limit_mb)
    if not rl and lic:                   # a release zip that leaves the license out: take the repo's
        return combine([(rf, [], rr), ([], lic, read)])
    return rf, rl, rr


def folder(name):
    return OUT / re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", nargs="*", help="family names to fetch")
    ap.add_argument("--no-web", action="store_true", help="skip families that only have a web page")
    ap.add_argument("--max-mb", type=int, default=400, help="largest single archive to download")
    args = ap.parse_args()

    families = tomllib.loads((ROOT / "fonts.toml").read_text())["family"]
    todo, manual, blocked, done = [], [], [], 0
    for f in families:
        if args.only and f["name"] not in args.only:
            continue
        web = f["type"] == "web"
        if (folder(f["name"]) / ".source.json").exists():
            done += 1
        elif f["type"] == "unknown" or (f["type"] == "google" and "/specimen/" not in f["upstream"]) \
                or (web and args.no_web):
            manual.append(f)
        elif f["license"] in NEVER or f["license"].startswith("upstream-") \
                or (not web and f["license"] not in REDISTRIBUTABLE):
            blocked.append(f)
        else:
            todo.append(f)

    print(f"{len(todo)} to fetch ({sum(f['type']=='web' for f in todo)} from web pages), {done} already "
          f"fetched, {len(blocked)} held for license, {len(manual)} to fetch by hand")
    if args.dry_run:
        for label, group in (("fetch", todo), ("held — license", blocked), ("by hand", manual)):
            print(f"\n--- {label} ({len(group)}) ---")
            for f in group:
                print(f"  {f['type']:<7} {f['license']:<18} {f['name']:<28} {f['upstream']}")
        return

    OUT.mkdir(exist_ok=True)
    failed = []
    for f in todo:
        name, up = f["name"], f["upstream"]
        try:
            try:
                fonts, lic, read = get(f, args.max_mb)
                via = ""
            except Exception as first:
                g = GOOGLE.get(norm(name))
                if not g or f["type"] == "google":
                    raise
                fonts, lic, read = from_google(g)      # same family, fetchable from Google Fonts
                via = f" (via Google Fonts; upstream: {first})"
            write(f, fonts, lic, read, via)
        except Exception as e:
            failed.append((name, str(e)))
            print(f"  FAIL  {name:<28} {e}")
    if failed:
        print(f"\n{len(failed)} failed — see above.")


def get(f, max_mb):
    up = f["upstream"]
    if True:
        if True:
            if f["type"] == "github":
                return from_github(up, max_mb)
            elif f["type"] == "gitlab":
                path = urllib.parse.quote(re.search(r"gitlab\.com/(.+?)/?$", up).group(1), safe="")
                return from_archive(
                    f"https://gitlab.com/api/v4/projects/{path}/repository/archive.zip", max_mb)
            elif f["type"] == "google":
                return from_google(re.search(r"/specimen/([^/?#]+)", up).group(1).replace("+", " "))
            return from_web(up, max_mb)


def write(f, fonts, lic, read, via=""):
    name, up = f["name"], f["upstream"]
    if True:
        if True:
            if not fonts:
                raise RuntimeError("no .otf/.ttf found upstream")
            if not lic:
                raise RuntimeError("no license file found upstream — not written")
            reads_as = next((c for n in lic if (c := classify(read(n).decode("utf-8", "replace")))), None)
            license = f["license"] if f["license"] in REDISTRIBUTABLE else reads_as
            if license not in REDISTRIBUTABLE:
                raise RuntimeError(f"the license that ships with it reads as {reads_as or 'unrecognised'} — not written")
            dest = folder(name)
            dest.mkdir(parents=True, exist_ok=True)
            for n in fonts + lic:
                (dest / Path(n).name).write_bytes(read(n))
            (dest / ".source.json").write_text(json.dumps({
                "name": name, "upstream": up, "license": license, "license_file_reads_as": reads_as,
                "fetched": date.today().isoformat(),
                "files": [Path(n).name for n in fonts], "license_files": [Path(n).name for n in lic],
            }, indent=1))
            print(f"  ok    {name:<28} {len(fonts):>3} fonts  {license:<12} {', '.join(Path(n).name for n in lic)}{via}")


if __name__ == "__main__":
    main()
