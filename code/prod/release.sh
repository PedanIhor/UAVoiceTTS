#!/bin/bash
# Publish a release: set the .toc version, refresh it inside the zip and the game folder, commit, tag, push, create the GitHub release with the zip.
# bash release.sh <version> <notes-file>      e.g. bash release.sh 0.4.1 out/notes_0.4.1.md
set -e
V=$1; NOTES=$(cd "$(dirname "$2")" && pwd)/$(basename "$2")
[[ -n $V && -f $NOTES ]] || { echo "usage: bash release.sh <version> <notes-file>"; exit 1; }
cd "$(dirname "$0")/../.."
rm -f .git/index.lock
TOC=code/addon/UAVoiceTTS/UAVoiceTTS.toc
sed -i '' "s/^## Version: .*/## Version: $V/" $TOC
(cd code/addon && zip -q ../../UAVoiceTTS.zip UAVoiceTTS/UAVoiceTTS.toc)
G="/Applications/World of Warcraft/_classic_beta_/Interface/AddOns/UAVoiceTTS"; [[ -d $G ]] && cp $TOC "$G/"
git add README.md $TOC code/prod/release.sh
git diff --cached --quiet || git commit -q -m "UAVoiceTTS $V

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01XrHA4aiQJkggfiYJZMf46A"
git tag -f v$V
git push -q origin HEAD && git push -q -f origin v$V
gh release create v$V UAVoiceTTS.zip --title "UAVoiceTTS $V" --notes-file "$NOTES"
echo "RELEASED v$V: $(gh release view v$V --json url -q .url)"
