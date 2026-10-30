# Ghost Sharing

Race other players' Time Trial ghosts and share your own, in CTR Nitro-Fueled ([OCTR PC port](https://github.com/Ryu7w7/OCTR-NitroFueled-PC)).

- **Share:** in the Time Trial ghost menu, press **R1** on your own ghost. A message shows the file and its folder.
- **Race one:** close the game, put the `.ctrghost` file (keep its name) in `mod-state/user/data/ghosts/`
  in your OCTR folder (create it if needed). It appears in that track's ghost menu with the sharer's name.

Shared ghosts unlock nothing. USA and EU players can share ghosts. Files are fully checked before use.

## Install
Download the ZIP for your game from [Releases](https://github.com/Erluinzo/ctrnf-ghost-share/releases):
`ghost-share` (USA, CUSA13795) or `ghost-share-eu` (EU, CUSA14876), version 1.21.
In the launcher: Mods > Add files, enable it, restart the game.

## Build
Needs the OCTR checkout at `../CTRNF`, gcc, clang, binutils, `pip install capstone unicorn`:
`python3 build.py`, tests: `python3 tests/run_tests.py`.

## License
MIT. Copyright (c) 2026 Onur.
