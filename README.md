# cmake-conan

![Build Status](https://github.com/conan-io/cmake-conan/actions/workflows/cmake_conan.yml/badge.svg?branch=develop2)

CMake dependency provider for the Conan C and C++ package manager.

> :warning: **Compatibility with Conan 2.0**: integration with Conan 2.0 is currently **experimental**, may have some limitations, and is subject to change, please read below. The code in this branch only supports Conan 2.0.2 and ablove - if you need Conan 1.x please check the `develop` branch.


## Quickstart with Conan 2.0

Prequisites:
* CMake 3.24
* Conan 2.0.2
* A CMake-based project that contains a `conanfile.txt` or `conanfile.py` to list the required dependencies.

First, clone this repository in the `develop2` branch.

```bash
git clone https://github.com/conan-io/cmake-conan.git -b develop2
```

### Example project

This repository contains a `CMakeLists.txt` with an example project that depends on `fmt`. 

```bash
cd cmake-conan
cmake --preset default
cmake --build --preset default
```

### In your own project

* Ensure you have placed a `conanfile.txt` or `conanfile.py` at the root of your project, listing your requirements. You can see [conanfile.txt](conanfile.txt) for an example, or check the Conan documentation for `conanfile`: [.txt docs](https://docs.conan.io/2/reference/conanfile_txt.html), [.py docs](https://docs.conan.io/2/reference/conanfile/attributes.html#requirements).

* When first invoking CMake to configure the project, pass `-DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=[path-to-cmake-conan]/conan_provider.cmake`. This will ensure that `conan install` is invoked from within CMake. This integration **does not require making any changes to your `CMakeLists.txt` scripts**. 

```bash
cd [your-project]
mkdir build
cmake -B build -S . -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=[path-to-cmake-conan]/conan_provider.cmake -DCMAKE_BUILD_TYPE=Release
```

### Known limitations with Conan 2.0

* Only the `CMakeDeps` generator is specified - for build settings that would otherwise be provided by `CMakeToolchain` (for example, the compiler itself or other global build settings) please invoke Conan separately as per [documentation](https://docs.conan.io/2/tutorial/consuming_packages/build_simple_cmake_project.html).
* Currently this only works such that Conan can satisfy invocations to CMake's `find_package`. For dependencies that have logic outside of `find_package`, for example, by making direct calls to `find_program`, `find_library`, `find_path` or `find_file`, these may not work correctly.
* When using a single-configuration CMake generator, you must specify a valid `CMAKE_BUILD_TYPE` (can't be left blank)
* Deriving Conan settings is currently only supported on the most common platforms with the most popular compilers.

## Development, contributors

There are some tests, you can run in python, with pytest, for example:

```bash
$ pytest tests.py -rA
```
