cmake_minimum_required(VERSION 3.24)

project(FormatOutput LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 14)

set(CMAKE_PROGRAM_PATH "/path/to/foo/bar")

find_package(fmt REQUIRED)

message("CMAKE_PROGRAM_PATH: ${CMAKE_PROGRAM_PATH}")
find_program(CMAKE_CXX_CPPCHECK cppcheck NAMES cppcheck)
if(NOT CMAKE_CXX_CPPCHECK)
    message(FATAL_ERROR "Unable to locate CPPCHECK")
else()
    message("Cppcheck found: ${CMAKE_CXX_CPPCHECK}")
endif()

add_executable(main main.cpp)
target_link_libraries(main PRIVATE fmt::fmt)
