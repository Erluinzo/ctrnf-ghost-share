# On-screen message after export (USA CUSA13795 1.21)

ELF addresses of `CTRNF/out/eboot.elf` (patch XML = + 0x400000). Read from code and assets only; nothing was run.
"Unverified" = not tested in game. Goal: after R1 export on your own ghost, show "Ghost saved: <file> ..." with the game's own UI
(sceMsgDialog has no UI in the port).

## Answer: the game's notice popup, opened with 0x9c3890 (recommended)
The game has a ready helper that opens the standard popup (project `Octane_YesNoDialog`) with a title and a body text and no option
buttons. The player closes it with Select (Cross). Raw text works (no .lng key needed).

`0x9c3890(void **out_handle, CGuiManager *gui, char **title, char **body, void *user_data, void (*on_close)(void *user_data, void *info), int a, int b)`
- `gui` = `[0x2ac0dc0]` (CGuiManager `_Instance`; set by 0x9809b0).
- `title`, `body`: **pointers to igString variables** (igString = `char*` from 0x1574080, refcount at -8). The helper adds its own refs;
  release yours after the call with 0x1518e30(pool, str-0x10). A null or empty title hides the header.
- `user_data`, `on_close`: 0, 0 is fine. If `on_close` != 0 it is stored as `_closeCallback` (+0x60) with `_callbackUserData` (+0x70)
  and called `on_close(user_data, info)` when the dialog project closes (0x9aa36d-0x9aa3a1).
- `a`, `b` (stack args 7 and 8): pass **5 and -2**, as all three game callers do (meaning not traced; open-params +8/+0xc).
- `*out_handle` = handle to the opened project (or 0). Release it like the callers do (below); the project stays open.

Game callers (all `push -2; push 5; call 0x9c3890`, rsi = `[0x2ac0dc0]`, r8 = r9 = 0, handle released right after):
- 0x9c289e in 0x9c2340, from `CGuiBehaviorOctaneTeamSelect` event handler 0x9c1250 (vtable slot 25 at 0x2543d68) on
  `CGuiEventTeamSelectConfirmTeam`: a GUI behavior event handler opening the popup, same situation as our R1 hook. Title/body = behavior +0x88/+0x90.
- 0xb38f6a in 0xb38cc0: title = `CGlobalPlatformStrings._dialogBoxNotificationTitle` ("NOTICE"), made with 0x1574080 from `[[0x2abce90]+0x260]`.
- 0x1287dbf in 0x1287d80: title = null (hidden), body = object +0xc8.

### What 0x9c3890 does (verified in code)
1. `info = 0x10c5710(pool)` = new `CDialogBoxInfo` (0xc8, meta slot 0x2ab7d78; pool picked like everywhere else).
2. `_title` +0x30 = *title, `_body` +0x38 = *body (ref +1 each), `_canCancel` +0x49 = 0; if on_close: +0x60/+0x70.
3. Open params on the stack: {+0 info (ref), +8 a, +0xc b, +0x10 0, +0x14 0, +0x18 8, +0x1c -1, +0x20 0}.
4. `0x986820(out, gui, [[0x2ac0dc0]+0x28]+0xb0, &params, -1, &zero16)` = open GUI project by name. `+0x28` = `_guiSystemData`,
   `+0xb0` = `_dialogBoxMenuName` = **"Octane_YesNoDialog"** (update2.pak `loosedata/guisystemdata.igz`, COctaneGuiSystemData at data +0xf20).
   0x986820 reuses an open/loaded project (0x97ed30 by name) or streams it in (0x987450; locks controls until loaded, CGuiManager +0x1b0).
5. Releases its temporaries (0x27ae10), the info ref, returns. Synchronous, no wait.

### How the popup shows the text and closes (verified in code + asset)
Dialog behavior: `CGuiBehaviorOctaneDialogBox` (vtable slot 25 = 0x12ad340 -> `CGuiBehaviorDialogBox` handler 0x9aa1c0; size 0x128).
Fields: +0x8c _option, +0x98 _dialogBoxInfo, +0xa8/+0xb0 option placeables, +0xb8 _bodyText, +0xc0 _titleText, +0x118 _defaultCancelInput,
+0x11c _noOptionContinueInput.
- Setup (0x9aa3a3..): info comes from the open params; body: `[_bodyText+0x30] = string(info._body)` (0x9aa606-0x9aa665);
  title copied the same way (0x9aa66a-0x9aa6cc) or the header is hidden when empty. igGuiPlaceable +0x30 = **_displayText**, the same field
  the ghost list VSC sets with raw names (already seen working in game), so raw text shows as is.
- No options + no option placeables: sets info `_useButtonPrompt` (+0xc0) = 1 and calls 0x9ab3d0 / 0x9ab5b0 (probably the button legend; unverified).
- Input (0x9aa781..): `_inputCallback` (+0x68) if set; cancel check 0x9aba50 only when `_canCancel` (0 here, so Circle does nothing);
  then 0x9abd00: with no _option1/_option2 it returns `signal == map(_noOptionContinueInput)` -> 0x9aadd8 -> 0x9aae36 -> **0x97f7a0(behavior, 1)** (close, result 1).
  Map table 0x1d9d330 (input enum 1..12 -> signal): 1->8 Select, 2->9 Back, 3->10 Option1, 4->11 Option2, 5->17, 6->16, 7->15, 8->14, 12->12.
