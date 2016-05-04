cmake_minimum_required(VERSION 2.8)
project(conan_wrapper C CXX)

include(conan.cmake)

set(CONAN_DIR ${CMAKE_SOURCE_DIR}/.conan)        
conan_requirements(REQUIRES Poco/1.7.2@lasote/stable 
                   OPTIONS Poco:shared=False
                   BUILD_DIR ${CONAN_DIR}
                   )
                   
if(EXISTS ${CONAN_DIR}/conanbuildinfo.cmake)
   message(STATUS "*Conan*: Loading conanbuildinfo.cmake")
   include(${CONAN_DIR}/conanbuildinfo.cmake)
   conan_basic_setup()
endif()

add_executable(main main.cpp)
target_link_libraries(main ${CONAN_LIBS})