set(CONAN_MINIMUM_VERSION 2.0.5)


function(detect_os OS OS_API_LEVEL OS_VERSION)
    # it could be cross compilation
    message(STATUS "CMake-Conan: cmake_system_name=${CMAKE_SYSTEM_NAME}")
    if(CMAKE_SYSTEM_NAME AND NOT CMAKE_SYSTEM_NAME STREQUAL "Generic")
        if(${CMAKE_SYSTEM_NAME} STREQUAL "Darwin")
            set(${OS} Macos PARENT_SCOPE)
            message(STATUS "CMake-Conan: cmake_osx_deployment_target=${CMAKE_OSX_DEPLOYMENT_TARGET}")
            set(${OS_VERSION} ${CMAKE_OSX_DEPLOYMENT_TARGET} PARENT_SCOPE)
        elseif(${CMAKE_SYSTEM_NAME} STREQUAL "QNX")
            set(${OS} Neutrino PARENT_SCOPE)
        else()
            set(${OS} ${CMAKE_SYSTEM_NAME} PARENT_SCOPE)
        endif()
        if(${CMAKE_SYSTEM_NAME} STREQUAL "Android")
            string(REGEX MATCH "[0-9]+" _OS_API_LEVEL ${ANDROID_PLATFORM})
            message(STATUS "CMake-Conan: android_platform=${ANDROID_PLATFORM}")
            set(${OS_API_LEVEL} ${_OS_API_LEVEL} PARENT_SCOPE)
        endif()
    endif()
endfunction()


function(detect_arch ARCH)
    if(CMAKE_SYSTEM_PROCESSOR STREQUAL aarch64)
        set(_ARCH armv8)
    elseif(CMAKE_SYSTEM_PROCESSOR STREQUAL armv7-a)
        set(_ARCH armv7)
    elseif(CMAKE_SYSTEM_PROCESSOR STREQUAL i686)
        set(_ARCH x86)
    elseif(CMAKE_SYSTEM_PROCESSOR MATCHES "AMD64|amd64|x86_64")
        set(_ARCH x86_64)
    endif()
    message(STATUS "CMake-Conan: cmake_system_processor=${_ARCH}")
    set(${ARCH} ${_ARCH} PARENT_SCOPE)
endfunction()


function(detect_cxx_standard CXX_STANDARD)
    set(${CXX_STANDARD} ${CMAKE_CXX_STANDARD} PARENT_SCOPE)
    if(CMAKE_CXX_EXTENSIONS)
        set(${CXX_STANDARD} "gnu${CMAKE_CXX_STANDARD}" PARENT_SCOPE)
    endif()
endfunction()


function(detect_lib_cxx OS LIB_CXX)
    if(${OS} STREQUAL "Android")
        message(STATUS "CMake-Conan: android_stl=${ANDROID_STL}")
        set(${LIB_CXX} ${ANDROID_STL} PARENT_SCOPE)
    endif()
endfunction()


function(detect_compiler COMPILER COMPILER_VERSION)
    if(DEFINED CMAKE_CXX_COMPILER_ID)
        set(_COMPILER ${CMAKE_CXX_COMPILER_ID})
        set(_COMPILER_VERSION ${CMAKE_CXX_COMPILER_VERSION})
    else()
        if(NOT DEFINED CMAKE_C_COMPILER_ID)
            message(FATAL_ERROR "C or C++ compiler not defined")
        endif()
        set(_COMPILER ${CMAKE_C_COMPILER_ID})
        set(_COMPILER_VERSION ${CMAKE_C_COMPILER_VERSION})
    endif()

    message(STATUS "CMake-Conan: CMake compiler=${_COMPILER}")
    message(STATUS "CMake-Conan: CMake compiler version=${_COMPILER_VERSION}")

    if(_COMPILER MATCHES MSVC)
        set(_COMPILER "msvc")
        string(SUBSTRING ${MSVC_VERSION} 0 3 _COMPILER_VERSION)
    elseif(_COMPILER MATCHES AppleClang)
        set(_COMPILER "apple-clang")
        string(REPLACE "." ";" VERSION_LIST ${CMAKE_CXX_COMPILER_VERSION})
        list(GET VERSION_LIST 0 _COMPILER_VERSION)
    elseif(_COMPILER MATCHES Clang)
        set(_COMPILER "clang")
        string(REPLACE "." ";" VERSION_LIST ${CMAKE_CXX_COMPILER_VERSION})
        list(GET VERSION_LIST 0 _COMPILER_VERSION)
    elseif(_COMPILER MATCHES GNU)
        set(_COMPILER "gcc")
        string(REPLACE "." ";" VERSION_LIST ${CMAKE_CXX_COMPILER_VERSION})
        list(GET VERSION_LIST 0 _COMPILER_VERSION)
    endif()

    message(STATUS "CMake-Conan: [settings] compiler=${_COMPILER}")
    message(STATUS "CMake-Conan: [settings] compiler.version=${_COMPILER_VERSION}")

    set(${COMPILER} ${_COMPILER} PARENT_SCOPE)
    set(${COMPILER_VERSION} ${_COMPILER_VERSION} PARENT_SCOPE)
