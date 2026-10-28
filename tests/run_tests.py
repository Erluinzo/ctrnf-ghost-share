#!/usr/bin/env python3
"""Tests the shared ghost file checks (src/share_format.c) on the PC.

  python3 tests/run_tests.py [--fuzz SECONDS]

1. Builds tests/check_files.c with AddressSanitizer and UBSan and runs its unit tests.
2. Real ghosts must pass: tests/data/*.ctrghost (made with tools/ctrghost.py, not in git: they
   come from game files and saves) and every challenge ghost of the game in ../CTRNF/orig.
3. Hand-made broken and hostile files must fail.
4. Thousands of randomly damaged files: the C checks and the separate Python checks in
   tools/ctrghost.py must agree on every one, and nothing may crash.
5. --fuzz: runs the libFuzzer target for that many seconds.
"""
import random, re, struct, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / 'tools'))
import ctrghost

GHOSTS = ROOT.parent / 'CTRNF/orig/CUSA13795/ghosts'
SANITIZE = ['-fsanitize=address,undefined', '-fno-sanitize-recover=all', '-g', '-O1']


def build(tmp):
    binary = tmp / 'check_files'
    subprocess.run(['clang', *SANITIZE, '-Wall', '-Wextra', '-Werror', '-o', binary,
                    HERE / 'check_files.c', ROOT / 'src/share_format.c'], check=True)
    return binary


def c_verdicts(binary, files):
    out = subprocess.run([binary, *files], capture_output=True, text=True)
    if out.returncode:
        sys.exit(f'check_files crashed:\n{out.stdout}\n{out.stderr}')
    return [line == 'valid' for line in out.stdout.splitlines()]


def hostile(base):
    """Broken files built from a valid one: (name, bytes). Each must be refused."""
    h = bytearray(base[:0x100])
    body = base[0x100:]
    moves, inputs = struct.unpack_from('<II', h, 0x10)

    def header(offset, value_bytes):
        changed = bytearray(h)
        changed[offset:offset + len(value_bytes)] = value_bytes
        return bytes(changed) + body

    def key(offset, value_bytes):
        data = bytearray(base)
        data[offset:offset + len(value_bytes)] = value_bytes
        return bytes(data)

    move0, input0 = 0x100, 0x100 + 20 * moves
    cases = [
        ('empty', b''), ('header only', bytes(h)), ('one byte short', base[:-1]), ('one byte long', base + b'\0'),
        ('magic', header(0, b'CTRGHST2')), ('version', header(8, struct.pack('<I', 2))),
        ('header size', header(0xc, struct.pack('<I', 0x200))),
        ('no move keys', header(0x10, struct.pack('<I', 0))), ('huge move count', header(0x10, struct.pack('<I', 0xffffffff))),
        ('move count past file', header(0x10, struct.pack('<I', moves + 1))),
        ('negative input count', header(0x14, struct.pack('<i', -1))),
        ('time NaN', header(0x18, struct.pack('<f', float('nan')))), ('time inf', header(0x18, struct.pack('<f', float('inf')))),
        ('time negative', header(0x18, struct.pack('<f', -1.0))), ('time too long', header(0x18, struct.pack('<f', 1000.0))),
        ('reserved', header(0x1c, b'\1')),
        ('player empty', header(0x20, b'\0' * 32)), ('player no end', header(0x20, b'A' * 32)),
        ('player control char', header(0x20, b'Ne\x1bx\0')), ('player byte 0xff', header(0x20, b'\xffox\0')),
        ('player leading space', header(0x20, b' Neox\0')), ('player data after end', header(0x20, b'Neox\0X')),
        ('level upper case', header(0x40, b'Octane/t112\0')), ('level dot dot', header(0x40, b'octane/../x\0')),
        ('level backslash', header(0x40, b'octane\\x\0')), ('level absolute', header(0x40, b'/octane\0')),
        ('level double slash', header(0x40, b'octane//x\0')), ('level no end', header(0x40, b'a' * 96)),
        ('driver format chars', header(0xa0, b'Driver%n%n\0')), ('driver path', header(0xa0, b'../Driver\0')),
        ('driver empty', header(0xa0, b'\0' * 48)), ('kart no end', header(0xd0, b'K' * 48)),
        ('position NaN', key(move0, struct.pack('<f', float('nan')))),
        ('position inf', key(move0 + 4, struct.pack('<f', float('-inf')))),
        ('position far', key(move0 + 8, struct.pack('<f', 1e7))),
        ('move time goes back', key(move0 + 20 * 5 + 12, struct.pack('<H', 0))),
        ('input unknown bit', key(input0, struct.pack('<H', 0x8000))),
        ('input time goes back', key(input0 + 4 * (inputs - 1) + 2, struct.pack('<H', 0))),
    ]
    return cases