- Asset `update2.pak ui/Octane_YesNoDialog.igz` (CGuiBehaviorOctaneDialogBox at data +0x10c8): `_noOptionContinueInput` = 1 (**Select = Cross**),
  `_defaultCancelInput` = 2 (Back). So Cross closes it.
- Body text box `[Description]` (placeable +0x6b0): extent 700 x 150, its igGuiText (+0x14d0): fontScale 0.35, **_wordWrap 1, _forceFitInBox 1**
  (long text wraps and shrinks). Header `[Header]` (+0x590): 589 x 75, caps on, no wrap, force fit.
  igGuiText field offsets: +0x5c hAlign, +0x60 vAlign, +0x64 _fontScale, +0x68 _forceFitInBox, +0x69 _wordWrap.
  Fonts GeekSpeak / Zoinks_Outline: plain ASCII expected to work; `\n` line breaks not checked.

### Handle release (copy of the callers' inline code, e.g. 0x9c28a7-0x9c28d8)
```c
int32_t *h = out;            /* the handle returned in *out_handle */
if (h) {
    int32_t old = __atomic_fetch_add(h, -1, __ATOMIC_SEQ_CST);
    int last = (old & 0x90000000) ? 3 : 2;
    if ((old & 0xffff) == last) game_handle_free(&out);   /* 0x149f280(&handle) */
    out = 0;
}
```

### Calls for the patch (gs_entry_button, after export_own_ghost)
New symbols: `game_open_dialog` = 0x9c3890, `game_handle_free` = 0x149f280, `g_gui_manager` = 0x2ac0dc0 (data, read the pointer).
```c
char *title = game_string(g_string_pool, "Ghost saved");
char *body  = game_string(g_string_pool, text);   /* e.g. "File: <name>. Folder: ... Send this file to a friend; they put it in ..." */
void *handle = 0;
if (g_gui_manager) game_open_dialog(&handle, g_gui_manager, &title, &body, 0, 0, 5, -2);
/* release handle (above), then: */
game_string_release(g_string_pool, title - 0x10);
game_string_release(g_string_pool, body - 0x10);
```
The hook already calls C with SAVE/RESTORE (aligned stack, all registers kept) and then jumps to 0x9b3a34, so nothing else changes.
Show an error text too when `export_result != EXPORT_OK`. The patch only knows `/data/ghosts`; the host folder text is our choice
(mod sessions: `mod-state/user/data/ghosts`, otherwise `user/data/ghosts`).
Code sanity bytes at 0x9c3890: `55 48 89 e5 41 57 41 56 41 55 41 54 53 48 83 ec 68`.

### Risks (unverified unless said)
- Thread: the R1 hook runs inside the ghost entry's GUI event handler (UI thread), like the TeamSelect handler that calls 0x9c3890. Low risk.
- Input under the popup: whether the Cross that closes it also reaches the ghost entry (toggling selection) or the menu Root VSC (Back/Option1)
  is not checked. Modal dialogs normally take focus. Test.
- Double open: 0x9c3890 does not check for an open popup (0xa07de0, the VSC path, does). R1 is not handled by the popup, so a second
  R1 should not reach the entry; if it does, guard with a flag cleared in `on_close`.
- Lifetimes: the info and both strings are refcounted copies; nothing points to our memory unless `on_close` is set (cave code is
  permanent). If the menu closes or the level changes while the popup is open, the popup is its own project owned by CGuiManager;
  not checked what a context switch does with it.
- If `Octane_YesNoDialog` is not resident (it is in `juicedomain_permanent.pak`, so it should be), 0x986820 streams it and locks controls until loaded.

## Other ways (not needed; less checked)
- VSC path `CGuiNodes.openDialogNoOptions_VSC` 0x110ae80 -> 0xa07de0(player obj, &out handle, title cstr, body cstr, forcePause, &project handle,
  &image handle, ?): same CDialogBoxInfo + 0x986820, but needs a player object and handles. `openDialogTwoOptions_VSC` 0x1109d60 -> 0xa07110.
  Option objects: `CUIDialogBoxOption` (0x78, factory 0x11d8a10; +0x20 _text, +0x28 _input) in info +0x10/+0x18 (see 0x12a4920).
- `CGuiBehaviorDialogBoxEventUpdateText` (0x28, meta 0x2abdd00): the dialog handler reacts to it (0x9aab1b) to change text while open.
- Hint HUD: `openHint_VSC` 0x110b560, `setHintText_VSC` 0x110b870 (project "Hint" = `_hintHudName`); meant for races, not checked in menus.
- Own-ghost entry text: build a new `CGuiEventOctaneGhostSelectionSetup` (0x10ee4d0(pool)) with +0x20 = message, +0x28 = time text,
  +0x18 = icon handle (behavior +0x38 has `_ghostDriverIcon`), send with 0x24de10(`[r15+0x10]`, event) from the button hook. Short text only.
- CGlobalPlatformStrings (`[0x2abce90]`, 0x8f0): localized common texts, e.g. +0x260 "NOTICE", +0x268 "WARNING", +0x10 Yes, +0x18 No.
