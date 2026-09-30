#!/usr/bin/env bash
# Bring this project up to date with the one it came from. upstream/README.md is the whole procedure.
#
#   upstream/sync.sh            fetch upstream and rebase the current branch onto upstream/main
#   upstream/sync.sh --merge    merge upstream/main instead, when the branch is already pushed and shared
#   upstream/sync.sh --fetch    only fetch and list what is new upstream
#
# Adds the `upstream` remote the first time. Stops on a dirty working tree, because a rebase would carry the
# uncommitted changes along. Puts the Tessera Dev name back afterwards (upstream/brand.py), which a conflict resolution
# can drop, and says what still has to be run by hand.
set -euo pipefail

UPSTREAM_URL=https://github.com/MaxGramser/homeassistant_espscreen.git
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"

mode=rebase
case ${1:-} in
  --merge) mode=merge ;;
  --fetch) mode=fetch ;;
  '') ;;
  -h|--help) sed -n '2,/^set -euo/p' "${BASH_SOURCE[0]}" | sed '$d; s/^# \{0,1\}//'; exit 0 ;;
  *) echo "Unknown option: $1 (see upstream/sync.sh --help)" >&2; exit 2 ;;
esac

if ! git remote get-url upstream >/dev/null 2>&1; then
  echo "Adding the upstream remote: $UPSTREAM_URL"
  git remote add upstream "$UPSTREAM_URL"
fi
git fetch upstream

branch=$(git rev-parse --abbrev-ref HEAD)
behind=$(git rev-list --count "HEAD..upstream/main")
ahead=$(git rev-list --count "upstream/main..HEAD")
echo
echo "$branch is $ahead commit(s) ahead of upstream/main and $behind behind."
if ((behind)); then
  echo "New upstream:"
  git log --oneline --no-decorate "HEAD..upstream/main" | sed 's/^/  /'
fi

[[ $mode == fetch ]] && exit 0
((behind)) || { echo "Nothing to take over."; exit 0; }

if [[ -n $(git status --porcelain) ]]; then
  echo >&2
  echo "The working tree is not clean. Commit or stash first; $mode would carry these along:" >&2
  git status --short >&2
  exit 1
fi

echo
echo "Running git $mode upstream/main on $branch ..."
# A conflict stops here on purpose: resolve it, finish the rebase or merge, then run upstream/sync.sh again.
git "$mode" upstream/main

echo
python3 upstream/brand.py
python3 upstream/brand.py --check
cat <<'NEXT'

Next:
  tools/check.sh                       the release checks; --firmware as well when the sync touched the firmware
  git push                             (--force-with-lease after a rebase of an already pushed branch)
Home Assistant offers the update once screen_manager/config.yaml carries a higher version than the copy it runs.
NEXT
