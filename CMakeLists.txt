cmake_minimum_required(VERSION 2.8)
project(conan_wrapper CXX)


# Extend file() with DOWNLOAD_ONCE sub-command: download only
# if there is no file with such name in the filesystem.

macro(file action)
    if(${action} STREQUAL DOWNLOAD_ONCE)
        if(${ARGC} LESS 3)
            # Too few arguments: show the standard error message
            _file(DOWNLOAD ${ARGN})
        endif ()
        if(NOT EXISTS ${ARGV2})
            message(STATUS "Downloading ${ARGV1}")
            _file(DOWNLOAD ${ARGN})
        endif()
    else()
        # Call the original function
        _file(${action} ${ARGN})
    endif()
endmacro()


file(DOWNLOAD_ONCE "https://github.com/conan-io/cmake-conan/raw/master/conan.cmake"
                   "${CMAKE_BINARY_DIR}/conan.cmake")

include(${CMAKE_BINARY_DIR}/conan.cmake)
conan_cmake_run(REQUIRES Hello/0.1@memsharded/testing
                BASIC_SETUP CMAKE_TARGETS
                BUILD missing)

add_executable(main main.cpp)
target_link_libraries(main CONAN_PKG::Hello)
# target_link_libraries(main ${CONAN_LIBS})
