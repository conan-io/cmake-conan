cmake_minimum_required(VERSION 3.24)
project(MyApp CXX)

set(CMAKE_CXX_STANDARD 17)
conan_configure(FLAGS "--format;json;--output-folder;${CMAKE_BINARY_DIR}/conan" BUILD missing PROFILE_HOST ${CMAKE_BINARY_DIR}/conan_host_profile GENERATORS CMakeDeps CMakeToolchain)
find_package(hello REQUIRED)
find_package(bye REQUIRED)
add_executable(app main.cpp)
target_link_libraries(app hello::hello bye::bye)
