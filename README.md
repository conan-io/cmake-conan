# cmake-conan

![Build Status](https://github.com/conan-io/cmake-conan/actions/workflows/cmake_conan.yml/badge.svg)

CMake dependency provider for the Conan C and C++ package manager.

> :warning: **Compatibility with Conan 2.0**: compatibility with Conan 2.0 is currently **experimental** and may have some limitations, please read below.

## Repository layout

The branches in this repo are:
- **develop**: PR are merged to this branch. Latest state of development, support only for Conan 1.X.
- **develop2**: Experimental support for Conan 2.0
- **master**: Latest release
- **tagged releases**: https://github.com/conan-io/cmake-conan/releases.

## Quickstart with Conan 2.0

Prequisites:
* CMake 3.24
* Conan 2.0.2
* A CMake-based project that contains a `conanfile.txt` or `conanfile.py` to list the required dependencies.

First, clone this repository in the `develop2` branch.

```bash
git clone https://github.com/conan-io/cmake-conan.git -b develop2
```

When initializing CMake for your project, specify Conan as the dependency provider, the following way:

``` bash
cmake -B [build-dir] -S [source-dir] -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=[path-to-cmake-conan]/conan_provider.cmake
```

This will ensure that `conan install` is invoked from within CMake. This integration **does not require making any changes to your `CMakeLists.txt` scripts**, but it does assume a valid `conanfile.txt` or `conanfile.py` exists in the root of the source directory.

### Known limitations with Conan 2.0

* Only the `CMakeDeps` generator is specified - for build settings that would otherwise be provided by `CMakeToolchain` (for example, the compiler itself or other global build settings) please invoke Conan separately as per documentation.
* Currently this only works such that Conan can satisfy invocations to CMake's `find_package`. For dependencies that have logic outside of `find_package`, for example, by making direct calls to `find_program`, `find_library`, `find_path` or `find_file`, these may not work correctly.
* When using a single-configuration CMake generator, you must specify a valid `CMAKE_BUILD_TYPE` (can't be left blank)
* Deriving Conan settings is currently only supported on the most common platforms with the most popular compilers.

## Development, contributors

There are some tests, you can run in python, with pytest, for example:

```bash
$ pytest tests.py -rA
```
