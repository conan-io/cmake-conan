#include "syscall_wrapper.h"


#include <stdlib.h>
#include <stdio.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <stdint.h>
#include <errno.h>
#include <sys/types.h>


// Symbol vom Linker
extern uint8_t _end;  // muss im Linkerskript vorhanden sein!
static uint8_t* heap_end = &_end;

void* __wrap_malloc(size_t size) {
    printf("[WRAP] malloc(%zu)\n", size);
    return NULL;
}

void __wrap_free(void* ptr) {
    printf("[WRAP] free(%p)\n", ptr);
    
}

void* __wrap_calloc(size_t nmemb, size_t size) {
    printf("[WRAP] calloc(%zu, %zu)\n", nmemb, size);
    return NULL;
}

void* __wrap_realloc(void* ptr, size_t size) {
    printf("[WRAP] realloc(%p, %zu)\n", ptr, size);
    return NULL;
}




void* _sbrk(ptrdiff_t incr) {
    uint8_t* prev_heap_end = heap_end;
    heap_end += incr;
    printf("[SYSCALL] _sbrk(%ld) = %p\n", (long)incr, prev_heap_end);
    return (void*)prev_heap_end;
}

int _close(int fd) {
    printf("[SYSCALL] _close(%d)\n", fd);
    return -1;
}

int _fstat(int fd, struct stat* st) {
    printf("[SYSCALL] _fstat(%d)\n", fd);
    st->st_mode = S_IFCHR;  // Char device
    return 0;
}

int _isatty(int fd) {
    printf("[SYSCALL] _isatty(%d)\n", fd);
    return 1;
}

off_t _lseek(int fd, off_t offset, int whence) {
    printf("[SYSCALL] _lseek(%d, %ld, %d)\n", fd, (long)offset, whence);
    return 0;
}

size_t _read(int fd, void* buf, size_t count) {
    printf("[SYSCALL] _read(%d, %p, %zu)\n", fd, buf, count);
    return 0;
}

size_t _write(int fd, const void* buf, size_t count) {
    const char* cbuf = (const char*)buf;
    printf("[SYSCALL] _write(%d, %p, %zu): \"", fd, buf, count);
    for (size_t i = 0; i < count; ++i) {
        putchar(cbuf[i]);
    }
    printf("\"\n");
    return count;
}

int _kill(int pid, int sig) {
    printf("[SYSCALL] _kill(%d, %d)\n", pid, sig);
    errno = EINVAL;
    return -1;
}

int _getpid(void) {
    printf("[SYSCALL] _getpid()\n");
    return 1;
}

void _exit(int status) {
    printf("[SYSCALL] _exit(%d)\n", status);
    while (1) {}  // Endlosschleife statt Exit
}
