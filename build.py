#!/usr/bin/env python3
"""Builds the ghost sharing patch, one mod package per game edition (the launcher needs each
package's XML to target one edition, and cannot pick between two ZIPs of one mod id), and a
switched-on test copy of each XML in the game's patches folder:
  package/patches/GhostShare.xml           USA CUSA13795 1.21
  package-eu/patches/GhostShare-EU.xml     EU CUSA14876 1.21, with mod.json and README.txt made from package/
  python3 build.py

Each edition's executable is only read: to check the original bytes at every write and to compute
the ExpectedSHA256 values the launcher checks before it applies the patch. The EU addresses were
found with ../CTRNF-Mods/tools/eu_map.py (same functions, moved by 0 to -0x40).
"""
import hashlib, json, re, shutil, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME_DIR = HERE.parent / 'CTRNF'
VERSION = '1.2.1'
EBOOT_BASE = 0x400000       # patch XML addresses are ELF addresses + 0x400000

CODE = 0x2320000            # unused zero padding at the end of the code segment (USA 0x2317810-0x233c078,
                            # EU 0x23177d0-0x233c038)
CODE_END = 0x2338000        # the Time Trial patch starts here; tomtotom's drift gauge ends at 0x23192df
STATE = 0x2bee680           # after the game's data (ends 0x2bee66d), before the page end 0x2bef000
STATE_END = 0x2bef000
MAX_WRITE = 4096
# Button that exports your ghost in the ghost menu (igGuiInput signal). Tested in game: Triangle/Y
# is 11 but also opens the Options screen; R1 is 16 and does nothing else there (L1 17, L2 15, R2 14).
EXPORT_SIGNAL = 16