def main():
    fuzz_seconds = int(sys.argv[sys.argv.index('--fuzz') + 1]) if '--fuzz' in sys.argv else 0
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        binary = build(tmp)
        if subprocess.run([binary, '--unit']).returncode:
            sys.exit('unit tests failed')

        valid = sorted((HERE / 'data').glob('*.ctrghost'))
        if GHOSTS.is_dir():
            for i, igb in enumerate(sorted(GHOSTS.glob('*.igb'))):
                track = re.match(r'(.+?)\1-', igb.name).group(1)   # "t112_roos_tubest112_roos_tubes-76.8-.igb"
                level = f'octane/{track}/{track}'
                out = tmp / f'game{i}.ctrghost'
                with open('/dev/null', 'w') as quiet:
                    sys.stdout, saved = quiet, sys.stdout
                    try:
                        ctrghost.make(igb, level, 'Test', out)
                    finally:
                        sys.stdout = saved
                valid.append(out)
        verdicts = c_verdicts(binary, valid)
        bad = [str(f) for f, ok in zip(valid, verdicts) if not ok or ctrghost.check(f.read_bytes())]
        if bad:
            sys.exit(f'real ghosts refused: {bad}')
        print(f'real ghosts: {len(valid)} accepted')

        base = valid[0].read_bytes()      # any real ghost works as the starting point
        cases = hostile(base)
        files = []
        for i, (name, data) in enumerate(cases):
            files.append(tmp / f'hostile{i}')
            files[-1].write_bytes(data)
        accepted = [name for (name, _), ok in zip(cases, c_verdicts(binary, files)) if ok]
        accepted += [name + ' (python)' for name, data in cases if not ctrghost.check(data)]
        if accepted:
            sys.exit(f'hostile files accepted: {accepted}')
        print(f'hostile files: {len(cases)} refused')

        rng = random.Random(1)
        files, datas = [], []
        for i in range(3000):
            data = bytearray(base)
            for _ in range(rng.choice((1, 1, 2, 5, 40))):
                data[rng.randrange(len(data))] = rng.randrange(256)
            if rng.random() < 0.1:
                data = data[:rng.randrange(len(data))]
            files.append(tmp / f'random{i}')
            files[-1].write_bytes(bytes(data))
            datas.append(bytes(data))
        differ = [f.name for f, data, ok in zip(files, datas, c_verdicts(binary, files)) if ok != (not ctrghost.check(data))]
        if differ:
            sys.exit(f'C and Python checks disagree on {len(differ)} files, e.g. {differ[:5]}')
        print(f'random damage: {len(files)} files, C and Python agree, no crash')

        if fuzz_seconds:
            fuzzer = tmp / 'fuzz'
            subprocess.run(['clang', '-DFUZZ', '-fsanitize=fuzzer,address,undefined', '-g', '-O1', '-o', fuzzer,
                            HERE / 'check_files.c', ROOT / 'src/share_format.c'], check=True)
            corpus = tmp / 'corpus'
            corpus.mkdir()
            (corpus / 'seed').write_bytes(base)
            result = subprocess.run([fuzzer, f'-max_total_time={fuzz_seconds}', '-max_len=70000', str(corpus)],
                                    capture_output=True, text=True)
            print('fuzz:', result.stderr.strip().splitlines()[-1])
            if result.returncode:
                sys.exit('fuzzer found a crash:\n' + result.stderr[-3000:])
    print('all tests passed')


if __name__ == '__main__':
    main()
