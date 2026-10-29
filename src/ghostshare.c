/* Ghost sharing: runs inside the game (CTR Nitro-Fueled 1.21, USA CUSA13795 or EU CUSA14876), called from the hooks in hooks.s.
 *
 * - Ghost menu: shared ghosts for this track (files in /data/ghosts) are added as challenge-ghost
 *   entries that show the sharer's name.
 * - Race start: chosen shared ghosts are taken out of the game's own selection list, so the game's
 *   file loader and its unlock rules never see them. Each file is then read again, checked value by
 *   value, built into a ghost in memory and added as an extra racer.
 * - Export: a button on your own ghost in the menu writes it to a save data folder of its own
 *   (EXPORT_DIR). Saves are the only files the port keeps after a game with mod packages.
 *   While your own ghost is focused, the menu's button bar shows the export button.
 *
 * Code and data addresses of the game come from build.py (--defsym). The image is not loaded at a
 * fixed address, so all of them are reached RIP-relative (hidden symbols, -fpie). The code segment
 * is read-only: the only writable state is `gs`, in unused space after the game's data.
 */
#include <stddef.h>
#include <stdint.h>
#include "share_format.h"

#define GAME __attribute__((visibility("hidden")))

/* Game code */
extern void *game_ghost_new(int pool) GAME;                                  /* CGhost */
extern void *game_move_key_new(int pool) GAME;                               /* CGhostMoveKey */
extern void *game_input_key_new(int pool) GAME;                              /* CGhostSnapshotKey */
extern void game_header_meta(void) GAME;                                     /* registers CChallengeGhostHeaderData */
extern void *game_create(void *meta, int pool, int zero) GAME;
extern void game_release(void *object) GAME;
extern void game_list_set_count(void *list, int count, int item_size) GAME;
extern void game_list_reserve(void *list, int capacity, int item_size) GAME;
extern char *game_string(void *pool, const char *text) GAME;                 /* new reference */
extern void game_string_release(void *pool, char *header) GAME;
extern void game_fill_challenge_ghosts(const char *level, void **list) GAME;
extern void game_send_event(void *target, void *event) GAME;
extern void game_spawn_ghost(void *racers, const char *driver, const char *kart, void *ghost, int is_player) GAME;
extern void *game_find_driver(void *drivers, const char *name) GAME;
extern void *game_find_kart(void *karts, const char *name) GAME;
extern void *game_saved_ghost(const char *level) GAME;
extern void *game_current_zone(void *zones) GAME;
/* Opens the game's notice popup (CDialogBoxInfo in "Octane_YesNoDialog"); Cross closes it */
extern void game_open_dialog(void **handle, void *gui, char **title, char **body, void *user_data,
                             void *on_close, int a, int b) GAME;
extern void game_handle_free(void **handle) GAME;
/* Adds a button to the button bar of a GUI project (addButtonToLegend_VSC) */
extern void game_legend_add(void *project, int button, char **text, int always) GAME;
/* PS4 system calls (the game's import stubs); errors are negative */
extern int sce_open(const char *path, int flags, int mode) GAME;
extern int64_t sce_pread(int fd, void *buffer, uint64_t size, int64_t offset) GAME;
extern int64_t sce_pwrite(int fd, const void *buffer, uint64_t size, int64_t offset) GAME;
extern int sce_close(int fd) GAME;
extern int sce_fstat(int fd, void *stat) GAME;
extern int64_t sce_getdents(int fd, char *buffer, uint64_t size) GAME;
extern int sce_unlink(const char *path) GAME;
extern int sce_initial_user(int *user) GAME;
extern int sce_user_name(int user, char *name, uint64_t size) GAME;
extern int sce_save_mount2(const void *mount, void *result) GAME;
extern int sce_save_umount(const void *point) GAME;
/* Game data */
extern void *g_string_pool GAME;
extern char *g_racer_manager GAME;
extern void *g_zone_system GAME;
extern void *g_gui_manager GAME;
extern void *g_header_meta GAME;
extern const char g_default_level[] GAME;
extern const char game_list_vtable[] GAME;                                  /* igGuiList */

