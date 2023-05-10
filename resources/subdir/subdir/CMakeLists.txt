cmake_minimum_required(VERSION 3.24)
project(MySubdirApp)

find_package(subdir REQUIRED)
add_executable(appSubdir main.cpp)
target_link_libraries(appSubdir subdir::subdir)
