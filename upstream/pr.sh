#!/usr/bin/env bash
# A branch for the upstream project: the change alone, on top of upstream/main, without this project's own name.
# upstream/README.md is the whole procedure.
#
#   upstream/pr.sh <branch> <commit>...    a new branch off upstream/main with those commits cherry-picked
#   upstream/pr.sh --dry-run <branch> ...  only say what it would do
#
# The branch starts at upstream/main, not at this fork's main, so the pull request holds the change and nothing else:
# no Tessera Dev name, no commits of yours that are not ready. Nothing is pushed; the commands to push and to open the
# pull request are printed at the end for you to run.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"

dry=0
[[ ${1:-} == --dry-run ]] && { dry=1; shift; }
if [[ ${1:-} == -h || ${1:-} == --help || $# -lt 2 ]]; then
  sed -n '2,/^set -euo/p' "${BASH_SOURCE[0]}" | sed '$d; s/^# \{0,1\}//'
  [[ $# -lt 2 && ${1:-} != -h && ${1:-} != --help ]] && exit 2
  exit 0
fi
branch=$1; shift
commits=("$@")

[[ $branch =~ ^[A-Za-z0-9][A-Za-z0-9._/-]*$ ]] || { echo "A branch name, such as fix/stop-build" >&2; exit 2; }
git show-ref --quiet --verify "refs/heads/$branch" && { echo "The branch $branch already exists." >&2; exit 1; }
[[ -n $(git status --porcelain) ]] && { echo "Commit or stash your changes first." >&2; git status --short >&2; exit 1; }

git remote get-url upstream >/dev/null 2>&1 || { echo "No upstream remote yet: run upstream/sync.sh --fetch once." >&2; exit 1; }
git fetch upstream

echo "Commits to take over, oldest first:"
for commit in "${commits[@]}"; do
  git log -1 --oneline --no-decorate "$commit" | sed 's/^/  /'
done
echo "on top of $(git log -1 --oneline --no-decorate upstream/main)"
((dry)) && exit 0

git switch --create "$branch" upstream/main
git cherry-pick "${commits[@]}"

# The fork's own name must not ride along. It normally cannot, because it lives in a commit of its own that is not
# cherry-picked here, but a squashed or amended commit can carry it.
if python3 upstream/brand.py --check >/dev/null 2>&1; then
  echo >&2
  echo "This branch carries the Tessera Dev name, which must not go upstream." >&2
  echo "Run: python3 upstream/brand.py --remove && git commit --amend --all --no-edit" >&2
  exit 1
fi

remote_branch=$(git rev-parse --abbrev-ref HEAD)
cat <<NEXT

$branch is ready: $(git rev-list --count upstream/main..HEAD) commit(s) on upstream/main.

Check it, then send it:
  tools/check.sh
  git push --set-upstream origin $remote_branch
  gh pr create --repo MaxGramser/homeassistant_espscreen --base main --head $(git config user.name 2>/dev/null || echo YOUR-USER):$remote_branch

Back to your own screens afterwards:
  git switch main
NEXT
