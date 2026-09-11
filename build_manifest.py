#!/usr/bin/env python3
"""Seed fonts.toml from every place this collection has lived.

  audit/libreFontList-README.md   the 2018 curated list — favourites, with upstreams
  audit/libretype-channel.json    the are.na channel — where finds land first
  audit/velvetyne-*.json          Velvetyne, taken whole: site catalog + GitLab
  google-fonts.txt                Google Fonts picks (embed URL or names)
  audit/google-fonts.json         Google's catalog — resolves names and unknowns
  the font files in this repo     what's actually installed today

Writes fonts.toml: one [[family]] per upstream. Re-running keeps the license
and updated values verify.py already filled (matched by upstream), but other
hand edits to fonts.toml are overwritten — once it's been edited by hand,
edit it rather than re-seed.
"""
import html, json, re, tomllib, urllib.parse
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FONT_EXT = {".otf", ".ttf", ".woff", ".woff2"}
ARENA = "https://www.are.na/kristian-bjornard/libretype"
LIST = "https://github.com/bjornmeansbear/libreFontList"

def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())

def clean_url(u):
    return u.rstrip("/.,;") if u else u

def rank(u):
    """Prefer what fetch.py can pull: a repo, then Google Fonts, then a web page."""
    if not u:
        return 0
    if "github.com" in u or "gitlab.com" in u:
        return 3
    return 2 if "fonts.google.com" in u else 1

specimen = lambda family: "https://fonts.google.com/specimen/" + family.replace(" ", "+")

# Channel GitHub links that aren't a text face.
NOT_FONTS = {
    "golang/image", "unicode-org/text-rendering-tests", "iconic/open-iconic",
    "LettError/mutatorSans", "Monotype/Monotype_prototype_variable_fonts",
    "twardoch/varfonts-ofl", "jenskutilek/free-fonts",
}
VELVETYNE_SKIP = {"velvetyne-standard-character-set", "velvetyne-libre-friends", "velvetyne-notdef"}
VELVETYNE_ALIAS = {"flor-de-ruina": "flor-des-ruina"}
# Velvetyne GitHub repo -> catalog family. Bluu Next is held there as a fork of its
# designer's repo, and is the retired face this listing exists to find.
VELVETYNE_GH_ALIAS = {"BluuNext": "Bluu Next", "resistance-generale": "Résistance", "Lment_": "Lment"}

RENAME = {"plex": "IBM Plex", "cormorantgaramond": "Cormorant", "dejavu": "DejaVu",
          "gnugrotesk": "GNU Grotesk", "redhat": "Red Hat"}

# One list entry that is really several upstreams.
SPLIT = {
    "sourcesanscodeserif": [
        ("Source Sans", "https://github.com/adobe-fonts/source-sans-pro", ["sourcesans"]),
        ("Source Code Pro", "https://github.com/adobe-fonts/source-code-pro", ["sourcecode"]),
        ("Source Serif", "https://github.com/adobe-fonts/source-serif-pro", ["sourceserif"]),
    ],
    "librecaslon": [
        ("Libre Caslon Text", "https://github.com/impallari/Libre-Caslon-Text", ["librecaslontext"]),
        ("Libre Caslon Display", "https://github.com/impallari/Libre-Caslon-Display", ["librecaslondisplay"]),
    ],
}

# Extra local filename prefixes a family should claim.
MATCH = {
    "IBM Plex": ["ibmplex"], "Noto": ["noto"], "Fira": ["fira"], "Cormorant": ["cormorant"],
    "Gentium": ["gentium"], "Garamond No. 8": ["garamondno8"], "Overpass": ["overpass"],
    "League Gothic": ["leaguegothic"], "League Mono": ["leaguemono"],
    "Libre Clarendon": ["libreclarendon", "mastercondensed", "masterwide"],
    "Inria": ["inria"], "Barlow": ["barlow"], "Poppins": ["poppins"], "Spectral": ["spectral"],
    "GNU Grotesk": ["gnugrotesk"], "3270": ["3270"],
    "Red Hat": ["redhat", "redhatdisplay", "redhattext", "redhatmono"],
}

