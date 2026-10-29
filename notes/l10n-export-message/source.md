# Ghost Sharing: the "Ghost exported" popup text (English review, owner's localization pass)

## Where it shows and how much room it has
The game's notice popup (title "GHOST EXPORTED", one button "CONTINUE"), opened when the player presses R1 on
their own ghost in the Time Trial ghost menu. The body is plain text; `\n` starts a new line and is the only
formatting. The game shrinks the font when the text gets long: the draft below (about 450 characters with the
file name) is already small but readable, so the reviewed text must not be longer than the draft (shorter is
better). The C buffer holds 600 characters. Readers: players of the OCTR PC port, many not native English
speakers: plain everyday words (CEFR B1), short lines, no em dash (a comma, a colon or two sentences instead).

## Values filled in by the code (keep them exactly)
- `<FILE>`: the exported file name, e.g. `t111_crash_cove_1m21s99_Neox.ctrghost`.
- `<N>`: the player's user number, nearly always `1`.
- `<GAME>`: `CUSA13795` (USA) or `CUSA14876` (EU).
Folder paths must stay exactly as written (they are real folders, relative to the player's OCTR folder):
`mod-state/sessions/<newest folder>/user/savedata/<N>/<GAME>/GhostShare`, `mod-state/user/savedata/<N>/<GAME>/GhostShare`,
`user/savedata/<N>/<GAME>/GhostShare`, `mod-state/user/data/ghosts`, `user/data/ghosts`.

## What the text must tell the player (the meaning to check against)
1. The file's name.
2. The file is ready NOW, while the game is still open, in `mod-state/sessions/<newest folder>/user/savedata/<N>/<GAME>/GhostShare`
   in the OCTR folder ("newest folder" = the most recent folder inside mod-state/sessions; its name is a long random code).
   This is true when the player uses mod packages (any ZIP mod enabled in the launcher's Mods page), which is the usual case.
3. When the player closes the game normally, the launcher also copies it to `mod-state/user/savedata/<N>/<GAME>/GhostShare`,
   where it stays. (The session folder is only temporary: the launcher deletes old session folders after a few launches,
   and after the next launch it is no longer the newest one.)
4. If the game does not close normally (a crash), the file is only in that session folder.
   (Nice to have in the popup if it fits; the README explains it anyway.)
5. Without mod packages, the file is at once in `user/savedata/<N>/<GAME>/GhostShare`, and the session folders don't apply.
6. The player can send this file to anyone.
7. The receiver puts it in `mod-state/user/data/ghosts` (without mod packages: `user/data/ghosts`) and then picks
   this ghost in the ghost menu of the same track.

## The draft (current code)
```
<FILE>

In your OCTR folder, now: mod-state/sessions/(newest folder)/user/savedata/<N>/<GAME>/GhostShare
After you close the game normally: mod-state/user/savedata/<N>/<GAME>/GhostShare
Without mod packages: user/savedata/<N>/<GAME>/GhostShare

Send this file to anyone. They put it in mod-state/user/data/ghosts (without mod packages: user/data/ghosts) and choose your ghost in this track's ghost menu.
```
