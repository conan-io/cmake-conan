set(CONAN_MINIMUM_VERSION 2.0.5)


function(detect_os OS OS_API_LEVEL OS_SDK OS_SUBSYSTEM OS_VERSION)
    # it could be cross compilation
    message(STATUS "CMake-Conan: cmake_system_name=${CMAKE_SYSTEM_NAME}")
    if(CMAKE_SYSTEM_NAME AND NOT CMAKE_SYSTEM_NAME STREQUAL "Generic")
        if(CMAKE_SYSTEM_NAME STREQUAL "Darwin")
            set(${OS} Macos PARENT_SCOPE)
        elseif(CMAKE_SYSTEM_NAME STREQUAL "QNX")
            set(${OS} Neutrino PARENT_SCOPE)
        elseif(CMAKE_SYSTEM_NAME STREQUAL "CYGWIN")
            set(${OS} Windows PARENT_SCOPE)
            set(${OS_SUBSYSTEM} cygwin PARENT_SCOPE)
        elseif(CMAKE_SYSTEM_NAME MATCHES "^MSYS")
            set(${OS} Windows PARENT_SCOPE)
            set(${OS_SUBSYSTEM} msys2 PARENT_SCOPE)
        else()
            set(${OS} ${CMAKE_SYSTEM_NAME} PARENT_SCOPE)
        endif()
        if(CMAKE_SYSTEM_NAME STREQUAL "Android")
            string(REGEX MATCH "[0-9]+" _OS_API_LEVEL ${ANDROID_PLATFORM})
            message(STATUS "CMake-Conan: android_platform=${ANDROID_PLATFORM}")
            set(${OS_API_LEVEL} ${_OS_API_LEVEL} PARENT_SCOPE)
        endif()
        if(CMAKE_SYSTEM_NAME MATCHES "Darwin|iOS|tvOS|watchOS")
            # CMAKE_OSX_SYSROOT contains the full path to the SDK for MakeFile/Ninja
            # generators, but just has the original input string for Xcode.
            if(NOT IS_DIRECTORY ${CMAKE_OSX_SYSROOT})
                set(_OS_SDK ${CMAKE_OSX_SYSROOT})
            else()
                if(CMAKE_OSX_SYSROOT MATCHES Simulator)
                    set(_APPLE_PLATFORM_SUFFIX simulator)
                else()
                    set(_APPLE_PLATFORM_SUFFIX os)
                endif()
                if(CMAKE_OSX_SYSROOT MATCHES AppleTV)
                    set(_OS_SDK "appletv${_APPLE_PLATFORM_SUFFIX}")
                elseif(CMAKE_OSX_SYSROOT MATCHES iPhone)
                    set(_OS_SDK "iphone${_APPLE_PLATFORM_SUFFIX}")
                elseif(CMAKE_OSX_SYSROOT MATCHES Watch)
                    set(_OS_SDK "watch${_APPLE_PLATFORM_SUFFIX}")
                endif()
            endif()
            if(DEFINED _OS_SDK)
                message(STATUS "CMake-Conan: cmake_osx_sysroot=${CMAKE_OSX_SYSROOT}")
                set(${OS_SDK} ${_OS_SDK} PARENT_SCOPE)
            endif()
            if(DEFINED CMAKE_OSX_DEPLOYMENT_TARGET)
                message(STATUS "CMake-Conan: cmake_osx_deployment_target=${CMAKE_OSX_DEPLOYMENT_TARGET}")
                set(${OS_VERSION} ${CMAKE_OSX_DEPLOYMENT_TARGET} PARENT_SCOPE)
            endif()
        endif()
    endif()
endfunction()