# Channel blocks that name a single family on a non-GitHub page: title prefix -> family.
# The block's own URL becomes the upstream unless a repo is known (UPSTREAM, below).
CHANNEL_WEB = {
    "Avería": "Avería", "INFINI": "Infini", "Infini typeface": "Infini",
    "National Park Typeface": "National Park", "Lunchtype": "Lunchtype",
    "The handwritten font Pecita": "Pecita", "Hershey Noailles": "Hershey Noailles",
    "Manrope": "Manrope", "Recursive Sans": "Recursive", "Inter UI font family": "Inter",
    "Inter font family": "Inter", "Home | OpenDyslexic": "OpenDyslexic", "Ubuntu font": "Ubuntu",
    "Libertine Fonts": "Linux Libertine", "Liberation Fonts": "Liberation Fonts",
    "Jost*": "Jost", "Renner*": "Renner", "Brazil": "Brazil", "Lincoln/MITRE": "Lincoln MITRE",
    "Monti Sans": "Monti Sans", "FiraGO": "FiraGO", "FiraSans": "Fira",
    "0xA000 Font Family": "0xA000", "Snap-it mono": "Snap-it Mono",
    "Steinbeck Typeface": "Steinbeck", "Mackinac 1895": "Mackinac 1895", "Go fonts": "Go",
    "Victor Mono": "Victor Mono", "Betatron": "Betatron", "Wremena": "Wremena",
}

# Upstreams known with confidence, by display name. A repo URL here upgrades a
# web page; verify.py reports upstream-404 if one of these is wrong.
UPSTREAM = {
    "Barlow": "https://github.com/jpt/barlow",
    "Overpass": "https://github.com/RedHatOfficial/Overpass",
    "League Gothic": "https://github.com/theleagueof/league-gothic",
    "IBM Plex": "https://github.com/IBM/plex",
    "Poppins": "https://fonts.google.com/specimen/Poppins",   # itfoundry repo archive now 404s
    "Noto": "https://fonts.google.com/noto",
    "Work Sans": "https://github.com/weiweihuanghuang/Work-Sans",
    "Space Mono": "https://github.com/googlefonts/spacemono",
    "Inter": "https://github.com/rsms/inter",
    "Recursive": "https://github.com/arrowtype/recursive",
    "Manrope": "https://fonts.google.com/specimen/Manrope",
    "Open Baskerville": "https://github.com/klepas/open-baskerville",
    "Cooper Hewitt": "https://github.com/cooperhewitt/cooperhewitt-typeface",
    "Manifont Grotesk": "https://github.com/Interstices-/Manifont-Grotesk",
    "Minipax": "https://github.com/ronotypo/Minipax",
    "Daubenton": "https://github.com/velvetyne/Daubenton",
    "HK Grotesk": "https://hanken.co/products/hk-grotesk",
    "Sinkin Sans": "https://www.k-type.com/fonts/sinkin-sans/",
    "Jabin": "https://www.behance.net/gallery/57785873/Jabin-Free-Font-and-Variable-Typeface",
    "Solide Mirage": "https://gitlab.com/StudioTriple/Solide-Mirage",
    "Belgika": "https://github.com/osp/osp.foundry.belgica-belgika",
    "Grobe Deutschmeister": "https://fontlibrary.org/en/font/grobe-deutschmeister",
    "Fengardo Neue": "https://fontlibrary.org/en/font/fengardo-neue",
    "Alfphabet": "https://osp.kitchen/foundry/alfphabet/",
    "OSP-DIN": "https://fontlibrary.org/en/font/osp-din",
    "Red Hat": "https://github.com/RedHatOfficial/RedHatFont",
    "Pilowlava": "https://gitlab.com/StudioTriple/pilowlava",   # Velvetyne's GitLab copy has no binaries
    "Victor Mono": "https://github.com/rubjo/victor-mono",
    "OpenDyslexic": "https://github.com/antijingoist/opendyslexic",
    "FiraGO": "https://github.com/bBoxType/FiraGO",
    "Jost": "https://github.com/indestructible-type/Jost",
    "Liberation Fonts": "https://github.com/liberationfonts/liberation-fonts",
}

