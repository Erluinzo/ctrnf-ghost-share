# Ghost code map (USA CUSA13795 1.21)

ELF addresses of `CTRNF/out/eboot.elf` (patch XML = ELF + 0x400000). Read from code only; nothing was run.
"Inferred" = read from how the code uses it, not proven. See also `time-trial.md`.

## Engine helpers (Alchemy)
| ELF | What |
|---|---|
| 0x14a0e30 | `createInstance(meta, pool, 0)`; pool 0 = default pool (null branch at 0x14a10b3) |
| 0x14b22a0 | `getMeta(&metaSlot, registerFn)` (lazy class registration) |
| 0x15083e0 | class registration; r8 = name, r9d = object size, r11 = field callback |
| 0x1507980 | field registration: rsi = names table, rcx = u16 offsets table |
| 0x149d260 | `release(obj)` (refcount is the dword at obj+8; add a ref = `lock inc [obj+8]`) |
| 0x14a1640 | `copy(dst, src)` field by field; deep for the key lists (inferred: the game clears the source's lists after copying) |
| 0x14a6f20 | list `setCount(list, n, 8)` (grows capacity, sets count) |
| 0x14a4ed0 | list `reserve(list, capacity, 8)` |
| 0x14f7ed0 | list `clear(list)` (releases elements) |
| 0x1574080 | `igString make(pool=[0x2af2600], const char*)`, returns a new reference |
| 0x1518e30 | `igString release([0x2af2600], str - 0x10)` (string header at -0x10, refcount at -8) |
| 0x14bea20 | `makeHandle(&h, obj)`; handle: flags in [h] (0x10000000/0x20000000 = slow path 0x149fca0), object at [h+0x28] |
| 0x1be9c78 | strcmp |
| 0x243a30 | format a string into a local buffer (used to copy and lower-case a path) |

igObjectList (size 0x28): +0x0c count, +0x10 capacity, +0x20 data (8-byte pointers). The game appends inline:
add a ref, `if count >= cap: setCount(list, count+1, 8) else count++`, `data[old count] = obj`.

## Classes (size from r9d at registration; fields from the reflection tables)
| Class | Size | Meta slot | Create (rdi = pool, 0 ok) | Vtable |
|---|---|---|---|---|
| CGhost | 0x50 | 0x2abc2f0 | 0x10e1050 | 0x261d238 (dtor body 0x10e0f30) |
| CGhostMoveKey | 0x20 | 0x2abc240 | 0x10e0cb0 | |
| CGhostMoveKeyList | 0x28 | 0x2abc270 | (made by CGhost create) | |
| CGhostSnapshotKey | 0x10 | 0x2abc278 | 0x10e0d80 | |
| CGhostSnapshotKeyList | 0x28 | 0x2abc2d0 | (made by CGhost create) | |
| CGhostSavedInfo | 0x18 | 0x2abc2d8 | 0x10e0e50 | |
| CGhostList | 0x28 | 0x2abc348 | | |
| CGhostManager | 0x60 | 0x2abc350 | | 0x259b158; `_Instance` at 0x2abc3d0 |
| CGhostData (table root) | 0x18 | 0x2abc1d8 | | getter 0xf9ba00 |
| CAIParticipantData | 0x68 | 0x2ad4ab8 | 0x1199f90 | |

A new CGhost already has empty `_moveKeys`/`_snapshotKeys` lists: 0xfcb9a0 uses them right after 0x10e1050 with no null check.

CGhost (names 0x261d370, offsets 0x1da20c0)
| Off | Field | Type / use |
|---|---|---|
| +0x0c | _version | int; files and saves need 3 (`ghost_version` header and `[ghost+0xc]==3` checks) |
| +0x10 | _kart | igHandle to the kart entity at run time (set by 0xfce080 or the recorder; not file data) |
| +0x18 | _kartName | igString (CRacerKartData name, +0x58 of the kart data) |
| +0x20 | _driverName | igString (CRacerDriverData name) |
| +0x28 | _time | float, race time in seconds |
| +0x30 | _moveKeys | CGhostMoveKeyList* |
| +0x38 | _snapshotKeys | CGhostSnapshotKeyList* |
| +0x40 | _playMoveKeyIndex | int (0xfce410 resets +0x40 and +0x44 with one qword store) |
| +0x44 | _playSnapshotKeyIndex | int, -1 = past the end |
| +0x48 | _playerId | int = racer slot; set by 0xf9bee0 |

CGhostMoveKey (names 0x261cce0, offsets 0x1da2090): +0x0c `_position` 3 floats; +0x18 `_timeInternal` u16 = s*100;
+0x1a/+0x1c/+0x1e `_anglesInternal0/1/2` s16 = radians*10430.06 (32768/pi). The recorder writes one key per update (0xfcbec0).

CGhostSnapshotKey (names 0x261cfd0, offsets 0x1da20a0): +0x0c `_bitfield` u16, +0x0e `_timeInternal` u16 = s*100.
Bits (from 0xfcc140 / 0xe54c20): 0-7 `_turnAnalog` (s8/127), 8 `_accelerate`, 9 `_reverse`, 10 `_brake`,
11 `_firstJump`, 12 `_secondJump`, 13 `_startDrift`, 14 `_raceStart` (from manager +0x1c). A key is only added when a bit changes.
Limits: recording stops at 360 s (0x1cab1c8); u16 time allows up to 655.35 s; lists get capacity 0x2a30 (10800).
0xfcb410 / 0xfcb6e0 thin out the lists once they hold more than 0x835 keys (and cut keys before a given time).

CGhostManager (names 0x261d620, offsets 0x1da20e0): +0x0c _isRecording, +0x10 _recordTime, +0x14 _isPlaying, +0x18 _playTime,
+0x1c _isRaceStartFrame, +0x20 _recordRaceStartTime, +0x28 _recordingGhost, +0x30 _unlockedNewGhost (byte),
+0x34/+0x38 highest playing challenge ghost index/time, +0x40 _playingGhosts (CGhostList*), +0x48 _loadPlayerGhost (byte),
+0x50 _challengeGhostToLoad (list of **CChallengeGhostData**, not CGhost), +0x58 _unlockedNTropy.
Vtable slots: +0x40 0xf9b190 set instance, +0xb8 0xf9b1e0 drop lists, +0xc8 **0xf9b250 level start**, +0xd0 **0xf9b450 level exit**.

CGhostSavedInfo (names 0x261d420): +0x0c unlockedChallengeGhostIndex, +0x10 _ghost (CGhost*).
CAIParticipantData: +0x0c _hostPlayerId, +0x10 _localPlayerId, +0x18 _driverName, +0x20 _driverInstance, +0x28 _characterData,
+0x30 _outfitData, +0x38 _driverData, +0x40 _vehicleId, +0x48 _kartName, +0x50 _kartData, +0x58 _kartCustomizationPreset, +0x60 _racerInfo.
CKartControllerComponent (meta 0x2ac4580, size 0x290): +0x260 _isGhost, +0x268 _ghostSnapshot.

## Singletons used
| Global (pointer) | Class | Used for |
|---|---|---|
| 0x2abc3d0 | CGhostManager | |
| 0x2ad4b70 | CRacerManager | +0x18 _allDrivers, +0x20 _allKarts, +0x38 _aiParticipantsInfo, +0x40 _ghostParticipantsInfo |
| 0x2acde48 | COctaneGameManager | +0xd4c _raceMode (2 = Time Trial), +0xdb0 _globalSaveData |
| 0x2ae3c18 | CZoneInfoSystem | 0x102e040 -> current zone; zone+0x10 = level name |
| 0x2ad1160 | CPlayerManager | +0x10 player list (count used in the racer limit) |
| 0x2ac57c0 | CKartManager | 0xf4dbc0 sets the kart for a slot; 0xe70860 spawns the kart entity |
| 0x2ac4ec8 | CKartCustomizationManager | array, 0x88 bytes per slot |
| 0x2ab4100 | frame time | +0x24 dt, +0x28 paused |
COctaneGlobalSaveData +0x18 `_zoneInfoGhost` = CZoneInfoGhostHashTable: key = lower-case level name with `\` -> `/`, FNV-1a; value = CGhostSavedInfo. Lookup 0xf9ce00.

## 1. Ghost file -> playing ghost (challenge ghosts)
| ELF | What |
|---|---|
| 0x9b3830 | ghost select menu item pressed: player ghost -> `_loadPlayerGhost = selected`; challenge ghost -> append CChallengeGhostData to `_challengeGhostToLoad` (0x9b4104); 0xfcf190 removes it |
| 0xf9b250 | level start: returns unless `_raceMode == 2`; `_loadPlayerGhost` -> 0xf9b670; `+0x34/+0x38 = -1 / FLT_MAX`; 0xf9b7f0 for each `_challengeGhostToLoad` entry; no ghost -> `+0x38 = unlock time`; then registers 0xf9b660 (sets _isRaceStartFrame and _recordRaceStartTime at the start signal) |
| 0xf9b7f0 | (mgr, CChallengeGhostData*): copies and lower-cases `_ghostFile` (0xf9b84c) -> 0xf9ba70 -> 0xf9bee0(racerMgr, data._driverName, data._kartName, ghost, 0) -> updates +0x34/+0x38 if faster |
| 0xf9ba70 | (mgr, path) -> CGhost*: **synchronous**. igFilePath (0x15806f0, 0x14c6820, 0x14c7fc0); header: igThumbnailSet 0x15820e0 + 0x156b7f0, `ghost_version` via 0x15857c0 must be 3; full load: igObjectDirectory 0x1582020 + 0x156b960(dir, path, 1, 0); takes the first object in dir+0x28 whose meta is CGhost; **appends it to `_playingGhosts`**; then igObjectStreamManager (0x22d0e0) 0x14fb600(mgr, dir, 1, 0) and releases the directory |

Names on track for challenge ghosts come from the GhostData table (`_driverName`/`_kartName`), not from the file.

## 2. Player's own ghost
0xf9b670 (from 0xf9b250 when `_loadPlayerGhost`): level name -> 0xf9cc00 (save hashtable -> CGhostSavedInfo._ghost) -> needs `_version == 3`
-> 0xf9bee0(racerMgr, ghost._driverName, ghost._kartName, savedGhost, 1) (sets savedGhost._playerId) -> new CGhost 0x10e1050 ->
0x14a1640 copy from the saved ghost -> append to `_playingGhosts`. The save copy is never played directly.

## 3. Playing ghost -> racer on track
| ELF | What |
|---|---|
| 0xf9bee0 | **spawn a ghost participant** (rdi = CRacerManager*, rsi = driver name, rdx = kart name, rcx = CGhost*, r8b = isPlayerGhost). Returns early if CGhost is null, if `0x94efa0()+0x1ac` is set (inferred: online), or if players + AI + ghost participants > 7. New CAIParticipantData (0x1199f90); slot = that count + 1. isPlayerGhost=1: names are looked up (drivers 0xf9c610, karts 0xf9c900; strcmp with data+0x58) and must pass 0xb37600 (unlock conditions) and 0xcb67e0, otherwise the first driver/kart is used (inferred: locked/not owned). isPlayerGhost=0: names used as given. Fills participant (0xc20700 character data, 0xf9c6f0 driver, 0xf9c9d0 kart, preset = none), clears the slot's kart customization, logs `Net: loadGhostData`, 0xf4dbc0 kart for the slot, appends to `_ghostParticipantsInfo`, sets `ghost._playerId = slot` |
| 0xe9d3a0 | racer spawn; in raceMode 2 calls 0x1000620 at 0xe9d5ba |
| 0x1000620 | for each ghost participant: driver instance (0xc20a30), kart entity (0xe70860), entity name `Ghost_<kartName>_<vehicleId>`, then 0xfce080 |
| 0xfce080 | (mgr, kartEntity, playerId): finds the CGhost with `_playerId == id` and >= 1 move key, sets `_kart` handle, places the kart at key 0, 0xf4cf20 on its CKartControllerComponent |
| 0xf4cf20 | ghost mode: `_isGhost = 1`, clears entity flag 0x10 at +0x78, 0xbad520(entity, 4), adds per-frame callback 0xe54c20 |
| 0xe54c20 | ghost kart input: snapshot key from 0xfce250 -> controller input bits / steering (visuals/animation) |
| 0xea55c0 | race start (inferred): 0xfce3b0 (0xfce410 per ghost: indices 0, `_playTime = 0`, kart to key 0, `_isPlaying = 1`), then 0xfcb9a0 starts recording the player |
| 0xea2d90 -> 0xfce570 | per frame (inferred): `_playTime += dt`; for each ghost with a live `_kart`: 0xfce6a0 (move keys: find pair by time, lerp position, lerp angles with wrap, set transform 0x3dc8e0/0xbabbf0) and 0xfcea00 (advance snapshot index) |
| 0xfce250 | (mgr, kartEntity) -> current CGhostSnapshotKey or null |
| 0x9f3ce0 -> 0xfce000 | per frame recording (0xfcbec0 move key, 0xfcc140 snapshot key) |

Look: driver character + kart body only. No outfit, no kart customization preset (paint/decals) is passed.
Name on screen: no in-race name tag for ghosts was found; the only per-ghost HUD item is the minimap icon:
0x9d2ec0 (CGuiBehaviorRacingMinimap) sends `_ghostSetupEvent` (CGuiEventRacingMinimapGhostSetup, `_ghost` = handle to the CGhost)
for each `_playingGhosts` entry (loop 0x9d36df); icon slot index continues after the racers, no bound check;
0x9d17e0 (CGuiBehaviorMinimapPlayer) stores it at +0x30 and plays `_ghostAnimation`. In the menu: CGuiListItemOctaneGhostSelect
(+0x80 _driverName, +0x88 _time, +0x90 _ghostName); 0xfceac0 fills challenge ghost times from the files' `ghost_time`.
Unverified: whether the minimap icon picture comes from the participant's driver.

## 4. Race end
0xf351b0 -> 0xfcefe0 (only while recording, and only for the kart in `_recordingGhost._kart`) -> 0xfcc430:
1. Stop recording, final snapshot key, `_recordingGhost._time = recordTime - recordRaceStartTime`.
2. `newBest` = no saved ghost, saved `_version != 3`, or saved `_time >= time`. `beat` = `+0x38 > time`.
3. Skip all when `!(newBest || beat)` or 0xfcd2e0(gameMgr) is true (inferred: active cheats check, reads `_activeCheats` +0xda8).
4. CGhostSavedInfo from the save hashtable (new one 0x10e0e50 if missing, inserted 0xfcc8f0).
5. newBest: `_loadPlayerGhost = 1`, thin keys, copy the recording into `CGhostSavedInfo._ghost` (new CGhost if none).
6. beat: stat `beat_{ntropy,oxide,velo,dev}_ghost` by `+0x34` (jump table 0x1cc1ae8, 0xaa2310 on 0x2aa48c0);
   `if record.index == +0x34: record.index++, _unlockedNewGhost = 1` (0xfcc890).
7. Counts over all tracks (0xfcda00/0xfcda70) -> trophies via 0xfcdce0 (0x19 / 0x1a), N. Tropy unlock (`_unlockedNTropy`,
   global save +0x2b/+0x2c, save request 0x9dba50 -> 0xc1d090), gameMgr +0xd0c/+0xd0d/+0xd00 rewards (not counting `sony_stadium`).
8. Clear the recording's key lists.
Results screen: 0xeab03e reads `_unlockedNewGhost` -> 0xfcee30 -> CGuiEventRacerUpdateTotalTime._newChallengeGhost.
Level exit 0xf9b450: stop flags, clear recording lists, for each playing ghost clear both lists + vtable+0xa8, clear `_playingGhosts`.

**For an imported ghost:** all of 2-7 reads only `+0x34/+0x38` (set only by 0xf9b7f0 for challenge ghosts) and the player's
own recording. A ghost added straight to `_playingGhosts` changes nothing there. The player's own record/ghost is still saved
as normal (the race itself is real). Leaderboard writes (igNetTaskWriteLeaderboard, meta 0x2a31658) are not in the ghost code; not traced.

## 5. Recommended hook
**0xf9b329 in 0xf9b250** (`8a 05 39 75 af 01  mov al,[0x2a92868]`, 6 bytes, a join point; 0xf9b32f is not a jump target).
Here: raceMode is 2, player and challenge ghosts already exist, before the start callback; r15 = CGhostManager*,
rbx = stack-guard pointer (keep), rsp is 16-aligned before the `call` (so the cave must re-align by 8).
Patch: `call cave; nop`; cave saves registers, adds the ghost, redoes `mov al, byte [0x2a92868]`, returns.
Steps in the cave (all game functions, no file parser):
1. `g = 0x10e1050(0)`; `g+0xc = 3`; `g+0x18 = 0x1574080([0x2af2600], kartName)`; `g+0x20 = 0x1574080(..., driverName)`; `g+0x28 = time`; `g+0x48 = -1`.
2. `0x14a4ed0(g->_moveKeys, n, 8)`; per key `k = 0x10e0cb0(0)`, fill +0xc..+0x1e, append (ref + count++), `0x149d260(k)`.
   Same for snapshot keys with 0x10e0d80.
3. Append g to `[r15+0x40]` (add ref).
4. `0xf9bee0([0x2ad4b70], driverName, kartName, g, 0)`; if `g+0x48` is still -1, remove g from the list again (no room or online).
5. `0x149d260(g)` (the list keeps it). Spawn, playback, minimap and cleanup then run by themselves.
Rules for the data (from the playback code): >= 2 move keys with strictly rising times (0xfce6a0 divides by the time gap);
**>= 1 snapshot key** (0xfce250 and 0xfcea00 read `snapshotKeys[0]` with no count check); times <= 65535 (u16);
driver/kart names that exist in `_allDrivers`/`_allKarts` (check with 0xf9c610 / 0xf9c900 before step 4; with r8b = 0 a
missing name gives a null `_driverData`/`_kartData` handle; effect unverified). Max 8 racers in total.
Do not call 0xf9b7f0 and do not touch +0x34/+0x38/_challengeGhostToLoad.
Do not patch the vtable slot 0x259b220: it is in the relocated segment (0x61000010) and relocations would likely overwrite it (unverified).

## Unverified
- Callers 0xad4bf0 (calls slot +0xc8) = level start, 0xad7c90 (+0xd0) = level exit, 0xea55c0 = race start, 0xea2d90 / 0x9f3ce0 = per-frame: inferred from the call patterns.
- Whether 0xf9b250 runs again on Retry.
- 0x14a1640 copy depth; 0xb37600 / 0xcb67e0 meaning (unlocked / owned); 0xfcd2e0 = cheat check.
- Assets for a driver/kart not used elsewhere in the race: loaded by the normal spawn path (as for challenge ghosts), not checked.
- Minimap icon image source; no in-race name text for ghosts was found, so showing a player name needs new GUI work.
