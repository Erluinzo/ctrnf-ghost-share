# Shared ghost folder: file I/O from patch code (USA CUSA13795 1.21, OCTR port)

Research 2026-10-28, read-only. ELF addresses of `CTRNF/out/eboot.elf`; patch XML = ELF + 0x400000.
"Verified" = read in source/disassembly; nothing was run in game.

## 1. Guest mounts (`CTRNF/src/runtime_file.c`, `runtime_savedata.c`)
| Guest path | Host folder | Writable |
|---|---|---|
| `/app0`, `/hostapp` (and any path without leading `/` = `/app0/...`) | game dir (`orig/CUSA13795`); mod file map overlays it | no: write/create/trunc/append flags, mkdir, unlink, rename -> EROFS |
| `/temp0`, `/download0`, `/data` | `<user>/temp0`, `<user>/download0`, `<user>/data` (created at start) | yes |
| `/savedata0`..`15` | `<user>/savedata/1/CUSA13795/<dir>` only while the game has it mounted (`sceSaveDataMount`) | yes, via temp copy + rename on close |

No other mounts; anything else -> ENOENT. Mount match = longest prefix ending at `/` or end; max 16 mounts.

`<user>` = `--user` = `BB_USER_DIR`, default `<data>/user`, `<data>` = `BB_DATA_DIR` or the port dir:
- Normal run: `/home/neox/Desktop/CTRNF/user` (launcher "Saves folder" setting empty).
- Mod session (`scripts/mod_packages.py` `prepare`, active whenever a `Mod:` package is enabled; the owner's
  `patches.json` has 3, so this is the owner's normal case): `<user>` = `mod-state/sessions/<uuid>/user`,
  a fresh copy of `mod-state/user` made at launch. After exit code 0 only `savedata/` is synced back to
  `mod-state/user/savedata` (whole tree replaced). `/data`, `/temp0`, `/download0` writes stay in the session
  folder; sessions beyond the newest 3 are deleted. `copy_tree` raises "Linked input is unsupported" on
  any symlink in `mod-state/user`, so a symlink there breaks mod launches.

## 2. Runtime behaviour
- Implemented: open/close/read/pread/write/pwrite/lseek/fstat/stat/getdents/getdirentries/mkdir/rmdir/
  unlink/rename/ftruncate/truncate/fsync/access (`exports[]`, end of `runtime_file.c`). Directories open
  as listings (`O_DIRECTORY` 0x20000 or a plain open of a dir).
- Listing: host `readdir`, so `.` and `..` ARE returned; `*.bbtmp` names are hidden. Record = FreeBSD
  dirent: u32 ino, u16 reclen, u8 type (4 dir, 8 file, 10 link), u8 namlen, name + NUL, 8-aligned.
  Buffer must be >= 512 bytes (else EINVAL); returns bytes, 0 at end.
- Open flags (PS4): RDONLY 0, WRONLY 1, RDWR 2, APPEND 8, CREAT 0x200, TRUNC 0x400, EXCL 0x800, DIRECTORY 0x20000.
- Path checks: any `..` component between `/` (or start/end) -> EACCES; no normalising. Prefix match
  needs a `/` boundary. Linux: `\` is an ordinary name char, so no escape. Windows build only:
  `..\` is NOT caught (check looks for `/` only) -> patch code must refuse names with `\ / :` or a leading `.`.
  Host symlinks inside the folder are followed (only the user can make them).
- Atomic writes only for `/savedataN`. A `/data` write is direct: crash mid-write = partial file.
  Write `<name>.bbtmp` then `sceKernelRename` (that suffix is also hidden from listings).
- Case: on a miss (read, not create) the host path is matched ignoring case (`fix_case`).
- Errors: `sceKernel*` return `0x8002xxxx` (negative as int32/int64), xxxx = FreeBSD errno
  (ENOENT 2, EACCES 0xd, EEXIST 0x11, EROFS 0x1e, ENAMETOOLONG 0x3f).

## 3. Callable functions in the game
Imports are bound by writing the runtime function's address into the GOT slot (`out/boot.bin`
relocations; `src/probe.c` ~1145). The image is relocatable (not fixed at 0x400000): patch code must
call the PLT stub with `call rel32` (`e8`), or `call [rip+GOT]` (`ff 15`). Patch bytes may not overlap
a GOT slot. SysV ABI: args rdi, rsi, rdx, rcx; result rax; rax, rcx, rdx, rsi, rdi, r8-r11, xmm0-15
clobbered; rsp 16-aligned at the call.

| Function (args) | PLT stub | GOT slot |
|---|---|---|
| sceKernelOpen(path, flags, mode) -> fd | 0x1beab78 | 0x2808928 |
| sceKernelRead(fd, buf, n) | 0x1beaeb8 | 0x2808ac8 |
| sceKernelPread(fd, buf, n, off) | 0x1bea7b8 | 0x2808748 |
| sceKernelPwrite(fd, buf, n, off) | 0x1bea868 | 0x28087a0 |
| sceKernelClose(fd) | 0x1beaa38 | 0x2808888 |
| sceKernelLseek(fd, off, whence) | 0x1beae78 | 0x2808aa8 |
| sceKernelStat(path, st*) | 0x1bea7f8 | 0x2808768 |
| sceKernelFstat(fd, st*) | 0x1beac08 | 0x2808970 |
| sceKernelGetdents(fd, buf, n) | 0x1beaa18 | 0x2808878 |
| sceKernelMkdir(path, mode) | 0x1beaad8 | 0x28088d8 |
| sceKernelRename(from, to) | 0x1beaae8 | 0x28088e0 |
| sceKernelUnlink(path) | 0x1beaab8 | 0x28088c8 |
| sceKernelRmdir(path) | 0x1bea7a8 | 0x2808740 |
| sceKernelFtruncate(fd, len) | 0x1bea828 | 0x2808780 |

`sceKernelWrite` is not imported: use `sceKernelPwrite` with a running offset.
Stat (120 bytes): mode u16 @+0x08 (dir 0x4000), mtime @+0x28, size i64 @+0x48.
libc (native, linked in) also has fopen PLT 0x1be90f8, fread 0x1be9a28, fwrite 0x1be9078, fclose
0x1be90e8 (NIDs match; that they reach the runtime's open/write is unverified).

How the game does it: the Alchemy engine's PS4 file device workers (args: device, request; request
+0x10 = native path, +0x18 handle (fd @+0x30), +0x20 buffer, +0x28 offset, +0x30 size, +0x50 mode bits)
- 0x14d0350 open: `sceKernelOpen(path, flags, 0x1ff)`, flags from +0x50: bits 0+1 -> 0x202, bit 1 only -> 0x601, else 0; then fstat if bit 0
- 0x14d0480 read = pread, 0x14d04d0 write = pwrite, 0x14d0440 close, 0x14d02e0 stat,
  0x14d0560 mkdir(path, 0x1ff), 0x14d06d0 unlink, 0x14d0710 rename
- 0x14d0800 list dir: `sceKernelOpen(dir, 0x20000, 0x16d)`, fstat, `sceKernelGetdents(fd, buf, size)` loop
- error map 0x14d07a0. Path prefixes the engine treats as native (0x14c6820, strings at 0x1d8f699):
  `/app0`, `/data`, `mem:`, `ram:`, `host:`.
These run behind the engine's request queue (igFileContext); calling them directly needs a request
object: not worth it. Ghost data: loader 0xf9bee0 (log "%s: loadGhostData:(%d-%s)"); the challenge
ghosts' `data:\Ghosts\...igb` and `ram:/tmpsavefile.igb` (0xc2fb40, igb serialised to memory) go
through the engine resource layer, not mapped. Unverified idea: since `/data` is a native prefix,
the engine loader might accept `/data/ghosts/x.igb` directly; test with `BB_FILE_TRACE=1`.

## 4. Recommended folder
Guest path for patch code: `/data/ghosts/` (absolute, `/` separators).
- Normal run: host `/home/neox/Desktop/CTRNF/user/data/ghosts` (git-ignored `user/`, survives
  `git pull` and rebuilds; works today, no change).
- Mod session today: reads see a launch-time copy of `mod-state/user/data/ghosts`; writes go to
  `mod-state/sessions/<uuid>/user/data/ghosts` and are lost later. Not one shared folder.
- Fix (needs a change in CTRNF, not done): mount `/data/ghosts` on the normal-run folder in mod sessions
  too. E.g. `mod_packages.prepare` sets `BB_GHOSTS_DIR=str(original_user/'data'/'ghosts')` before it
  replaces `BB_USER_DIR`; `runtime_file_configure` does `mkdir` + `runtime_file_mount("/data/ghosts", dir)`
  when it is set (longest prefix wins over `/data`). Then one host folder, `<normal user>/data/ghosts`,
  for both. Local edits must be kept across `git pull` or sent upstream.
- No-change alternatives fail: `/app0` is read-only; `/savedataN` is mounted only during saves and its
  mod-session sync replaces the whole tree; symlinks in `mod-state/user` break mod launches.

## 5. Limits
- Guest path <= 1023 bytes; host path <= 1023 (ENAMETOOLONG); mount host <= 511; names in listings <= 255.
- 1024 descriptors shared with the game: always close.
- Calls are synchronous host syscalls (blocking); one runtime mutex held briefly. A few KB of ghost data
  is fine on the game thread at a menu; avoid big loops mid-race. Runtime C code uses ~6 KB of the
  calling thread's stack (path buffers).
- Same PLT stubs the game's own threads use, so any game thread may call them (the engine calls them
  from its file worker thread; main-thread use is unverified but nothing in the runtime is thread-bound).
- `/data` is port-only: a real PS4 has no such mount for retail games.
