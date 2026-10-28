# Ghost menu button bar: an R1 "EXPORT GHOST" prompt (USA CUSA13795 1.21)

ELF addresses of `CTRNF/out/eboot.elf` (patch XML = + 0x400000). Read from code and assets only; nothing was run.
"Verified" = read in code/asset. "Unverified" = not tested in game.

## Answer (recommended)
Add our entry to the menu's own legend with the game's "add button to legend" helper when your own ghost entry gains
focus, and remove it when the entry loses focus. This is the same pattern the pause menu uses (below). Two new hooks on the
ghost entry's focus events, no asset change. The bar becomes `(X) SELECT  (R1) EXPORT GHOST  (□) CONTINUE  (△) OPTIONS  (○) BACK`
(the order comes from the game data). On Xbox prompts (`bbport.ini button_prompts=xbox`) the R1 icon is drawn as RB.

## 1. How the bar is built (verified)
- Asset: the ghost project `ui/Octane_MainMenu_GhostSelection.igz` instances the shared asset `ui/GuiSharedAssets/ButtonLegendHorizontal.igz`
  (`Comp__ButtonLegendHorizontal`). Its root has `CGuiBehaviorButtonLegend` (0x58, meta 0x2abdbf0, event handler 0x9a1220).
  Fields: +0x10 _buttonLegendScaleAnimation, +0x18 _buttonLegendListPlaceable, +0x20 _buttonLegendPlaceable, +0x28 _buttonLegendTextPlaceable,
  +0x30 _forceListDisplay (0 here), +0x31 _isVertical (0), +0x32 _moveToDefaultPosition (1), +0x38 _workingButtonLegendData (CGuiButtonLegendTable),
  +0x40 _buttonLegendTable, +0x48 _currentButtonLegend (igString), +0x50 _buttonLegendHasChanged, +0x51 _buttonLegendVisible.
- `CGuiButtonLegendTable` = hash table (`_keys`, `_values`): key = `EButtonLegendButton`, value = igString text.
  `EButtonLegendButton` (names 0x2624a50): 0 Invalid, 1 Select, 2 Back, 3 Option1, 4 Option2, 5 BumperLeft, **6 BumperRight (R1)**,
  7 TriggerLeft, 8 TriggerRight, 9 LeftStick, 10 RightStick, 11 Dpad, 12 Menu.
- The bar is one text, not a list: rebuild 0x9a1c30 walks `_guiSystemData._buttonLegendOrder` (COctaneGuiSystemData +0x58,
  update2.pak `loosedata/guisystemdata.igz` data +0x2418) = **1, 9, 10, 11, 5, 6, 8, 7, 3, 4, 12, 2**; for each key in the working table
  0x9a2020 appends `"%*s%s %s"` (5 spaces = +0x78 _numSpacesBetweenOptions, button character, text) to +0x48; 0x9a1860 puts it in
  `_buttonLegendTextPlaceable._displayText` (+0x30). So BumperRight lands after Select, before Option1.
  Text box: igGuiText font Geek_Speak2, _capsMode (+0x28) 1, _fontScale 0.23, _forceFitInBox 1, no word wrap: a longer bar shrinks to fit.
- Who fills it in this menu: VSC only. Root VSC (`update.pak vsc/UI/Octane_MainMenu_GhostSelection/..._Root.igz`) calls
  `CGuiNodes::addButtonToLegend_VSC` 3 times (enum consts 1, 2, 3) and `Octane_MainMenu_Option_Button_Prompt` VSC adds one more
  (getGlobalString). No behavior in this project has `CGuiBehavior._defaultButtonLegendData` (+0x18) set (all 0 in the asset), and neither
  VSC calls reset, so nothing rebuilds the table on focus. Buttons on this pad: Option1 = Square ("CONTINUE"), Option2 = Triangle ("OPTIONS").
- Events the legend behavior handles (0x9a1220): igGuiEventProjectLoad (init), ProjectGainFocus (show), ProjectLoseFocus (hide),
  `CGuiEventButtonLegendTable` (meta 0x2abfb68, +0x18 _table: replaces the working table), `CGuiEventSetButtonLegendVisibility` (0x2abfb78),
  **`CGuiEventAddButton`** (0x2abfb88, size 0x28: +0x18 _button, +0x20 _text) -> 0x9a1dd0 inserts/replaces the key and rebuilds,
  **`CGuiEventRemoveButton`** (0x2abfba0, 0x20: +0x18 _button) -> removes the key (0x149e320) and rebuilds, `CGuiEventRefreshButtonLegend` (0x2abfbb8).
