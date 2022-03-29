# cmake-conan

![Build Status](https://github.com/conan-io/cmake-conan/actions/workflows/cmake_conan.yml/badge.svg)

CMake wrapper for the Conan C and C++ package manager.


This cmake module allows to launch ``conan install`` from cmake.

The branches in this repo are:
- **develop**: PR are merged to this branch. Latest state of development
- **master**: Latest release
- **tagged releases**: https://github.com/conan-io/cmake-conan/releases.

You probably want to use a tagged release to ensure controlled upgrades.

You can just clone or grab the *conan.cmake* file and put in in your project.
Or it can be used in this way. Note the ``0.18.0`` tag in the URL, change it to point to your desired release:

```cmake

cmake_minimum_required(VERSION 3.9)
project(FormatOutput CXX)

list(APPEND CMAKE_MODULE_PATH ${CMAKE_BINARY_DIR})
list(APPEND CMAKE_PREFIX_PATH ${CMAKE_BINARY_DIR})

add_definitions("-std=c++11")

if(NOT EXISTS "${CMAKE_BINARY_DIR}/conan.cmake")
  message(STATUS "Downloading conan.cmake from https://github.com/conan-io/cmake-conan")
  file(DOWNLOAD "https://raw.githubusercontent.com/conan-io/cmake-conan/0.18.0/conan.cmake"
                "${CMAKE_BINARY_DIR}/conan.cmake"
                EXPECTED_HASH SHA256=396e16d0f5eabdc6a14afddbcfff62a54a7ee75c6da23f32f7a31bc85db23484
                TLS_VERIFY ON)
endif()

include(${CMAKE_BINARY_DIR}/conan.cmake)

conan_cmake_configure(REQUIRES fmt/6.1.2
                      GENERATORS cmake_find_package)

conan_cmake_autodetect(settings)

conan_cmake_install(PATH_OR_REFERENCE .
                    BUILD missing
                    REMOTE conancenter
                    SETTINGS ${settings})

find_package(fmt)

add_executable(main main.cpp)
target_link_libraries(main fmt::fmt)
```

There are different functions you can use from your CMake project to use Conan from there. The
recommended flow to use cmake-conan is successively calling to `conan_cmake_configure`,
`conan_cmake_autodetect` and `conan_cmake_install`. This flow is recommended from v0.16 where these
functions were introduced.

The example above is using the Conan `cmake_find_package` generator which is less intrusive than the
`cmake` generator and more aligned with the direction Conan is taking for the 2.0 version. If you
want to continue using the `cmake` generator with `conan_cmake_configure`, `conan_cmake_autodetect`
and `conan_cmake_install` flow, you should manually include the `conanbuildinfo.cmake` file generated
and also call to `conan_basic_setup`:

```cmake

include(${CMAKE_BINARY_DIR}/conanbuildinfo.cmake)
conan_basic_setup(TARGETS)
```

Please [check the cmake generator documentation](https://docs.conan.io/en/latest/integrations/build_system/cmake/cmake_generator.html#cmake-generator)
for further details.

## conan_cmake_configure()

This function will accept the same arguments as the sections of the
[conanfile.txt](https://docs.conan.io/en/latest/reference/conanfile_txt.html).

```cmake
conan_cmake_configure(REQUIRES fmt/6.1.2
                      GENERATORS cmake_find_package
                      BUILD_REQUIRES cmake/3.15.7
                      IMPORTS "bin, *.dll -> ./bin"
                      IMPORTS "lib, *.dylib* -> ./bin")
                      OPTIONS fmt:shared=True)

```

## conan_cmake_autodetect()

This function will return the auto-detected settings (things like *build_type*, *compiler* or *system
name*) so you can pass that information to `conan_cmake_install`. This step is optional as you may
want to rely on profiles, lockfiles or any other way of passing that information. This function will
also accept as arguments `BUILD_TYPE` and `ARCH`. Setting those arguments will force that settings
to the value provided (this can be useful for the multi-configuration generator scenario below).

```cmake
conan_cmake_autodetect(settings)
```

## conan_cmake_install()

This function is a wrapper for the [conan
install](https://docs.conan.io/en/latest/reference/commands/consumer/install.html) command. You can
pass all the arguments that the command supports. Also, you can pass the auto-detected settings from
`conan_cmake_autodetect` in the `SETTINGS` argument.

It can receive as arguments: `UPDATE`, `NO_IMPORTS`, `PATH_OR_REFERENCE`, `REFERENCE`, `REMOTE`,
`LOCKFILE`, `LOCKFILE_OUT`, `LOCKFILE_NODE_ID`, `INSTALL_FOLDER`, `OUTPUT_FOLDER`, `GENERATOR`, `BUILD` (if this
parameter takes the `all` value, Conan will build everything from source), `ENV`, `ENV_HOST`,
`ENV_BUILD`, `OPTIONS_HOST`, `OPTIONS`, `OPTIONS_BUILD`, `PROFILE`, `PROFILE_HOST`, `PROFILE_BUILD`,
`SETTINGS`, `SETTINGS_HOST`, `SETTINGS_BUILD`. For more information, check [conan
install](https://docs.conan.io/en/latest/reference/commands/consumer/install.html) documentation.

It will also accept `OUTPUT_QUIET` and `ERROR_QUIET` arguments so that when it runs the `conan install`
command the output is quiet or the error is bypassed (or both).

```cmake
conan_cmake_install(PATH_OR_REFERENCE .
                    BUILD missing
                    REMOTE conancenter
                    SETTINGS ${settings})
```

## conan_cmake_lock_create()

This function is an additional wrapper for the [conan lock
create](https://docs.conan.io/en/latest/reference/commands/misc/lock.html#conan-lock-create)
sub-command of conan lock command to enable lockfile based workflows. You can pass all the arguments
that the command supports. Also, you can pass the auto-detected settings from
`conan_cmake_autodetect` in the `SETTINGS` argument.

It can receive as arguments: `PATH`, `REFERENCE`, `UPDATE`, `BASE`, `REMOTE`, `LOCKFILE`,
`LOCKFILE_OUT`, `LOCKFILE_NODE_ID`, `INSTALL_FOLDER`, `GENERATOR`, `BUILD`, `ENV`, `ENV_HOST`,
`ENV_BUILD`, `OPTIONS`, `OPTIONS_HOST`, `OPTIONS_BUILD`, `PROFILE`, `PROFILE_HOST`, `PROFILE_BUILD`,
`SETTINGS`, `SETTINGS_HOST`, `SETTINGS_BUILD`. For more information, check [conan lock
create](https://docs.conan.io/en/latest/reference/commands/misc/lock.html#conan-lock-create)
documentation.

It will also accept `OUTPUT_QUIET` and `ERROR_QUIET` arguments so that when it runs the `conan
install` command the output is quiet or the error is bypassed (or both).

## Using conan_cmake_autodetect() and conan_cmake_install() with Multi Configuration generators

The recommended approach when using Multi Configuration generators like Visual Studio or Xcode is
looping through the `CMAKE_CONFIGURATION_TYPES` in your _CMakeLists.txt_ and calling
`conan_cmake_autodetect` with the `BUILD_TYPE` argument and `conan_cmake_install` for each one using
a Conan multiconfig generator like `cmake_find_package_multi`. Please check the example:

```cmake
cmake_minimum_required(VERSION 3.9)
project(FormatOutput CXX)
list(APPEND CMAKE_MODULE_PATH ${CMAKE_BINARY_DIR})
list(APPEND CMAKE_PREFIX_PATH ${CMAKE_BINARY_DIR})
add_definitions("-std=c++11")
include(conan.cmake)

conan_cmake_configure(REQUIRES fmt/6.1.2 GENERATORS cmake_find_package_multi)

foreach(TYPE ${CMAKE_CONFIGURATION_TYPES})
    conan_cmake_autodetect(settings BUILD_TYPE ${TYPE})
    conan_cmake_install(PATH_OR_REFERENCE .
                        BUILD missing
                        REMOTE conancenter
                        SETTINGS ${settings})
endforeach()

find_package(fmt CONFIG)
add_executable(main main.cpp)
target_link_libraries(main fmt::fmt)
```

## conan_cmake_run() high level wrapper

This function is not the recommended way of using cmake-conan any more and will be deprecated in the
near future. It will make the configure, auto-detect and install in one step so if you plan to use
any new Conan features like lockfiles or build and host profiles it's possible that the auto-detected
settings collide with the call to conan install.

### conan_cmake_run() options:

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

### IMPORTS

List of files to be imported to a local folder. Read more about imports in [Conan docs](https://docs.conan.io/en/latest/using_packages/conanfile_txt.html#imports-txt).

```cmake
conan_cmake_run(...
                IMPORTS "bin, *.dll -> ./bin"
                IMPORTS "lib, *.dylib* -> ./bin")
```

### NO_LOAD

Use ``NO_LOAD`` argument to avoid loading the _conanbuildinfo.cmake_ generated by the default ``cmake`` generator.

```cmake
include(conan.cmake)
conan_cmake_run(...
                NO_LOAD)
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
    conan_cmake_configure(REQUIRES fmt/6.1.2 GENERATORS cmake_find_package)
    conan_cmake_autodetect(settings)
    conan_cmake_install(PATH_OR_REFERENCE . BUILD missing REMOTE conancenter SETTINGS ${settings})
endif()
```


Please check the source code for other options and arguments.

## Development, contributors

There are some tests, you can run in python, with pytest, for example:

```bash
$ pytest tests.py -rA
```
