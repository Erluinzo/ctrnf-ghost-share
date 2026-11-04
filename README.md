# Ghost Sharing

Race other players' Time Trial ghosts and share your own, in CTR Nitro-Fueled ([OCTR PC port](https://github.com/Ryu7w7/OCTR-NitroFueled-PC)).

- **Share:** in the Time Trial ghost menu, press **R1** on your own ghost. A message shows the file and its folder
  (`user/savedata/1/<game>/GhostShare/` in your OCTR folder; `<game>`: CUSA13795 USA, CUSA14876 EU).
- **Race one:** put the `.ctrghost` file (keep its name) in `user/savedata/1/<game>/GhostShare/received/`
  in your OCTR folder (create the folders if needed). It appears in that track's ghost menu with the sharer's name.
- **Full race:** with [Replay Mode](https://github.com/Erluinzo/ctrnf-replay-mode), the export also writes a `.crr` file of the same run (Replay Mode keeps every Time Trial personal best). Put it in `user/savedata/1/<game>/RaceReplay/` to watch the exact race; [Ghost Viewer](https://github.com/Erluinzo/ctrnf-time-trial-replay) then also plays the ghost exactly. The `.ctrghost` file is unchanged and works without it, and your ghost in the game's save is never changed.

Shared ghosts unlock nothing. USA and EU players can share ghosts. Files are fully checked before use.

## Install
Download the ZIP for your game from [Releases](https://github.com/Erluinzo/ctrnf-ghost-share/releases):
`ghost-share` (USA, CUSA13795) or `ghost-share-eu` (EU, CUSA14876), version 1.21, OCTR v0.8 or newer.
In the launcher: Mods > Add files, enable it, restart the game.

## Build
Needs the OCTR checkout at `../CTRNF`, gcc, clang, binutils, `pip install capstone unicorn`:
`python3 build.py`, tests: `python3 tests/run_tests.py`.

## License
MIT. Copyright (c) 2026 Onur.