# Licenses read by hand off a foundry page, for upstreams verify.py can't check.
# Only used while the manifest still says "unverified".
HAND_LICENSE = {
    "HK Grotesk": "OFL-1.1",          # hanken.co
    "Sinkin Sans": "Apache-2.0",      # k-type.com
    "Jabin": "personal-use-only",     # Frida Medrano: all rights reserved, paid commercial license
    "Cooper Hewitt": "OFL-1.1",       # cooperhewitt.org; the repo keeps it as files/-OFL.txt
    "Grobe Deutschmeister": "OFL-1.1",   # Peter Wiegel, via fontlibrary.org
    "Fengardo Neue": "OFL-1.1",       # Loïc Sander, via fontlibrary.org
    "Solide Mirage": "OFL-1.1",       # Studio Triple
    "Alfphabet": "OFL-1.1",           # OSP
    "OSP-DIN": "OFL-1.1",             # OSP
    "Wremena": "unclear",             # files say all rights reserved; foundry calls it free
}

NOTES = {
    "Jabin": "Not libre. Personal use only, all rights reserved; take it out of this public repo.",
    "HK Grotesk": "Hanken Grotesk on Google Fonts is its OFL successor.",
    "Minipax": "Retired from Velvetyne's catalogue; still available.",
    "Bluu Next": "Retired from Velvetyne's catalogue; still available.",
    "Mixo": "Retired from Velvetyne's catalogue; still available.",
    "Daubenton": "Retired from Velvetyne's catalogue; still available.",
    "Wremena": "The font files say 'All rights reserved'; the foundry offers it free. Ask before redistributing.",
    "Counter": "Bryce Wilner's repo carries no license, so it can't be redistributed until it does.", "Evening": "Bryce Wilner's repo carries no license, so it can't be redistributed until it does.", "Fontlab": "Bryce Wilner's repo carries no license, so it can't be redistributed until it does.",
    "Half": "Bryce Wilner's repo carries no license, so it can't be redistributed until it does.", "Section": "Bryce Wilner's repo carries no license, so it can't be redistributed until it does.", "Standard": "Bryce Wilner's repo carries no license, so it can't be redistributed until it does.",
    "Metropolis": "The upstream repo is gone (404).",
    "Krayewski Open": "The upstream repo is gone (404).",
    "Euripedes": "The channel link is truncated; the repo needs finding.",
    "Urw Garamond": "Same design as Garamond No. 8 (garamond.org).",
}

# Families already in the repo that nothing else names: filename prefix -> family.
LOCAL = {
    "hkgrotesk": "HK Grotesk", "sinkinsans": "Sinkin Sans", "linlibertine": "Linux Libertine",
    "linbiolinum": "Linux Libertine", "cooperhewitt": "Cooper Hewitt", "charissil": "Charis SIL",
    "manifont": "Manifont Grotesk", "playfair": "Playfair Display", "wdroge": "W Droge Itinerary",
    "redhatdisplay": "Red Hat", "fengardo": "Fengardo Neue", "solidemirage": "Solide Mirage",
    "commune": "Commune", "unifraktur": "UnifrakturCook", "quattrocento": "Quattrocento",
    "yatra": "Yatra One", "youngserif": "Young Serif", "lemurmure": "Le Murmure",
    "grobedeutschmeister": "Grobe Deutschmeister", "helvetiaverbundene": "Helvetia Verbundene",
    "vtfmixo": "Mixo", "ospdin": "OSP-DIN", "openbaskerville": "Open Baskerville",
    "pinyonscript": "Pinyon Script", "belgika": "Belgika", "wremena": "Wremena",
    "bluunext": "Bluu Next", "jabin": "Jabin", "tillana": "Tillana", "cantarell": "Cantarell",
    "alfphabet": "Alfphabet", "avara": "Avara", "savate": "Savate", "kaerukaeru": "Kaerukaeru",
    "spacegrotesk": "Space Grotesk", "worksans": "Work Sans", "spacemono": "Space Mono",
}

families = {}

def find(k):
    return families.get(k) or next((f for f in families.values()
                                    if k in f["match"] or norm(f["name"]) == k), None)