function(detect_arch ARCH)
    # CMAKE_OSX_ARCHITECTURES can contain multiple architectures, but Conan only supports one.
    # Therefore this code only finds one. If the recipes support multiple architectures, the
    # build will work. Otherwise, there will be a linker error for the missing architecture(s).
    if(DEFINED CMAKE_OSX_ARCHITECTURES)
        string(REPLACE " " ";" _APPLE_ARCH_LIST "${CMAKE_OSX_ARCHITECTURES}")
        list(LENGTH _APPLE_ARCH_LIST _APPLE_ARCH_COUNT)
        if(_APPLE_ARCH_COUNT GREATER 1)
            message(WARNING "CMake-Conan: Multiple architectures detected, this will only work if Conan recipe(s) produce fat binaries.")
        endif()
    endif()
    if(CMAKE_SYSTEM_PROCESSOR MATCHES "aarch64|ARM64|arm64" OR CMAKE_OSX_ARCHITECTURES MATCHES arm64)
        set(_ARCH armv8)
    elseif(CMAKE_SYSTEM_PROCESSOR MATCHES "armv7-a|armv7l" OR CMAKE_OSX_ARCHITECTURES MATCHES armv7)
        set(_ARCH armv7)
    elseif(CMAKE_OSX_ARCHITECTURES MATCHES armv7s)
        set(_ARCH armv7s)
    elseif(CMAKE_SYSTEM_PROCESSOR MATCHES "i686" OR CMAKE_OSX_ARCHITECTURES MATCHES i386)
        set(_ARCH x86)
    elseif(CMAKE_SYSTEM_PROCESSOR MATCHES "AMD64|amd64|x86_64" OR CMAKE_OSX_ARCHITECTURES MATCHES x86_64)
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
    if(OS STREQUAL "Android")
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
    detect_os(_OS _OS_API_LEVEL _OS_SDK _OS_SUBSYSTEM _OS_VERSION)
    detect_arch(_ARCH)
    detect_compiler(_COMPILER _COMPILER_VERSION)
    detect_cxx_standard(_CXX_STANDARD)
    detect_lib_cxx(_OS _LIB_CXX)
    detect_build_type(_BUILD_TYPE)

    set(_PROFILE "")
    string(APPEND _PROFILE "include(default)\n")
    string(APPEND _PROFILE "[settings]\n")
    if(_ARCH)
        string(APPEND _PROFILE arch=${_ARCH} "\n")
    endif()
    if(_OS)
        string(APPEND _PROFILE os=${_OS} "\n")
    endif()
    if(_OS_API_LEVEL)
        string(APPEND _PROFILE os.api_level=${_OS_API_LEVEL} "\n")
    endif()
    if(_OS_VERSION)
        string(APPEND _PROFILE os.version=${_OS_VERSION} "\n")
    endif()
    if(_OS_SDK)
        string(APPEND _PROFILE os.sdk=${_OS_SDK} "\n")
    endif()
    if(_OS_SUBSYSTEM)
        string(APPEND _PROFILE os.subsystem=${_OS_SUBSYSTEM} "\n")
    endif()
    if(_COMPILER)
        string(APPEND _PROFILE compiler=${_COMPILER} "\n")
    endif()
    if(_COMPILER_VERSION)
        string(APPEND _PROFILE compiler.version=${_COMPILER_VERSION} "\n")
    endif()
    if(_CXX_STANDARD)
        string(APPEND _PROFILE compiler.cppstd=${_CXX_STANDARD} "\n")
    endif()
    if(_LIB_CXX)
        string(APPEND _PROFILE compiler.libcxx=${_LIB_CXX} "\n")
    endif()
    if(_BUILD_TYPE)
        string(APPEND _PROFILE "build_type=${_BUILD_TYPE}\n")
    endif()

    if(NOT DEFINED output_file)
        set(_FN "${CMAKE_BINARY_DIR}/profile")
    else()
        set(_FN ${output_file})
    endif()

    string(APPEND _PROFILE "[conf]\n")
    string(APPEND _PROFILE "tools.cmake.cmaketoolchain:generator=${CMAKE_GENERATOR}\n")
    if(_OS STREQUAL "Android")
        string(APPEND _PROFILE "tools.android:ndk_path=${CMAKE_ANDROID_NDK}\n")
    endif()

    message(STATUS "CMake-Conan: Creating profile ${_FN}")
    file(WRITE ${_FN} ${_PROFILE})
    message(STATUS "CMake-Conan: Profile: \n${_PROFILE}")
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


