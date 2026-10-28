#!/usr/bin/env python3
"""Reads Alchemy IGB files of CTR Nitro-Fueled (PS4 USA 1.21) and prints the ghosts in them.

  igb_ghost.py FILE [--types] [--objects] [--keys N]

FILE is a challenge ghost (orig/CUSA13795/ghosts/*.igb) or a save (SYS-DATA.sav): both use
the same container. --types prints every stored class with its fields, --objects every object,
--keys N the first N keys of each key list (default 3). Format: ../notes/ghost-format.md
"""
import struct
import sys

# In the file every field takes 4 bytes unless listed here (small values are padded to 4 bytes;
# the padding is not cleared, so mask it off). A bit field is kept inside another field.
FIELD_SIZE = {'igVec3f': 12, 'igVec4f': 16, 'igVector': 8, 'igHandle': 8, 'igBitField': 0}
# Size of one element in a memory block; each block is padded to a multiple of 4 bytes.
ELEMENT_SIZE = {'igName': 8, 'igChar': 1, 'igUnsignedChar': 1, 'igBool': 1,
                'igShort': 2, 'igUnsignedShort': 2}
GHOST_VERSIONS = {0: 'InitialVersion', 1: 'ThumbnailVersion', 2: 'StartTimeVersion',
                  3: 'OptimizeSize (latest)'}
# CGhostSnapshotKey._bitfield: (name, first bit, bit count), from the game's field registration
SNAPSHOT_BITS = [('turn', 0, 8), ('accelerate', 8, 1), ('reverse', 9, 1), ('brake', 10, 1),
                 ('firstJump', 11, 1), ('secondJump', 12, 1), ('startDrift', 13, 1),
                 ('raceStart', 14, 1)]


