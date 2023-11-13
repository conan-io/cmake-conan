cmake_minimum_required(VERSION 3.24)
project(MyApp CXX)


set(CMAKE_CXX_STANDARD 17)

set(CMAKE_MODULE_PATH "${CMAKE_SOURCE_DIR}/cmake")

# Search only for "Andromeda", which has a requirement on "Orion"
# And both are "MODULE" only - this forces a recursive call to `find_package` via the dependency provider
find_package(Andromeda REQUIRED)

# Ensure that CMake module path is a list with two values:
# - the `orion-module-subfolder` is first, and the one set above (cmake-source-dir/cmake) is second
list(LENGTH CMAKE_MODULE_PATH _cmake_module_path_length)
if(NOT _cmake_module_path_length EQUAL 2)
  message(STATUS "CMAKE_MODULE_PATH DOES NOT have expected value: ${CMAKE_MODULE_PATH}")
endif()

list(GET CMAKE_MODULE_PATH 0 _cmake_module_path_first_element)
if(NOT _cmake_module_path_first_element MATCHES "^.*orion-module-subfolder$")
  message(STATUS "CMAKE_MODULE_PATH DOES NOT have expected value: ${CMAKE_MODULE_PATH}")
endif()

if(CMAKE_MODULE_PATH STREQUAL "${_cmake_module_path_first_element};${CMAKE_SOURCE_DIR}/cmake")
  message(STATUS "CMAKE_MODULE_PATH has expected value: ${CMAKE_MODULE_PATH}")
else()
  message(STATUS "CMAKE_MODULE_PATH DOES NOT have expected value: ${CMAKE_MODULE_PATH}")
endif()

