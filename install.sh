#!/bin/sh
# Install every fetched family on this machine.
#
#   ./install.sh             copy the fonts in install-list.txt into place —
#                            variable fonts first, statics only where no
#                            variable font covers them
#   ./install.sh --all       every font in Families/, statics included
#   ./install.sh --dry-run   list what would be copied
#   ./install.sh --remove    take out everything this script installed
#
# Syncing a new machine is: git clone (or pull), then ./install.sh.
#
# macOS: ~/Library/Fonts, flat — fonts in its subfolders don't load reliably.
# Linux: ~/.local/share/fonts/libreFontLibrary, then fc-cache.
#
# Only Families/ is installed — fetched, licensed, one folder per family. The
# loose 2019 files at the repo root are not. A record of what this script
# copied lives beside the fonts, so --remove never touches anything else, and
# a font already there that this script didn't put there is left alone.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
mode=${1:-install}

case "$(uname)" in
  Darwin) dest="$HOME/Library/Fonts" ;;
  *)      dest="${XDG_DATA_HOME:-$HOME/.local/share}/fonts/libreFontLibrary" ;;
esac
record="$dest/.libreFontLibrary-installed"

if [ "$mode" = "--remove" ]; then
  [ -f "$record" ] || { echo "nothing recorded as installed in $dest"; exit 0; }
  n=0
  while IFS= read -r f; do rm -f "$dest/$f"; n=$((n + 1)); done < "$record"
  rm -f "$record"
  echo "removed $n fonts from $dest"
  exit 0
fi

[ -d "$here/Families" ] || { echo "no Families/ yet — run python3 fetch.py first"; exit 1; }
mkdir -p "$dest"
touch "$record"
new=$(mktemp); copied=0; same=0; skipped=0

if [ "$mode" = "--all" ] || [ ! -f "$here/install-list.txt" ]; then
  find "$here/Families" -type f \( -iname '*.otf' -o -iname '*.ttf' \) > "$new.list"
else
  grep -v '^#' "$here/install-list.txt" | sed "s#^#$here/Families/#" > "$new.list"
fi
while IFS= read -r src; do
  name=$(basename "$src")
  if [ -e "$dest/$name" ] && ! grep -qxF "$name" "$record"; then
    echo "  skip  $name (already installed, not by this script)"
    skipped=$((skipped + 1)); continue
  fi
  echo "$name" >> "$new"
  if cmp -s "$src" "$dest/$name" 2>/dev/null; then same=$((same + 1)); continue; fi
  if [ "$mode" = "--dry-run" ]; then echo "  copy  $name"; else cp "$src" "$dest/$name"; fi
  copied=$((copied + 1))
done < "$new.list"

if [ "$mode" != "--dry-run" ]; then
  sort -u "$record" "$new" -o "$record"
  command -v fc-cache >/dev/null 2>&1 && fc-cache -f "$dest" >/dev/null
fi
rm -f "$new" "$new.list"
echo "${copied} copied, ${same} unchanged, ${skipped} skipped -> $dest"