# Per edition: game code and data the patch uses ('game', set with ld --defsym), and the hooks
# ('hooks': address, original bytes, new instruction, target symbol, padding; each replaces whole
# instructions). The EU hooks that replace a call or a RIP-relative load have other original bytes.
# The owner tests each build at once: a copy goes into the game's patches folder, switched on.
EDITIONS = {
    'CUSA13795': dict(
        name='USA', elf=GAME_DIR / 'out/eboot.elf', xml=HERE / 'package/patches/GhostShare.xml',
        test_copy=GAME_DIR / 'patches/GhostShare.xml',
        game={
            'game_ghost_new': 0x10e1050, 'game_move_key_new': 0x10e0cb0, 'game_input_key_new': 0x10e0d80,
            'game_header_meta': 0x10e09e0, 'game_create': 0x14a0e30, 'game_release': 0x149d260,
            'game_list_set_count': 0x14a6f20, 'game_list_reserve': 0x14a4ed0,
            'game_string': 0x1574080, 'game_string_release': 0x1518e30,
            'game_fill_challenge_ghosts': 0xfceac0, 'game_send_event': 0x24de10, 'game_spawn_ghost': 0xf9bee0,
            'game_find_driver': 0xf9c610, 'game_find_kart': 0xf9c900, 'game_saved_ghost': 0xf9cc00,
            'game_current_zone': 0x102e040, 'game_open_dialog': 0x9c3890, 'game_handle_free': 0x149f280,
            'game_legend_add': 0xa09d30, 'game_focus_gain_event': 0x10ee760, 'game_focus_lost_event': 0x10ee880, 'game_list_vtable': 0x2436b18,
            'game_button_select': 0x9b3a5a, 'game_button_exit': 0x9b3a34,
            # PS4 import stubs
            'sce_open': 0x1beab78, 'sce_pread': 0x1bea7b8, 'sce_pwrite': 0x1bea868, 'sce_close': 0x1beaa38,
            'sce_fstat': 0x1beac08, 'sce_getdents': 0x1beaa18,
            'sce_unlink': 0x1beaab8, 'sce_initial_user': 0x1be8df8, 'sce_user_name': 0x1bea528,
            'sce_save_mount2': 0x1beaa68, 'sce_save_umount': 0x1bea988,
            # data
            'g_string_pool': 0x2af2600, 'g_racer_manager': 0x2ad4b70, 'g_zone_system': 0x2ae3c18, 'g_gui_manager': 0x2ac0dc0,
            'g_header_meta': 0x2abc210, 'g_default_level': 0x1df8d10, 'game_race_flag': 0x2a92868, 'gs': STATE,
        },
        hooks=[
            (0x9e2756, 'e865c35e00', 'e8', 'hook_fill', 0),                 # ghost menu: add challenge ghosts
            (0x9e2d22, 'e899bd5e00', 'e8', 'hook_fill', 0),
            (0x9b3e88, 'e8839f89ff', 'e8', 'hook_entry_setup', 0),          # entry text: send setup event
            (0x9b3a53, '41837d180875da', 'e9', 'hook_button', 2),           # button on an entry
            (0x9b3baa, 'e8b1ab7300', 'e8', 'hook_focus_gain', 0),           # an entry gets focus
            (0x9b3998, 'e8e3ae7300', 'e8', 'hook_focus_lost', 0),           # an entry loses focus
            (0xf9b298, '41807f4800', 'e8', 'hook_take_chosen', 0),          # race start, before chosen ghosts load
            (0xf9b329, '8a053975af01', 'e8', 'hook_add_chosen', 1),         # race start, after them
        ]),
    'CUSA14876': dict(
        name='EU', elf=GAME_DIR / 'orig/CUSA14876-eboot.elf', xml=HERE / 'package-eu/patches/GhostShare-EU.xml',
        test_copy=GAME_DIR / 'patches/GhostShare-EU.xml',
        game={
            'game_ghost_new': 0x10e1040, 'game_move_key_new': 0x10e0ca0, 'game_input_key_new': 0x10e0d70,
            'game_header_meta': 0x10e09d0, 'game_create': 0x14a0e20, 'game_release': 0x149d250,
            'game_list_set_count': 0x14a6f10, 'game_list_reserve': 0x14a4ec0,
            'game_string': 0x1574070, 'game_string_release': 0x1518e20,
            'game_fill_challenge_ghosts': 0xfceab0, 'game_send_event': 0x24de10, 'game_spawn_ghost': 0xf9bed0,
            'game_find_driver': 0xf9c600, 'game_find_kart': 0xf9c8f0, 'game_saved_ghost': 0xf9cbf0,
            'game_current_zone': 0x102e030, 'game_open_dialog': 0x9c3890, 'game_handle_free': 0x149f270,
            'game_legend_add': 0xa09d30, 'game_focus_gain_event': 0x10ee750, 'game_focus_lost_event': 0x10ee870, 'game_list_vtable': 0x2436b18,
            'game_button_select': 0x9b3a5a, 'game_button_exit': 0x9b3a34,
            # PS4 import stubs
            'sce_open': 0x1beab58, 'sce_pread': 0x1bea798, 'sce_pwrite': 0x1bea848, 'sce_close': 0x1beaa18,
            'sce_fstat': 0x1beabe8, 'sce_getdents': 0x1bea9f8,
            'sce_unlink': 0x1beaa98, 'sce_initial_user': 0x1be8dd8, 'sce_user_name': 0x1bea508,
            'sce_save_mount2': 0x1beaa48, 'sce_save_umount': 0x1bea968,
            # data
            'g_string_pool': 0x2af2600, 'g_racer_manager': 0x2ad4b70, 'g_zone_system': 0x2ae3c18, 'g_gui_manager': 0x2ac0dc0,
            'g_header_meta': 0x2abc210, 'g_default_level': 0x1df8cd0, 'game_race_flag': 0x2a92868, 'gs': STATE,
        },
        hooks=[
            (0x9e2756, 'e855c35e00', 'e8', 'hook_fill', 0),                 # ghost menu: add challenge ghosts
            (0x9e2d22, 'e889bd5e00', 'e8', 'hook_fill', 0),
            (0x9b3e88, 'e8839f89ff', 'e8', 'hook_entry_setup', 0),          # entry text: send setup event
            (0x9b3a53, '41837d180875da', 'e9', 'hook_button', 2),           # button on an entry
            (0x9b3baa, 'e8a1ab7300', 'e8', 'hook_focus_gain', 0),           # an entry gets focus
            (0x9b3998, 'e8d3ae7300', 'e8', 'hook_focus_lost', 0),           # an entry loses focus
            (0xf9b288, '41807f4800', 'e8', 'hook_take_chosen', 0),          # race start, before chosen ghosts load
            (0xf9b319, '8a054975af01', 'e8', 'hook_add_chosen', 1),         # race start, after them
        ]),
}

