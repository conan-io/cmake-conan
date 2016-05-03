cmake_minimum_required(VERSION 2.8)
project(conan_wrapper C CXX)

include(conan.cmake)
                   
conan_requirements(REQUIRES Poco/1.7.2@lasote/stable 
                   OPTIONS Poco:shared=False)

conan_basic_setup()
    
add_executable(main main.cpp)
target_link_libraries(main ${CONAN_LIBS})