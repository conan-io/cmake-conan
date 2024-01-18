cmake_minimum_required(VERSION 3.24)

project(FormatOutput LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 14)

find_package(fmt REQUIRED)

add_executable(main main.cpp)
target_link_libraries(main PRIVATE fmt::fmt)


get_property(CONAN_GENERATORS_FOLDER GLOBAL PROPERTY CONAN_GENERATORS_FOLDER)
list(PREPEND CMAKE_MODULE_PATH "${CONAN_GENERATORS_FOLDER}")
message("CMAKE_MODULE_PATH: ${CMAKE_MODULE_PATH}")

CHECK_CXX_SOURCE_COMPILES("int main(){return 0;}" HELLO_WORLD_CAN_COMPILE)