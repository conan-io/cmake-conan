cmake_minimum_required(VERSION 3.24)
project(MyApp CXX)

list(APPEND CMAKE_MODULE_PATH ${CMAKE_SOURCE_DIR}/modules)

find_program(CCACHE ccache)
find_package(OpenSSL)
find_package(ZLIB)
find_package(prometheus-cpp)

include(CustomModule)
hello_world()

add_executable(app main.cpp)
target_link_libraries(app hello::hello bye::bye)
