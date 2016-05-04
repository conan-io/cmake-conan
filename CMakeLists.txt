cmake_minimum_required(VERSION 2.8)
project(conan_wrapper C CXX)

include(conan.cmake)       
conan_requirements(REQUIRES Hello/0.1@memsharded/testing
                   BUILD_DIR ${CMAKE_SOURCE_DIR}/.conan
                   BASIC_SETUP
                   BUILD missing)

add_executable(main main.cpp)
target_link_libraries(main ${CONAN_LIBS})