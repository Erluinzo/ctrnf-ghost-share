# Ghost Sharing (CTR Nitro-Fueled, OCTR PC port)

A game patch by Neox: race other players' Time Trial ghosts, and share your own.
For the USA game, CUSA13795 version 1.21, on the [OCTR port](https://github.com/Ryu7w7/OCTR-NitroFueled-PC).

## What it does
- **Shared ghosts in the ghost menu.** Every shared ghost file for the track appears in the Time Trial
  ghost menu, under the challenge ghosts, with the sharer's name, their driver and their time. Select
  it like any other ghost; you can race several at once (up to 6 shared ghosts per track).
- **Export your own ghost.** In the ghost menu, move to your own ghost (under "Player Ghost") and press
  **R1**. The file `<track>_<time>_<your name>.ctrghost` appears in the export folder (below), and a
  popup shows its name and where to find it. Send it to anyone. Your ghost is kept in your save, so you can export it again at any time.
- **It counts for nothing.** Beating a shared ghost does not unlock ghosts, give trophies or change
  stats. Your own time and ghost are saved as in any Time Trial race.

## The folders
| | With mod packages enabled (any ZIP mod on the Mods page) | Without mod packages |
|---|---|---|
| Received ghosts: put them here | `mod-state/user/data/ghosts/` | `user/data/ghosts/` |
| Your exports appear here | `mod-state/user/savedata/1/CUSA13795/GhostShare/` | `user/savedata/1/CUSA13795/GhostShare/` |

Paths are in the OCTR folder. Exports go to a save data folder of the patch's own, because saves are
the only files the port keeps after a game with mod packages. The game never reads that folder: it
opens its own saves by name. Put received files in place while the game is closed or before you open
the ghost menu of that track.

## What a ghost carries
Your name, driver, kart, time and the full recording of your driving line. The game draws ghosts as a
driver and kart body only, so paint, decals, wheels and stickers are not shown, and there is no name
tag on the track (the name is in the menu).

## Safety
Ghost files come from other people, so the patch never lets the game read them directly:
- The file format is this patch's own, fixed layout (`src/share_format.h`), not the game's ghost format.
- Every field is checked before use: exact file size, text only from a small set of characters with
  nothing after its end, driver and kart names that exist in the game, the track of the menu, finite
  numbers in range, times that never go back, known input bits only.
- The ghost is then built in memory from the checked values with the game's own functions. A file that
  fails any check is skipped; a bad key found while building drops that ghost.
- File names are limited to `[A-Za-z0-9_.-]` ending in `.ctrghost`, so a name cannot leave the folder.
- Tested on the PC with AddressSanitizer: all 163 game ghosts and real player ghosts pass, hostile and
  randomly damaged files are refused, and the C checks agree with a separate Python checker
  (`tools/ctrghost.py`) on every file; fuzzed with libFuzzer.

## Building (developers)
Needs the OCTR checkout at `../CTRNF` (with `out/eboot.elf` from a build), gcc, clang, binutils,
`pip install capstone unicorn`.

```sh
python3 build.py              # writes package/patches/GhostShare.xml (+ a switched-on copy in ../CTRNF/patches)
python3 tests/run_tests.py    # PC tests; add --fuzz 120 for a 2-minute fuzz run
python3 tools/peek.py         # state of the patch in the running game (Linux)
```

Notes on the game code: `notes/`.
