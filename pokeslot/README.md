# Pokeslot

Standalone Game Boy slot-game project. Current milestone: an untested ROM boot screen showing POKESLOT. No reels, wagering, audio playback, or saving are implemented yet.

## Build

Install RGBDS 0.9.1 and run `make -C pokeslot` from the repository root. Output: `pokeslot/build/pokeslot.gb`.

The Pokeslot ROM workflow builds this project independently of the original Pokemon Red/Blue Makefile and uploads a ZIP containing the ROM, map, and symbols. Import the GB file into Delta after extracting if necessary.

The first Actions run and a Delta boot test must pass before this is considered verified.

## Planned architecture

One shared five-reel, three-row engine with 25 paylines. Machine definitions will hold names, species rosters, reel strips, payout tables, and bonus settings. The first playable milestone is one complete machine; additional machines follow through data definitions.

Preserve all original front sprites in `gfx/pokemon/front/` and species metadata until extraction is complete. Original slot artwork lives in `gfx/slots/`. These assets are not yet included in this boot-test ROM. Keep original assets separate from generated compact reel symbols. No inherited assets or original build files have been deleted.

Pokemon and original game assets belong to their respective rights holders. This is an unofficial fan project, not a license grant for those assets. Upstream source: https://github.com/pret/pokered.
