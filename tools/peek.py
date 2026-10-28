#!/usr/bin/env python3
"""Prints the ghost sharing patch's state from the running game (Linux; reads /proc/PID/mem).

  peek.py [PID]      (default: the running sacredfire process)

The image is found by the first bytes of a game function at a known address. The state layout
must match `struct state` in src/ghostshare.c.
"""
import struct, subprocess, sys

PROBE = 0xfcc430    # the ghost manager's race-end function: its prologue is known
PROLOGUE = bytes.fromhex('554889e541574156415541545348')
STATE = 0x2bee680
SHARED_SIZE = 112   # void *header; char file[64]; char player[32]; uint8_t chosen; padding
EXPORT = ['none', 'ok', 'no level', 'no saved ghost', 'bad ghost', 'open failed', 'write failed', 'mount failed']


def find_base(mem, maps):
    for line in maps:
        start = int(line.split('-')[0], 16)
        try:
            mem.seek(start + PROBE)
            if mem.read(len(PROLOGUE)) == PROLOGUE:
                return start
        except OSError:
            pass
    sys.exit('game image not found')


def main():
    pid = int(sys.argv[1]) if len(sys.argv) > 1 else int(subprocess.check_output(['pgrep', '-x', 'sacredfire']).split()[0])
    maps = open(f'/proc/{pid}/maps').read().splitlines()
    with open(f'/proc/{pid}/mem', 'rb') as mem:
        base = find_base(mem, maps)
        mem.seek(base + STATE)
        state = mem.read(0x350)
    text = lambda b: b.split(b'\0')[0].decode(errors='replace')
    count, = struct.unpack_from('<i', state, 0x60)
    last_signal, export_result = struct.unpack_from('<ii', state, 0x68 + 6 * SHARED_SIZE)
    print(f'image base {base:#x}; menu level "{text(state[:96])}"; {count} shared ghosts')
    for i in range(min(max(count, 0), 6)):
        at = 0x68 + i * SHARED_SIZE
        header, = struct.unpack_from('<Q', state, at)
        print(f'  {text(state[at + 8:at + 72])}: player "{text(state[at + 72:at + 104])}", '
              f'chosen {state[at + 104]}, header {header:#x}')
    print(f'last button signal {last_signal}; last export: '
          f'{EXPORT[export_result] if 0 <= export_result < len(EXPORT) else export_result}'
          f' "{text(state[0x70 + 6 * SHARED_SIZE:0xb0 + 6 * SHARED_SIZE])}"')


if __name__ == '__main__':
    main()
