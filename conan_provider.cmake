set(CONAN_MINIMUM_VERSION 2.0.5)


function(detect_os OS OS_API_LEVEL OS_SDK OS_SUBSYSTEM OS_VERSION)
    # it could be cross compilation
    message(STATUS "CMake-Conan: cmake_system_name=${CMAKE_SYSTEM_NAME}")
    if(CMAKE_SYSTEM_NAME AND NOT CMAKE_SYSTEM_NAME STREQUAL "Generic")
        if(${CMAKE_SYSTEM_NAME} STREQUAL "Darwin")
            set(${OS} Macos PARENT_SCOPE)
        elseif(${CMAKE_SYSTEM_NAME} STREQUAL "QNX")
            set(${OS} Neutrino PARENT_SCOPE)
        elseif(${CMAKE_SYSTEM_NAME} STREQUAL "CYGWIN")
            set(${OS} Windows PARENT_SCOPE)
            set(${OS_SUBSYSTEM} cygwin PARENT_SCOPE)
        elseif(${CMAKE_SYSTEM_NAME} MATCHES "^MSYS")
            set(${OS} Windows PARENT_SCOPE)
            set(${OS_SUBSYSTEM} msys2 PARENT_SCOPE)
        else()
            set(${OS} ${CMAKE_SYSTEM_NAME} PARENT_SCOPE)
        endif()
        if(${CMAKE_SYSTEM_NAME} STREQUAL "Android")
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
                    set(apple_platform_suffix simulator)
                else()
                    set(apple_platform_suffix os)
                endif()
                if(CMAKE_OSX_SYSROOT MATCHES AppleTV)
                    set(_OS_SDK "appletv${apple_platform_suffix}")
                elseif(CMAKE_OSX_SYSROOT MATCHES iPhone)
                    set(_OS_SDK "iphone${apple_platform_suffix}")
                elseif(CMAKE_OSX_SYSROOT MATCHES Watch)
                    set(_OS_SDK "watch${apple_platform_suffix}")
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
        string(REPLACE " " ";" apple_arch_list "${CMAKE_OSX_ARCHITECTURES}")
        list(LENGTH apple_arch_list apple_arch_count)
        if(apple_arch_count GREATER 1)
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
    if(${OS} STREQUAL "Android")
        message(STATUS "CMake-Conan: android_stl=${ANDROID_STL}")
        set(${LIB_CXX} ${ANDROID_STL} PARENT_SCOPE)
    endif()
endfunction()


function(detect_compiler COMPILER COMPILER_VERSION COMPILER_RUNTIME COMPILER_RUNTIME_TYPE)
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
        # Configure compiler.runtime and compiler.runtime_type settings for MSVC
        if(CMAKE_MSVC_RUNTIME_LIBRARY)
            set(_KNOWN_MSVC_RUNTIME_VALUES "")
            list(APPEND _KNOWN_MSVC_RUNTIME_VALUES MultiThreaded MultiThreadedDLL)
            list(APPEND _KNOWN_MSVC_RUNTIME_VALUES MultiThreadedDebug MultiThreadedDebugDLL)
            list(APPEND _KNOWN_MSVC_RUNTIME_VALUES MultiThreaded$<$<CONFIG:Debug>:Debug> MultiThreaded$<$<CONFIG:Debug>:Debug>DLL)

            # only accept the 6 possible values, otherwise we don't don't know to map this
            if(NOT CMAKE_MSVC_RUNTIME_LIBRARY IN_LIST _KNOWN_MSVC_RUNTIME_VALUES)
                message(FATAL_ERROR "CMake-Conan: unable to map MSVC runtime: ${CMAKE_MSVC_RUNTIME_LIBRARY} to Conan settings")
            endif()
            
            # Runtime is "dynamic" in all cases if it ends in DLL
            if(CMAKE_MSVC_RUNTIME_LIBRARY MATCHES ".*DLL$")
                set(_COMPILER_RUNTIME "dynamic")
            else()
                set(_COMPILER_RUNTIME "static")
            endif()

            # Only define compiler.runtime_type when explicitly requested
            # If a generator expression is used, let Conan handle it conditional on build_type
            get_property(_IS_MULTI_CONFIG_GENERATOR GLOBAL PROPERTY GENERATOR_IS_MULTI_CONFIG)
            if(NOT CMAKE_MSVC_RUNTIME_LIBRARY MATCHES "<CONFIG:Debug>:Debug>")
                if(CMAKE_MSVC_RUNTIME_LIBRARY MATCHES "Debug")
                    set(_COMPILER_RUNTIME_TYPE "Debug")
                else()
                    set(_COMPILER_RUNTIME_TYPE "Release")
                endif()
            endif()

            unset(_KNOWN_MSVC_RUNTIME_VALUES)
            unset(_IS_MULTI_CONFIG_GENERATOR)
        endif()
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
    if (_COMPILER_RUNTIME)
        message(STATUS "CMake-Conan: [settings] compiler.runtime=${_COMPILER_RUNTIME}")
    endif()
    if (_COMPILER_RUNTIME_TYPE)
        message(STATUS "CMake-Conan: [settings] compiler.runtime_type=${_COMPILER_RUNTIME_TYPE}")
    endif()

    set(${COMPILER} ${_COMPILER} PARENT_SCOPE)
    set(${COMPILER_VERSION} ${_COMPILER_VERSION} PARENT_SCOPE)
    set(${COMPILER_RUNTIME} ${_COMPILER_RUNTIME} PARENT_SCOPE)
    set(${COMPILER_RUNTIME_TYPE} ${_COMPILER_RUNTIME_TYPE} PARENT_SCOPE)