#define O_READ 0
#define O_WRITE_NEW 0x601   /* write, create, truncate */
#define O_DIRECTORY 0x20000

#define FOLDER "/data/ghosts"
/* Save data folder for exports: <user>/savedata/<user id>/<TITLE_ID>/GhostShare (TITLE_ID, the
 * game edition, is set by build.py). The game opens
 * its own saves by exact name (savedata0, savedata1), so it never reads this one. */
#define EXPORT_DIR "GhostShare"
#define MOUNT_RDWR_CREATE 0x22   /* RDWR | CREATE2 (create if missing) */
#define MOUNT_BLOCKS 0x60        /* the smallest size the game asks for its own saves */
#define LEGEND_R1 6              /* EButtonLegendButton; must match EXPORT_SIGNAL */
#define MAX_SHARED 6        /* the game races at most 8 karts */
#define LIST_BOTTOM_MARGIN 32.5f
/* A path the game cannot open: if a shared entry ever reached the game's own loader, it fails. */
#define NO_FILE "data:\\Ghosts\\shared_ghost_is_not_a_game_file.igb"

struct shared {
    void *header;           /* our CChallengeGhostHeaderData (we hold one reference) */
    char file[64];
    char player[PLAYER_SIZE];
    uint8_t chosen;
};

struct state {
    char level[LEVEL_SIZE]; /* canonical name of the level in the ghost menu */
    int count;
    struct shared shared[MAX_SHARED];
    /* For tests and bug reports (tools/peek.py reads them from the running game) */
    int last_signal;        /* last button signal on a ghost entry, other than Select */
    int export_result;      /* EXPORT_* of the last export */
    char export_file[64];   /* file name of the last export */
};
enum { EXPORT_NONE, EXPORT_OK, EXPORT_NO_LEVEL, EXPORT_NO_GHOST, EXPORT_BAD_GHOST, EXPORT_OPEN_FAILED,
       EXPORT_WRITE_FAILED, EXPORT_MOUNT_FAILED };
_Static_assert(sizeof(struct state) <= 0x400, "state must fit 0x2bee680-0x2beea80 (the ghost spectator uses the rest)");
extern struct state gs GAME;

/* Field access on game objects */
#define AT(object, offset, type) (*(type *)((char *)(object) + (offset)))

static void copy_text(char *out, const char *in, int size)
{
    int n = 0;
    for (; in[n] && n < size - 1; n++)
        out[n] = in[n];
    for (; n < size; n++)
        out[n] = 0;
}

static int same_text(const char *a, const char *b)
{
    while (*a && *a == *b) a++, b++;
    return *a == *b;
}

/* Game objects keep a reference count at +8. */
static void add_ref(void *object) { __atomic_fetch_add(&AT(object, 8, int32_t), 1, __ATOMIC_SEQ_CST); }

/* igObjectList: +0xc count, +0x10 capacity, +0x20 items. Same steps as the game's own appends. */
static void list_append(void *list, void *object)
{
    int count = AT(list, 0xc, int32_t);
    add_ref(object);
    if (count >= AT(list, 0x10, int32_t)) game_list_set_count(list, count + 1, 8);
    else AT(list, 0xc, int32_t) = count + 1;
    AT(list, 0x20, void **)[count] = object;
}

static void list_remove(void *list, void *object)
{
    int count = AT(list, 0xc, int32_t);
    void **items = AT(list, 0x20, void **);
    for (int i = 0; i < count; i++)
        if (items[i] == object) {
            for (int j = i; j < count - 1; j++)
                items[j] = items[j + 1];
            AT(list, 0xc, int32_t) = count - 1;
            game_release(object);
            return;
        }
}

static void set_string(void *object, int offset, const char *text)
{
    char *old = AT(object, offset, char *);
    AT(object, offset, char *) = game_string(g_string_pool, text);
    if (old) game_string_release(g_string_pool, old - 0x10);
}

