cmake_minimum_required(VERSION 3.15)
project(archconfig CXX)

add_library(archconfig src/archconfig.cpp)

# Generated public header that legitimately differs per architecture: Conan's
# CMakeToolchain sets CMAKE_OSX_ARCHITECTURES to the single architecture of each
# per-architecture install
if(CMAKE_OSX_ARCHITECTURES)
    set(_arch "${CMAKE_OSX_ARCHITECTURES}")
else()
    set(_arch "${CMAKE_SYSTEM_PROCESSOR}")
endif()
file(WRITE ${CMAKE_CURRENT_BINARY_DIR}/include/archconfig_arch.h
     "#define ARCHCONFIG_ARCH \"${_arch}\"\n")

target_include_directories(archconfig PUBLIC include ${CMAKE_CURRENT_BINARY_DIR}/include)

set_target_properties(archconfig PROPERTIES
                      PUBLIC_HEADER "include/archconfig.h;${CMAKE_CURRENT_BINARY_DIR}/include/archconfig_arch.h")
install(TARGETS archconfig)
