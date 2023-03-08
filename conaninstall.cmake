function(detect_os OS)
    # it could be cross compilation
    message(STATUS "CMAKE_SYSTEM_NAME=${CMAKE_SYSTEM_NAME}")
    if(CMAKE_SYSTEM_NAME AND NOT CMAKE_SYSTEM_NAME STREQUAL "Generic")
        if(${CMAKE_SYSTEM_NAME} STREQUAL "Darwin")
            set(OS Macos PARENT_SCOPE)
        elseif(${CMAKE_SYSTEM_NAME} STREQUAL "QNX")
            set(OS Neutrino PARENT_SCOPE)
        else()
            set(OS ${CMAKE_SYSTEM_NAME} PARENT_SCOPE)
        endif()
    endif()
endfunction()

function(detect_compiler COMPILER COMPILER_VERSION)
    if(DEFINED CMAKE_CXX_COMPILER_ID)
        set(COMPILER ${CMAKE_CXX_COMPILER_ID})
        set(COMPILER_VERSION ${CMAKE_CXX_COMPILER_VERSION})
    else()
        if(NOT DEFINED CMAKE_C_COMPILER_ID)
            message(FATAL_ERROR "C or C++ compiler not defined")
        endif()
        set(COMPILER ${CMAKE_C_COMPILER_ID})
        set(COMPILER_VERSION ${CMAKE_C_COMPILER_VERSION})
    endif()

    message(STATUS "Conan-cmake: CMake compiler=${COMPILER}") 
    message(STATUS "Conan-cmake: CMake cmpiler version=${COMPILER_VERSION}")

    if(${COMPILER} EQUAL MSVC)
        set(COMPILER "msvc")
        string(SUBSTRING ${MSVC_VERSION} 0 3 COMPILER_VERSION)
    endif()

    message(STATUS "Conan-cmake: [settings] compiler=${COMPILER}") 
    message(STATUS "Conan-cmake: [settings] compiler.version=${COMPILER_VERSION}")

    set(COMPILER ${COMPILER} PARENT_SCOPE)
    set(COMPILER_VERSION ${COMPILER_VERSION} PARENT_SCOPE)
endfunction()

function(conan_install)
    cmake_parse_arguments(ARGS CONAN_ARGS ${ARGN})
    # Invoke "conan install" with the provided arguments
    message(STATUS "conan install ${CMAKE_CURRENT_SOURCE_DIR} ${CONAN_ARGS}")
    execute_process(COMMAND conan install ${CMAKE_CURRENT_SOURCE_DIR} ${CONAN_ARGS}
                    RESULT_VARIABLE return_code
                    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR})
    if(NOT "${return_code}" STREQUAL "0")
        message(FATAL_ERROR "Conan install failed='${return_code}'")
    endif()
endfunction()


detect_os(OS)
detect_compiler(COMPILER COMPILER_VERSION)

# TODO: Discuss what to do with the default and build profile
#execute_process(COMMAND conan profile detect --force)
set(CONAN_ARGS -s os=${OS} -s compiler=${COMPILER} -s compiler.version=${COMPILER_VERSION})
conan_install(${CONAN_ARGS})

# TODO: this is variable path
set(CMAKE_PREFIX_PATH ${CMAKE_CURRENT_BINARY_DIR}/generators)