static int64_t file_size(int fd)
{
    uint8_t stat[120];
    if (sce_fstat(fd, stat) < 0) return -1;
    return AT(stat, 0x48, int64_t);
}

/* Opens a shared file and checks its header, size, level and names. Returns the fd, or -1. */
static int open_shared(const char *file, const char *level, struct share_header *h)
{
    char path[sizeof FOLDER + 64];
    copy_text(path, FOLDER "/", sizeof path);
    copy_text(path + sizeof FOLDER, file, 64);
    int fd = sce_open(path, O_READ, 0);
    if (fd < 0) return -1;
    if (sce_pread(fd, h, sizeof *h, 0) == sizeof *h && share_check_header(h) == SHARE_OK
        && file_size(fd) == (int64_t)share_file_size(h) && same_text(h->level, level)
        && game_find_driver(AT(g_racer_manager, 0x18, void *), h->driver)
        && game_find_kart(AT(g_racer_manager, 0x20, void *), h->kart))
        return fd;
    sce_close(fd);
    return -1;
}

static void forget_shared(void)
{
    for (int i = 0; i < gs.count; i++)
        game_release(gs.shared[i].header);
    gs.count = 0;
}

/* The ghost menu's list never scrolls (focus scroll mode "none"), so entries after the 4 challenge
 * ghosts would stay hidden under the button bar. With shared ghosts it scrolls just enough to show
 * the focused entry; the bottom margin keeps that entry above the bar (the game's value is 2.5). */
static void let_list_scroll(void *widget)
{
    if (!widget || AT(widget, 0, const void *) != game_list_vtable) return;
    AT(widget, 0x74, int32_t) = 1;          /* _focusScrollMode: kFocusScrollToFit */
    AT(widget, 0x4c, float) = LIST_BOTTOM_MARGIN;
}

/* Called instead of the game's "add challenge ghosts" step when the ghost menu is filled
 * (widget: the menu's igGuiList, from hooks.s). */
void gs_fill_ghost_list(const char *level, void **list, void *widget)
{
    game_fill_challenge_ghosts(level, list);
    forget_shared();
    char name[LEVEL_SIZE];
    gs.level[0] = 0;    /* no export for a menu whose level we do not know */
    if (!list || !*list || share_level_name(level, name) != SHARE_OK) return;
    copy_text(gs.level, name, LEVEL_SIZE);

    int dir = sce_open(FOLDER, O_DIRECTORY, 0);
    if (dir < 0) return;
    char buffer[2048];
    int64_t n;
    while (gs.count < MAX_SHARED && (n = sce_getdents(dir, buffer, sizeof buffer)) > 0) {
        if (n > (int64_t)sizeof buffer) break;
        /* Each record: u32 id, u16 record length, u8 type, u8 name length, name at +8 */
        for (int64_t at = 0; at + 8 <= n && gs.count < MAX_SHARED;) {
            uint16_t length = AT(buffer + at, 4, uint16_t);
            uint8_t name_length = AT(buffer + at, 7, uint8_t);
            if (length < 8 || at + length > n || 8 + name_length > length) break;
            const char *name = buffer + at + 8;
            at += length;
            if (!share_file_name_ok(name, name_length)) continue;

            struct shared *s = &gs.shared[gs.count];
            copy_text(s->file, "", sizeof s->file);
            for (int i = 0; i < name_length; i++)
                s->file[i] = name[i];
            struct share_header h;
            int fd = open_shared(s->file, gs.level, &h);
            if (fd < 0) continue;
            sce_close(fd);

            game_header_meta();
            void *header = game_create(g_header_meta, 0, 0);
            if (!header) break;
            set_string(header, 0x10, h.kart);
            set_string(header, 0x18, h.driver);
            AT(header, 0x20, float) = h.time;
            set_string(header, 0x28, NO_FILE);
            copy_text(s->player, h.player, sizeof s->player);
            s->header = header;
            s->chosen = 0;
            gs.count++;
            list_append(*list, header);
        }
    }
    sce_close(dir);
    if (gs.count) let_list_scroll(widget);
}

