/* Checks for shared ghost files (see share_format.h). No game calls here, so the same code also
 * runs in the PC tests and the fuzzer. */
#include "share_format.h"

/* Text field: 1..size-1 allowed characters, a 0 byte, then only 0 bytes. */
static int text_ok(const char *s, int size, int (*allowed)(char c, int at))
{
    int n = 0;
    while (n < size && s[n])
        if (!allowed(s[n], n)) return 0;
        else n++;
    if (n == 0 || n == size) return 0;
    for (int i = n; i < size; i++)
        if (s[i]) return 0;
    return 1;
}

static int player_char(char c, int at) { return c > ' ' && c < 0x7f ? 1 : c == ' ' && at > 0; }
static int id_char(char c, int at)
{
    (void)at;
    return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '_';
}
static int level_char(char c, int at)
{
    return (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '_' || (c == '/' && at > 0);
}

/* NaN fails both comparisons. */
static int in_range(float v, float low, float high) { return v >= low && v <= high; }

int share_check_header(const struct share_header *h)
{
    const char *magic = SHARE_MAGIC;
    for (int i = 0; i < 8; i++)
        if (h->magic[i] != magic[i]) return SHARE_BAD_MAGIC;
    if (h->version != SHARE_VERSION || h->header_size != SHARE_HEADER_SIZE) return SHARE_BAD_VERSION;
    if (h->move_count < MIN_MOVES || h->move_count > MAX_MOVES) return SHARE_BAD_COUNT;
    if (h->input_count < MIN_INPUTS || h->input_count > MAX_INPUTS) return SHARE_BAD_COUNT;
    if (!in_range(h->time, 0.01f, MAX_TIME)) return SHARE_BAD_TIME;
    if (h->reserved) return SHARE_BAD_RESERVED;
    if (!text_ok(h->player, PLAYER_SIZE, player_char)) return SHARE_BAD_PLAYER;
    if (!text_ok(h->level, LEVEL_SIZE, level_char)) return SHARE_BAD_LEVEL;
    for (int i = 1; h->level[i]; i++)
        if (h->level[i] == '/' && h->level[i - 1] == '/') return SHARE_BAD_LEVEL;
    if (!text_ok(h->driver, NAME_SIZE, id_char)) return SHARE_BAD_DRIVER;
    if (!text_ok(h->kart, NAME_SIZE, id_char)) return SHARE_BAD_KART;
    return SHARE_OK;
}

uint64_t share_file_size(const struct share_header *h)
{
    return SHARE_HEADER_SIZE + (uint64_t)h->move_count * SHARE_MOVE_SIZE + (uint64_t)h->input_count * SHARE_INPUT_SIZE;
}

int share_check_move(const struct share_move *m, int32_t *last)
{
    for (int i = 0; i < 3; i++)
        if (!in_range(m->position[i], -MAX_POSITION, MAX_POSITION)) return SHARE_BAD_POSITION;
    /* Times never go back. Equal neighbours are normal (a high frame rate records several keys in one
     * hundredth of a second); playback (0xfce6a0) only uses a pair with a.time <= now < b.time. */
    if ((int32_t)m->time < *last) return SHARE_BAD_KEY_TIME;
    *last = m->time;
    return SHARE_OK;
}

int share_check_input(const struct share_input *k, int32_t *last)
{
    if (k->bits & ~INPUT_BITS) return SHARE_BAD_INPUT_BITS;
    if ((int32_t)k->time < *last) return SHARE_BAD_KEY_TIME;
    *last = k->time;
    return SHARE_OK;
}

int share_level_name(const char *level, char out[LEVEL_SIZE])
{
    int n = 0;
    for (; level[n]; n++) {
        if (n == LEVEL_SIZE - 1) return SHARE_BAD_LEVEL;
        char c = level[n];
        out[n] = c == '\\' ? '/' : c >= 'A' && c <= 'Z' ? c + 32 : c;
    }
    for (int i = n; i < LEVEL_SIZE; i++)
        out[i] = 0;
    if (!text_ok(out, LEVEL_SIZE, level_char)) return SHARE_BAD_LEVEL;
    for (int i = 1; out[i]; i++)
        if (out[i] == '/' && out[i - 1] == '/') return SHARE_BAD_LEVEL;
    return SHARE_OK;
}

void share_player_name(const char *name, char out[PLAYER_SIZE])
{
    int n = 0;
    for (; name && name[n] && n < PLAYER_SIZE - 1; n++)
        out[n] = player_char(name[n], n) ? name[n] : '_';
    if (n == 0) out[n++] = '_';
    for (int i = n; i < PLAYER_SIZE; i++)
        out[i] = 0;
}

int share_file_name_ok(const char *name, int length)
{
    static const char ending[] = ".ctrghost";
    const int ending_length = sizeof ending - 1;
    if (length <= ending_length || length > 63 || name[0] == '.') return 0;
    for (int i = 0; i < length; i++) {
        char c = name[i];
        if (!((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '_' || c == '-' || c == '.'))
            return 0;
    }
    for (int i = 0; i < ending_length; i++)
        if (name[length - ending_length + i] != ending[i]) return 0;
    return 1;
}