endfunction()

function(detect_build_type BUILD_TYPE)
    if(NOT CMAKE_CONFIGURATION_TYPES)
        # Only set when we know we are in a single-configuration generator
        # Note: we may want to fail early if `CMAKE_BUILD_TYPE` is not defined
        set(${BUILD_TYPE} ${CMAKE_BUILD_TYPE} PARENT_SCOPE)
    endif()
endfunction()


function(detect_host_profile output_file)
    detect_os(MYOS MYOS_API_LEVEL MYOS_VERSION)
    detect_arch(MYARCH)
    detect_compiler(MYCOMPILER MYCOMPILER_VERSION)
    detect_cxx_standard(MYCXX_STANDARD)
    detect_lib_cxx(MYOS MYLIB_CXX)
    detect_build_type(MYBUILD_TYPE)

    set(PROFILE "")
    string(APPEND PROFILE "include(default)\n")
    string(APPEND PROFILE "[settings]\n")
    if(MYARCH)
        string(APPEND PROFILE arch=${MYARCH} "\n")
    endif()
    if(MYOS)
        string(APPEND PROFILE os=${MYOS} "\n")
    endif()
    if(MYOS_API_LEVEL)
        string(APPEND PROFILE os.api_level=${MYOS_API_LEVEL} "\n")
    endif()
    if(MYOS_VERSION)
        string(APPEND PROFILE os.version=${MYOS_VERSION} "\n")
    endif()
    if(MYCOMPILER)
        string(APPEND PROFILE compiler=${MYCOMPILER} "\n")
    endif()
    if(MYCOMPILER_VERSION)
        string(APPEND PROFILE compiler.version=${MYCOMPILER_VERSION} "\n")
    endif()
    if(MYCXX_STANDARD)
        string(APPEND PROFILE compiler.cppstd=${MYCXX_STANDARD} "\n")
    endif()
    if(MYLIB_CXX)
        string(APPEND PROFILE compiler.libcxx=${MYLIB_CXX} "\n")
    endif()
    if(MYBUILD_TYPE)
        string(APPEND PROFILE "build_type=${MYBUILD_TYPE}\n")
    endif()

    if(NOT DEFINED output_file)
        set(_FN "${CMAKE_BINARY_DIR}/profile")
    else()
        set(_FN ${output_file})
    endif()

    string(APPEND PROFILE "[conf]\n")
    string(APPEND PROFILE "tools.cmake.cmaketoolchain:generator=${CMAKE_GENERATOR}\n")
    if(${MYOS} STREQUAL "Android")
        string(APPEND PROFILE "tools.android:ndk_path=${CMAKE_ANDROID_NDK}\n")
    endif()

    message(STATUS "CMake-Conan: Creating profile ${_FN}")
    file(WRITE ${_FN} ${PROFILE})
    message(STATUS "CMake-Conan: Profile: \n${PROFILE}")
endfunction()


function(conan_profile_detect_default)
    message(STATUS "CMake-Conan: Checking if a default profile exists")
    execute_process(COMMAND ${CONAN_COMMAND} profile path default
                    RESULT_VARIABLE return_code
                    OUTPUT_VARIABLE conan_stdout
                    ERROR_VARIABLE conan_stderr
                    ECHO_ERROR_VARIABLE    # show the text output regardless
                    ECHO_OUTPUT_VARIABLE
                    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR})
    if(NOT ${return_code} EQUAL "0")
        message(STATUS "CMake-Conan: The default profile doesn't exist, detecting it.")
        execute_process(COMMAND ${CONAN_COMMAND} profile detect
            RESULT_VARIABLE return_code
            OUTPUT_VARIABLE conan_stdout
            ERROR_VARIABLE conan_stderr
            ECHO_ERROR_VARIABLE    # show the text output regardless
            ECHO_OUTPUT_VARIABLE
            WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR})
    endif()