CFLAGS = ['-c', '-O2', '-std=c11', '-fpie', '-ffreestanding', '-fno-stack-protector',
          '-fno-asynchronous-unwind-tables', '-fno-unwind-tables', '-fcf-protection=none', '-mno-red-zone',
          '-fvisibility=hidden', '-fno-tree-loop-distribute-patterns', '-Wall', '-Wextra', '-Werror']
# Only RIP-relative references: the game image is not loaded at a fixed address.
RELATIVE = {'R_X86_64_PC32', 'R_X86_64_PLT32'}

LINKER_SCRIPT = '''SECTIONS {
  . = %#x;
  .text : { *(.text .text.*) *(.rodata .rodata.*) }
  /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }
}
'''


def read(elf, va, n):
    # The code segment starts at file offset 0x4000 with address 0.
    return elf[0x4000 + va:0x4000 + va + n]


def run(*command):
    subprocess.run([str(c) for c in command], check=True)


def build_code(tmp, title, game):
    objects = []
    for source in ('ghostshare.c', 'share_format.c', 'mem.c'):
        obj = tmp / (source + '.o')
        run('gcc', *CFLAGS, f'-DEXPORT_SIGNAL={EXPORT_SIGNAL}', f'-DTITLE_ID="{title}"', '-o', obj, HERE / 'src' / source)
        objects.append(obj)
    obj = tmp / 'hooks.o'
    run('as', '--64', '-o', obj, HERE / 'src/hooks.s')
    objects.append(obj)
    for obj in objects:
        relocs = subprocess.run(['readelf', '-rW', obj], capture_output=True, text=True, check=True).stdout
        kinds = set(re.findall(r'\bR_X86_64_\w+', relocs))
        if kinds - RELATIVE:
            sys.exit(f'{obj.name}: not RIP-relative: {sorted(kinds - RELATIVE)}')
    script = tmp / 'link.ld'
    script.write_text(LINKER_SCRIPT % CODE)
    linked = tmp / 'patch.elf'
    run('ld', '-T', script, '-o', linked, '-e', 'gs_fill_ghost_list',
        *[f'--defsym={name}={address:#x}' for name, address in game.items()], *objects)
    sections = subprocess.run(['readelf', '-SW', linked], capture_output=True, text=True, check=True).stdout
    # [Nr] Name Type Address Off Size ES Flg ...: only .text may take space in memory
    for name, size, flags in re.findall(r'\[\s*\d+\]\s+(\S+)\s+\S+\s+[0-9a-f]+\s+[0-9a-f]+\s+([0-9a-f]+)\s+[0-9a-f]+\s+(\S*)', sections):
        if 'A' in flags and name != '.text' and int(size, 16):
            sys.exit(f'unexpected section {name}: the code segment cannot hold writable data')
    symbols = {}
    for line in subprocess.run(['nm', linked], capture_output=True, text=True, check=True).stdout.splitlines():
        address, _, name = line.split()
        symbols[name] = int(address, 16)
    binary = tmp / 'patch.bin'
    run('objcopy', '-O', 'binary', '-j', '.text', linked, binary)
    return binary.read_bytes(), symbols


