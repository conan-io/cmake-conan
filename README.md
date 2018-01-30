# cmake-conan

[![Build status](https://ci.appveyor.com/api/projects/status/0y2994lfwcpw9232/branch/master?svg=true)](https://ci.appveyor.com/project/ConanCIintegration/cmake-conan/branch/master)

[![Build Status](https://travis-ci.org/conan-io/cmake-conan.svg?branch=master)](https://travis-ci.org/conan-io/cmake-conan)

CMake wrapper for the Conan C and C++ package manager.


This cmake module allows to launch ``conan install`` from cmake.

The branches in this repo are:
- **develop**: PR are merged to this branch. Latest state of development
- **master**: Latest release
- **tagged releases**: https://github.com/conan-io/cmake-conan/releases. 

You probably want to use a tagged release to ensure controlled upgrades.

You can just clone or grab the *conan.cmake* file and put in in your project.
Or it can be used in this way. Note the ``v0.8`` tag in the URL, change it to point to your desired release:


```cmake

cmake_minimum_required(VERSION 2.8)
project(myproject CXX)

# Download automatically, you can also just copy the conan.cmake file
if(NOT EXISTS "${CMAKE_BINARY_DIR}/conan.cmake")
   message(STATUS "Downloading conan.cmake from https://github.com/conan-io/cmake-conan")
   file(DOWNLOAD "https://raw.githubusercontent.com/conan-io/cmake-conan/v0.8/conan.cmake"
                 "${CMAKE_BINARY_DIR}/conan.cmake")
endif()

include(${CMAKE_BINARY_DIR}/conan.cmake)

conan_cmake_run(REQUIRES Hello/0.1@memsharded/testing
                BASIC_SETUP 
                BUILD missing)

add_executable(main main.cpp)
target_link_libraries(main ${CONAN_LIBS})
```

## conan_cmake_run() options

### CMAKE_TARGETS

If you want to use targets, you could do:

```cmake
include(conan.cmake)
conan_cmake_run(REQUIRES Hello/0.1@memsharded/testing
                BASIC_SETUP CMAKE_TARGETS
                BUILD missing)

add_executable(main main.cpp)
target_link_libraries(main CONAN_PKG::Hello)
```

This will do a ``conan_basic_setup(TARGETS)`` for modern CMake targets definition

### CONANFILE

If you want to use your own ``conanfile.txt`` or ``conanfile.py`` instead of generating a temporary one, you could do:

```cmake
include(conan.cmake)
conan_cmake_run(CONANFILE conanfile.txt  # or relative build/conanfile.txt
                BASIC_SETUP CMAKE_TARGETS
                BUILD missing)
```

The resolution of the path will be relative to the root ``CMakeLists.txt`` file.


### KEEP_RPATHS

```cmake
include(conan.cmake)
conan_cmake_run(CONANFILE conanfile.txt
                BASIC_SETUP KEEP_RPATHS)
```

### NO_OUTPUT_DIRS

```cmake
include(conan.cmake)
conan_cmake_run(CONANFILE conanfile.txt
                BASIC_SETUP NO_OUTPUT_DIRS)
```

Pass to ``conan_basic_setup(NO_OUTPUT_DIRS)`` so *conanbuildinfo.cmake* does not change the output directories (lib, bin)

### CMAKE_BUILD_TYPE

To use the [cmake_multi](http://docs.conan.io/en/latest/integrations/cmake.html#cmake-multi-configuration-environments) generator you just need to make sure ``CMAKE_BUILD_TYPE`` is empty and use a CMake generator that supports multi-configuration.

## Creating packages

This cmake wrapper launchs conan, installing dependencies, and injecting a ``conan_basic_setup()`` call. So it is for end-users only, but not necessary at all for creating packages, because conan already downloaded and installed dependencies the moment that a package needs to be built. So if you are using the same CMakeLists.txt for both consuming and creating packages, consider doing something like:


```cmake
if(CONAN_EXPORTED) # in conan local cache
    # standard conan installation, deps will be defined in conanfile.py
    # and not necessary to call conan again, conan is already running
    include(${CMAKE_BINAR_DIR}/conanbuildinfo.cmake)
    conan_basic_setup()
else() # in user space
    include(conan.cmake)
    # Make sure to use conanfile.py to define dependencies, to stay consistent
    conan_cmake_run(CONANFILE conanfile.py
                    BASIC_SETUP)
endif()
```


Please check the source code for other options and arguments.

## Development, contributors

There are some tests, you can run in python, with nosetests, for example:

```bash
$ nosetests . --nocapture
```
