# libreFontLibrary

The free/libre/open-source fonts I use on all my machines.

> When people see type that they feel could be improved, if it is in the public domain they are free to do so. With the development of free software font editors, everyone has access to the necessary tools. Now the obstacle is that the knowledge of how to develop and refine type is not freely available.
> — David Crossland

## How it fits together

**[libretype on are.na](https://www.are.na/kristian-bjornard/libretype)** is where finds land first — anything interesting, saved as it turns up.

**`fonts.toml`** is the list. One entry per family: where it comes from, what license it carries, whether it's in this repo yet. It's the only file here edited by hand.

**`Families/`** holds the fonts: one folder per family, fetched from its upstream, with its license inside. That's the only folder that gets installed.

**`Unsorted/`** holds files from the 2019 collection that haven't been fetched fresh yet — kept, not installed. `audit/AUDIT.md` has the history of how it got here.

## Adding a font

Save it to the are.na channel. A link to its GitHub repo or its Google Fonts specimen page is enough. Then:

```sh
python3 build_manifest.py   # reads the channel back into fonts.toml
python3 verify.py           # checks each new family's license upstream
python3 fetch.py            # downloads it, with its license, into Families/
python3 build_manifest.py   # records what was fetched
```

For Google Fonts, `google-fonts.txt` takes the embed link from a "Get font" bag on fonts.google.com.

Or add a `[[family]]` to `fonts.toml` by hand. Foundries whose whole catalog belongs here are listed under `foundries` at the top of that file — Velvetyne, so far.

## On a new machine

```sh
git clone https://github.com/bjornmeansbear/libreFontLibrary
cd libreFontLibrary && ./install.sh
```

Later, `git pull && ./install.sh`. On macOS it copies into `~/Library/Fonts`; on Linux into `~/.local/share/fonts`. It keeps a list of what it put there, so `./install.sh --remove` takes out exactly that and nothing else.

## Licenses

Every family ships with its license. The OFL allows redistribution "provided that each copy contains the above copyright notice and this license," and a public repo is redistribution.

`verify.py` records what each upstream declares, and reads the license text itself when the host can't tell. `fetch.py` won't write a family without a license file, and for families with only a web page, the license inside the download decides. Anything free to use but not free to redistribute stays out.

## History

- **2018** — [libreFontList](https://github.com/bjornmeansbear/libreFontList), a list of favourites. It came out of [a Twitter thread](https://twitter.com/imagineterrain/status/1017789533390286849) and the Spring 2018 course *Special Topics in Graphic Design: Open Source* at MICA ([gd399-osd](https://github.com/gd399-osd)). Absorbed into `fonts.toml`, where those families are marked `favourite = true`.
- **2019** — the first files, added to this repo by hand.
- **2026** — the manifest, the audit, license checks against every upstream.

## Where to look

- [Libre fonts by womxn](http://design-research.be/by-womxn/)
- [Fontain](https://fontain.org/)
- [Google Fonts](https://fonts.google.com/), and its source at [github.com/googlefonts](https://github.com/googlefonts)
- [Use & Modify](http://usemodify.com/)
- [Typotheque Interstices](http://typotheque.interstices.io/)
- [Velvetyne](https://velvetyne.fr/) — source on [GitLab](https://gitlab.com/velvetyne)