def build(title, e):
    elf = e['elf'].read_bytes()
    with tempfile.TemporaryDirectory() as tmp:
        code, symbols = build_code(Path(tmp), title, e['game'])
    if CODE + len(code) > CODE_END:
        sys.exit(f'code is {len(code)} bytes: does not fit before {CODE_END:#x}')
    if read(elf, CODE, len(code)) != bytes(len(code)):
        sys.exit(f'{e["elf"]}: the area at {CODE:#x} is not empty')
    data_end = 0x2a00000 + 0x1ee66d
    if STATE < data_end or STATE + 0x400 > STATE_END - 0x500:   # 0x2beea80-0x2beef80: the ghost spectator's state
        sys.exit('state area is not in the free space after the game data')

    lines = []
    for address, original, opcode, target, padding in e['hooks']:
        original = bytes.fromhex(original)
        if read(elf, address, len(original)) != original:
            sys.exit(f'{e["elf"]}: the code at {address:#x} is not the expected {e["name"]} 1.21 code')
        rel = symbols[target] - (address + 5)
        new = bytes.fromhex(opcode) + rel.to_bytes(4, 'little', signed=True) + b'\x90' * padding
        assert len(new) == len(original), hex(address)
        # Signature: the replaced bytes and 8 bytes on each side, unique in the executable
        signature = read(elf, address - 8, len(original) + 16)
        if elf.count(signature) != 1:
            sys.exit(f'signature at {address:#x} is not unique')
        lines.append((address, new, signature, 8))
    # The port's loader takes at most 4096 bytes per write (src/probe.c, "bad patch entry")
    for at in range(0, len(code), MAX_WRITE):
        lines.append((CODE + at, code[at:at + MAX_WRITE], None, 0))

    def line(va, value, signature, offset):
        sha = hashlib.sha256(read(elf, va, len(value))).hexdigest()
        extra = f' Signature="{signature.hex(" ")}" SignatureOffset="{offset:#x}"' if signature else ''
        return (f'      <Line Type="bytes" Address="{va + EBOOT_BASE:#010x}" Value="{value.hex()}"'
                f'{extra} ExpectedSHA256="{sha}" />')

    xml = f'''<?xml version="1.0" encoding="utf-8"?>
<!-- Built by build.py from src/: edit those, not this file.{" EU edition." if e["name"] == "EU" else ""}
     Ghost sharing: shared ghosts (/data/ghosts/*.ctrghost) as extra entries in the Time Trial ghost
     menu, raced as extra ghosts that count for nothing; a button on your own ghost exports it.
     Every shared file is checked field by field before the game gets any of it; the game's own
     ghost file loader never reads a shared file. The last lines are the new code ({len(code)} bytes). -->
<Patch>
  <TitleID><ID>{title}</ID></TitleID>
  <Metadata Title="Crash Team Racing Nitro-Fueled" Name="Ghost Sharing"
            Note="Race other players' shared ghosts (folder data/ghosts) and export your own from the ghost menu."
            Author="Onur" PatchVer="{VERSION}" AppVer="01.21" AppElf="eboot.bin">
    <PatchList>
{chr(10).join(line(*l) for l in lines)}
    </PatchList>
  </Metadata>
</Patch>
'''
    e['xml'].parent.mkdir(parents=True, exist_ok=True)
    e['xml'].write_text(xml, encoding='utf-8')
    print(f'{e["xml"].relative_to(HERE)}: {len(e["hooks"])} hooks, code {len(code)} bytes at {CODE:#x}')
    if e['test_copy'].parent.is_dir():
        e['test_copy'].write_text(xml.replace('AppElf="eboot.bin">', 'AppElf="eboot.bin" isEnabled="true">'),
                                  encoding='utf-8')
        print(f'test copy, switched on: {e["test_copy"]}')


def eu_package():
    """package-eu/ gets the USA package's README and manifest, with its own id and name"""
    manifest = json.loads((HERE / 'package/mod.json').read_text())
    assert manifest['version'] == VERSION, 'package/mod.json has another version'
    manifest.update(id=manifest['id'] + '-eu', name=manifest['name'] + ' (EU)',
                    patches=['patches/GhostShare-EU.xml'], files=[])
    (HERE / 'package-eu/mod.json').write_text(json.dumps(manifest, indent=2) + '\n')
    shutil.copy(HERE / 'package/README.txt', HERE / 'package-eu/README.txt')
    shutil.copy(HERE / 'package/gamebananapageurl.txt', HERE / 'package-eu/gamebananapageurl.txt')


def main():
    for title, e in EDITIONS.items():
        build(title, e)
    eu_package()


if __name__ == '__main__':
    main()
