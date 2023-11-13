cmake_minimum_required(VERSION 3.24)
project(MyApp CXX)


set(CMAKE_CXX_STANDARD 17)

set(CMAKE_MODULE_PATH "${CMAKE_SOURCE_DIR}/cmake")

# Search only for "Andromeda", which has a requirement on "Orion"
# And both are "MODULE" only - this forces a recursive call to `find_package` via the dependency provider
find_package(Andromeda REQUIRED)

# Ensure that CMake module path is a list with two values:
# - the `orion-module-subfolder` is first, and the one set above (cmake-source-dir/cmake) is second
# Note: on multi-config generators, CMakeDeps will prepend it twice (one for Debug, one for Release)
get_property(is_multi_config GLOBAL PROPERTY GENERATOR_IS_MULTI_CONFIG)
if(is_multi_config)
  set(_expected_list_size 3)
else()
  set(_expected_list_size 2)
endif()

list(LENGTH CMAKE_MODULE_PATH _cmake_module_path_length)
if(NOT _cmake_module_path_length EQUAL ${_expected_list_size})
  message(STATUS "CMAKE_MODULE_PATH DOES NOT have expected value 1: ${CMAKE_MODULE_PATH}")
endif()

list(GET CMAKE_MODULE_PATH 0 _cmake_module_path_first_element)
if(NOT _cmake_module_path_first_element MATCHES "^.*orion-module-subfolder$")
  message(STATUS "CMAKE_MODULE_PATH DOES NOT have expected value 2: ${_cmake_module_path_first_element}")
endif()

if(is_multi_config)
  list(GET CMAKE_MODULE_PATH 1 _cmake_module_path_second_element)
  if(NOT _cmake_module_path_second_element MATCHES "^.*orion-module-subfolder$")
    message(STATUS "CMAKE_MODULE_PATH DOES NOT have expected value 3: ${_cmake_module_path_second_element}")
  endif()
  set(_expected_cmake_module_path "${_cmake_module_path_first_element};${_cmake_module_path_second_element};${CMAKE_SOURCE_DIR}/cmake")
else()
  set(_expected_cmake_module_path "${_cmake_module_path_first_element};${CMAKE_SOURCE_DIR}/cmake")
endif()

if(CMAKE_MODULE_PATH STREQUAL "${_expected_cmake_module_path}")
  message(STATUS "CMAKE_MODULE_PATH has expected value: ${CMAKE_MODULE_PATH}")
else()
  message(STATUS "CMAKE_MODULE_PATH DOES NOT have expected value 4: ${CMAKE_MODULE_PATH}")
endif()

