cmake_minimum_required(VERSION 3.24)
project(MyApp CXX)

set(CMAKE_CXX_STANDARD 17)

# Ensure that CMake can find a non-Conan provided
# package by using a built-in Module:
# https://cmake.org/cmake/help/latest/module/FindThreads.html
find_package(Threads REQUIRED)
