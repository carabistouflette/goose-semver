// SPDX-License-Identifier: Apache-2.0
// Test-only read-only slices abutting inaccessible pages. No product native code.
#define _GNU_SOURCE
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
#include "semver-fuzz.h"

_Noreturn void goose_fuzz_exit(int status) {
    if (status != 0) abort();
    _Exit(status);
}
static size_t checks;
static void exercise(uint8_t *body, size_t capacity, size_t length, int at_end,
                     int build, int bad_byte) {
    assert(length <= capacity);
    uint8_t *input = at_end ? body + capacity - length : body;
    memset(input, '9', length);
    static const uint8_t pre[] = "1.2.3-";
    static const uint8_t meta[] = "1.2.3+";
    const uint8_t *prefix = build ? meta : pre;
    if (length >= sizeof(pre) - 1) memcpy(input, prefix, sizeof(pre) - 1);
    if (length > sizeof(pre) && bad_byte >= 0) input[length - 1] = (uint8_t)bad_byte;
    assert(mprotect(body, capacity, PROT_READ) == 0);
    (void)fuzz_check((sl_u8){input, (int64_t)length});
    assert(mprotect(body, capacity, PROT_READ | PROT_WRITE) == 0);
    checks++;
}
int main(int argc, char **argv) {
    long page = sysconf(_SC_PAGESIZE);
    assert(page > 0);
    size_t page_size = (size_t)page;
    size_t capacity = ((16385 + page_size - 1) / page_size) * page_size;
    size_t total = capacity + 2 * page_size;
    uint8_t *mapping = mmap(NULL, total, PROT_NONE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    assert(mapping != MAP_FAILED);
    uint8_t *body = mapping + page_size;
    assert(mprotect(body, capacity, PROT_READ | PROT_WRITE) == 0);
    goose_init(argc, argv);
    for (size_t length = 0; length <= 4097; length++) {
        for (int at_end = 0; at_end <= 1; at_end++) {
            exercise(body, capacity, length, at_end, 0, -1);
            exercise(body, capacity, length, at_end, 1, -1);
        }
    }
    static const size_t lengths[] = {15, 16, 17, 31, 32, 33, 63, 64, 65, 127, 4096, 16383, 16384, 16385};
    for (size_t i = 0; i < sizeof(lengths) / sizeof(lengths[0]); i++) {
        for (int byte = 0; byte < 256; byte++) {
            exercise(body, capacity, lengths[i], 1, 0, byte);
            exercise(body, capacity, lengths[i], 1, 1, byte);
        }
    }
    goose_exit();
    assert(munmap(mapping, total) == 0);
    printf("protected-page read-only slices: %zu checks passed\n", checks);
    return 0;
}