- Per-focus example in the game: `CGuiBehaviorPauseMenuOption` handler 0x9c81b0: PlaceableGainFocus -> sends a CGuiEventButtonLegendTable with
  its `_focusButtonLegendData` (+0xc0) (0x9c86d5); PlaceableLoseFocus -> sends `CGuiEventResetButtonLegend` (0x9c884e); CGuiBehavior (0x97d780)
  answers Reset by resending its `_defaultButtonLegendData` (0x97f460). Target in both: the item's project, `vtable+0xb0`.

## 2. R1 icon and Xbox (verified)
- Button characters: `_globalButtonCharacters` (+0x40, CXButtonStringTable at guisystemdata +0x1e08): key 0xd = U+E006 (R1). Also 4 E000 Cross,
  5 E001 Circle, 6 E002 Triangle, 8 E003 Square, 0xb E004 L1, 0xc E007 L2, 7 E008 R2.
- 0x99af00(legendButton, controllerType): for 5..8 it returns table 0x1d9d190/0x1d9d210 values: 5 -> 0xb (L1), **6 -> 0xd (R1)**, 7 -> 0xc (L2), 8 -> 7 (R2),
  the same for every controller type. So eBLB_BumperRight shows U+E006.
- The port's Xbox prompts restyle the font image cells, not the text: `scripts/button_prompts.py` CODES 0xE006 -> 'R1', and
  `tools/make_button_prompts.py` draws 'RB' in that cell (GeekSpeak, GeekSpeak_Outline, Zoinks_Outline). So R1 shows as RB with `button_prompts=xbox`
  with no work on our side. The owner's `bbport.ini` has `button_prompts=playstation` now.
- Markup: not needed in the bar (the game adds the character). In other GeekSpeak text, the raw UTF-8 character `"\xee\x80\x86"` should draw the R1
  icon (unverified; the bar itself is just such a string). There is also `CGuiNodes::replaceTokenWithButton_VSC` 0x110bec0 (-> 0xa091e0) for tokens.

## 3. Calls and hooks for the patch
### Add: 0xa09d30 (the body of addButtonToLegend_VSC 0x110bbc0) (verified in code)
`void legend_add(void *project, int button, char **text, int always)`
- `text`: pointer to an igString variable (0x1574080). The helper puts it in the shared event `CGuiManager._addButtonEvent` ([0x2ac0dc0]+0xe8),
  with its own reference; release yours after the call (0x1518e30(pool, str-0x10)). Raw text works (the VSC passes a plain string).
- `always` (cl): pass 1. With 0 it skips when `project+0x34` bit 3 is set (a project flag; unverified which).
- Then `project->vtable[0xb0](project, event)` = igGuiProject 0x253740 -> 0x24e510(project._rootPlaceable): sends to every placeable in the
  project, synchronously. Only this project's legend sees it, so other menus are not changed.
- Code bytes at 0xa09d30: `55 48 89 e5 41 57 41 56 41 54 53 49 89 fc 49 89 d6`.

### Remove: no game helper; do what removeButtonFromLegend_VSC 0x110bcb0 does (verified in code)
```c
void *event = AT(g_gui_manager, 0xf0, void *);     /* CGuiManager._removeButtonEvent (CGuiEventRemoveButton) */
if (event) {
    AT(event, 0x18, int32_t) = 6;                   /* _button: eBLB_BumperRight */
    (*(void (**)(void *, void *))(AT(project, 0, char *) + 0xb0))(project, event);
}
```
Removing a key that is not there is harmless (hash remove + rebuild). If the legend has no table yet (+0x38 = 0) it does nothing.

### Getting the project
Like the pause menu (0x9c8700): `placeable = handler's 3rd argument` (saved at `[rbp-0xa8]` in the ghost entry handler 0x9b3830, written once at 0x9b384b);
`project = [placeable+0x20]` (igGuiPlaceable._project). The pause menu also normalizes with `project = [[project+0x10]+0x20]` (vtable+0xb8 = 0x2731d0 returns
`_rootPlaceable` +0x10); doing the same is safe. Fallback: `[behavior+0x10]` (_ghostButtonPlaceable) +0x20. Unverified that runtime list item placeables
have `_project` set (they must, for focus/animations; the handler plays animations on `[rbp-0xa8]`).

