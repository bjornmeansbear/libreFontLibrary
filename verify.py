#!/usr/bin/env python3
"""Fill `license` and `updated` in fonts.toml from each family's upstream.

One call per family — GitHub, GitLab, or Google Fonts. Unauthenticated GitHub allows 60
an hour, so GitHub checks stop cleanly when that runs out and resume on the
next run — anything still "unverified" gets checked. GitLab has its own,
much larger budget and carries on regardless. Set GITHUB_TOKEN for 5,000 an
hour.

license is the host's own detection, as an SPDX-style id (OFL-1.1,
Apache-2.0, ...), NOASSERTION (a license file it couldn't classify — read
it), or none-found (no license file at all — the family can't be
redistributed until that's resolved).
"""
import json, os, re, urllib.error, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOML = ROOT / "fonts.toml"
norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())
GH_HEAD = {"User-Agent": "libreFontLibrary-verify", "Accept": "application/vnd.github+json"}
if os.environ.get("GITHUB_TOKEN"):
    GH_HEAD["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"

# GitLab reports lowercase keys; match GitHub's SPDX casing so the file reads as one set.
GL_SPDX = {"ofl-1.1": "OFL-1.1", "mit": "MIT", "apache-2.0": "Apache-2.0",
           "bitstream-vera": "Bitstream-Vera", "lal-1.3": "LAL-1.3",
           "gpl-3.0": "GPL-3.0", "gpl-2.0": "GPL-2.0", "cc0-1.0": "CC0-1.0"}

def github(slug):
    req = urllib.request.Request(f"https://api.github.com/repos/{slug}", headers=GH_HEAD)
    with urllib.request.urlopen(req) as r:
        d, left = json.load(r), int(r.headers.get("X-RateLimit-Remaining", 1))
    lic = (d.get("license") or {}).get("spdx_id") or "none-found"
    return lic, d["pushed_at"][:10] + (" archived" if d.get("archived") else ""), left

# Google Fonts' own catalog has dates but no license. The google/fonts repo files
# each family under its license instead — ofl/, apache/, ufl/, cc-by-sa/ — and
# raw.githubusercontent.com doesn't count against the API's hourly limit.
GOOGLE_SPDX = {"OFL": "OFL-1.1", "APACHE2": "Apache-2.0", "UFL": "UFL-1.0", "CC-BY-SA": "CC-BY-SA-4.0"}
_gf = ROOT / "audit/google-fonts.json"
GOOGLE_UPDATED = {norm(g["family"]): g.get("lastModified") or ""
                  for g in (json.loads(_gf.read_text()) if _gf.exists() else [])}

def google(name):
    for folder in ("ofl", "apache", "ufl", "cc-by-sa"):
        url = f"https://raw.githubusercontent.com/google/fonts/main/{folder}/{norm(name)}/METADATA.pb"
        try:
            with urllib.request.urlopen(url) as r:
                meta = r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue
            raise
        m = re.search(r'^license:\s*"([^"]+)"', meta, re.M)
        lic = GOOGLE_SPDX.get(m.group(1), m.group(1)) if m else folder.upper()
        return lic, GOOGLE_UPDATED.get(norm(name), "")
    return "google-dir-not-found", ""

def gitlab(path):
    enc = urllib.parse.quote(path, safe="")
    with urllib.request.urlopen(f"https://gitlab.com/api/v4/projects/{enc}?license=true") as r:
        d = json.load(r)
    key = (d.get("license") or {}).get("key")
    lic = GL_SPDX.get(key, key.upper()) if key else "none-found"
    return lic, (d.get("last_activity_at") or "")[:10] + (" archived" if d.get("archived") else "")

# When the host can't classify a license (NOASSERTION) or finds no file it
# recognises (none-found), read the likely files ourselves. Raw file hosts
# don't count against any API limit.
LICENSE_FILES = ("OFL.txt", "OFL.md", "LICENSE", "LICENSE.txt", "LICENSE.md", "LICENCE",
                 "LICENCE.txt", "License.txt", "COPYING", "COPYING.txt", "OFL-1.1.txt")

from licenses import classify

def read_license(up):
    gh = re.search(r"github\.com/([^/]+/[^/?#\s]+)", up)
    gl = re.search(r"gitlab\.com/([^?#\s]+?)/?$", up)
    base = (f"https://raw.githubusercontent.com/{gh.group(1)}/HEAD/" if gh else
            f"https://gitlab.com/{gl.group(1)}/-/raw/HEAD/" if gl else None)
    if not base:
        return None
    def raw(path):
        try:
            req = urllib.request.Request(base + urllib.parse.quote(path), headers={"User-Agent": "libreFontLibrary-verify"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return classify(r.read(200_000).decode("utf-8", "replace"))
        except urllib.error.HTTPError:
            return None
    for name in LICENSE_FILES:
        if found := raw(name):
            return found
    # Not at the root: list the repo and look wherever a license file sits.
    # One API call on GitHub; GitLab's tree listing is free.
    try:
        if gh:
            req = urllib.request.Request(
                f"https://api.github.com/repos/{gh.group(1)}/git/trees/HEAD?recursive=1", headers=GH_HEAD)
            with urllib.request.urlopen(req, timeout=60) as r:
                paths = [t["path"] for t in json.load(r).get("tree", []) if t.get("type") == "blob"]
        else:
            enc, paths = urllib.parse.quote(gl.group(1), safe=""), []
            for page in range(1, 6):
                with urllib.request.urlopen(f"https://gitlab.com/api/v4/projects/{enc}/repository/tree"
                                            f"?recursive=true&per_page=100&page={page}", timeout=60) as r:
                    batch = json.load(r)
                paths += [t["path"] for t in batch if t["type"] == "blob"]
                if len(batch) < 100:
                    break
    except urllib.error.HTTPError:
        return None
    tree_license = re.compile(r"(^|/)[-_]?(OFL|LICEN[CS]E|COPYING)[^/]*$", re.I)
    for path in sorted((p for p in paths if tree_license.search(p) and "FAQ" not in p.upper()),
                       key=lambda p: p.count("/"))[:6]:
        if found := raw(path):
            return found
    return None

blocks = TOML.read_text().split("\n[[family]]\n")
checked, github_out = 0, False
for i, b in enumerate(blocks[1:], 1):
    if 'license   = "unverified"' not in b:
        continue
    up = re.search(r'^upstream\s*=\s*"(.*)"', b, re.M).group(1)
    gh = re.search(r"github\.com/([^/]+/[^/?#\s]+)", up)
    gl = re.search(r"gitlab\.com/([^?#\s]+?)/?$", up)
    gg = re.search(r"fonts\.google\.com/specimen/([^/?#\s]+)", up)
    try:
        if gh and not github_out:
            lic, upd, left = github(gh.group(1))
            github_out = left <= 1
        elif gl:
            lic, upd = gitlab(gl.group(1))
        elif gg:
            lic, upd = google(urllib.parse.unquote_plus(gg.group(1)))
        else:
            continue
    except urllib.error.HTTPError as e:
        if gh and e.code in (403, 429):
            github_out = True
            continue
        lic, upd = f"upstream-{e.code}", ""
    b = re.sub(r'^license   = "unverified"', f'license   = "{lic}"', b, flags=re.M)
    b = re.sub(r'^updated   = ""', f'updated   = "{upd}"', b, flags=re.M)
    blocks[i] = b
    checked += 1

read_by_text = 0
for i, b in enumerate(blocks[1:], 1):
    m = re.search(r'^license   = "(NOASSERTION|none-found|OTHER)"', b, re.M)
    if not m:
        continue
    found = read_license(re.search(r'^upstream\s*=\s*"(.*)"', b, re.M).group(1))
    if found:
        blocks[i] = b.replace(m.group(0), f'license   = "{found}"')
        read_by_text += 1

TOML.write_text("\n[[family]]\n".join(blocks))
rest = sum(1 for b in blocks[1:] if 'license   = "unverified"' in b
           and re.search(r"git(hub|lab)\.com|fonts\.google\.com/specimen", b))
print(f"checked {checked}; license read from text for {read_by_text}; {rest} still unverified"
      + (" — GitHub rate limit reached, re-run after it resets" if github_out and rest else ""))