endfunction()


function(conan_configure)
    get_property(CONAN_INSTALL_SUCCESS GLOBAL PROPERTY CONAN_INSTALL_SUCCESS)
    if(CONAN_INSTALL_SUCCESS)
        message(FATAL_ERROR "CMake-Conan: 'conan install' already ran, conan_configure() has to be called before the first find_package()")
        return()
    endif()

    message(STATUS "CMake-Conan: Configuring conan install parameters")
    set(multiValueArgs FLAGS BUILD OPTIONS_HOST OPTIONS_BUILD PROFILE_HOST PROFILE_BUILD SETTINGS_HOST SETTINGS_BUILD CONF_HOST CONF_BUILD GENERATORS)
    cmake_parse_arguments(ARGS "" "" "${multiValueArgs}" ${ARGN})
    foreach(arg IN LISTS multiValueArgs)
        if(DEFINED ARGS_${arg})
            if("${arg}" STREQUAL "BUILD")
                set(flag "--build")
            elseif("${arg}" STREQUAL "OPTIONS_HOST")
                set(flag "--options:host")
            elseif("${arg}" STREQUAL "OPTIONS_BUILD")
                set(flag "--options:build")
            elseif("${arg}" STREQUAL "PROFILE_HOST")
                set(flag "--profile:host")
            elseif("${arg}" STREQUAL "PROFILE_BUILD")
                set(flag "--profile:build")
            elseif("${arg}" STREQUAL "SETTINGS_HOST")
                set(flag "--settings:host")
            elseif("${arg}" STREQUAL "SETTINGS_BUILD")
                set(flag "--settings:build")
            elseif("${arg}" STREQUAL "CONF_HOST")
                set(flag "--conf:host")
            elseif("${arg}" STREQUAL "CONF_BUILD")
                set(flag "--conf:build")
            elseif("${arg}" STREQUAL "GENERATORS")
                set(flag "--generator")
            endif()
            list(TRANSFORM ARGS_${arg} PREPEND "${flag};" OUTPUT_VARIABLE ${arg})
        endif()
    endforeach()

    set_property(GLOBAL PROPERTY CONAN_INSTALL_ARGUMENTS ${ARGS_FLAGS}
        ${BUILD} ${OPTIONS_HOST} ${OPTIONS_BUILD} ${PROFILE_HOST} ${PROFILE_BUILD} ${SETTINGS_HOST} ${SETTINGS_BUILD} ${CONF_HOST} ${CONF_BUILD} ${GENERATORS})
    set_property(GLOBAL PROPERTY CONAN_CONFIGURE_SUCCESS TRUE)
endfunction()


function(conan_install)
    # Invoke "conan install" with the provided arguments
    message(STATUS "CMake-Conan: conan install ${CMAKE_SOURCE_DIR} ${ARGN}")
    execute_process(COMMAND ${CONAN_COMMAND} install ${CMAKE_SOURCE_DIR} ${ARGN}
                    RESULT_VARIABLE return_code
                    OUTPUT_VARIABLE conan_stdout
                    ERROR_VARIABLE conan_stderr
                    ECHO_ERROR_VARIABLE    # show the text output regardless
                    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR})
    if(NOT "${return_code}" STREQUAL "0")
        message(FATAL_ERROR "Conan install failed='${return_code}'")
    else()
        # the files are generated in a folder that depends on the layout used, if
        # one is specified, but we don't know a priori where this is.
        # TODO: this can be made more robust if Conan can provide this in the json output
        string(JSON CONAN_GENERATORS_FOLDER GET ${conan_stdout} graph nodes 0 generators_folder)
        # message("conan stdout: ${conan_stdout}")
        message(STATUS "CMake-Conan: CONAN_GENERATORS_FOLDER=${CONAN_GENERATORS_FOLDER}")
        set_property(GLOBAL PROPERTY CONAN_GENERATORS_FOLDER "${CONAN_GENERATORS_FOLDER}")
        # reconfigure on conanfile changes
        string(JSON CONANFILE GET ${conan_stdout} graph nodes 0 label)
        message(STATUS "CMake-Conan: CONANFILE=${CMAKE_SOURCE_DIR}/${CONANFILE}")
        set_property(DIRECTORY ${CMAKE_SOURCE_DIR} APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_SOURCE_DIR}/${CONANFILE}")
        # success
        set_property(GLOBAL PROPERTY CONAN_INSTALL_SUCCESS TRUE)
    endif()
