# cmake-conan

CMake wrapper for conan C and C++ package manager

** Testing required **: This tools is still experimental, please try and contribute, specially with the extraction of settings from cmake.


This cmake code allows to launch ``conan install`` from cmake.

It can be used this way:


```cmake

cmake_minimum_required(VERSION 2.8)
project(myproject CXX)

# Download automatically, you can also just copy the conan.cmake file
if(NOT EXISTS "${CMAKE_BINARY_DIR}/conan.cmake")
   message(STATUS "Downloading conan.cmake from https://github.com/memsharded/cmake-conan")
   file(DOWNLOAD "https://raw.githubusercontent.com/conan-io/cmake-conan/master/conan.cmake"
                 "${CMAKE_BINARY_DIR}/conan.cmake")
endif()

include(${CMAKE_BINARY_DIR}/conan.cmake)

conan_cmake_run(REQUIRES Hello/0.1@memsharded/testing
                BASIC_SETUP 
                BUILD missing)

add_executable(main main.cpp)
target_link_libraries(main ${CONAN_LIBS})
```

If you want to use targets, you could do:

```cmake
include(conan.cmake)
conan_cmake_run(REQUIRES Hello/0.1@memsharded/testing
                BASIC_SETUP CMAKE_TARGETS
                BUILD missing)

add_executable(main main.cpp)
target_link_libraries(main CONAN_PKG::Hello)
```

Please check the source code for other options and arguments