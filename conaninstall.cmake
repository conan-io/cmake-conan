include(conantools.cmake)

detect_host_profile()

# TODO: Discuss what to do with the default and build profile
# execute_process(COMMAND conan profile detect --force)
conan_install(-pr profile)

# TODO: this is variable path
set(CMAKE_PREFIX_PATH ${CMAKE_BINARY_DIR}/generators)
