# Time Trial ghost menu: findings (USA CUSA13795 1.21)

ELF addresses of `CTRNF/out/eboot.elf` (patch XML = + 0x400000). "Unverified" = read from code, not tested in game.
Field names/offsets come from the reflection tables (see time-trial.md).

## Engine helpers (used everywhere below)
| ELF | What |
|---|---|
| 0x149d260 | release object (refcount dword at obj+8; `lock inc [obj+8]` = add ref) |
| 0x1574080 | `str = intern(pool=[0x2af2600], cstr)`; returns string with +1 ref |
| 0x1518e30 | release string: `(pool=[0x2af2600], str-0x10)`; string refcount dword at str-8 |
| 0x14a6f20 | grow igObjectList `(list, newCount, 8)`; list: +0xc count, +0x10 capacity, +0x20 item array |
| 0x14f7ed0 | clear igObjectList |
| 0x14b22a0 / 0x14a0e30 | ensure meta registered `(&meta, regFunc)` / create instance `(meta, pool, 0)` |
| 0x24de10 | send gui event `(target = behavior+0x10, event)` (to the item's VSC script) |
| 0xe63d30 + 0x9b4510 | float seconds -> time text (used for the menu's time) |
| 0xf9c610 | driver lookup `(list=[0x2ad4b70]+0x18, name)` -> CRacerDriverData by `_name` (+0x58), or 0 |

## Classes
- `CGuiListItemPopulatorOctaneGhost` (0x48, vtable 0x25469f0): +0x10 _categoryTemplateItem, +0x18 _continueButtonTemplateItem,
  +0x20 _noGhostDataTemplateItem, +0x28 _mirrorModeTemplateItem, +0x30 _playerGhostTitle, +0x38 _challengeGhostTitle, +0x40 _noGhostDataText.
  Titles are plain strings filled from `ui/Octane_MainMenu_GhostSelection_<lang>.lng` ("Player Ghost", "Challenge Ghost(s)", "No Ghost Data").
- `igGuiListItem` (0x80): +0x10 _templateItem, +0x18 bitfield (populate clears bit 3), +0x58 _label, ...
- `CGuiListItemOctaneGhostSelectCategory` (0x90, factory 0x11048b0(pool)): +0x80 _ghostCategoryName, +0x88 _maxGhostInCategory (shown as "%d/%d").
- `CGuiListItemOctaneGhostSelect` (0xa8, factory 0x11047c0(pool)): +0x80 _driverName (driver id), +0x88 _time (float s),
  +0x90 _ghostName, +0x98 _challengeGhost (CChallengeGhostHeaderData*, 0 for player ghost), +0xa0 _isPlayerGhost (byte).
- Generic `igGuiListItem` factory 0x26d810(pool) (continue button, mirror mode, "no ghost data" entries).
- `CGuiBehaviorOctaneGhostSelectItem` (0x60, vtable 0x2542f60): +0x10 owner, +0x18 _focusAnimation, +0x20 _defocusAnimation,
  +0x28 _pressedSelectedAnimation, +0x30 _pressedUnselectedAnimation, +0x38 _ghostDriverIcon, +0x40 _ghostDriverName (copy of item._ghostName, otherwise unused),
  +0x48 _ghostTime (float), +0x4c _ghostSelected, +0x4d _isPlayerGhost, +0x50 _challengeGhost, +0x58 _focusCategory.
- `CGuiEventOctaneGhostSelectionSetup` (0x30, factory 0x10ee4d0): +0x18 _ghostDriverIcon (driver `_icon` handle), +0x20 _ghostDriverName (string), +0x28 _ghostTime (string).
- `CGuiEventOctaneGhostSelected` (0x20, factory 0x10ee640): +0x18 _ghostSelected. FocusGain 0x10ee760, FocusLost 0x10ee880.
- `CChallengeGhostHeaderData` (0x30, meta 0x2abc210, reg 0x189039a; no own factory): +0x10 _kartName, +0x18 _driverName, +0x20 _time, +0x28 _ghostFile.
  `CGhostHeaderDataList` factory 0x10e0c70(pool).
- `CGhost` (0x50, factory 0x10e1050(pool)): +0xc _version (must be 3), +0x10 _kart, +0x18 _kartName, +0x20 _driverName, +0x28 _time,
  +0x30 _moveKeys, +0x38 _snapshotKeys, +0x40/+0x44 play indices, +0x48 _playerId.
  `CGhostMoveKey` (0x20): +0xc _position, +0x18 _timeInternal, +0x1a/1c/1e angles. `CGhostSnapshotKey` (0x10): +0xc bitfield (inputs), +0xe _timeInternal.
- `CRacerBaseData`/`CRacerDriverData`: +0x58 _name (id), +0x60 _displayName (shown text), +0x70 _icon.
- Ghost manager instance pointer: `[0x2abc3d0]` (+0x40 _playingGhosts, +0x48 _loadPlayerGhost, +0x50 _challengeGhostToLoad list).

## 1. Populate: 0x9e23d0 (populator vtable slot 23)
`(this, rsi = obj used for pool choice, rdx = output list)`; returns at once if the list is not empty.
Level name = `[[[0x2ad4e30]+0x18]+0x28]+0x10`. Item pool = picked from `[0x2af1fa8]` with `[rsi+8]>>22` (repeated sequence, e.g. 0x9e2f30-0x9e2fa3).
Order of appended entries:
1. Continue button (generic item, template +0x18).
2. Mirror mode (generic item, template +0x28).
3. `playerGhost = 0xf9cc00(level)` (save map lookup, returns the saved CGhost or 0). `list = new CGhostHeaderDataList`; `0xfceac0(level, &list)`.
4. Reset: `gm+0x48 = 0`, clear `gm+0x50` (0x9e276e). The selection is not remembered between visits.
5. If playerGhost and its _driverName: category (name = +0x30, max = 1, template +0x10), then one ghost item:
   _driverName/_ghostName = ghost._driverName (if the driver lookup 0xf9c610 fails or the driver is not usable (0xb37600, 0xcb67e0): the first driver's _name),
   _time = ghost._time, _isPlayerGhost = 1 (0x9e2a95).
6. If list.count > 0: category (name = +0x38, max = count) then per header (loop 0x9e2f30-0x9e306c):
   _ghostName = _driverName = hdr._driverName, _time = hdr._time, _isPlayerGhost = 0, _challengeGhost = hdr (no extra ref).
7. Else if there was no player ghost: "No Ghost Data" item (generic; +0x58 = +0x40 text, template +0x20).

`0xfceac0(level, &list)` (only called from populate, at 0x9e2756 and 0x9e2d22): reads the save record (`+0xc` unlockedChallengeGhostIndex);
if index >= 0 appends static headers `_ghosts[0..index]` of the track entry (0xf9b970), so -1 = none, 0 = Tropy, 3/4 = all four.
For each it opens `_ghostFile` and copies its `ghost_time` attribute into hdr._time (this is where the real time comes from).

## 2. Item events: 0x9b3830 (GhostSelectItem vtable slot 25, `(this, event, ?)`)
Dispatch by event meta: igGuiEventListAdd (0x2a21db0), igGuiEventFocusInputPressed (0x2a21d10), PlaceableGainFocus (0x2a21eb8), PlaceableLoseFocus (0x2a21ec8).
- ListAdd (0x9b3bd5, item = event+0x20): copies item fields to the behavior; `driver = 0xf9c610(item._driverName)` (no null check: a bad driver id crashes at 0x9b3c64);
  builds SelectionSetup: `_ghostDriverName = driver._displayName` (0x9b3de5), `_ghostTime = text(item._time)`, `_ghostDriverIcon = driver._icon`; sends it at 0x9b3e7a-0x9b3e88.
  The ListButton VSC (`vsc/common/UI/Octane_GhostListEntry/..._ListButton.igz`) only does `set_DisplayText` with the two strings and `setSpriteMaterial` with the icon,
  so any raw string works; no .lng or VSC change is needed for names/times.
- FocusInputPressed (0x9b3a53): only `signal (event+0x18) == 8` (kSignalButtonSelect) is handled; every other signal goes to the exit 0x9b3a34.
  Select: `_ghostSelected ^= 1` (0x9b3a5a), sends GhostSelected event, then
  - player ghost: `gm+0x48 = _ghostSelected` (0x9b3b00);
  - challenge/header entry (0x9b40e6): selected -> append hdr (with ref) to `gm+0x50`; unselected -> `0xfcf190(gm, hdr)` removes it.
  Then plays the pressed-selected/unselected animation.
- Gain/LoseFocus: send FocusGain/FocusLost events.
Category behavior 0x9b46b0 (shows "%d/%d"), NoGhost 0x9b5d30, Continue button 0x127ec50 (signal 8 -> CGuiEventOctaneGhostContinueButtonPressed, Root VSC starts the race).

## 3. Race start: 0xf9b250 (Time Trial only: `[[0x2acde48]+0xd4c] == 2`)
- `gm+0x48` set -> 0xf9b670: saved CGhost of the level (version 3) -> `0xf9bee0(charDB, ghost._driverName, ghost._kartName, ghost, 1)`; a copy goes to `_playingGhosts`.
- each non-null hdr in `gm+0x50` -> 0xf9b7f0: `ghost = 0xf9ba70(gm, lowercase(hdr._ghostFile))` (loads .igb, needs `ghost_version` == 3),
  `0xf9bee0(charDB, hdr._driverName, hdr._kartName, ghost, 0)` ("loadGhostData" spawn), then if hdr is in the track's `_ghosts`, sets +0x34/+0x38 (fastest raced).
- If no hdr was in the list, +0x38 = track unlock time; if any hdr (also a foreign one) is in the list, +0x38 stays FLT_MAX and +0x34 = -1.
  So racing only foreign ghosts may unlock N. Tropy with any time (unverified; see race end 0xfcc430 in time-trial.md). A patch should skip foreign headers in the loop 0xf9b2d3 or restore +0x38.

## 4. Multiple ghosts
Yes: the player ghost and any number of challenge headers can be selected together (bool + list); all are spawned at race start.

## 5. Buttons
`igGuiInput::Signal` (enum table 0x242cd00): 0 ButtonUp, 1 ButtonDown, 2 ButtonLeft, 3 ButtonRight, 4-7 Dpad, 8 Select, 9 Back, 10 Option1, 11 Option2, 12 Menu, 13 Pause,
14 TriggerRight, 15 TriggerLeft, 16 BumperRight, 17 BumperLeft, 18-22 Touched1-5, 23 Gestured1. Event field: igGuiEventInput +0x18 _signal, +0x1c _control.
- Root VSC (`update.pak vsc/UI/Octane_MainMenu_GhostSelection/..._Root.igz`) listens to ProjectInputPressed with signal 9 (Back) and 10 (Option1);
  it references `enterCustomizationMenu_VSC`, and the legend shows Select, Back, Option1. So Option1 is likely "customize" here (unverified).
- Physical mapping not found in code. Likely (unverified): Select = Cross/A, Back = Circle/B, Option1 = Triangle/Y, Option2 = Square/X
  (button-prompt materials per controller: Select/Interact/Option1/Option2 in `loosedata/guisystemdata.igz`). If Option1 is Triangle, Triangle on a ghost entry
  also triggers the Root's Option1 action unless that is blocked.
- Hook for "button on own ghost entry": replace 0x9b3a53 `41 83 7d 18 08 75 da` (cmp signal,8; jne exit; 0x9b3a53 is a jump target, 0x9b3a58 is not)
  with `jmp cave`: `if [r13+0x18] == 8 -> jmp 0x9b3a5a`; `if [r13+0x18] == WANTED && byte [r15+0x4d] -> export`; `jmp 0x9b3a34`.
  r15 = behavior, r13 = event, frame intact; 0x9b3a34 is the normal exit (stack check + ret).
  First probe the value: log `[r13+0x18]` there and press Triangle.

## 6. Recommended way to add entries (unverified)
- Wrap 0xfceac0: redirect both calls (0x9e2756, 0x9e2d22: `e8 rel32`) to a cave that calls 0xfceac0 and then appends our own
  CChallengeGhostHeaderData objects (+ref) to `*rsi` list. Populate then builds the items, the category count, selection, and race start loads them (`_ghostFile`).
  Create headers with 0x14b22a0(0x2abc210, 0x189039a) + 0x14a0e30([0x2abc210], pool, 0); set strings via 0x1574080 (add ref). Pool: copy the pick
  sequence (e.g. 0xfcec20-0xfcecd0 or 0x9e2f30-0x9e2fa3); pool 0 path not checked.
- `_driverName` must be a real driver id (crash otherwise) and gives the icon; `_kartName` must be a real kart id; `_time` = seconds; `_ghostFile` = path that 0xf9ba70 can open.
- Other player's name: hook 0x9b3e7a-0x9b3e8d (19 bytes, only 0x9b3e7a is a jump target): if `[rbp-0xb0]` behavior's +0x50 is one of our headers,
  replace event(r12)+0x20 with our name string (release old string, store new +1 ref), then do the original `mov rax,[rbp-0xb0]; mov rsi,r12; mov rdi,[rax+0x10]; call 0x24de10`; `jmp 0x9b3e8d`.
  Keep a cave table hdr -> name (header has no spare field). They appear under "Challenge Ghost(s)"; a separate category would need a populate hook (e.g. at 0x9e30e1).

## 7. Export / file formats (open)
- No ghost writer exists in the game (only `ghost_time`/`ghost_version` readers: 0xfceac0, 0xf9ba70). Ghost .igb = object directory with attributes
  (`0x15857c0([dir+0x10], name, &out, 4)` reads one) and a CGhost object (0xf9be2e looks for meta CGhost).
- The save code writes an object directory to a file: `0x156b960(dir, path, 1, &opts)` (0xc2fcf3, path "ram:/tmpsavefile.igb"); 0x156b7f0 loads.
  Exporting a stock-compatible .igb with this needs an attribute writer (not found). Simpler: custom raw format (CGhost fields + both key lists) and
  build CGhost (0x10e1050) on import, then spawn with 0xf9bee0 (would need a race-start hook instead of `_ghostFile`).
- Player's ghost for export: `0xf9cc00(level)` (level from the populate path above or `0x102e040([0x2ae3c18])+0x10`, as race start does).
- Writable host paths for the PC port: not checked.