class Igb:
    def __init__(self, data):
        self.data = data
        (self.entries_size, self.entry_count, self.types_size, self.type_count,
         self.objects_size, self.object_count, self.memory_size, self.memory_count,
         self.field_types_size, self.field_type_count, magic, version) = self.u32s(0, 12)
        if magic != 0xFADA:
            raise ValueError('not an IGB file (no 0xFADA at offset 0x28)')
        self.version, self.flags = version & 0xFFFF, version & 0xFFFF0000
        self.pos = 0x30
        self.properties, self.strings = {}, []
        if self.flags & 0x80000000:
            self.read_properties()
            self.read_strings()
        self.read_field_types()
        self.read_types()
        self.handle_names = self.block() if self.flags & 0x04000000 else b''
        if self.flags & 0x10000000:
            self.pool_names = self.block()
            self.pool_table = self.block()
        self.read_entries()
        self.read_index()
        self.read_objects()
        self.read_memory()

    def u32s(self, pos, count):
        return struct.unpack_from('<%dI' % count, self.data, pos)

    def u32(self):
        value, = struct.unpack_from('<I', self.data, self.pos)
        self.pos += 4
        return value

    def block(self):
        """A section that starts with its own size (the size counts itself)."""
        size, = self.u32s(self.pos, 1)
        self.pos += size
        return self.data[self.pos - size:self.pos]

    def read_properties(self):
        # count (3), then count x (u32 size, bytes): descriptors, names, values
        parts = []
        for _ in range(self.u32()):
            size = self.u32()
            parts.append(self.data[self.pos:self.pos + size])
            self.pos += size
        descriptors, names, values = parts
        for i in range(0, len(descriptors), 12):
            kind, name_at, value_at = struct.unpack_from('<3I', descriptors, i)
            name = names[name_at:names.index(b'\0', name_at)].decode()
            self.properties[name] = struct.unpack_from('<f' if kind == 1 else '<i', values, value_at)[0]

    def read_strings(self):
        end = self.pos + self.u32()
        for _ in range(self.u32()):
            size = self.u32()
            self.strings.append(self.data[self.pos:self.pos + size].split(b'\0')[0].decode('latin-1'))
            self.pos += size
        assert self.pos == end, 'string table size does not match'

    def read_field_types(self):
        start = self.pos
        lengths = [self.u32s(self.pos + 12 * i, 1)[0] for i in range(self.field_type_count)]
        self.pos += 12 * self.field_type_count   # each: name length, major, minor version
        self.field_types = []
        for n in lengths:
            name = self.data[self.pos:self.pos + n].split(b'\0')[0].decode()
            self.field_types.append(name.replace('MetaField', ''))
            self.pos += n
        assert self.pos == start + self.field_types_size

    def read_types(self):
        start = self.pos
        heads = [self.u32s(self.pos + 24 * i, 6) for i in range(self.type_count)]
        self.pos += 24 * self.type_count
        self.types = []   # (name, parent index, [(field type, field index, size in memory)])
        for name_len, _major, _minor, field_count, parent, _slots in heads:
            name = self.data[self.pos:self.pos + name_len].split(b'\0')[0].decode()
            self.pos += name_len
            fields = []
            for _ in range(field_count):
                kind, index, size = struct.unpack_from('<3H', self.data, self.pos)
                fields.append((self.field_types[kind], index, size))
                self.pos += 6
            self.types.append((name, parent, fields))
        assert self.pos == start + self.types_size

    def read_entries(self):
        # One entry per kind of object or memory block: (type index, size, its fields)
        end = self.pos + self.entries_size
        self.entries = []
        while self.pos < end:
            kind, size = self.u32s(self.pos, 2)
            values = self.u32s(self.pos + 8, (size - 8) // 4)
            if self.types[kind][0] == 'igObjectDirEntry':
                self.entries.append(('object', values[1]))   # object type index
            else:   # igMemoryDirEntry: element count, element field type
                self.entries.append(('memory', values[1], self.field_types[values[2]]))
            self.pos += size
        assert len(self.entries) == self.entry_count

    def read_index(self):
        # Every object and memory block gets a number (its place here); references use it.
        size, count = self.u32s(self.pos, 2)
        self.index = struct.unpack_from('<%dH' % count, self.data, self.pos + 8)
        self.pos += size
        self.root = self.u32()

    def read_objects(self):
        start = self.pos
        self.objects = {}   # number -> (type name, {field name or index: value})
        for number, entry in enumerate(self.index):
            if self.entries[entry][0] != 'object':
                continue
            kind, size = self.u32s(self.pos, 2)
            self.objects[number] = (self.types[kind][0], self.decode(kind, self.pos + 8, self.pos + size))
            self.pos += size
        assert self.pos == start + self.objects_size, 'object section size does not match'

    def decode(self, kind, pos, end):
        name, _, fields = self.types[kind]
        names = FIELD_NAMES.get(name, {})
        out = {}
        for field, index, memory_size in fields:
            key = names.get(index, index)
            size = FIELD_SIZE.get(field, 4)
            if field == 'igObjectRefArray':
                size = memory_size // 2   # 8-byte pointers in memory, 4-byte numbers in the file
            if pos + size > end:
                out[key] = '(no data)'
                continue
            raw = self.data[pos:pos + size]
            if field == 'igFloat':
                value = round(struct.unpack('<f', raw)[0], 6)
            elif field == 'igVec3f':
                value = tuple(round(v, 3) for v in struct.unpack('<3f', raw))
            elif field == 'igString':
                value = self.strings[struct.unpack('<I', raw)[0]]
            elif field in ('igShort', 'igUnsignedShort'):
                value = struct.unpack('<h' if field == 'igShort' else '<H', raw[:2])[0]
            elif field in ('igBool', 'igChar', 'igUnsignedChar'):
                value = raw[0]
            elif field == 'igBitField':
                continue
            elif size == 4:
                value = struct.unpack('<i', raw)[0]   # numbers, enums, object/memory references
            else:
                value = raw.hex(' ', 4)
            out[key] = value
            pos += size
        if pos < end:
            out['(rest)'] = self.data[pos:end].hex(' ', 4)
        return out

    def read_memory(self):
        start = self.pos
        self.memory = {}   # number -> (element type, element count, bytes)
        for number, entry in enumerate(self.index):
            if self.entries[entry][0] != 'memory':
                continue
            _, count, field = self.entries[entry]
            size = count * ELEMENT_SIZE.get(field, 4)
            self.memory[number] = (field, count, self.data[self.pos:self.pos + size])
            self.pos += (size + 3) & ~3
        assert self.pos == start + self.memory_size, 'memory section size does not match'
        assert self.pos == len(self.data) or not any(self.data[self.pos:]), 'data after the end'

    def numbers(self, memory_ref):
        """The 4-byte numbers in a memory block (object references, ints, string indices)."""
        if memory_ref not in self.memory:   # -2: an empty list has no block
            return []
        _, count, raw = self.memory[memory_ref]
        return struct.unpack('<%di' % count, raw[:4 * count])

    def list_items(self, list_number):
        """The object numbers held by an igObjectList-style object, in list order."""
        fields = self.objects[list_number][1]
        return self.numbers(fields['_data'])[:fields['_count']]


# Field names by field index, from the game's reflection tables (see the notes).
FIELD_NAMES = {
    'CGhost': {0: '_version', 2: '_kartName', 3: '_driverName', 4: '_time', 5: '_moveKeys',
               6: '_snapshotKeys'},
    'CGhostMoveKey': {0: '_position', 1: '_timeInternal', 2: '_anglesInternal0',
                      3: '_anglesInternal1', 4: '_anglesInternal2'},
    'CGhostSnapshotKey': {0: '_bitfield', 1: '_timeInternal'},
    'CGhostSavedInfo': {0: 'unlockedChallengeGhostIndex', 1: '_ghost'},
    'COctaneCustomizationSaveData': {0: '_driver', 1: '_driverSkinIndex', 2: '_kart',
                                     3: '_kartWheelsIndex', 4: '_kartPaintIndex',
                                     5: '_kartDecalIndex', 6: '_kartStickerIndex',
                                     7: '_kartPresetIndex'},
    'COctaneTimeTrialData': {0: '_timeInSeconds', 1: '_driverName', 2: '_userName'},
    'igHashTable': {0: '_values', 1: '_keys', 2: '_hashItemCount', 3: '_autoRehash',
                    4: '_loadFactor'},
}
FIELD_NAMES['CZoneInfoGhostHashTable'] = FIELD_NAMES['igHashTable']
for _name in ('igDataList', 'igObjectList', 'CGhostMoveKeyList', 'CGhostSnapshotKeyList',
              'igInfoList', 'igNameList'):
    FIELD_NAMES[_name] = {0: '_count', 1: '_capacity', 2: '_data'}


def snapshot_text(bits):
    turn = bits & 0xFF
    turn = turn - 256 if turn > 127 else turn
    on = [name for name, first, count in SNAPSHOT_BITS[1:] if bits >> first & 1]
    return 'turn %4d %s' % (turn, ' '.join(on))


def print_ghost(igb, number, show_keys):
    _, ghost = igb.objects[number]
    version = ghost['_version']
    print('  CGhost #%d: version %d (%s), driver %s, kart %s, time %.6f s' % (
        number, version, GHOST_VERSIONS.get(version, '?'), ghost['_driverName'],
        ghost['_kartName'], ghost['_time']))

    moves = [igb.objects[n][1] for n in igb.list_items(ghost['_moveKeys'])]
    times = [k['_timeInternal'] / 100 for k in moves]
    steps = sorted(b - a for a, b in zip(times, times[1:]))
    print('    move keys: %d, time %.2f..%.2f s, step %.2f..%.2f s (median %.2f)' % (
        len(moves), times[0], times[-1], steps[0], steps[-1], steps[len(steps) // 2]))
    for axis in range(3):
        values = [k['_position'][axis] for k in moves]
        print('      position %s: %.1f..%.1f' % ('xyz'[axis], min(values), max(values)))
    for i in range(3):
        values = [k['_anglesInternal%d' % i] for k in moves]
        print('      angle %d: %d..%d' % (i, min(values), max(values)))
    for k in moves[:show_keys]:
        print('      t=%6.2f pos=%s angles=%d %d %d' % (
            k['_timeInternal'] / 100, k['_position'], k['_anglesInternal0'],
            k['_anglesInternal1'], k['_anglesInternal2']))

    shots = [igb.objects[n][1] for n in igb.list_items(ghost['_snapshotKeys'])]
    print('    snapshot (input) keys: %d, time %.2f..%.2f s' % (
        len(shots), shots[0]['_timeInternal'] / 100, shots[-1]['_timeInternal'] / 100))
    for k in shots[:show_keys]:
        print('      t=%6.2f bits=%04x %s' % (
            k['_timeInternal'] / 100, k['_bitfield'] & 0xFFFF, snapshot_text(k['_bitfield'])))


def main():
    args = sys.argv[1:]
    if not args or args[0].startswith('-'):
        sys.exit(__doc__)
    show_keys = int(args[args.index('--keys') + 1]) if '--keys' in args else 3
    igb = Igb(open(args[0], 'rb').read())
    print('%s: IGB version %d, flags %#x, %d objects (%d bytes), %d memory blocks (%d bytes)' % (
        args[0], igb.version, igb.flags, igb.object_count, igb.objects_size, igb.memory_count,
        igb.memory_size))
    print('  properties:', igb.properties)
    print('  strings:', igb.strings if len(igb.strings) < 12 else '%d strings' % len(igb.strings))
    if '--types' in args:
        for i, (name, parent, fields) in enumerate(igb.types):
            print('  type %2d %-32s parent %2d %s' % (
                i, name, parent if parent < 0x10000 else -1,
                ', '.join('%d:%s' % (index, kind) for kind, index, _ in fields)))
    if '--objects' in args:
        for number, (name, fields) in sorted(igb.objects.items()):
            if name not in ('CGhostMoveKey', 'CGhostSnapshotKey'):
                print('  #%d %s %s' % (number, name, fields))

    # A save keeps its ghosts in a CZoneInfoGhostHashTable: track name -> CGhostSavedInfo.
    track_of = {}
    for name, fields in igb.objects.values():
        if name == 'CZoneInfoGhostHashTable':
            keys = igb.numbers(fields['_keys'])
            for key, value in zip(keys, igb.numbers(fields['_values'])):
                if value >= 0:
                    track_of[value] = igb.strings[key]
    saved_info = {f['_ghost']: (n, f) for n, (name, f) in igb.objects.items()
                  if name == 'CGhostSavedInfo'}
    for number, (name, _) in sorted(igb.objects.items()):
        if name != 'CGhost':
            continue
        if number in saved_info:
            info_number, info = saved_info[number]
            print('  track %s: unlocked challenge ghost index %d' % (
                track_of.get(info_number, '?'), info['unlockedChallengeGhostIndex']))
        print_ghost(igb, number, show_keys)


if __name__ == '__main__':
    main()
