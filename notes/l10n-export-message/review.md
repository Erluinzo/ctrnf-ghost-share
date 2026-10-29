# Review: "Ghost exported" popup text (English, second pair of eyes)

Checked against `source.md`: meaning points 1-7, then natural reading, register, length. Paths, `<FILE>`, `<N>`, `<GAME>` unchanged. No em dash or spaced en dash in draft or reviewed text.

## Must fix
(none)

## Should fix
- line 3 | "In your OCTR folder, now:" is not natural English, and "In your OCTR folder" looks tied to the first path only, while all three paths are in that folder (a reader may take `user/savedata/...` for a system folder) | `In your OCTR folder, now: mod-state/sessions/...` | `In your OCTR folder:` as its own line, then `Now: mod-state/sessions/...` (same length)
- line 4 | "normally" reads as "usually" for many learners, so point 3 is blurred, and the crash case (point 4) stays unsaid | `After you close the game normally:` | `After closing the game (no crash):` (same length; covers point 4 at no cost)

## Optional
- line 5 | nothing says the two lines above are the mod-packages case; a player without mod packages may look in `mod-state/sessions` first (+5 characters, so not applied) | `Without mod packages:` | `Without mod packages: only`
- last line | "pick" is the usual menu word and 2 characters shorter | `and choose your ghost` | `and pick your ghost`
- last line | "this track" is said from the sender's side; "the same track" is clear from both sides (+4) | `in this track's ghost menu` | `in the same track's ghost menu`
- last line | a bare command; a game message more often says what the player can do (+8) | `Send this file to anyone.` | `You can send this file to anyone.`

## Reviewed text
```
<FILE>

In your OCTR folder:
Now: mod-state/sessions/(newest folder)/user/savedata/<N>/<GAME>/GhostShare
After closing the game (no crash): mod-state/user/savedata/<N>/<GAME>/GhostShare
Without mod packages: user/savedata/<N>/<GAME>/GhostShare

Send this file to anyone. They put it in mod-state/user/data/ghosts (without mod packages: user/data/ghosts) and choose your ghost in this track's ghost menu.
```

characters: draft 437, reviewed 437

## Follow-up after the blind reading
Judged against `blind.md` (section 7) and `compare.md`. Limit for this round: 520 characters.
- crash case not covered (blind 7, compare point 4; now required by the owner) | fixed: new line `After a crash: only in the newest session folder.` ("newest session folder" points at `mod-state/sessions/(newest folder)`); the closing line loses "(no crash)" and reads `After closing the game:`.
- receiver's "without mod packages" could mean the sender's setup (blind 7, compare point 7) | fixed: `(or user/data/ghosts if they play without mod packages)`, "they" is the receiver.
- receiver's folder is not said to be in their OCTR folder (blind 7, compare point 7) | fixed: `They put it in their own OCTR folder, in mod-state/user/data/ghosts ...`.
- "(newest folder)": newest created or last changed | not changed: for the running game both give the same folder (compare.md agrees).
- first two lines not marked as the mod-packages case | not changed: the reader resolved it from the "Without mod packages" line; the new crash line sits in that group too; kept short.
- copied or moved on close, is the session copy still there | not changed in words: "After a crash: only in ..." now implies the session copy stays and closing adds a copy; the README has the detail.
- "mod packages" not explained, no way to check | not changed: launcher term, README topic.
- "this track's ghost menu" only makes sense to the sender; where the menu is | not changed: the sender reads the popup; the file name carries the track; Time Trial is README material. "choose" became "pick" (2 characters shorter, the menu word).
- receiver may need the mod or a restart | not changed: README.
- bare file name first, "t111" unexplained | not changed: the title GHOST EXPORTED sits right above it; the name is a real value.
- stiff, note-like style | partly: the crash and receiver lines are sentences now; the path list stays a list so it fits.

```
<FILE>

In your OCTR folder:
Now: mod-state/sessions/(newest folder)/user/savedata/<N>/<GAME>/GhostShare
After closing the game: mod-state/user/savedata/<N>/<GAME>/GhostShare
After a crash: only in the newest session folder.
Without mod packages: user/savedata/<N>/<GAME>/GhostShare

Send this file to anyone. They put it in their own OCTR folder, in mod-state/user/data/ghosts (or user/data/ghosts if they play without mod packages), and pick your ghost in this track's ghost menu.
```

characters: 516 (limit 520; previous 437)
