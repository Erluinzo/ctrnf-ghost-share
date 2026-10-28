/* PC test program for src/share_format.c (built with AddressSanitizer and UBSan by run_tests.py).
 *
 *   check_files FILE...   prints "valid" or "invalid <reason number>" for each file, checking it in
 *                         the same order as the game patch reads it (header, size, then each key)
 *   check_files --unit    small tests of the name helpers
 *
 * With -DFUZZ it is a libFuzzer target instead.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../src/share_format.h"

static int check_file(const uint8_t *data, size_t size)
{
    struct share_header h;
    if (size < sizeof h) return 100;
    memcpy(&h, data, sizeof h);
    int bad = share_check_header(&h);
    if (bad) return bad;
    if (share_file_size(&h) != size) return 101;
    size_t at = sizeof h;
    int32_t last = -1;
    for (uint32_t i = 0; i < h.move_count; i++, at += SHARE_MOVE_SIZE) {
        struct share_move m;
        memcpy(&m, data + at, sizeof m);
        if ((bad = share_check_move(&m, &last))) return bad;
    }
    last = -1;
    for (uint32_t i = 0; i < h.input_count; i++, at += SHARE_INPUT_SIZE) {
        struct share_input k;
        memcpy(&k, data + at, sizeof k);
        if ((bad = share_check_input(&k, &last))) return bad;
    }
    return 0;
}

#ifdef FUZZ
int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size)
{
    check_file(data, size);
    /* The name helpers get the same bytes as text */
    char text[200] = {0}, level[LEVEL_SIZE], player[PLAYER_SIZE];
    memcpy(text, data, size < sizeof text - 1 ? size : sizeof text - 1);
    share_level_name(text, level);
    share_player_name(text, player);
    share_file_name_ok(text, (int)strlen(text));
    return 0;
}
#else
static int failures;
#define EXPECT(condition) do { if (!(condition)) { printf("FAIL line %d: %s\n", __LINE__, #condition); failures++; } } while (0)

static void unit(void)
{
    char out[LEVEL_SIZE], player[PLAYER_SIZE];
    EXPECT(share_level_name("Octane\\T112_Roos_Tubes\\T112_Roos_Tubes", out) == 0
           && !strcmp(out, "octane/t112_roos_tubes/t112_roos_tubes"));
    EXPECT(share_level_name("", out) != 0);
    EXPECT(share_level_name("/octane", out) != 0);
    EXPECT(share_level_name("a//b", out) != 0);
    EXPECT(share_level_name("a/../b", out) != 0);
    EXPECT(share_level_name("a b", out) != 0);
    char longer[200];
    memset(longer, 'a', sizeof longer - 1);
    longer[sizeof longer - 1] = 0;
    EXPECT(share_level_name(longer, out) != 0);

    share_player_name("Neox", player);
    EXPECT(!strcmp(player, "Neox"));
    share_player_name(" \x01\xffZ", player);
    EXPECT(!strcmp(player, "___Z"));
    share_player_name("", player);
    EXPECT(!strcmp(player, "_"));
    share_player_name(0, player);
    EXPECT(!strcmp(player, "_"));
    share_player_name(longer, player);
    EXPECT(strlen(player) == PLAYER_SIZE - 1);

    EXPECT(share_file_name_ok("t112_roos_tubes_1m17s99_Neox.ctrghost", 37));
    EXPECT(!share_file_name_ok(".ctrghost", 9));
    EXPECT(!share_file_name_ok(".hidden.ctrghost", 16));
    EXPECT(!share_file_name_ok("a.ctrghost.bbtmp", 16));
    EXPECT(!share_file_name_ok("../a.ctrghost", 13));
    EXPECT(!share_file_name_ok("a\\b.ctrghost", 12));
    EXPECT(!share_file_name_ok("a:b.ctrghost", 12));
    EXPECT(!share_file_name_ok("a b.ctrghost", 12));
    EXPECT(!share_file_name_ok("a.CTRGHOST", 10));
    char name[80];
    memset(name, 'a', 64);
    strcpy(name + 55, ".ctrghost");
    EXPECT(!share_file_name_ok(name, 64));
    EXPECT(share_file_name_ok(name + 1, 63));
}

int main(int argc, char **argv)
{
    if (argc == 2 && !strcmp(argv[1], "--unit")) {
        unit();
        printf(failures ? "unit: %d failures\n" : "unit: ok\n", failures);
        return failures != 0;
    }
    for (int i = 1; i < argc; i++) {
        FILE *f = fopen(argv[i], "rb");
        if (!f) return 2;
        static uint8_t data[1 << 20];
        size_t n = fread(data, 1, sizeof data, f);
        fclose(f);
        uint8_t *copy = malloc(n ? n : 1);   /* exact size, so AddressSanitizer sees any over-read */
        memcpy(copy, data, n);
        int bad = check_file(copy, n);
        free(copy);
        printf(bad ? "invalid %d\n" : "valid\n", bad);
    }
    return 0;
}
#endif
