# Ghost file format (USA CUSA13795 1.21)

Challenge ghosts (`orig/CUSA13795/ghosts/*.igb`, 150-185 KB) and the save (`SYS-DATA.sav`) are Alchemy
IGB files (little-endian). Parser: `tools/igb_ghost.py FILE [--types] [--objects] [--keys N]`.
Checked on all 163 challenge ghosts and one save (4 player ghosts). ELF addresses are `CTRNF/out/eboot.elf`.
"Unverified" = guessed from data, not from game code.

## Container
| Offset | Size | What |
|---|---|---|
| 0x00 | 0x30 | header: 12 x u32 (below) |
| 0x30 | | header properties (flag 0x80000000, unverified which bit) |
| | | string table |
| | h[8] | field-type table, h[9] entries |
| | h[2] | type (class) table, h[3] entries |
| | | handle names (save only: flag 0x04000000, unverified bit) |
| | | memory-pool names, then pool table (flag 0x10000000, unverified bit) |
| | h[0] | directory entries, h[1] entries |
| | | index (u16 per object/memory block), then u32 root number |
| | h[4] | objects, h[5] of them, in index order |
| | h[6] | memory blocks, h[7] of them, in index order |

Header u32s: h[0] entries size, h[1] entry count, h[2] types size, h[3] type count, h[4] objects size,
h[5] object count, h[6] memory size, h[7] memory count, h[8] field-types size, h[9] field-type count,
h[10] magic 0xFADA, h[11] version 12 | flags (ghost 0xB0000000, save 0xB4000000).
No checksum anywhere. The save is zero-padded to 7 MiB (7340032) after the IGB data.

Sections:
- **Header properties**: u32 n (3), then n x (u32 size, bytes): descriptors (12 B each: u32 kind 0 int / 1 float,
  u32 name offset, u32 value offset), names (NUL-ended), values (4 B each). Ghost: `ghost_version`=3,
  `ghost_time`=race time (float). Save: `most_recent_save_slot`, `save_version`=31. Reader loop: 0x1585e78.
- **String table**: u32 size (counts itself), u32 count, count x (u32 length incl. NUL, bytes). String fields
  hold an index into it; index 0 is "". Ghost: `["", "CGhost0", driver, kart, "root"]`.
- **Field types**: count x (u32 name length, u32 major, u32 minor), then the names (`igIntMetaField`...).
  It is the game's whole list (~900; count differs per file), not only used ones.
- **Types**: count x 6 u32 (name length, major, minor, stored-field count, parent type, total field count),
  then per type: name (even length, padded) + stored-field count x 3 u16 (field type, field index in the class,
  size in memory). Non-persistent fields are left out.
- **Handle names**: u32 size, u32 1 (namespace count?), u32 count, count x u32 hash, NUL-ended names.
- **Pool names**: u32 size, u32 count (108), names. **Pool table**: u32 size, u32 (0x1E ghost / 0x33 save),
  u32 list (0..114 with gaps). Meaning unknown; not needed.
- **Directory entries**: per entry u32 type, u32 size, fields as 4-byte words. `igObjectDirEntry`
  (name, type index, pool), `igMemoryDirEntry` (name, element count, element field type, bool, alignment 8, pool).
- **Index**: u32 size, u32 count, count x u16 entry number. Position in this list = object/block number;
  every reference is this number. The order is not race order (looks like memory order).
- **Objects**: per object u32 type, u32 size (with these 8 bytes), stored fields in table order.
- **Memory blocks**: count x element size, padded to 4 bytes.

Field encoding in the file (not the in-memory size):
| Field type | File bytes |
|---|---|
| Int, UnsignedInt, Float, Enum | 4 |
| Bool, Char, Short, UnsignedShort | 4; value in the low bytes, **upper bytes are uncleared garbage** |
| String | 4: string-table index |
| ObjectRef | 4: object number, -1 null |
| MemoryRef | 4: block number, -2 none (empty list) |
| Vec3f | 12 |
| Vector | 8: block number, count (seen only empty: -2, 0) |
| Handle | 8: name hash, namespace hash |
| ObjectRefArray | 4 per element |
| BitField | 0 (inside another field) |

Memory elements: ObjectRef/Int/UInt/String 4, Name 8 (string index + hash), Char/Bool 1, UShort 2.
Hashes (igName, handles) are FNV-1a 32 of the lowercased text (`CGhost0` -> 0x94EDC78B).

## Object graph of a challenge ghost (23 types, 13 entries)
`root` (u32 after index) -> igInfoList -> igObjectDirectoryIGBInfo {`root`, bool 1, igObjectList [CGhost],
igNameList [`CGhost0`], empty igVector, igNameList [""]}.
CGhost -> CGhostMoveKeyList -> 2100 CGhostMoveKey; CGhost -> CGhostSnapshotKeyList -> 470-2242 CGhostSnapshotKey.
Object count = keys + 8.

| Class | File size | In-memory offsets (from the offset tables) |
|---|---|---|
| CGhost | 32 | +0x0c `_version`, +0x10 `_kart`, +0x18 `_kartName`, +0x20 `_driverName`, +0x28 `_time`, +0x30 `_moveKeys`, +0x38 `_snapshotKeys`, +0x40 `_playMoveKeyIndex`, +0x44 `_playSnapshotKeyIndex`, +0x48 `_playerId` |
| CGhostMoveKey | 36 | +0x0c `_position` vec3f, +0x18 `_timeInternal` u16, +0x1a/+0x1c/+0x1e `_anglesInternal0..2` s16 (size 0x20) |
| CGhostSnapshotKey | 16 | +0x0c `_bitfield` s16, +0x0e `_timeInternal` u16 |
| *KeyList (igObjectList) | 20 | +0x0c `_count`, +0x10 `_capacity`, +0x20 data (8-byte pointers) |

