# Tessera Dev, and the project it came from

Tessera Dev is its own project. It is derived from
[MaxGramser/homeassistant_espscreen](https://github.com/MaxGramser/homeassistant_espscreen) (Tessera) under the MIT
licence, and it keeps a line to it: upstream's releases can be taken over, and work done here can be sent back as a
pull request. It runs in Home Assistant under its own name, **Tessera Dev**, and its screens build their firmware
from this repository, so there is never any doubt about which of the two is on the glass.

Everything in this `upstream/` folder exists only here: the tooling for that line, and the one place that knows which
lines make this project its own. Upstream has no such folder, so it never causes a conflict when its releases are
taken over, and it is never part of a pull request.

## What makes it its own project

`upstream/brand.py` owns every line that must not go upstream, in two kinds.

**The name Home Assistant shows:**

| Where | Upstream | Here |
|---|---|---|
| `repository.yaml` `name`, `url`, `maintainer` | Tessera, upstream's website | Tessera Dev, this repository |
| `screen_manager/config.yaml` `name` | Tessera Screen Manager | Tessera Dev Screen Manager |
| `screen_manager/config.yaml` `panel_title` | Tessera | Tessera Dev |

**Where things come from and go to:**

| Where | Upstream | Here |
|---|---|---|
| `screen_manager/app/core.py` `REPO` | upstream's repository | this one: the screens build their firmware from here |
| `packages/<board>.yaml` | upstream's URL and fonts | this one (generated from `REPO`, never edited by hand) |
| `screen_manager/app/feedback.py` `API` | upstream's website | empty: nothing is shared, and the card never asks |
| `docker/compose.yaml` image | `ghcr.io/maxgramser/...` | `ghcr.io/agillis/tessera-dev` |
| `README.md`, `docs/EASY_SETUP.md` | upstream's repository to add to HA | this one |
| `.github/FUNDING.yml` | upstream's donation link | none |
| `.github/workflows/preview.yml` | upstream's commit identity | the Actions bot |

The screens' firmware is the part that matters most: since `REPO` points here, a firmware change reaches a screen once
it is **pushed to GitHub**. ESPHome fetches the packages over HTTPS at build time, so an unpushed change never gets to
the glass. Build from the checkout instead while working on one: `esphome run checkout/<board>.yaml`
(`checkout/README.md`).

Upstream's copyright stays in `LICENSE`, and `NOTICE` says this is a fork of it.

`upstream/brand.py` puts all of that on and takes it off:

```sh
python3 upstream/brand.py            # put the name on
python3 upstream/brand.py --check    # say whether it is on (exit 1 when it is not)
python3 upstream/brand.py --remove   # take it off, for a branch that goes upstream
```

It is one commit of its own, and it is never cherry-picked into a pull request. Later work goes on top of it; `upstream/pr.sh` takes the commits you name, so the branding does not have to stay at the tip of `main`.
Running it twice changes nothing, so after a rebase you run it again instead of resolving the same conflict by hand.

The editor's own sidebar inside the add-on still says Tessera. That is on purpose: the page is built from `web/src`
into `screen_manager/app/static`, which is committed, so renaming it there would rewrite the whole bundle in every
sync and in every pull request. The name in Home Assistant's sidebar is what tells the two apart.

## Installing it in Home Assistant

Home Assistant's add-on store takes a repository, not a branch: it reads the repository's **default branch**. So the
branch you want to run is the one that has to be `main` here (or whatever you set as the default branch on GitHub,
under Settings, General, Default branch).

1. Settings, Add-ons, Add-on store, the three dots top right, Repositories.
2. Add `https://github.com/agillis/tessera-dev`.
3. The store gets a **Tessera Dev** section with **Tessera Dev Screen Manager** in it. Install that one.

Two things to know:

- **It is a separate add-on**, not an update of the upstream one: Home Assistant names an add-on after its repository
  as well. Its data (`screens.json`, the tiles, the ESPHome profiles it made) starts empty, so the screens have to be
  added again, or the data folder copied over from a backup of the other add-on.
- **Don't run both at once.** Both map host port 8098 for the camera pictures the screens fetch, and both would send
  layouts to the same screens. Stop the one you are not using. (Changing `ports:` in
  `screen_manager/config.yaml` here is enough to run them side by side, but then the screens have to be told the
  other port, so it is simpler to stop one.)

Home Assistant offers an update when the `version` in `screen_manager/config.yaml` is higher than the one it runs. So
a change you want to see on your own Home Assistant needs a version bump and a `CHANGELOG.md` entry, the same rule
upstream has (`AGENTS.md`).

## Day to day

```sh
# your own work, on main
git switch main
... edit ...
tools/check.sh                  # --firmware as well when the firmware changed
git commit -am "What changed"
# bump screen_manager/config.yaml and write the CHANGELOG entry, then
git push
```

Keep one change per commit and keep the version bump out of it, in a commit of its own. That is what makes a pull
request cheap later: the change alone travels, without the release bookkeeping that would collide with whatever
upstream released in the meantime.

## Taking over an upstream release

```sh
upstream/sync.sh --fetch     # only look: what is new upstream
upstream/sync.sh             # fetch, rebase main onto upstream/main, put the Tessera Dev name back
upstream/sync.sh --merge     # merge instead of rebasing, for a branch someone else also has
```

A conflict stops the script on purpose. Resolve it, finish the rebase (`git rebase --continue`), and run
`upstream/sync.sh` again; it will put the name back and tell you what is left to run. The two files that conflict most
often are `screen_manager/config.yaml` (the `version` line) and `screen_manager/CHANGELOG.md` (both sides added an
entry at the top). Take upstream's version and bump past it, and keep both changelog entries.

After a sync: `tools/check.sh`, then `git push --force-with-lease` (a rebase rewrites what was pushed before).

## Sending a change upstream

```sh
upstream/pr.sh fix/stop-build <commit> [<commit> ...]
```

That makes a branch that starts at `upstream/main` with only those commits on it, so the pull request holds the
change and nothing else: not the Tessera Dev name, not your other work in progress. It refuses if the branding ever
did ride along. Nothing is pushed; it prints the `git push` and `gh pr create` lines to run.

Upstream's `AGENTS.md` is the house style to follow in the change itself: plain English, no em dashes, no names or
personal entity ids, `tools/check.sh` green, and a `CHANGELOG.md` entry with the version bump as the last commit of
the branch, where the maintainer can redo or drop it.

## Keeping pull requests clean

`upstream/brand.py --remove` puts upstream's identity back, which is what `upstream/pr.sh` checks before it lets a branch go
out. So work that is meant for upstream stays sendable: write it as an ordinary commit, cut the branch from
`upstream/main` with `upstream/pr.sh`, and the identity never rides along. Three pieces of this fork's work were written
that way on purpose and could go upstream as they are: the repository named in one place, the feedback card needing a
website to share with, and the Stop button.
