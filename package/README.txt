Ghost Sharing 1.0.1
Author: Onur

Race other players' Time Trial ghosts, and share your own.

SHARE YOUR GHOST
In Time Trial, open the ghost menu of a track, move to your own ghost (under
"Player Ghost") and press R1. A message shows the file name and where it is:
  <OCTR folder>/mod-state/user/savedata/1/CUSA13795/GhostShare/
Send that .ctrghost file to anyone. Your ghost stays in your save, so you can
export it again at any time.

The file appears in that folder only when you close the game normally (the
game writes to a session folder while it runs; the launcher copies it when the
game closes). Without mod packages it is at once in:
  <OCTR folder>/user/savedata/1/CUSA13795/GhostShare/
Can't find it? Close the game normally and look again. After a crash it is in
the newest session folder:
  <OCTR folder>/mod-state/sessions/<session>/user/savedata/1/CUSA13795/GhostShare/
Or simply press R1 on your ghost again.

RACE A SHARED GHOST
1. Close the game first: it only sees files that were there when it started.
2. Open <OCTR folder>/mod-state/user/data/ and create a folder named "ghosts"
   if it is not there (without mod packages: <OCTR folder>/user/data/ghosts/).
3. Put the .ctrghost files you received in it. Keep the original file name:
   only letters, numbers, "_", "-" and "." (at most 63 characters, ending in
   ".ctrghost"). A name like "..._Neox (1).ctrghost", as browsers make for a
   second download, is skipped: rename it back.
In the ghost menu of that track, each ghost appears under the challenge ghosts
with the sharer's name. Select it like any other ghost. Up to 6 shared ghosts
per track; you can race them together with the game's own ghosts.

Shared ghosts count for nothing: no unlocks, trophies or stats. Your own time
and ghost are saved as in any Time Trial race.

A ghost carries the player's name, driver, kart, time and full driving line.
The game draws every ghost as a plain driver and kart, so paint, decals and
stickers are not shown.

SAFE FILES
Ghost files come from other people, so the game never reads them directly.
The patch checks every value first (size, names, track, numbers, times) and
builds the ghost itself with the game's own functions. A file that fails any
check is skipped.

GAME: Crash Team Racing Nitro-Fueled, USA (CUSA13795) version 1.21, OCTR
launcher with code-signature support. The launcher checks the game code before
it applies the patch and refuses it on any other game build. The EU edition is
not supported.

INSTALL: Mods > Add files, choose this ZIP, enable it, fully restart the game.
UNINSTALL: disable or remove it. Your exported ghosts stay in their folder.
