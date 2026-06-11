#pragma once

#include <stddef.h>


#ifdef __cplusplus
extern "C" {
#endif

    void* __wrap_malloc(size_t size);

    void __wrap_free(void* ptr);

    void* __wrap_calloc(size_t nmemb, size_t size);

    void* __wrap_realloc(void* ptr, size_t size);

#ifdef __cplusplus
}
#endif
