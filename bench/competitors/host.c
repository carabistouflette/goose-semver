// SPDX-License-Identifier: Apache-2.0
// Separate translation unit, deliberately no LTO: opaque calls prevent folding.
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "competitor.h"
int64_t semver_bench_opaque(int64_t value) {
    __asm__ __volatile__("" : "+r"(value) : : "memory");
    return value;
}
void semver_bench_version(sl_u8 a, sl_u8 b, sl_u8 c, sl_u8 d, sl_u8 e) {
    __asm__ __volatile__("" : : "g"(a.data),"g"(a.len),"g"(b.data),"g"(b.len),"g"(c.data),"g"(c.len),"g"(d.data),"g"(d.len),"g"(e.data),"g"(e.len) : "memory");
}
void semver_bench_bytes(sl_u8 data) {
    __asm__ __volatile__("" : : "g"(data.data),"g"(data.len) : "memory");
}
int main(int argc, char **argv) {
    if (argc != 3) { fputs("usage: goose-competitor FIXTURES ITERATIONS\n", stderr); return 2; }
    char *end; long long count = strtoll(argv[2], &end, 10);
    if (*end || count < 1 || count > 10000000) return 2;
    goose_init(argc, argv);
    if (strcmp(argv[1], "--barriers") == 0) bench_controls(count);
    else bench_run((sl_u8){(uint8_t *)argv[1], (int64_t)strlen(argv[1])}, count);
    goose_exit();
    return 0;
}
