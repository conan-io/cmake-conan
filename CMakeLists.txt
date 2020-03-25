cmake_minimum_required(VERSION 2.8.12)
project(MD5hasher)

add_definitions("-std=c++11")

# if(NOT EXISTS "${CMAKE_BINARY_DIR}/conan.cmake")
#   message(STATUS "Downloading conan.cmake from https://github.com/memsharded/cmake-conan")
#   file(DOWNLOAD "https://github.com/conan-io/cmake-conan/raw/master/conan.cmake"
#                 "${CMAKE_BINARY_DIR}/conan.cmake")
# endif()

# include(${CMAKE_BINARY_DIR}/conan.cmake)
include(conan.cmake)
conan_cmake_run(REQUIRES poco/1.9.4
                BASIC_SETUP CMAKE_TARGETS
                BUILD missing)

 
add_executable(md5 md5.cpp)
target_link_libraries(md5 CONAN_PKG::poco)
#target_link_libraries(md5 ${CONAN_LIBS})