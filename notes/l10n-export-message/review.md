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
