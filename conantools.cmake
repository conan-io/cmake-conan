function(detect_os OS)
    # it could be cross compilation
    message(STATUS "Conan-cmake: cmake_system_name=${CMAKE_SYSTEM_NAME}")
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


function(detect_cxx_standard CXX_STANDARD)
    set(CXX_STANDARD ${CMAKE_CXX_STANDARD} PARENT_SCOPE)
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


function(detect_host_profile)
    detect_os(OS)
    detect_compiler(COMPILER COMPILER_VERSION)
    detect_cxx_standard(CXX_STANDARD)

    set(PROFILE "")
    string(APPEND PROFILE "include(default)\n")
    string(APPEND PROFILE "[settings]\n")
    if(OS)
        string(APPEND PROFILE os=${OS} "\n")
    endif()
    if(COMPILER)
        string(APPEND PROFILE compiler=${COMPILER} "\n")
    endif()
    if(COMPILER_VERSION)
        string(APPEND PROFILE compiler.version=${COMPILER_VERSION} "\n")
    endif()
    if(CXX_STANDARD)
        string(APPEND PROFILE compiler.cppstd=${CXX_STANDARD} "\n")
    endif()

    set(_FN "${CMAKE_BINARY_DIR}/profile")
    message(STATUS "Conan-cmake: Creating profile ${_FN}")
    file(WRITE ${_FN} ${PROFILE})
    message(STATUS "Conan-cmake: Profile: \n${PROFILE}")
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