static struct shared *find_shared(void *header)
{
    for (int i = 0; header && i < gs.count; i++)
        if (gs.shared[i].header == header) return &gs.shared[i];
    return 0;
}

/* Called instead of sending a ghost entry's setup event: shows the sharer's name. */
void gs_send_entry_setup(void *target, void *event, void *behavior)
{
    struct shared *s = find_shared(AT(behavior, 0x50, void *));
    if (s) set_string(event, 0x20, s->player);
    game_send_event(target, event);
}

/* Race start, before the game loads the chosen challenge ghosts. */
void gs_take_chosen(void *manager)
{
    void *chosen = AT(manager, 0x50, void *);
    for (int i = 0; chosen && i < gs.count; i++) {
        struct shared *s = &gs.shared[i];
        int count = AT(chosen, 0xc, int32_t);
        void **items = AT(chosen, 0x20, void **);
        for (int j = 0; j < count; j++)
            if (items[j] == s->header) {
                s->chosen = 1;
                list_remove(chosen, s->header);
                break;
            }
    }
}

/* Reads the keys of an open, checked file into a new ghost. Returns 0 if any key is not valid. */
static void *build_ghost(int fd, const struct share_header *h)
{
    void *ghost = game_ghost_new(0);
    if (!ghost) return 0;
    AT(ghost, 0xc, int32_t) = 3;            /* _version */
    set_string(ghost, 0x18, h->kart);
    set_string(ghost, 0x20, h->driver);
    AT(ghost, 0x28, float) = h->time;
    AT(ghost, 0x48, int32_t) = -1;          /* _playerId: set when it gets a racer slot */

    void *moves = AT(ghost, 0x30, void *), *inputs = AT(ghost, 0x38, void *);
    game_list_reserve(moves, h->move_count, 8);
    game_list_reserve(inputs, h->input_count, 8);

    uint8_t buffer[SHARE_MOVE_SIZE * 100];  /* 100 keys of either kind per read */
    int64_t at = SHARE_HEADER_SIZE;
    int32_t last = -1;
    for (uint32_t done = 0; done < h->move_count;) {
        uint32_t n = h->move_count - done < 100 ? h->move_count - done : 100;
        if (sce_pread(fd, buffer, n * SHARE_MOVE_SIZE, at) != n * SHARE_MOVE_SIZE) goto bad;
        for (uint32_t i = 0; i < n; i++) {
            struct share_move m;
            __builtin_memcpy(&m, buffer + i * SHARE_MOVE_SIZE, sizeof m);
            if (share_check_move(&m, &last) != SHARE_OK) goto bad;
            void *key = game_move_key_new(0);
            if (!key) goto bad;
            for (int k = 0; k < 3; k++)
                AT(key, 0xc + 4 * k, float) = m.position[k];
            AT(key, 0x18, uint16_t) = m.time;
            for (int k = 0; k < 3; k++)
                AT(key, 0x1a + 2 * k, int16_t) = m.angle[k];
            list_append(moves, key);
            game_release(key);
        }
        done += n;
        at += n * SHARE_MOVE_SIZE;
    }
    last = -1;
    for (uint32_t done = 0; done < h->input_count;) {
        uint32_t n = h->input_count - done < 100 ? h->input_count - done : 100;
        if (sce_pread(fd, buffer, n * SHARE_INPUT_SIZE, at) != n * SHARE_INPUT_SIZE) goto bad;
        for (uint32_t i = 0; i < n; i++) {
            struct share_input k;
            __builtin_memcpy(&k, buffer + i * SHARE_INPUT_SIZE, sizeof k);
            if (share_check_input(&k, &last) != SHARE_OK) goto bad;
            void *key = game_input_key_new(0);
            if (!key) goto bad;
            AT(key, 0xc, uint16_t) = k.bits;
            AT(key, 0xe, uint16_t) = k.time;
            list_append(inputs, key);
            game_release(key);
        }
        done += n;
        at += n * SHARE_INPUT_SIZE;
    }
    return ghost;
bad:
    game_release(ghost);
    return 0;
}

