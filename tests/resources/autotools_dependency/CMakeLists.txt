cmake_minimum_required(VERSION 3.24)
project(MyApp CXX)

set(CMAKE_CXX_STANDARD 17)

find_package(helloautotools REQUIRED)
add_executable(app main.cpp)
target_link_libraries(app helloautotools::helloautotools)