function(conan_install)
    cmake_parse_arguments(ARGS CONAN_ARGS ${ARGN})
    set(CONAN_OUTPUT_FOLDER ${CMAKE_BINARY_DIR}/conan)
    # Invoke "conan install" with the provided arguments
    set(CONAN_ARGS ${CONAN_ARGS} -of=${CONAN_OUTPUT_FOLDER})
    message(STATUS "CMake-Conan: conan install ${CMAKE_SOURCE_DIR} ${CONAN_ARGS} ${ARGN}")
    execute_process(COMMAND ${CONAN_COMMAND} install ${CMAKE_SOURCE_DIR} ${CONAN_ARGS} ${ARGN} --format=json
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
    set(_OPTIONS )
    set(_ONE_VALUE_ARGS MINIMUM CURRENT)
    set(_MULTI_VALUE_ARGS )
    cmake_parse_arguments(CONAN_VERSION_CHECK
        "${_OPTIONS}" "${_ONE_VALUE_ARGS}" "${_MULTI_VALUE_ARGS}" ${ARGN})

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


macro(conan_provide_dependency method package_name)
    set_property(GLOBAL PROPERTY CONAN_PROVIDE_DEPENDENCY_INVOKED TRUE)
    get_property(CONAN_INSTALL_SUCCESS GLOBAL PROPERTY CONAN_INSTALL_SUCCESS)
    if(NOT CONAN_INSTALL_SUCCESS)
        find_program(CONAN_COMMAND "conan" REQUIRED)
        conan_get_version(${CONAN_COMMAND} CONAN_CURRENT_VERSION)
        conan_version_check(MINIMUM ${CONAN_MINIMUM_VERSION} CURRENT ${CONAN_CURRENT_VERSION})
        message(STATUS "CMake-Conan: first find_package() found. Installing dependencies with Conan")
        conan_profile_detect_default()
        detect_host_profile(${CMAKE_BINARY_DIR}/conan_host_profile)
        if(NOT CMAKE_CONFIGURATION_TYPES)
            message(STATUS "CMake-Conan: Installing single configuration ${CMAKE_BUILD_TYPE}")
            conan_install(-pr ${CMAKE_BINARY_DIR}/conan_host_profile --build=missing -g CMakeDeps)
        else()
            message(STATUS "CMake-Conan: Installing both Debug and Release")
            conan_install(-pr ${CMAKE_BINARY_DIR}/conan_host_profile -s build_type=Release --build=missing -g CMakeDeps)
            conan_install(-pr ${CMAKE_BINARY_DIR}/conan_host_profile -s build_type=Debug --build=missing -g CMakeDeps)
        endif()
    else()
        message(STATUS "CMake-Conan: find_package(${ARGV1}) found, 'conan install' already ran")
    endif()

    get_property(CONAN_GENERATORS_FOLDER GLOBAL PROPERTY CONAN_GENERATORS_FOLDER)

    # Ensure that we consider Conan-provided packages ahead of any other,
    # irrespective of other settings that modify the search order or search paths
    # This follows the guidelines from the find_package documentation
    #  (https://cmake.org/cmake/help/latest/command/find_package.html):
    #       find_package (<PackageName> PATHS paths... NO_DEFAULT_PATH)
    #       find_package (<PackageName>)

    # Filter out `REQUIRED` from the argument list, as the first call may fail
    set(_FIND_ARGS "${ARGN}")
    list(REMOVE_ITEM _FIND_ARGS "REQUIRED")
    if(NOT "MODULE" IN_LIST _FIND_ARGS)
        find_package(${package_name} ${_FIND_ARGS} BYPASS_PROVIDER PATHS "${CONAN_GENERATORS_FOLDER}" NO_DEFAULT_PATH NO_CMAKE_FIND_ROOT_PATH)
    endif()

    # Invoke find_package a second time - if the first call succeeded,
    # this will simply reuse the result. If not, fall back to CMake default search
    # behaviour, also allowing modules to be searched.
    set(_CMAKE_MODULE_PATH_ORIG "${CMAKE_MODULE_PATH}")
    list(PREPEND CMAKE_MODULE_PATH "${CONAN_GENERATORS_FOLDER}")
    if(NOT ${package_name}_FOUND)
        find_package(${package_name} ${ARGN} BYPASS_PROVIDER)
    endif()

    set(CMAKE_MODULE_PATH "${_CMAKE_MODULE_PATH_ORIG}")
    unset(_FIND_ARGS)
    unset(_CMAKE_MODULE_PATH_ORIG)
endmacro()


cmake_language(
  SET_DEPENDENCY_PROVIDER conan_provide_dependency
  SUPPORTED_METHODS FIND_PACKAGE
)


macro(conan_provide_dependency_check)
    set(_CONAN_PROVIDE_DEPENDENCY_INVOKED FALSE)
    get_property(_CONAN_PROVIDE_DEPENDENCY_INVOKED GLOBAL PROPERTY CONAN_PROVIDE_DEPENDENCY_INVOKED)
    if(NOT _CONAN_PROVIDE_DEPENDENCY_INVOKED)
        message(WARNING "Conan is correctly configured as dependency provider, "
                        "but Conan has not been invoked. Please add at least one "
                        "call to `find_package()`.")
        if(DEFINED CONAN_COMMAND)
            # supress warning in case `CONAN_COMMAND` was specified but unused.
            set(_CONAN_COMMAND ${CONAN_COMMAND})
            unset(_CONAN_COMMAND)
        endif()
    endif()
    unset(_CONAN_PROVIDE_DEPENDENCY_INVOKED)
endmacro()


# Add a deferred call at the end of processing the top-level directory
# to check if the dependency provider was invoked at all.
cmake_language(DEFER DIRECTORY "${CMAKE_SOURCE_DIR}" CALL conan_provide_dependency_check)
