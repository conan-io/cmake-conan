cmake_minimum_required(VERSION 3.24)

project(FormatOutput LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 14)

find_package(fmt REQUIRED)
find_package(Threads REQUIRED)
find_package(BZip2 REQUIRED MODULE)

add_executable(main main.cpp)
target_link_libraries(main PRIVATE fmt::fmt)                    