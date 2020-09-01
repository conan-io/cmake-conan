cmake_minimum_required(VERSION 2.8.12)
project(FormatOutput)

add_definitions("-std=c++11")

# if(NOT EXISTS "${CMAKE_BINARY_DIR}/conan.cmake")
#   message(STATUS "Downloading conan.cmake from https://github.com/conan-io/cmake-conan")
#   file(DOWNLOAD "https://github.com/conan-io/cmake-conan/raw/master/conan.cmake"
#                 "${CMAKE_BINARY_DIR}/conan.cmake"
#                 TLS_VERIFY ON)
# endif()

# include(${CMAKE_BINARY_DIR}/conan.cmake)
include(conan.cmake)
conan_cmake_run(REQUIRES fmt/6.1.2
                BASIC_SETUP CMAKE_TARGETS
                BUILD missing)

 
add_executable(main main.cpp)
target_link_libraries(main CONAN_PKG::fmt)
#target_link_libraries(main ${CONAN_LIBS})