endfunction()

function(detect_build_type BUILD_TYPE)
    get_property(_MULTICONFIG_GENERATOR GLOBAL PROPERTY GENERATOR_IS_MULTI_CONFIG)
    if(NOT _MULTICONFIG_GENERATOR)
        # Only set when we know we are in a single-configuration generator
        # Note: we may want to fail early if `CMAKE_BUILD_TYPE` is not defined
        set(${BUILD_TYPE} ${CMAKE_BUILD_TYPE} PARENT_SCOPE)
    endif()
endfunction()


function(detect_host_profile output_file)
    detect_os(MYOS MYOS_API_LEVEL MYOS_SDK MYOS_SUBSYSTEM MYOS_VERSION)
    detect_arch(MYARCH)
    detect_compiler(MYCOMPILER MYCOMPILER_VERSION MYCOMPILER_RUNTIME MYCOMPILER_RUNTIME_TYPE)
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
    if(MYOS_SDK)
        string(APPEND PROFILE os.sdk=${MYOS_SDK} "\n")
    endif()
    if(MYOS_SUBSYSTEM)
        string(APPEND PROFILE os.subsystem=${MYOS_SUBSYSTEM} "\n")
    endif()
    if(MYCOMPILER)
        string(APPEND PROFILE compiler=${MYCOMPILER} "\n")
    endif()
    if(MYCOMPILER_VERSION)
        string(APPEND PROFILE compiler.version=${MYCOMPILER_VERSION} "\n")
    endif()
    if(MYCOMPILER_RUNTIME)
        string(APPEND PROFILE compiler.runtime=${MYCOMPILER_RUNTIME} "\n")
    endif()
    if(MYCOMPILER_RUNTIME_TYPE)
        string(APPEND PROFILE compiler.runtime_type=${MYCOMPILER_RUNTIME_TYPE} "\n")
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
        get_property(_MULTICONFIG_GENERATOR GLOBAL PROPERTY GENERATOR_IS_MULTI_CONFIG)
        if(NOT _MULTICONFIG_GENERATOR)
            message(STATUS "CMake-Conan: Installing single configuration ${CMAKE_BUILD_TYPE}")
            conan_install(-pr ${CMAKE_BINARY_DIR}/conan_host_profile --build=missing -g CMakeDeps)
        else()
            message(STATUS "CMake-Conan: Installing both Debug and Release")
            conan_install(-pr ${CMAKE_BINARY_DIR}/conan_host_profile -s build_type=Release --build=missing -g CMakeDeps)
            conan_install(-pr ${CMAKE_BINARY_DIR}/conan_host_profile -s build_type=Debug --build=missing -g CMakeDeps)
        endif()
        unset(_MULTICONFIG_GENERATOR)
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
    set(_find_args "${ARGN}")
    list(REMOVE_ITEM _find_args "REQUIRED")
    if(NOT "MODULE" IN_LIST _find_args)
        find_package(${package_name} ${_find_args} BYPASS_PROVIDER PATHS "${CONAN_GENERATORS_FOLDER}" NO_DEFAULT_PATH NO_CMAKE_FIND_ROOT_PATH)
    endif()

    # Invoke find_package a second time - if the first call succeeded,
    # this will simply reuse the result. If not, fall back to CMake default search
    # behaviour, also allowing modules to be searched.
    set(_cmake_module_path_orig "${CMAKE_MODULE_PATH}")
    list(PREPEND CMAKE_MODULE_PATH "${CONAN_GENERATORS_FOLDER}")
    if(NOT ${package_name}_FOUND)
        find_package(${package_name} ${ARGN} BYPASS_PROVIDER)
    endif()

    set(CMAKE_MODULE_PATH "${_cmake_module_path_orig}")
    unset(_find_args)
    unset(_cmake_module_path_orig)
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