# cmake-conan

![Build Status](https://github.com/conan-io/cmake-conan/actions/workflows/cmake_conan.yml/badge.svg?branch=develop2)

CMake dependency provider for the Conan C and C++ package manager.

> :warning: **Compatibility with Conan 2.0**: integration with Conan 2.0 is currently **experimental**, may have some limitations, and is subject to change, please read below. The code in this branch only supports Conan 2.0.2 and above - if you need Conan 1.x please check the `develop` branch.


## Quickstart with Conan 2.0

Prerequisites:
* CMake 3.24
* Conan 2.0.5
* A CMake-based project that contains a `conanfile.txt` or `conanfile.py` to list the required dependencies.

First, clone this repository in the `develop2` branch.

```bash
git clone https://github.com/conan-io/cmake-conan.git -b develop2
```

### Example project

This repository contains a `CMakeLists.txt` with an example project that depends on `fmt`.

```bash
cd cmake-conan/example
mkdir build
cmake -B build -S . -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=../conan_provider.cmake -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release
```

### In your own project

* Ensure you have placed a `conanfile.txt` or `conanfile.py` at the root of your project, listing your requirements. You can see [conanfile.txt](example/conanfile.txt) for an example, or check the Conan documentation for `conanfile`: [.txt docs](https://docs.conan.io/2/reference/conanfile_txt.html), [.py docs](https://docs.conan.io/2/reference/conanfile/attributes.html#requirements).

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

### Customizing Conan profiles
The CMake-Conan dependency provider will create a Conan profile where the settings (`os`, `arch`, `compiler`, `build_type`) are retrieved from what CMake has detected for the current build. Conan uses two profiles for dependencies, the _host_ and the _build_ profiles. You can read more about them [here](https://docs.conan.io/2.0/tutorial/consuming_packages/cross_building_with_conan.html?highlight=build%20profile#conan-two-profiles-model-build-and-host-profiles). In CMake-Conan, the default behaviour is as follows:

* Conan host profile: settings detected from CMake. For anything that cannot be detected from CMake, it falls back to the `default` Conan profile.
* Conan build profile: the `default` Conan profile.

Please note that for the above to work, a `default` profile must already exist. If it doesn't, `cmake-conan` will invoke Conan's autodetection mechanism which tries to guess the system defaults.

If you need to customize the profile, you can do so by modifying the value of `CONAN_HOST_PROFILE` and `CONAN_BUILD_PROFILE` and passing them as CMake cache variables. Some examples:

* `-DCONAN_HOST_PROFILE=default;auto-cmake`: perform autodetection as described above, and fallback to the default profile for anything else (default behaviour).
* `-DCONAN_HOST_PROFILE=clang16`: do not perform autodetection, and use the `clang16` profile which must exist in the Conan profiles folder (see [docs](https://docs.conan.io/2.0/reference/commands/profile.html?highlight=profiles%20folder#conan-profile-list).)
* `-DCONAN_BUILD_PROFILE=/path/to/profile`: alternatively, provide a path to a profile file that may be anywhere in the filesystem.
* `-DCONAN_HOST_PROFILE=default;custom`: semi-colon separated list of profiles. A compound profile will be used (see [docs](https://docs.conan.io/2.0/reference/commands/install.html#profiles-settings-options-conf)) - compunded from left to right, where right has the highest priority.

### Custom Conan configuration install directory

To use Conan config from a specific directory, just change the `CONAN_CONFIG_DIR` variable by passing it as CMake cache variable.

* `-DCONAN_HOST_PROFILE=default;auto-cmake`: perform autodetection as described above, and fallback to the default profile for anything else (default behaviour).

## Development, contributors

There are some tests, you can run in python, with pytest, for example:

```bash
$ pytest -rA
```
