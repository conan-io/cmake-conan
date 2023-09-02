cmake_minimum_required(VERSION 3.24)
project(MyToolApp CXX)

set(CMAKE_CXX_STANDARD 17)
find_package(hello REQUIRED)
find_program(
  NINJA_EXECUTABLE ninja
  PATHS ${CONAN_TOOL_PATH} REQUIRED
  NO_DEFAULT_PATH NO_CMAKE_FIND_ROOT_PATH)
