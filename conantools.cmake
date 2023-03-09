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
    if (CMAKE_CXX_EXTENSIONS)
        set(CXX_STANDARD "gnu${CMAKE_CXX_STANDARD}" PARENT_SCOPE)
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

    if(COMPILER MATCHES MSVC)
        set(COMPILER "msvc")
        string(SUBSTRING ${MSVC_VERSION} 0 3 COMPILER_VERSION)
    elseif(COMPILER MATCHES AppleClang)
        set(COMPILER "apple-clang")
        string(REPLACE "." ";" VERSION_LIST ${CMAKE_CXX_COMPILER_VERSION})
        list(GET VERSION_LIST 0 COMPILER_VERSION)
    endif()

    message(STATUS "Conan-cmake: [settings] compiler=${COMPILER}") 
    message(STATUS "Conan-cmake: [settings] compiler.version=${COMPILER_VERSION}")

    set(COMPILER ${COMPILER} PARENT_SCOPE)
    set(COMPILER_VERSION ${COMPILER_VERSION} PARENT_SCOPE)
endfunction()

function(detect_build_type)
    if(NOT CMAKE_CONFIGURATION_TYPES)
        # Only set when we know we are in a single-configuration generator
        # Note: we may want to fail early if `CMAKE_BUILD_TYPE` is not defined
        set(BUILD_TYPE ${CMAKE_BUILD_TYPE} PARENT_SCOPE)
    endif()
endfunction()


function(detect_host_profile output_file)
    detect_os(OS)
    detect_compiler(COMPILER COMPILER_VERSION)
    detect_cxx_standard(CXX_STANDARD)
    detect_build_type()

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
    if(BUILD_TYPE)
        string(APPEND PROFILE "build_type=${BUILD_TYPE}\n")
    endif()

    if(NOT DEFINED output_file)
        set(_FN "${CMAKE_BINARY_DIR}/profile")
    else()
        set(_FN ${output_file})
    endif()
    message(STATUS "Conan-cmake: Creating profile ${_FN}")
    file(WRITE ${_FN} ${PROFILE})
    message(STATUS "Conan-cmake: Profile: \n${PROFILE}")
endfunction()


function(conan_install)
    cmake_parse_arguments(ARGS CONAN_ARGS ${ARGN})
    # Invoke "conan install" with the provided arguments
    message(STATUS "conan install ${CMAKE_SOURCE_DIR} ${CONAN_ARGS} ${ARGN}")
    execute_process(COMMAND conan install ${CMAKE_SOURCE_DIR} ${CONAN_ARGS} ${ARGN} --format=json
                    RESULT_VARIABLE return_code
                    OUTPUT_VARIABLE conan_stdout
                    ERROR_VARIABLE conan_stderr
                    ECHO_ERROR_VARIABLE    # show the text output regardless
                    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR})
    if(NOT "${return_code}" STREQUAL "0")
        message(FATAL_ERROR "Conan install failed='${return_code}'")
        string()
    else()
        # the files are generated in a folder that depends on the layout used, if
        # one if specified, but we don't know a priori where this is. 
        # TODO: this can be made more robust if Conan can provide this in the json output
        string(JSON conan_build_folder GET ${conan_stdout} graph nodes 0 build_folder)
        # message("conan stdout: ${conan_stdout}")
        message("conan build folder: ${conan_build_folder}")
        file(GLOB_RECURSE conanrun_files LIST_DIRECTORIES false "conanrun*")
        list(GET conanrun_files 0 conanrun)
        get_filename_component(CONAN_GENERATORS_FOLDER ${conanrun} DIRECTORY)
        set(CONAN_GENERATORS_FOLDER "${CONAN_GENERATORS_FOLDER}" PARENT_SCOPE)
        set(CONAN_INSTALL_SUCCESS TRUE CACHE BOOL "Conan install has been invoked and was successful")
    endif()
endfunction()