def add(name, upstream=None, source=None, favourite=False, match=(), foundry=""):
    hit = find(norm(name))
    key = next(k for k, v in families.items() if v is hit) if hit else norm(name)
    f = hit or families.setdefault(key, {"name": RENAME.get(key, name), "upstream": None,
                                         "sources": [], "favourite": False, "match": {key},
                                         "foundry": ""})
    up = clean_url(upstream)
    if up and rank(up) > rank(f["upstream"]):
        f["upstream"] = up
    if source and source not in f["sources"]:
        f["sources"].append(source)
    f["favourite"] |= favourite
    f["match"].update(m for m in match if m)
    if foundry:
        f["foundry"] = foundry
    return f

def apply_match():
    for name, prefixes in MATCH.items():
        f = find(norm(name))
        if f:
            f["match"].update(prefixes)

google = {norm(g["family"]): g for g in json.loads((ROOT / "audit/google-fonts.json").read_text())}

# --- 1. libreFontList
lines = (ROOT / "audit/libreFontList-README.md").read_text().splitlines()
start = next(i for i, l in enumerate(lines) if l.startswith("My personal favs"))
current = None
for l in lines[start + 1:]:
    if l.startswith("A more general listing"):
        break
    urls = re.findall(r"https?://[^\s)&]+", l)
    top = re.match(r"^- (.+)$", l)
    if top:
        name = re.split(r"\s*(?::|\(| - |https?://)", top.group(1), maxsplit=1)[0].strip()
        gh = [u for u in urls if "github.com" in u]
        current = add(name, (gh or urls or [None])[0], "libreFontList", favourite=True)
    elif urls and current is not None:
        for u in urls:
            add(current["name"], u)

for key, parts in SPLIT.items():
    old = families.pop(key, None)
    for name, url, match in parts:
        add(name, url, "libreFontList", favourite=bool(old and old["favourite"]), match=match)
apply_match()

# --- 2. libretype channel
for b in json.loads((ROOT / "audit/libretype-channel.json").read_text()):
    title = html.unescape(b["title"] or "")
    g = re.search(r"fonts\.google\.com/specimen/([^/?#\s]+)", b["url"])
    if g:
        add(urllib.parse.unquote_plus(g.group(1)), specimen(urllib.parse.unquote_plus(g.group(1))), "libretype")
        continue
    web = next((fam for pre, fam in CHANNEL_WEB.items() if title.startswith(pre)), None)
    if web:
        add(web, b["url"], "libretype")
        continue
    m = re.search(r"github\.com/([^/\s]+)/([^/?#\s]+)", b["url"])
    if not m:
        continue
    slug = f"{m.group(1)}/{re.sub(r'[.]git$', '', m.group(2))}"
    if slug in NOT_FONTS:
        continue
    url = f"https://github.com/{slug}"
    name = re.sub(r"(?<=[A-Za-z0-9])[-_]?(fonts?|typeface)$", "", slug.split("/")[1], flags=re.I)
    name = re.sub(r"[-_]+", " ", name).strip()
    if name == name.lower():
        name = name.title()
    hit = next((f for f in families.values()
                if f["upstream"] and f["upstream"].lower() == url.lower()), None)
    add(hit["name"] if hit else name, url, "libretype")

# --- 3. Velvetyne, taken whole
vkey = lambda s: re.sub(r"(font|3d)$", "", norm(s))
gitlab = {vkey(p["path"]): p for p in json.loads((ROOT / "audit/velvetyne-gitlab.json").read_text())
          if p["path"].lower() not in VELVETYNE_SKIP}
used = set()
for c in json.loads((ROOT / "audit/velvetyne-catalog.json").read_text()):
    k = vkey(VELVETYNE_ALIAS.get(c["slug"], c["slug"]))
    p = gitlab.get(k) or next((q for kk, q in gitlab.items()
                               if min(len(k), len(kk)) >= 5 and (kk in k or k in kk)), None)
    if p:
        used.add(p["path"])
    add(c["name"], p["url"] if p else c["url"], "velvetyne", foundry="Velvetyne",
        match=[norm(c["slug"]), norm(c["name"])] + ([vkey(p["path"])] if p else []))
for p in gitlab.values():
    if p["path"] not in used:
        add(p["name"] or p["path"], p["url"], "velvetyne", foundry="Velvetyne", match=[vkey(p["path"])])

