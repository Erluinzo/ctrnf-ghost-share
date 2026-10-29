# Ghost Sharing (CTR Nitro-Fueled, OCTR PC port)

A game patch by Onur: race other players' Time Trial ghosts, and share your own.
For the game version 1.21, USA (CUSA13795) or EU (CUSA14876), on the [OCTR port](https://github.com/Ryu7w7/OCTR-NitroFueled-PC).

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
| Your exports: right away (while the game runs) | `mod-state/sessions/<newest folder>/user/savedata/1/CUSA13795/GhostShare/` | `user/savedata/1/CUSA13795/GhostShare/` |
| Your exports: after you close the game | `mod-state/user/savedata/1/CUSA13795/GhostShare/` | (same as above) |

Paths are in the OCTR folder; on the EU edition, `CUSA14876` instead of `CUSA13795`. If you installed the ZIP on the Mods page, use the first column.
Exports go to a save data folder of the patch's own, because saves are the only files the port keeps
after a game with mod packages. The game never reads that folder: it opens its own saves by name.

**With mod packages, the game runs in a session folder:** every file it writes goes to the newest
folder in `mod-state/sessions/`, and the launcher copies the saves to `mod-state/user/savedata/` only
when the game closes normally. So your file is ready at once in the session folder, and after a normal
close it is also in `mod-state/user/savedata/`, where it stays. The export message shows both places.
After a crash, it is only in that game's session folder (the newest one until you start the game
again; the launcher deletes old session folders after a few launches). Without mod packages, the file
is in `user/savedata/` at once.

Can't find your file?
- While the game runs: open the newest folder in `mod-state/sessions/` (sort by date).
- After a crash: the session folder of that game, before you start the game a few more times.
- Or export it again: your ghost stays in your save, so R1 on your ghost exports it again at any time.

## Install
Download the ZIP for your game from the [releases](https://github.com/Erluinzo/ctrnf-ghost-share/releases):
`ghost-share-<version>.zip` for USA (CUSA13795), `ghost-share-eu-<version>.zip` for EU (CUSA14876).
In the OCTR launcher: Mods > Add files, choose it, enable it, fully restart the game. To update, add the
new ZIP and remove the old one. Use only the ZIP for your game: with the other one enabled, the game does
not start ("executable patch targets a different game edition/version"). Ghost files are the same on both
editions, so USA and EU players can share ghosts.

## Import a ghost
1. Close the game. With mod packages, the game only sees files that were there when it started.
2. In your OCTR folder, open `mod-state/user/data/` and create a folder named `ghosts` if it is not there.
3. Put the `.ctrghost` file in it. **Keep the original file name:** only letters, numbers, `_`, `-` and
   `.` are allowed (at most 63 characters, ending in `.ctrghost`). A name like
   `t112_roos_tubes_1m17s51_Neox (1).ctrghost`, as browsers and chat apps make for a second download,
   is skipped without a message; rename it back.
4. Start the game and open the ghost menu of that track. The ghost is at the bottom of the list, with
   the sharer's name.

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
Needs the OCTR checkout at `../CTRNF` (with `out/eboot.elf` from a USA build, and the EU executable at
`orig/CUSA14876-eboot.elf`), gcc, clang, binutils,
`pip install capstone unicorn`.

```sh
python3 build.py              # writes package/ (USA) and package-eu/ (EU) (+ switched-on copies in ../CTRNF/patches)
python3 tests/run_tests.py    # PC tests; add --fuzz 120 for a 2-minute fuzz run
python3 tools/peek.py         # state of the patch in the running game (Linux)
```

Notes on the game code: `notes/`.
