/* Shared ghost file (.ctrghost), version 1. Little-endian, fixed layout:
 *
 *   header (0x100 bytes)
 *     0x00 char  magic[8]      "CTRGHST1"
 *     0x08 u32   version       1
 *     0x0c u32   header_size   0x100
 *     0x10 u32   move_count    MIN_MOVES..MAX_MOVES
 *     0x14 u32   input_count   MIN_INPUTS..MAX_INPUTS
 *     0x18 f32   time          race time in seconds
 *     0x1c u32   reserved      0
 *     0x20 char  player[32]    who raced it (printable ASCII)
 *     0x40 char  level[96]     e.g. "octane/t112_roos_tubes/t112_roos_tubes" (lower case, '/')
 *     0xa0 char  driver[48]    game driver id, e.g. "DriverCrash"
 *     0xd0 char  kart[48]      game kart id, e.g. "KartCrash"
 *   move keys  (move_count x 20 bytes): f32 x, y, z; u16 time (1/100 s); s16 angle0, angle1, angle2
 *   input keys (input_count x 4 bytes): u16 bits; u16 time (1/100 s)
 *
 * Each text field ends with a 0 byte and every byte after it is 0 too, so one ghost has exactly one
 * file form. The file size must be exactly header + keys. Files come from other people: the reader
 * checks every field before the game sees any of it.
 */
#ifndef SHARE_FORMAT_H
#define SHARE_FORMAT_H

#include <stdint.h>

#define SHARE_MAGIC "CTRGHST1"
#define SHARE_VERSION 1
#define SHARE_HEADER_SIZE 0x100
#define SHARE_MOVE_SIZE 20
#define SHARE_INPUT_SIZE 4

/* The game keeps at most 2101 move keys after a race and records an input key only when an input
 * changes (its lists hold up to 10800). Playback needs 2 move keys and 1 input key. */
#define MIN_MOVES 2
#define MAX_MOVES 4096
#define MIN_INPUTS 1
#define MAX_INPUTS 16384
#define MAX_TIME 655.0f         /* key times are u16 hundredths of a second */
#define MAX_POSITION 1000000.0f /* track coordinates seen in the game: under 30000 */
#define INPUT_BITS 0x7fff       /* steering (bits 0-7), accelerate, reverse, brake, 2 jumps, drift, race start */

#define PLAYER_SIZE 32
#define LEVEL_SIZE 96
#define NAME_SIZE 48

struct share_header {
    char magic[8];
    uint32_t version;
    uint32_t header_size;
    uint32_t move_count;
    uint32_t input_count;
    float time;
    uint32_t reserved;
    char player[PLAYER_SIZE];
    char level[LEVEL_SIZE];
    char driver[NAME_SIZE];
    char kart[NAME_SIZE];
};
_Static_assert(sizeof(struct share_header) == SHARE_HEADER_SIZE, "header layout");

struct share_move {
    float position[3];
    uint16_t time;
    int16_t angle[3];
};
_Static_assert(sizeof(struct share_move) == SHARE_MOVE_SIZE, "move key layout");

struct share_input {
    uint16_t bits;
    uint16_t time;
};
_Static_assert(sizeof(struct share_input) == SHARE_INPUT_SIZE, "input key layout");

/* Checks the header alone. Returns 0 when it is valid, otherwise a SHARE_BAD_* number. */
int share_check_header(const struct share_header *h);
/* The file size a valid header asks for. */
uint64_t share_file_size(const struct share_header *h);

/* Key checks keep the previous key's time: start with *last = -1. */
int share_check_move(const struct share_move *m, int32_t *last);
int share_check_input(const struct share_input *k, int32_t *last);

/* Level names compare without case and with '\' as '/'. Writes the canonical form (lower case, '/')
 * of `level` to out; returns 0 when it fits and is a valid level name. */
int share_level_name(const char *level, char out[LEVEL_SIZE]);

/* Turns any text into a valid player name (other characters become '_'); never empty. */
void share_player_name(const char *name, char out[PLAYER_SIZE]);

/* A file name in the ghosts folder we accept: [A-Za-z0-9_.-], at most 63 characters, ending in
 * ".ctrghost", not starting with '.'. */
int share_file_name_ok(const char *name, int length);

enum {
    SHARE_OK = 0,
    SHARE_BAD_MAGIC, SHARE_BAD_VERSION, SHARE_BAD_COUNT, SHARE_BAD_TIME, SHARE_BAD_RESERVED,
    SHARE_BAD_PLAYER, SHARE_BAD_LEVEL, SHARE_BAD_DRIVER, SHARE_BAD_KART,
    SHARE_BAD_POSITION, SHARE_BAD_KEY_TIME, SHARE_BAD_INPUT_BITS,
};

#endif
