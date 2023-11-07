cmake_minimum_required(VERSION 3.24)
project(MyApp CXX)

if(OVERRIDE_CONFIG_TYPES)
  message(STATUS "Overriding config types")
  set(CMAKE_CONFIGURATION_TYPES "Debug;Release" CACHE STRING "" FORCE)
endif()

set(CMAKE_CXX_STANDARD 17)
find_package(hello REQUIRED)
find_package(bye REQUIRED)
add_executable(app main.cpp)
target_link_libraries(app hello::hello bye::bye)

option(BASIC_TEST_FIND_THREADS ... "OFF")

