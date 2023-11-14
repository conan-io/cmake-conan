cmake_minimum_required(VERSION 3.24)
project(MyApp CXX)


set(CMAKE_CXX_STANDARD 17)

set(CMAKE_MODULE_PATH "${CMAKE_SOURCE_DIR}/cmake")

# Search only for "Andromeda", which has a requirement on "Orion"
# And both are "MODULE" only - this forces a recursive call to `find_package` via the dependency provider
find_package(Andromeda REQUIRED)

# Ensure that CMake module path has exactly the value it had before
if(CMAKE_MODULE_PATH  STREQUAL "${CMAKE_SOURCE_DIR}/cmake")
  message(STATUS "CMAKE_MODULE_PATH has expected value")
else()
  message(STATUS "CMAKE_MODULE_PATH DOES NOT have expected value")
endif()