endfunction()


function(conan_get_version conan_command conan_current_version)
    execute_process(
        COMMAND ${conan_command} --version
        OUTPUT_VARIABLE conan_output
        RESULT_VARIABLE conan_result
        OUTPUT_STRIP_TRAILING_WHITESPACE
    )
    if(conan_result)
        message(FATAL_ERROR "CMake-Conan: Error when trying to run Conan")
    endif()

    string(REGEX MATCH "[0-9]+\\.[0-9]+\\.[0-9]+" conan_version ${conan_output})
    set(${conan_current_version} ${conan_version} PARENT_SCOPE)
endfunction()


function(conan_version_check)
    set(options )
    set(oneValueArgs MINIMUM CURRENT)
    set(multiValueArgs )
    cmake_parse_arguments(CONAN_VERSION_CHECK
        "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})

    if(NOT CONAN_VERSION_CHECK_MINIMUM)
        message(FATAL_ERROR "CMake-Conan: Required parameter MINIMUM not set!")
    endif()
        if(NOT CONAN_VERSION_CHECK_CURRENT)
        message(FATAL_ERROR "CMake-Conan: Required parameter CURRENT not set!")
    endif()

    if(CONAN_VERSION_CHECK_CURRENT VERSION_LESS CONAN_VERSION_CHECK_MINIMUM)
        message(FATAL_ERROR "CMake-Conan: Conan version must be ${CONAN_VERSION_CHECK_MINIMUM} or later")
    endif()
endfunction()


macro(conan_provide_dependency package_name)
    get_property(CONAN_INSTALL_SUCCESS GLOBAL PROPERTY CONAN_INSTALL_SUCCESS)
    if(NOT CONAN_INSTALL_SUCCESS)
        find_program(CONAN_COMMAND "conan" REQUIRED)
        conan_get_version(${CONAN_COMMAND} CONAN_CURRENT_VERSION)
        conan_version_check(MINIMUM ${CONAN_MINIMUM_VERSION} CURRENT ${CONAN_CURRENT_VERSION})
        message(STATUS "CMake-Conan: first find_package() found. Installing dependencies with Conan")
        conan_profile_detect_default()
        detect_host_profile(${CMAKE_BINARY_DIR}/conan_host_profile)
        get_property(CONAN_CONFIGURE_SUCCESS GLOBAL PROPERTY CONAN_CONFIGURE_SUCCESS)
        if(NOT CONAN_CONFIGURE_SUCCESS)
            message(STATUS "CMake-Conan: Using default parameters for conan install configuration")
            conan_configure(FLAGS "--format;json;--output-folder;${CMAKE_BINARY_DIR}/conan"
              BUILD missing PROFILE_HOST ${CMAKE_BINARY_DIR}/conan_host_profile GENERATORS CMakeDeps)
        endif()
        get_property(CONAN_INSTALL_ARGUMENTS GLOBAL PROPERTY CONAN_INSTALL_ARGUMENTS)
        if(NOT CMAKE_CONFIGURATION_TYPES)
            message(STATUS "CMake-Conan: Installing single configuration ${CMAKE_BUILD_TYPE}")
            conan_install(${CONAN_INSTALL_ARGUMENTS})
        else()
            message(STATUS "CMake-Conan: Installing both Debug and Release")
            conan_install(-s build_type=Release ${CONAN_INSTALL_ARGUMENTS})
            conan_install(-s build_type=Debug ${CONAN_INSTALL_ARGUMENTS})
        endif()
    else()
        message(STATUS "CMake-Conan: find_package(${ARGV1}) found, 'conan install' already ran")
    endif()

    get_property(CONAN_GENERATORS_FOLDER GLOBAL PROPERTY CONAN_GENERATORS_FOLDER)
    list(FIND CMAKE_PREFIX_PATH "${CONAN_GENERATORS_FOLDER}" index)
    if(${index} EQUAL -1)
        list(PREPEND CMAKE_PREFIX_PATH "${CONAN_GENERATORS_FOLDER}")
    endif()
    find_package(${ARGN} BYPASS_PROVIDER CMAKE_FIND_ROOT_PATH_BOTH)
endmacro()


cmake_language(
  SET_DEPENDENCY_PROVIDER conan_provide_dependency
  SUPPORTED_METHODS FIND_PACKAGE
)