Stored CGhost fields (file order): `_version` (enum), `_kartName`, `_driverName`, `_time` (float s), `_moveKeys`,
`_snapshotKeys`. Not stored: `_kart`, `_playMoveKeyIndex`, `_playSnapshotKeyIndex`, `_playerId`.

Values:
- `_version`: EGhostVersion (values table 0x1da2060): INVALID -1, Initial 0, Thumbnail 1, StartTime 2,
  OptimizeSize 3; `LATEST_GHOST_VERSION` = `INITIAL_GHOST_VALID_VERSION` = 3. All files: 3.
- `_timeInternal`: centiseconds since recording start (code divides by 100.0 at 0xfcb440). Recording starts in the
  countdown: `raceStart` input at 3.80 s (153 files; 3.82/3.83 in 10). Last key = race start + `_time` - ~0.03 s.
  The last move key and last snapshot key have the same time.
- Move keys: always exactly 2100 = default capacity (set at 0x1890f65). Step 0.03 s (2 frames) for ~80 s laps,
  median 0.07 s for 140-190 s races, up to 3.8 s in the countdown, so keys are thinned to fit (unverified how).
- `_position`: world units; ranges about -25000..+35000, z is up (save ghost on Electron Avenue: z 36000-53500).
- `_anglesInternal`: radians x 10430.06 (32767/pi; divisor at 0xfce509, 0xfce1a9 when placing the ghost).
  Angle 2 covers the full circle (yaw); 0 and 1 stay small (pitch/roll; which is which unverified).
- Snapshot keys = input changes only. `_bitfield` bits (registration 0x18906bc):
  0-7 `_turnAnalogInternal` (signed, -127..127), 8 `_accelerate`, 9 `_reverse`, 10 `_brake`, 11 `_firstJump`,
  12 `_secondJump`, 13 `_startDrift`, 14 `_raceStart`. All 15 bits seen. Default capacity 2250 (0x18910e4).

Garbage note: uncleared padding (e.g. `d609 803f`: angle 0x09d6, then high half of 1.0f) must be masked.

## Player ghosts in SYS-DATA.sav (49 types)
COctaneGlobalSaveData -> CZoneInfoGhostHashTable (igHashTable: `_values` refs, `_keys` string indices,
parallel arrays, `_hashItemCount`, `_autoRehash`, `_loadFactor` 0.5). Key = zone
(`octane/t112_roos_tubes/t112_roos_tubes`), value = CGhostSavedInfo {`unlockedChallengeGhostIndex` (int,
+0x0c), `_ghost` (ref, +0x10)} -> CGhost with the same layout as above (version 3, 2100 move keys).
Backup save: 4 ghosts (t111, t112, t113, t243), all `DriverBigNorm` + `KartChampion`.

## Identity and kart look
- No player name, user id or online id in a ghost. `_playerId` is the enum `EPlayerId` (local player slot),
  not stored. Only `_driverName` (e.g. `DriverPolar`) and `_kartName` (e.g. `KartCrash`) are stored.
- `_kart` (object ref; type from 0x1ba40a0, probably a DotNet object, unverified) has its persistent flag cleared
  (0x1890e23), so no kart customization is saved: no paint, decals, wheels, stickers, preset or driver skin.
- The look lives elsewhere in the save: COctaneCustomizationSaveData (4 in the save) {`_driver` handle,
  `_driverSkinIndex`, `_kart` handle, `_kartWheelsIndex`, `_kartPaintIndex`, `_kartDecalIndex`,
  `_kartStickerIndex`, `_kartPresetIndex`}; e.g. driver `SystemData/SystemData_availableDrivers_21`,
  kart `SystemData/kartChampion`, wheels 26, paint 109, sticker 0, skin 0.
- Leaderboard rows COctaneTimeTrialData {`_timeInSeconds`, `_driverName`, `_userName`} have a user-name field
  (empty in local records); not part of a ghost.
- Challenge ghost names seen: 22 driver/kart pairs, e.g. `DriverKCN`/`KartMWP`, `DriverHereIAm`/`KartSBY`.

## Export / import notes
- A shareable ghost = one challenge-style .igb: CGhost + 2 lists + keys. Copying the header, properties and
  type sections from a game ghost and rewriting strings/objects/memory should give a valid file (unverified:
  the game was never fed a rebuilt file).
- Before loading a foreign file check: magic 0xFADA, version 12; every section size adds up; the 6 ghost
  classes have the expected stored fields; `_version` 3; every ref is in range and points to the right class;
  move keys <= 2100, snapshot keys <= 2250, times rising and <= 65535; floats finite; `_time` = `ghost_time`;
  driver/kart names from the game's known list (unknown names: unverified what the game does).

## Code addresses
| ELF | What |
|---|---|
| 0x1890d5c | CGhost field registration (names 0x261d370, offsets 0x1da20c0) |
| 0x189051c | CGhostMoveKey (names 0x261cce0, offsets 0x1da2090) |
| 0x18906bc | CGhostSnapshotKey (names 0x261cfd0, offsets 0x1da20a0) |
| 0xfce080, 0xfce410 | put a ghost at its first move key (angles / 10430.06) |
| 0xfcb410 | reads `_timeInternal` / 100.0 |
| 0x1585cd0 | IGB header sniffer (magic, version 12, header properties) |

Note: the earlier guess had the two key name tables swapped; 0x261cfd0 (`_bitfield`...) is CGhostSnapshotKey.

## Unverified
Which flag bit enables which section; pool table meaning; handle-section count fields; directory-entry field
names; igVector with data; how keys are thinned to 2100; pitch/roll order and turn sign; what `_kart` points to;
whether the game accepts a rebuilt or foreign ghost file and what it does with unknown driver/kart names.
