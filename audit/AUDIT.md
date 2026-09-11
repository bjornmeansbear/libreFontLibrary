# libreFontLibrary — audit, 2026-09-11

State of the repo as cloned: **601 font files, ~111 families, last pushed October 2019.**

Three problems, one fix.

---

## Where it ended up (2026-09-11, same day)

**`Families/` — 136 families, 429 MB.** Each fetched from its upstream, each with the
license file that ships with it, each with a `.source.json` recording where it came
from and when. The installable part of the repo.

**`Unsorted/` — 18 families, 24 MB.** The 2019 files for families that couldn't be
fetched fresh yet. Kept, not installed. Alfphabet, Avara, Bluu Next, Cooper Hewitt,
Fengardo Neue, GNU Grotesk, Garamond No. 8, HK Grotesk, Helvetia Verbundene, Linux
Libertine, Mixo, Noto, Open Baskerville, Polsku, Sinkin Sans, TCA, W Droge Itinerary,
Wremena.

**Deleted:** Jabin (personal use only, 13 files), the four X11 index files, and every
2019 file with a fresh licensed copy in `Families/`.

**Held — no license anyone could find.** Bryce Wilner's six (Counter, Evening, Fontlab,
Half, Section, Standard); three dead upstreams (Euripedes, Krayewski Open, Metropolis);
and repos with no license file anywhere in them, including several retired Velvetyne
faces (Bluu Next, Lack, Marcel, Pictoporn, BilboINC) and Avara, whose only "license" is a
glyph drawing named `copyright.glif`.

**By hand.** Families whose page offers no zip (Sinkin Sans, HK Grotesk, Pecita, Renner,
Snap-it Mono, Steinbeck, Linux Libertine, the librarystack faces…) or whose repo
publishes no binaries (Cooper Hewitt, Open Baskerville, DejaVu, Wallingford, Wu3
Segments). Fengardo Neue's download ships without a license file, so it wasn't written.
The fetch logs (`audit/fetch-log*.txt`) have each one's reason.

**The pipeline:** `build_manifest.py` → `verify.py` → `fetch.py` → `build_manifest.py`
→ `tidy.py`, and `install.sh` on each machine. `fonts.toml` is the file to edit.


---

## 1. Licenses: 3% coverage

**20 of 601 font files sit beside a license file. 581 do not.**

Six families do it correctly — BioRhyme, BioRhyme_Expanded, Compagnon, Daubenton,
Happy-Times-at-the-IKOB, format-1452. Every other family is a bare pile of `.otf`/`.ttf`
at the repo root.

The README asks whether this matters. It does. The OFL permits redistribution "provided
that each copy contains the above copyright notice and this license" — the license has to
travel with the font. A public GitHub repo is redistribution. Same clause in the Ubuntu
Font License; Apache-2.0 §4 says the same thing differently.

So the six correctly-structured families are the target shape, already present, applied to
5% of the collection.

**Second-order problem:** the README says these are "all FLOS licensed in some way or
form." That's the assumption to test, not to trust. Free-to-use and free-to-redistribute
are different permissions, and this repo exercises the second one. Ones to check by hand
before re-publishing:

- **Jabin** (Frida Medrano) — **personal use only, all rights reserved**, with a paid
  commercial license. Not libre. It's the one family found so far that has to come out
  of a public repo: 13 files.
- **Wremena**, **Grobe Deutschmeister**, **Helvetia Verbundene**, **Polsku**,
  **W Droge Itinerary**, **TCA**, **Combat** — still unverified

Checked and fine, correcting an earlier guess in this audit: **Sinkin Sans** is Apache 2.0
(K-Type), **HK Grotesk** is OFL-1.1 (Hanken), **Cooper Hewitt** is OFL-1.1 with a repo at
`cooperhewitt/cooperhewitt-typeface`, **Manifont Grotesk** is OFL-1.1 from Interstices
(not Manufactura Independente), and **BackOut** is Velvetyne, OFL-1.1.

