cmake_minimum_required(VERSION 2.8)
project(conan_wrapper CXX)

# if(NOT EXISTS "${CMAKE_BINARY_DIR}/conan.cmake")
#   message(STATUS "Downloading conan.cmake from https://github.com/memsharded/cmake-conan")
#   file(DOWNLOAD "https://raw.githubusercontent.com/conan-io/cmake-conan/master/conan.cmake"
#                 "${CMAKE_BINARY_DIR}/conan.cmake")
# endif()

# include(${CMAKE_BINARY_DIR}/conan.cmake)
include(conan.cmake)
conan_cmake_run(REQUIRES Hello/0.1@memsharded/testing
                BASIC_SETUP CMAKE_TARGETS
                CONAN_COMMAND C:/Users/drodri/scripts/conan.bat
                BUILD missing)

add_executable(main main.cpp)
target_link_libraries(main CONAN_PKG::Hello)
# target_link_libraries(main ${CONAN_LIBS})