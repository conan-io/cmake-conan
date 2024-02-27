find_package(hello REQUIRED)
add_executable(appSubdir main.cpp)
target_link_libraries(appSubdir hello::hello)