seed_license = {}
vgh = ROOT / "audit/velvetyne-github.json"
if vgh.exists():
    for r in json.loads(vgh.read_text()):
        if (r["fork"] and r["name"] not in VELVETYNE_GH_ALIAS) or r["name"].lower() in VELVETYNE_SKIP:
            continue
        name = VELVETYNE_GH_ALIAS.get(r["name"]) or re.sub(
            r"[-_](font|typeface)$", "", r["name"], flags=re.I).replace("-", " ").replace("_", " ").strip()
        f = add(name, r["url"], "velvetyne", foundry="Velvetyne", match=[vkey(r["name"])])
        if r["license"] and r["license"] != "NOASSERTION":
            seed_license[r["url"].lower()] = (r["license"], r["pushed"])

page_license = {}
vp = ROOT / "audit/velvetyne-pages.json"
if vp.exists():
    for c in json.loads(vp.read_text()):
        f = find(norm(c["name"]))
        if not f:
            continue
        if any("Open Font" in t or "OFL" in t for t in c.get("license_text", [])):
            page_license[norm(f["name"])] = "OFL-1.1"
        repos = [m.group(1) for r in c.get("repos", [])
                 for m in [re.match(r"(https?://(?:gitlab|github)\.com/[^/]+/[^/#?]+)", r)] if m]
        if repos and rank(f["upstream"]) < 3:
            add(f["name"])["upstream"] = repos[0]

# --- 4. Google Fonts picks
unknown_picks = []
picks = ROOT / "google-fonts.txt"
if picks.exists():
    for line in picks.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        names = ([urllib.parse.unquote_plus(n) for n in re.findall(r"family=([^&:]+)", line)]
                 if "family=" in line else [line])
        for n in names:
            g = google.get(norm(n))
            if g:
                add(g["family"], specimen(g["family"]), "google-picks", favourite=True)
            else:
                unknown_picks.append(n)

# --- 5. known upstreams, umbrella prefixes, local names
for name, url in UPSTREAM.items():
    add(name)["upstream"] = clean_url(url)   # curated: overrides the sources
apply_match()
for prefix, name in LOCAL.items():
    add(name, match=[prefix])

# --- 5b. what's been fetched is in the repo too. Without this, a family whose
# only source was the 2019 files vanishes from the manifest once tidy.py
# deletes those files in favour of the fresh copy.
for src in sorted((ROOT / "Families").glob("*/.source.json")):
    d = json.loads(src.read_text())
    add(d["name"], d["upstream"], "Families")

# --- 6. claim this repo's files by longest matching prefix
files = sorted(p for p in ROOT.rglob("*") if p.suffix.lower() in FONT_EXT
               and not {".git", "audit", "Families"} & set(p.parts))
claimed = {}
for p in files:
    stem = norm(p.stem)
    best = max(((pre, k) for k, f in families.items() for pre in f["match"]
                if stem.startswith(pre)), key=lambda t: len(t[0]), default=None)
    if not best:
        parts = p.relative_to(ROOT).parts
        group = parts[0] if len(parts) > 1 else re.split(r"[-_ ]", p.stem)[0]
        f = add(group.replace("-", " ").replace("_", " "))
        best = (None, next(k for k, v in families.items() if v is f))
    claimed.setdefault(best[1], []).append(p)

# --- what verify.py already learned, keyed by upstream
prev = {}
if (ROOT / "fonts.toml").exists():
    for f in tomllib.loads((ROOT / "fonts.toml").read_text()).get("family", []):
        if f.get("upstream"):
            prev[f["upstream"].lower()] = (f.get("license", "unverified"), f.get("updated", ""))

# --- 7. no upstream, or one that 404'd? Google may have it
from_google = 0
for f in families.values():
    dead = f["upstream"] and prev.get(f["upstream"].lower(), ("",))[0].startswith("upstream-")
    web_only = f["upstream"] and rank(f["upstream"]) == 1
    if web_only and norm(f["name"]) in google:      # a web page loses to Google Fonts, which fetch.py can pull
        f["upstream"] = specimen(google[norm(f["name"])]["family"])
        from_google += 1
        continue
    if f["upstream"] and not dead:
        continue
    k = norm(f["name"])
    g = google.get(k)
    if not g and len(k) >= 5:
        cands = [v for gk, v in google.items() if gk.startswith(k)]
        g = cands[0] if len(cands) == 1 else None
    if g:
        f["upstream"] = specimen(g["family"])
        from_google += 1