**Minipax, Bluu Next, Mixo and Daubenton** are Velvetyne faces the foundry has since
retired from its catalogue — still available, and forkable, just no longer listed
([When fonts retire](https://velvetyne.fr/news/vtf-is-dead-long-live-velvetyne/)).

Anything that turns out to be free-to-use-only comes out of the repo and goes back to
being a local install.

## 2. The binaries are seven years stale

Committed October 2019, several sourced years before that. The cost isn't cosmetic — a
2019 binary predates the variable-font releases of several families in here:

- **Work Sans** — the repo has `WorkSans-Roman-VF.ttf` from the old Latin-only cut
- **Space Grotesk** — only five static weights; upstream is a variable font now
- **Libre Franklin** — `LibreFranklinGX-*-v4015.ttf`, long superseded
- **IBM Plex** — moved repos and versions since
- **Cormorant**, **Spectral**, **Grenze**, **Barlow**, **Poppins** — all have had
  releases since

## 3. About 40 families in the channel aren't in the repo at all

The are.na channel `libretype` (231 blocks, current) resolves to **53 distinct GitHub
sources**, of which **46 have no match in the repo**. Roughly six of those are not text
faces and should be ignored — `golang/image`, `unicode-org/text-rendering-tests`,
`iconic/open-iconic`, `LettError/mutatorSans`, `Monotype/Monotype_prototype_variable_fonts`,
and the `jenskutilek/free-fonts` / `twardoch/varfonts-ofl` collections.

That leaves ~40 real families absent, including several worth having:

`productiontype/Newsreader` · `googlefonts/atkinson-hyperlegible` · `intel/intel-one-mono` ·
`tonsky/FiraCode` · `source-foundry/Hack` · `uswds/public-sans` · `Etcetera-Type-Co/epilogue` ·
`RingoSeeber/Petrona` · `huertatipografica/piazzolla` · `chrismsimpson/Metropolis` ·
`larsenwork/Gidole` · `fcambus/spleen` · `sursly/league-spartan` · `sursly/sono` ·
`dejavu-fonts/dejavu-fonts` · `BlackFoundry/InriaFonts` · `mjlagattuta/Hepta-Slab` ·
`coreyhu/Urbanis` · `eliheuer/wallingford` · `eliheuer/hasubi-mono` · plus Bryce Wilner's
six (`Counter`, `Evening`, `Fontlab-Font`, `Half`, `Section`, `Standard`)

**Newsreader is the notable one** — it sets the GD420 and DI200 syllabus PDFs through
`di200/md2pdf.sh`, and it isn't in the font library.

**Correction.** The first pass of this list trimmed repo names with Python's
`rstrip('.git')`, which strips *characters* rather than the suffix — `3270font` came out
`3270fon`, `RedHat` came out `RedHa`. Fixed in `build_manifest.py`; `fonts.toml` is the
accurate list and supersedes this section.

## 3b. There are three layers, and only one of them is current

`libreFontList` (github.com/bjornmeansbear/libreFontList, 2018) is the piece that makes
this tractable. It came out of the Spring 2018 Open Source course at MICA (`gd399-osd`)
and it is **24 curated families, each with its upstream URL, organised by family rather
than by file** — which is exactly the shape the manifest needs.

So the collection exists in three layers, none of which know about each other:

| Layer | What it is | State |
|---|---|---|
| `libretype` (are.na, 231 blocks) | the wide net — anything interesting | **current** |
| `libreFontList` (2018) | 24 curated favourites, with sources | stale, but editorially the best of the three |
| `libreFontLibrary` (2019) | 601 binaries, 111 families | stale, 3% licensed |

Plus a fourth by accident: `color-system-and-guidelines/tools/slideshow/fonts/` holds six
OFL faces **with their licenses beside them** — the only place in the whole set that is
already correct.

The manifest should seed from the union of all three, not from any one. `libreFontList`
supplies curation and upstreams, `libretype` supplies reach, `libreFontLibrary` supplies
the families that are already in use and would otherwise be silently dropped.

**Not every upstream is GitHub**, which the `libreFontList` entries make obvious and the
channel alone would have hidden:

- `pagure.io` — Liberation Fonts
- `software.sil.org` — Gentium, Charis
- `garamond.org` — Garamond No. 8
- `ospublish.constantvzw.org` — Not Courier Sans
- `ibm.com/plex`, `theleagueofmoveabletype.com`, `adobe-fonts.github.io`, `typenetwork.com`

So `fetch.py` needs an `upstream_type` per row — `github-release`, `github-raw`,
`zip-url`, `manual` — rather than assuming a GitHub API call will work. Amstelvar, Fira,
Source Sans, Noto and Liberation are all named in `libreFontList` and none are in the
channel's GitHub set.

## 4. Junk and duplicates

- **X11 font-server index files**, committed by accident: `fonts.dir` and `fonts.scale`
  (431 KB each), `fonts.list`, `encodings.dir`. Delete.
- **13 duplicate pairs** from downloading the same family twice under different naming:
  `HKGrotesk-Bold.otf` / `hkgrotesk_bold.otf`, the Manifont Grotesks, Linux Libertine in
  both `.otf` and `.ttf`.

---

## The fix: stop repairing, start deriving

All three problems have the same shape, and patching them one at a time means doing this
again in 2033. The repo should be **derived from a manifest**, not hand-assembled:

1. **`fonts.toml`** (or CSV) — one row per family: name, upstream URL, license SPDX,
   pinned version. This is the only file maintained by hand, and it's the thing worth
   reviewing.
2. **`fetch.py`** — reads the manifest, pulls each family's *built binaries plus its
   license file* from the upstream release, into `Families/<Name>/`. Not a full clone —
   font repos carry sources, tests and build chains and would be enormous.
3. **`install.sh`** — symlinks every family into `~/Library/Fonts`. This is the part that
   actually delivers "use on all my machines"; git alone gives you files macOS can't see.
4. The binaries stay committed, unlike the are.na image archives. Durability is the whole
   point here, upstreams disappear, and the sizes are trivial by comparison.

Seeding the manifest is mostly mechanical: 53 upstreams are already in the channel, and a
GitHub font repo almost always carries `OFL.txt` at its root, so the license field can be
verified by script rather than by trust.

**Blocked on:** unauthenticated GitHub API allows 60 requests/hour and this needs ~53 for
the staleness pass alone. Set `GITHUB_TOKEN`, or `brew install gh && gh auth login`.

`audit/libretype-channel.json` holds the 231 channel blocks this was read from.
