# cmake-conan

[![Build status](https://ci.appveyor.com/api/projects/status/xufl3dbdfrlnuhcp/branch/master?svg=true&passingText=master%20-%20OK)](https://ci.appveyor.com/project/ConanOrgCI/cmake-conan/branch/master) [![Build status](https://ci.appveyor.com/api/projects/status/xufl3dbdfrlnuhcp/branch/develop?svg=true&passingText=develop%20-%20OK)](https://ci.appveyor.com/project/ConanOrgCI/cmake-conan/branch/develop) [![Build Status](https://travis-ci.org/conan-io/cmake-conan.svg?branch=master)](https://travis-ci.org/conan-io/cmake-conan)

CMake wrapper for the Conan C and C++ package manager.


This cmake module allows to launch ``conan install`` from cmake.

The branches in this repo are:
- **develop**: PR are merged to this branch. Latest state of development
- **master**: Latest release
- **tagged releases**: https://github.com/conan-io/cmake-conan/releases. 

You probably want to use a tagged release to ensure controlled upgrades.

You can just clone or grab the *conan.cmake* file and put in in your project.
Or it can be used in this way. Note the ``v0.15`` tag in the URL, change it to point to your desired release:

```cmake

cmake_minimum_required(VERSION 2.8)
project(FormatOutput CXX)

# Download automatically, you can also just copy the conan.cmake file
if(NOT EXISTS "${CMAKE_BINARY_DIR}/conan.cmake")
   message(STATUS "Downloading conan.cmake from https://github.com/conan-io/cmake-conan")
   file(DOWNLOAD "https://github.com/conan-io/cmake-conan/raw/v0.15/conan.cmake"
                 "${CMAKE_BINARY_DIR}/conan.cmake" 
                 TLS_VERIFY ON)
endif()

include(${CMAKE_BINARY_DIR}/conan.cmake)

conan_cmake_run(REQUIRES fmt/6.1.2
                BASIC_SETUP 
                BUILD missing)

add_executable(main main.cpp)
target_link_libraries(main ${CONAN_LIBS})
```

## conan_cmake_run() options


### REQUIRES, OPTIONS
```cmake
conan_cmake_run(REQUIRES fmt/1.9.4
                         cgal/5.0.2
                OPTIONS Pkg:shared=True
                        OtherPkg:option=value
                )
```

Define requirements and their options. These values are written to a temporary `conanfile.py`. If you need more advanced functionality, like conditional requirements, you can define your own `conanfile.txt` or `conanfile.py` and provide
it with the ``CONANFILE`` argument

### CMAKE_TARGETS

If you want to use targets, you could do:

```cmake
include(conan.cmake)
conan_cmake_run(REQUIRES fmt/1.9.4
                BASIC_SETUP CMAKE_TARGETS
                BUILD missing)

add_executable(main main.cpp)
target_link_libraries(main CONAN_PKG::fmt)
```

This will do a ``conan_basic_setup(TARGETS)`` for modern CMake targets definition.

### CONANFILE

If you want to use your own ``conanfile.txt`` or ``conanfile.py`` instead of generating a temporary one, you could do:

```cmake
include(conan.cmake)
conan_cmake_run(CONANFILE conanfile.txt  # or relative build/conanfile.txt
                BASIC_SETUP CMAKE_TARGETS
                BUILD missing)
```

The resolution of the path will be relative to the root ``CMakeLists.txt`` file.

### BUILD

```cmake
conan_cmake_run(REQUIRES fmt/6.1.2 boost...
                BASIC_SETUP 
                BUILD <value>)
```

Used to define the build policy used for ``conan install``. Can take different values:
- ``BUILD all``. Build all the dependencies for the project.
- ``BUILD missing``. Build packages from source whose binary package is not found.
- ``BUILD outdated``. Build packages from source whose binary package was not generated from the
  latest recipe or is not found.
- ``BUILD cascade``. Build packages from source that have at least one dependency being built from
  source.
- ``BUILD [pattern]``. Build packages from source whose package reference matches the pattern. The
  pattern uses *'fnmatch'* style wildcards.

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

Pass to ``conan_basic_setup(NO_OUTPUT_DIRS)`` so *conanbuildinfo.cmake* does not change the output directories (lib, bin).

### ARCH

```cmake
include(conan.cmake)
conan_cmake_run(ARCH armv7)
```

Use it to override the architecture detection and force to call conan with the provided one. The architecture should
exist in *settings.yml*.


### BUILD_TYPE

```cmake
include(conan.cmake)
conan_cmake_run(BUILD_TYPE "None")
```

Use it to override the build_type detection and force to call conan with the provided one. The build type should
exist in *settings.yml*.

### CONFIGURATION_TYPES

```cmake
include(conan.cmake)
conan_cmake_run(CONFIGURATION_TYPES "Release;Debug;RelWithDebInfo")
```

Use it to set the different configurations when using multi-configuration generators. The default 
configurations used for multi-configuration generators are `Debug` and `Release` if the argument 
`CONFIGURATION_TYPES` is not specified  The build types passed through this argument should exist 
in *settings.yml*.

### PROFILE
```cmake
include(conan.cmake)
conan_cmake_run(PROFILE default)
```

Use it to use the "default" (or your own profile) conan profile rather than inferring settings from CMake.
When it is defined, the CMake automatically detected settings are not used at all,
and are overridden by the values from the profile.

### PROFILE_AUTO
```cmake
include(conan.cmake)
conan_cmake_run(PROFILE default
                PROFILE_AUTO build_type)
```

Use the CMake automatically detected value, instead of the profile one. The above
means use the profile named "default", but override its content with the ``build_type``
automatically detected by CMake.

The precedence for settings definition is:

```
CMake detected < PROFILE < PROFILE_AUTO < Explicit ``conan_cmake_run()`` args
```

The ``ALL`` value is used to use all detected settings from CMake, instead of the ones
defined in the profile:

```cmake
include(conan.cmake)
conan_cmake_run(PROFILE default
                PROFILE_AUTO ALL)
```

This is still useful, as the profile can have many other things defined (options, build_requires, etc).


### CMAKE_BUILD_TYPE

To use the [cmake_multi](http://docs.conan.io/en/latest/integrations/cmake.html#cmake-multi-configuration-environments) generator you just need to make sure ``CMAKE_BUILD_TYPE`` is empty and use a CMake generator that supports multi-configuration.

If the ``BUILD_TYPE`` is explictly passed to ``conan_cmake_run()``, then single configuration ``cmake`` generator will be used.


### SETTINGS
```cmake
include(conan.cmake)
conan_cmake_run(...
                SETTINGS arch=armv6
                SETTINGS compiler.cppstd=14)
```

### ENV
```cmake
include(conan.cmake)
conan_cmake_run(...
                ENV env_var=value
                ENV Pkg:env_var2=value2)
```

Define command line environment variables. Even if with CMake it is also possible to
directly define environment variables, with this syntax you can define environment
variables per-package, as the above is equivalent to:

```bash
$ conan install .... -e env_var=value -e Pkg:env_var2=value
```

If environment variables were defined in a given profile, command line arguments
have higher precedence, so these values would be used instead of the profiles ones.

### INSTALL_FOLDER

Provide the ``conan install --install-folder=[folder]`` argument:

```cmake
include(conan.cmake)
conan_cmake_run(...
                INSTALL_FOLDER myfolder
                )
```

### GENERATORS

Add additional [generators](https://docs.conan.io/en/latest/reference/generators.html?highlight=generator). It may useful to add the [virtualrunenv](https://docs.conan.io/en/latest/mastering/virtualenv.html#virtualrunenv-generator)-generator:

```cmake
include(conan.cmake)
conan_cmake_run(...
                GENERATORS virtualrunenv)
```

### CONAN_COMMAND

Use ``CONAN_COMMAND`` argument to specify the conan path, e.g. in case of running from source cmake
does not identify conan as command, even if it is +x and it is in the path.

```cmake
include(conan.cmake)
conan_cmake_run(...
                CONAN_COMMAND "path_to_conan")
```

## Other macros and functions

### conan_check()

Checks conan availability in PATH.
Arguments ``REQUIRED`` and ``VERSION`` are optional.

Example usage:
```
conan_check(VERSION 1.0.0 REQUIRED)
```

### conan_add_remote()

Adds a remote.
Arguments ``URL`` and ``NAME`` are required, ``INDEX`` and ``VERIFY_SSL`` are optional.

Example usage:
```
conan_add_remote(NAME bincrafters 
                 INDEX 1
                 URL https://api.bintray.com/conan/bincrafters/public-conan
                 VERIFY_SSL True)            
```

### conan_config_install()

Installs a full configuration from a local or remote zip file.
Argument ``ITEM`` is required,  arguments ``TYPE``, ``SOURCE``, ``TARGET`` and ``VERIFY_SSL`` are optional.

Example usage:
```
conan_config_install(ITEM ./config.git TYPE git SOURCE src TARGET dst VERIFY_SSL False)
```


## Creating packages

This cmake wrapper launches conan, installing dependencies, and injecting a ``conan_basic_setup()`` call. So it is for end-users only, but not necessary at all for creating packages, because conan already downloaded and installed dependencies the moment that a package needs to be built. If you are using the same CMakeLists.txt for both consuming and creating packages, consider doing something like:


```cmake
if(CONAN_EXPORTED) # in conan local cache
    # standard conan installation, deps will be defined in conanfile.py
    # and not necessary to call conan again, conan is already running
    include(${CMAKE_BINARY_DIR}/conanbuildinfo.cmake)
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