for k, f in list(families.items()):
    f["in_repo"] = len(claimed.get(k, []))
    if f["in_repo"] and "libreFontLibrary" not in f["sources"]:
        f["sources"].append("libreFontLibrary")
    if not f["sources"]:
        del families[k]

# --- write
q = lambda s: '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'
def typ(u):
    if not u: return "unknown"
    for host, t in (("github.com", "github"), ("gitlab.com", "gitlab"), ("fonts.google.com", "google")):
        if host in u: return t
    return "web"

out = [
    "# libreFontLibrary manifest — one entry per upstream family.",
    "# The only file here maintained by hand. Seeded by build_manifest.py;",
    "# license and updated are filled by verify.py.",
    "#",
    "# type: github | gitlab | google (fetch.py can pull these)",
    "#       web (fetch by hand) | unknown (upstream not found yet)",
    "",
    "[collection]",
    f"arena = {q(ARENA)}   # where new finds land first",
    f"list  = {q(LIST)}   # the 2018 curated list, absorbed here",
    'foundries = ["Velvetyne"]   # taken whole, not family by family',
    "",
]
display_of = {}
for k, f in sorted(families.items(), key=lambda kv: (not kv[1]["favourite"], kv[1]["name"].lower())):
    display = f["name"].title() if re.fullmatch(r"[a-z][a-z0-9 ]*", f["name"]) else f["name"]
    up = (f["upstream"] or "").lower()
    lic, upd = prev.get(up, ("unverified", ""))
    open_q = ("unverified", "none-found", "NOASSERTION", "OTHER")
    if lic in open_q and up in seed_license:
        lic, upd = seed_license[up]
    if lic in open_q and norm(f["name"]) in page_license:
        lic = page_license[norm(f["name"])]
    if lic in open_q and f["name"] in HAND_LICENSE:
        lic = HAND_LICENSE[f["name"]]
    source = ROOT / "Families" / re.sub(r"[^A-Za-z0-9._-]+", "-", display).strip("-") / ".source.json"
    fetched = source.exists()
    if lic in open_q and fetched:     # fetch.py read the license that shipped in the download
        lic = json.loads(source.read_text()).get("license", lic)
    display_of[k] = display
    out += ["[[family]]",
            f"name      = {q(display)}",
            f"upstream  = {q(f['upstream'] or '')}",
            f"type      = {q(typ(f['upstream']))}",
            f"foundry   = {q(f['foundry'])}",
            f"license   = {q(lic)}",
            f"updated   = {q(upd)}",
            f"favourite = {'true' if f['favourite'] else 'false'}",
            f"in_repo   = {f['in_repo']}",
            f"note      = {q(NOTES.get(f['name'], ''))}",
            f"fetched   = {'true' if fetched else 'false'}",
            f"sources   = [{', '.join(q(s) for s in f['sources'])}]",
            f"match     = [{', '.join(q(m) for m in sorted(f['match']))}]",
            ""]
(ROOT / "fonts.toml").write_text("\n".join(out))
# which loose file belongs to which family — tidy.py reads this
(ROOT / "audit/claims.json").write_text(json.dumps(
    {str(p.relative_to(ROOT)): display_of[k] for k, ps in claimed.items() if k in display_of for p in ps},
    indent=1, ensure_ascii=False))

d = tomllib.loads((ROOT / "fonts.toml").read_text())["family"]
print(f"{len(d)} families | in repo {sum(1 for f in d if f['in_repo'])}, "
      f"to fetch {sum(1 for f in d if not f['in_repo'])} | files {sum(f['in_repo'] for f in d)}/{len(files)}")
print("types:", dict(Counter(f["type"] for f in d)),
      f"| upstream found via Google: {from_google} | verified carried over: "
      f"{sum(1 for f in d if f['license'] != 'unverified')}")
if unknown_picks:
    print("google-fonts.txt names not in Google's catalog:", ", ".join(unknown_picks))