### Hook sites (in the ghost entry handler 0x9b3830; both only reached for this menu's entries)
| ELF | Original bytes | Instruction | Live |
|---|---|---|---|
| 0x9b3baa | `e8 b1 ab 73 00` | `call 0x10ee760` (new CGuiEventOctaneGhostSelectionFocusGain) | PlaceableGainFocus; r12 = entry behavior, rdi = argument (keep), [rbp-0xa8] = placeable |
| 0x9b3998 | `e8 e3 ae 73 00` | `call 0x10ee880` (new ...FocusLost) | PlaceableLoseFocus; r12 = entry behavior, rdi = argument (keep), [rbp-0xa8] = placeable |
Neither address is a jump target (jumps go to the `mov rdi, rbx` 3 bytes before each). Signatures (8 bytes each side) are unique.
r12 = behavior on every path: gain sets it at 0x9b3b49 (paths 0x9b3f00, 0x9b432e, 0x9b43e6, 0x9b43f9 keep it), lose at 0x9b38f1
(paths 0x9b3fa6, 0x9b4236, 0x9b4397, 0x9b4428, 0x9b443b keep it).

```asm
# build.py: HOOKS += (0x9b3baa, 'e8b1ab7300', 'e8', 'hook_focus_gain', 0), (0x9b3998, 'e8e3ae7300', 'e8', 'hook_focus_lost', 0)
# GAME += 'game_legend_add': 0xa09d30, 'game_focus_gain_event': 0x10ee760, 'game_focus_lost_event': 0x10ee880
hook_focus_gain:
    SAVE
    mov rdi, r12                 # entry behavior (+0x4d: your own ghost)
    mov rsi, [rbp - 0xa8]        # entry placeable
    mov edx, 1
    call gs_entry_focus
    RESTORE
    jmp game_focus_gain_event    # the replaced call; returns to 0x9b3baf
hook_focus_lost:                 # same with edx = 0 and jmp game_focus_lost_event
```
```c
#define LEGEND_EXPORT 6   /* eBLB_BumperRight: R1 (RB with Xbox prompts) */
void gs_entry_focus(void *behavior, void *placeable, int gained)
{
    if (!AT(behavior, 0x4d, uint8_t) || !placeable || !g_gui_manager) return;   /* only your own ghost */
    void *project = AT(placeable, 0x20, void *);
    if (!project) return;
    if (gained) {
        char *text = game_string(g_string_pool, "EXPORT GHOST");
        game_legend_add(project, LEGEND_EXPORT, &text, 1);
        game_string_release(g_string_pool, text - 0x10);
    } else {
        /* remove, as above */
    }
}
```
Text: the bar uses caps mode, so "Export ghost" also shows in capitals; "EXPORT GHOST" is safe. If 5 entries make the bar too small, use "EXPORT".

### Other ways (less good)
- Second best, always on while your ghost exists: in `gs_fill_ghost_list` call the add once when `game_saved_ghost(level)` is set;
  project = `[[widget+0xc0]+0x20]` (igGuiList._rootPlaceable._project). It runs inside the list update (0x25f5f0 -> populate), before the
  Root VSC may add its own buttons (order does not matter: separate keys). Unverified that broadcasting there is harmless.
- Asset change (no code): add a key 6 entry to the legend data; needs a repacked .igz and the Root VSC; not worth it.

## 4. Risks
- Thread: focus events and the legend run on the GUI update thread, like the VSC calls and our existing hooks. The broadcast is synchronous
  and only sets the legend's text; the game sends legend events from inside focus handlers the same way (pause menu). Low risk.
- Shared event objects (`CGuiManager` +0xe8/+0xf0) are reused by every caller; fill and send at once, no lifetime issue. The text string is
  refcounted (the table keeps its own copy).
- Only this menu: events go to the ghost project's own tree (its own CGuiBehaviorButtonLegend instance). The hooks are in the ghost entry
  handler, which only ghost entries use. Other menus are not touched.
- Stale entry: if the menu closes while your ghost is focused and no LoseFocus comes, the key stays in that project's working table.
  Harmless if each open makes a new project instance (likely: projects have `_sourceProject` +0x98; unverified). If the instance is reused,
  R1 could show on a track with no own ghost. Safe fix: keep the project pointer in `gs` (compare only, never dereference) and in
  `gs_fill_ghost_list` send the remove if the new list's project (`[[widget+0xc0]+0x20]`) is the same pointer.
- Export popup: while it is open the ghost project loses focus and the legend hides (ProjectLoseFocus). Not checked whether the entry gets
  PlaceableLoseFocus/GainFocus around the popup. If it gets LoseFocus but no GainFocus, R1 disappears until focus moves away and back;
  then re-add in the popup's `on_close` callback (0x9c3890 supports one). Test this.
- Focus does not change on Select (toggle) or on R1 itself, so the prompt stays while you export.
- Not tested in game at all: the bar layout with 5 entries, the hook paths, the project pointer.