/* Race start, after the game's own ghosts: adds the chosen shared ghosts as extra racers. */
void gs_add_chosen(void *manager)
{
    void *zone = game_current_zone(g_zone_system);
    const char *name = zone && AT(zone, 0x10, const char *) ? AT(zone, 0x10, const char *) : g_default_level;
    char level[LEVEL_SIZE];
    if (share_level_name(name, level) != SHARE_OK) return;

    for (int i = 0; i < gs.count; i++) {
        struct shared *s = &gs.shared[i];
        if (!s->chosen) continue;
        struct share_header h;
        int fd = open_shared(s->file, level, &h);
        if (fd < 0) continue;
        void *ghost = build_ghost(fd, &h);
        sce_close(fd);
        if (!ghost) continue;
        void *playing = AT(manager, 0x40, void *);
        if (!playing) {
            game_release(ghost);
            return;
        }
        list_append(playing, ghost);
        game_spawn_ghost(g_racer_manager, AT(ghost, 0x20, char *), AT(ghost, 0x18, char *), ghost, 0);
        if (AT(ghost, 0x48, int32_t) < 0) list_remove(playing, ghost);   /* no free racer slot */
        game_release(ghost);
    }
}

/* Writes "<track>_<m>m<ss>s<cc>_<player>.ctrghost" from the level, time and player name. */
static void export_name(char *out, int size, const struct share_header *h)
{
    const char *track = h->level;
    for (const char *p = h->level; *p; p++)
        if (*p == '/') track = p + 1;
    int hundredths = (int)(h->time * 100.0f + 0.5f);
    char time[12] = {'0' + hundredths / 6000 % 10, 'm', '0' + hundredths / 1000 % 6, '0' + hundredths / 100 % 10, 's',
                     '0' + hundredths / 10 % 10, '0' + hundredths % 10, 0};
    int n = 0;
    for (const char *p = track; *p && n < 24; p++)
        out[n++] = *p;
    out[n++] = '_';
    for (const char *p = time; *p; p++)
        out[n++] = *p;
    out[n++] = '_';
    for (const char *p = h->player; *p && n < size - 10 && n < 50; p++) {
        char c = *p;
        int ok = (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '-';
        out[n++] = ok ? c : '_';
    }
    copy_text(out + n, ".ctrghost", size - n);
}

/* Writes your saved ghost of the menu's level to the export save folder. Returns EXPORT_*. */
static int export_own_ghost(void)
{
    if (!gs.level[0]) return EXPORT_NO_LEVEL;
    void *ghost = game_saved_ghost(gs.level);
    if (!ghost || AT(ghost, 0xc, int32_t) != 3) return EXPORT_NO_GHOST;
    void *moves = AT(ghost, 0x30, void *), *inputs = AT(ghost, 0x38, void *);
    const char *driver = AT(ghost, 0x20, const char *), *kart = AT(ghost, 0x18, const char *);
    if (!moves || !inputs || !driver || !kart) return EXPORT_BAD_GHOST;

    struct share_header h;
    __builtin_memset(&h, 0, sizeof h);
    __builtin_memcpy(h.magic, SHARE_MAGIC, 8);
    h.version = SHARE_VERSION;
    h.header_size = SHARE_HEADER_SIZE;
    h.move_count = AT(moves, 0xc, uint32_t);
    h.input_count = AT(inputs, 0xc, uint32_t);
    h.time = AT(ghost, 0x28, float);
    int user = 0;
    if (sce_initial_user(&user) < 0) return EXPORT_MOUNT_FAILED;
    char name[PLAYER_SIZE] = {0};
    if (sce_user_name(user, name, sizeof name - 1) < 0) name[0] = 0;
    share_player_name(name, h.player);
    copy_text(h.level, gs.level, LEVEL_SIZE);
    copy_text(h.driver, driver, NAME_SIZE);
    copy_text(h.kart, kart, NAME_SIZE);
    if (share_check_header(&h) != SHARE_OK) return EXPORT_BAD_GHOST;   /* never write a file we would refuse */

    /* OrbisSaveDataMount2 and OrbisSaveDataMountResult (64 bytes each; the result starts with the
     * mount point, e.g. "/savedata2") */
    struct { int32_t user, pad; const char *dir; uint64_t blocks; uint32_t mode; uint8_t reserved[36]; } mount;
    struct { char point[16]; uint8_t rest[48]; } result;
    _Static_assert(sizeof mount == 64 && sizeof result == 64, "PS4 save data mount layouts");
    char dir[32] = EXPORT_DIR;
    __builtin_memset(&mount, 0, sizeof mount);
    __builtin_memset(&result, 0, sizeof result);
    mount.user = user;
    mount.dir = dir;
    mount.blocks = MOUNT_BLOCKS;
    mount.mode = MOUNT_RDWR_CREATE;
    if (sce_save_mount2(&mount, &result) < 0) return EXPORT_MOUNT_FAILED;
    result.point[15] = 0;

    char file[64], path[16 + 1 + 64];
    export_name(file, sizeof file, &h);
    copy_text(path, result.point, sizeof path);
    int length = 0;
    while (path[length]) length++;
    path[length++] = '/';
    copy_text(path + length, file, sizeof path - length);
    /* The port writes save files to a copy and puts it in place at close: no half-written file */
    int fd = sce_open(path, O_WRITE_NEW, 0666);
    if (fd < 0) {
        sce_save_umount(result.point);
        return EXPORT_OPEN_FAILED;
    }

    int ok = sce_pwrite(fd, &h, sizeof h, 0) == sizeof h;
    int64_t at = sizeof h;
    int32_t last = -1;
    void **items = AT(moves, 0x20, void **);
    for (uint32_t i = 0; ok && i < h.move_count; i++) {
        struct share_move m;
        for (int k = 0; k < 3; k++)
            m.position[k] = AT(items[i], 0xc + 4 * k, float);
        m.time = AT(items[i], 0x18, uint16_t);
        for (int k = 0; k < 3; k++)
            m.angle[k] = AT(items[i], 0x1a + 2 * k, int16_t);
        ok = share_check_move(&m, &last) == SHARE_OK && sce_pwrite(fd, &m, sizeof m, at) == sizeof m;
        at += sizeof m;
    }
    last = -1;
    items = AT(inputs, 0x20, void **);
    for (uint32_t i = 0; ok && i < h.input_count; i++) {
        struct share_input k = {AT(items[i], 0xc, uint16_t), AT(items[i], 0xe, uint16_t)};
        ok = share_check_input(&k, &last) == SHARE_OK && sce_pwrite(fd, &k, sizeof k, at) == sizeof k;
        at += sizeof k;
    }
    sce_close(fd);
    if (!ok) sce_unlink(path);
    sce_save_umount(result.point);
    if (ok) copy_text(gs.export_file, file, sizeof gs.export_file);
    return ok ? EXPORT_OK : EXPORT_WRITE_FAILED;
}

/* Adds text at the end of out (size bytes, always ends with 0) */
static void add_text(char *out, int size, const char *text)
{
    int n = 0;
    while (out[n]) n++;
    copy_text(out + n, text, size - n);
}

/* Shows the game's notice popup, as its team select screen does (0x9c289e) */
static void show_popup(const char *title_text, const char *body_text)
{
    if (!g_gui_manager) return;
    char *title = game_string(g_string_pool, title_text);
    char *body = game_string(g_string_pool, body_text);
    void *handle = 0;
    game_open_dialog(&handle, g_gui_manager, &title, &body, 0, 0, 5, -2);
    if (handle) {   /* the popup keeps its own reference; drop ours as the game does */
        uint32_t old = __atomic_fetch_add((uint32_t *)handle, -1, __ATOMIC_SEQ_CST);
        if ((old & 0xffff) == ((old & 0x90000000) ? 3u : 2u)) game_handle_free(&handle);
    }
    game_string_release(g_string_pool, title - 0x10);
    game_string_release(g_string_pool, body - 0x10);
}

/* Tells the player where the exported file is and how to share it, or why there is none */
static void show_export_result(int result)
{
    char body[600] = {0};
    if (result == EXPORT_OK) {
        int user = 1;
        sce_initial_user(&user);
        char number[12] = {0};
        int n = 0;
        for (int u = user < 0 ? 0 : user; n == 0 || u; u /= 10)
            n++;
        for (int i = n - 1, u = user < 0 ? 0 : user; i >= 0; i--, u /= 10)
            number[i] = (char)('0' + u % 10);
        /* With mod packages the game runs in a session folder (mod-state/sessions/<id>/user), which the
         * launcher copies to mod-state/user/savedata only when the game closes normally
         * (scripts/mod_packages.py finish), and deletes after a few launches. Every folder the game
         * can write to is inside it, so the file is there at once, and nowhere else until then. */
        char folder[64] = "savedata/";
        add_text(folder, sizeof folder, number);
        add_text(folder, sizeof folder, "/" TITLE_ID "/GhostShare");
        add_text(body, sizeof body, gs.export_file);
        add_text(body, sizeof body, "\n\nIn your OCTR folder, now: mod-state/sessions/(newest folder)/user/");
        add_text(body, sizeof body, folder);
        add_text(body, sizeof body, "\nAfter you close the game normally: mod-state/user/");
        add_text(body, sizeof body, folder);
        add_text(body, sizeof body, "\nWithout mod packages: user/");
        add_text(body, sizeof body, folder);
        add_text(body, sizeof body, "\n\nSend this file to anyone. They put it in mod-state/user/data/ghosts "
                 "(without mod packages: user/data/ghosts) and choose your ghost in this track's ghost menu.");
        show_popup("Ghost exported", body);
        return;
    }
    add_text(body, sizeof body,
             result == EXPORT_NO_LEVEL || result == EXPORT_NO_GHOST ? "You have no saved ghost for this track yet."
             : result == EXPORT_BAD_GHOST ? "Your saved ghost for this track could not be read."
             : "The file could not be written.");
    show_popup("Ghost not exported", body);
}

/* A ghost menu entry gets (gained = 1) or loses focus. While your own ghost is focused, the button
 * bar shows the export button. placeable = the entry's GUI placeable (+0x20: the menu's project). */
void gs_entry_focus(void *behavior, void *placeable, int gained)
{
    if (!behavior || !placeable || !AT(behavior, 0x4d, uint8_t) || !g_gui_manager) return;
    void *project = AT(placeable, 0x20, void *);
    if (!project) return;
    if (gained) {
        char *text = game_string(g_string_pool, "Export ghost");
        game_legend_add(project, LEGEND_R1, &text, 1);
        game_string_release(g_string_pool, text - 0x10);
        return;
    }
    /* As removeButtonFromLegend_VSC (0x110bcb0): the GUI manager's remove event, sent to the project */
    void *event = AT(g_gui_manager, 0xf0, void *);
    if (!event) return;
    AT(event, 0x18, int32_t) = LEGEND_R1;
    typedef void handler(void *project, void *event);
    AT(*(void **)project, 0xb0, handler *)(project, event);
}

/* Any button other than Select on a ghost menu entry; own = it is your own ghost's entry. */
void gs_entry_button(int signal, int own)
{
    gs.last_signal = signal;
    if (signal != EXPORT_SIGNAL || !own) return;
    gs.export_result = export_own_ghost();
    show_export_result(gs.export_result);
}
