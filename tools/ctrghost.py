#!/usr/bin/env python3
"""Test helper for shared ghost files (.ctrghost; format in src/share_format.h).

  ctrghost.py make GHOST LEVEL PLAYER OUT.ctrghost
      GHOST is a challenge ghost (.igb) or a save (SYS-DATA.sav: the ghost of LEVEL is used).
  ctrghost.py show FILE.ctrghost
      Prints the file and checks it with the same rules as the game patch (Python copy of them).
"""
import math, re, struct, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from igb_ghost import Igb

HEADER = struct.Struct('<8sIIIIfI32s96s48s48s')
MOVE = struct.Struct('<fffHhhh')
INPUT = struct.Struct('<HH')


def signed16(v):
    v &= 0xFFFF
    return v - 0x10000 if v >= 0x8000 else v


def find_ghost(igb, level):
    """The CGhost of a challenge ghost file, or the ghost of `level` in a save."""
    ghosts = [n for n, (kind, _) in igb.objects.items() if kind == 'CGhost']
    saved = {f['_ghost']: n for n, (kind, f) in igb.objects.items() if kind == 'CGhostSavedInfo'}
    tracks = {}
    for kind, fields in igb.objects.values():
        if kind == 'CZoneInfoGhostHashTable':
            for key, value in zip(igb.numbers(fields['_keys']), igb.numbers(fields['_values'])):
                if value >= 0:
                    tracks[value] = igb.strings[key].lower().replace('\\', '/')
    for n in ghosts:
        if n not in saved or tracks.get(saved[n]) == level:
            return igb.objects[n][1]
    sys.exit(f'no ghost for {level}')


def make(source, level, player, out):
    igb = Igb(Path(source).read_bytes())
    ghost = find_ghost(igb, level)
    moves = [igb.objects[n][1] for n in igb.list_items(ghost['_moveKeys'])]
    inputs = [igb.objects[n][1] for n in igb.list_items(ghost['_snapshotKeys'])]
    data = HEADER.pack(b'CTRGHST1', 1, 0x100, len(moves), len(inputs), ghost['_time'], 0,
                       player.encode(), level.encode(), ghost['_driverName'].encode(), ghost['_kartName'].encode())
    for k in moves:
        data += MOVE.pack(*k['_position'], k['_timeInternal'] & 0xFFFF,
                          *(signed16(k['_anglesInternal%d' % i]) for i in range(3)))
    for k in inputs:
        data += INPUT.pack(k['_bitfield'] & 0xFFFF, k['_timeInternal'] & 0xFFFF)
    Path(out).write_bytes(data)
    print(f'{out}: {len(moves)} move keys, {len(inputs)} input keys, {len(data)} bytes')


def text(field, pattern):
    """The text of a fixed field, or None if it breaks the rules (see share_format.c)."""
    value, _, rest = field.partition(b'\0')
    if not value or field.find(b'\0') < 0 or rest.strip(b'\0') or not re.fullmatch(pattern, value):
        return None
    return value.decode()


def check(data):
    """Returns a list of problems; empty when the file is valid."""
    if len(data) < HEADER.size:
        return ['too short']
    (magic, version, header_size, moves, inputs, time, reserved,
     player, level, driver, kart) = HEADER.unpack_from(data)
    problems = []
    if magic != b'CTRGHST1' or version != 1 or header_size != 0x100 or reserved:
        problems.append('bad magic/version/reserved')
    if not (2 <= moves <= 4096 and 1 <= inputs <= 16384):
        return problems + ['bad key counts']
    if not (0.01 <= time <= 655.0):
        problems.append('bad time')
    if not text(player, rb'[\x21-\x7e][\x20-\x7e]*'):
        problems.append('bad player')
    level_text = text(level, rb'[a-z0-9_][a-z0-9_/]*')
    if not level_text or '//' in level_text:
        problems.append('bad level')
    if not text(driver, rb'[A-Za-z0-9_]+') or not text(kart, rb'[A-Za-z0-9_]+'):
        problems.append('bad driver/kart')
    if len(data) != HEADER.size + moves * MOVE.size + inputs * INPUT.size:
        return problems + ['bad file size']
    last = -1
    for i in range(moves):
        x, y, z, t, *_ = MOVE.unpack_from(data, HEADER.size + i * MOVE.size)
        if not all(math.isfinite(v) and abs(v) <= 1e6 for v in (x, y, z)) or t < last:
            return problems + [f'bad move key {i}']
        last = t
    last = -1
    for i in range(inputs):
        bits, t = INPUT.unpack_from(data, HEADER.size + moves * MOVE.size + i * INPUT.size)
        if bits & ~0x7FFF or t < last:
            return problems + [f'bad input key {i}']
        last = t
    return problems


def show(path):
    data = Path(path).read_bytes()
    fields = HEADER.unpack_from(data) if len(data) >= HEADER.size else None
    if fields:
        name = lambda b: b.split(b'\0')[0].decode(errors='replace')
        print(f'{path}: player {name(fields[7])}, level {name(fields[8])}, driver {name(fields[9])}, '
              f'kart {name(fields[10])}, time {fields[5]:.3f} s, {fields[3]} move keys, {fields[4]} input keys')
    problems = check(data)
    print('valid' if not problems else 'NOT valid: ' + ', '.join(problems))
    return not problems


if __name__ == '__main__':
    if len(sys.argv) == 6 and sys.argv[1] == 'make':
        make(*sys.argv[2:])
    elif len(sys.argv) == 3 and sys.argv[1] == 'show':
        sys.exit(0 if show(sys.argv[2]) else 1)
    else:
        sys.exit(__doc__)
