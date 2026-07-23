# The MIT License (MIT)
#
# Copyright (c) 2024 JFrog
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

set(CONAN_MINIMUM_VERSION 2.0.5)

# Create a new policy scope and set the minimum required cmake version so the
# features behind a policy setting like if(... IN_LIST ...) behaves as expected
# even if the parent project does not specify a minimum cmake version or a minimum
# version less than this module requires (e.g. 3.0) before the first project() call.
# (see: https://cmake.org/cmake/help/latest/variable/CMAKE_PROJECT_TOP_LEVEL_INCLUDES.html)
#
# The policy-affecting calls like cmake_policy(SET...) or `cmake_minimum_required` only
# affects the current policy scope, i.e. between the PUSH and POP in this case.
#
# https://cmake.org/cmake/help/book/mastering-cmake/chapter/Policies.html#the-policy-stack
cmake_policy(PUSH)
cmake_minimum_required(VERSION 3.24)


function(detect_os os os_api_level os_sdk os_subsystem os_version)
    # it could be cross compilation
    message(STATUS "CMake-Conan: cmake_system_name=${CMAKE_SYSTEM_NAME}")
    if(CMAKE_SYSTEM_NAME AND NOT CMAKE_SYSTEM_NAME STREQUAL "Generic")
        if(CMAKE_SYSTEM_NAME STREQUAL "Darwin")
            set(${os} Macos PARENT_SCOPE)
        elseif(CMAKE_SYSTEM_NAME STREQUAL "QNX")
            set(${os} Neutrino PARENT_SCOPE)
        elseif(CMAKE_SYSTEM_NAME STREQUAL "CYGWIN")
            set(${os} Windows PARENT_SCOPE)
            set(${os_subsystem} cygwin PARENT_SCOPE)
        elseif(CMAKE_SYSTEM_NAME MATCHES "^MSYS")
            set(${os} Windows PARENT_SCOPE)
            set(${os_subsystem} msys2 PARENT_SCOPE)
        elseif(CMAKE_SYSTEM_NAME STREQUAL "Emscripten")
            # https://github.com/emscripten-core/emscripten/blob/4.0.6/cmake/Modules/Platform/Emscripten.cmake#L17C1-L17C34
            set(${os} Emscripten PARENT_SCOPE)
        else()
            set(${os} ${CMAKE_SYSTEM_NAME} PARENT_SCOPE)
        endif()
        if(CMAKE_SYSTEM_NAME STREQUAL "Android")
            if(DEFINED ANDROID_PLATFORM)
                string(REGEX MATCH "[0-9]+" _os_api_level ${ANDROID_PLATFORM})
            elseif(DEFINED CMAKE_SYSTEM_VERSION)
                set(_os_api_level ${CMAKE_SYSTEM_VERSION})
            endif()
            message(STATUS "CMake-Conan: android api level=${_os_api_level}")
            set(${os_api_level} ${_os_api_level} PARENT_SCOPE)
        endif()
        if(CMAKE_SYSTEM_NAME MATCHES "Darwin|iOS|tvOS|watchOS")
            # CMAKE_OSX_SYSROOT contains the full path to the SDK for MakeFile/Ninja
            # generators, but just has the original input string for Xcode.
            if(NOT IS_DIRECTORY ${CMAKE_OSX_SYSROOT})
                set(_os_sdk ${CMAKE_OSX_SYSROOT})
            else()
                if(CMAKE_OSX_SYSROOT MATCHES Simulator)
                    set(apple_platform_suffix simulator)
                else()
                    set(apple_platform_suffix os)
                endif()
                if(CMAKE_OSX_SYSROOT MATCHES AppleTV)
                    set(_os_sdk "appletv${apple_platform_suffix}")
                elseif(CMAKE_OSX_SYSROOT MATCHES iPhone)
                    set(_os_sdk "iphone${apple_platform_suffix}")
                elseif(CMAKE_OSX_SYSROOT MATCHES Watch)
                    set(_os_sdk "watch${apple_platform_suffix}")
                endif()
            endif()
            if(DEFINED os_sdk)
                message(STATUS "CMake-Conan: cmake_osx_sysroot=${CMAKE_OSX_SYSROOT}")
                set(${os_sdk} ${_os_sdk} PARENT_SCOPE)
            endif()
            if(DEFINED CMAKE_OSX_DEPLOYMENT_TARGET)
                message(STATUS "CMake-Conan: cmake_osx_deployment_target=${CMAKE_OSX_DEPLOYMENT_TARGET}")
                set(${os_version} ${CMAKE_OSX_DEPLOYMENT_TARGET} PARENT_SCOPE)
            endif()
        endif()
    endif()
endfunction()


function(convert_to_conan_arch host_arch arch)
    # Converts a host architecture name to the Conan arch setting value, empty for
    # unknown names
    set(_arch "")
    if(host_arch MATCHES "aarch64|arm64|ARM64")
        set(_arch armv8)
    elseif(host_arch MATCHES "armv7|armv7-a|armv7l|ARMV7")
        set(_arch armv7)
    elseif(host_arch MATCHES armv7s)
        set(_arch armv7s)
    elseif(host_arch MATCHES "i686|i386|X86")
        set(_arch x86)
    elseif(host_arch MATCHES "AMD64|amd64|x86_64|x64")
        set(_arch x86_64)
    endif()
    set(${arch} "${_arch}" PARENT_SCOPE)
endfunction()


function(detect_arch arch)
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
    if(CMAKE_SYSTEM_NAME MATCHES "Darwin|iOS|tvOS|watchOS" AND NOT CMAKE_OSX_ARCHITECTURES STREQUAL "")
        set(host_arch ${CMAKE_OSX_ARCHITECTURES})
    elseif(MSVC)
        set(host_arch ${CMAKE_CXX_COMPILER_ARCHITECTURE_ID})
    else()
        set(host_arch ${CMAKE_SYSTEM_PROCESSOR})
    endif()
    convert_to_conan_arch("${host_arch}" _arch)
    if(EMSCRIPTEN)
        # https://github.com/emscripten-core/emscripten/blob/4.0.6/cmake/Modules/Platform/Emscripten.cmake#L294C1-L294C80
        set(_arch wasm)
    endif()
    message(STATUS "CMake-Conan: cmake_system_processor=${_arch}")
    set(${arch} ${_arch} PARENT_SCOPE)
endfunction()


function(detect_osx_universal_archs archs)
    # Two distinct supported architectures in CMAKE_OSX_ARCHITECTURES on macOS mean a
    # universal binary build: one "conan install" per architecture plus a lipo merge,
    # since Conan resolves a single architecture per install. The first architecture
    # is the primary one, it provides the profile arch and the generators. Returns an
    # empty list for anything else, which falls through to the detect_arch flow.
    set(${archs} "" PARENT_SCOPE)
    if(NOT CMAKE_SYSTEM_NAME STREQUAL "Darwin" OR NOT CMAKE_OSX_ARCHITECTURES)
        return()
    endif()
    # Documented as a ;-list, but also accept the space-separated form
    string(REPLACE " " ";" _host_archs "${CMAKE_OSX_ARCHITECTURES}")
    list(REMOVE_ITEM _host_archs "")
    list(LENGTH _host_archs _host_count)
    if(_host_count LESS 2)
        return()
    endif()
    if(_host_count GREATER 2)
        message(FATAL_ERROR "CMake-Conan: at most two architectures are supported for a "
                "universal binary build, got '${CMAKE_OSX_ARCHITECTURES}'. Set "
                "CONAN_OSX_UNIVERSAL_BINARIES=OFF to restore the previous single-install behavior.")
    endif()

    set(_archs "")
    set(_unsupported "")
    foreach(_host_arch IN LISTS _host_archs)
        convert_to_conan_arch("${_host_arch}" _arch)
        if(_arch MATCHES "^(armv8|x86_64)$")
            list(APPEND _archs ${_arch})
        else()
            list(APPEND _unsupported ${_host_arch})
        endif()
    endforeach()
    if(_unsupported)
        message(FATAL_ERROR "CMake-Conan: cannot map '${_unsupported}' from "
                "CMAKE_OSX_ARCHITECTURES='${CMAKE_OSX_ARCHITECTURES}' to a Conan architecture "
                "for a universal binary build. Supported: arm64 and x86_64. Set "
                "CONAN_OSX_UNIVERSAL_BINARIES=OFF to restore the previous single-install behavior.")
    endif()
    list(REMOVE_DUPLICATES _archs)
    list(LENGTH _archs _unique_count)
    if(_unique_count LESS 2)
        message(FATAL_ERROR "CMake-Conan: CMAKE_OSX_ARCHITECTURES='${CMAKE_OSX_ARCHITECTURES}' "
                "maps to Conan architecture '${_archs}' more than once; a universal binary "
                "build needs two distinct architectures. Set CONAN_OSX_UNIVERSAL_BINARIES=OFF "
                "to restore the previous single-install behavior.")
    endif()

    message(STATUS "CMake-Conan: cmake_system_processor=${_archs}")
    set(${archs} ${_archs} PARENT_SCOPE)
endfunction()


function(detect_cxx_standard compiler cxx_standard)
    set(${cxx_standard} ${CMAKE_CXX_STANDARD} PARENT_SCOPE)
    if(CMAKE_CXX_EXTENSIONS)
        if(compiler STREQUAL "msvc")
            set(${cxx_standard} "${CMAKE_CXX_STANDARD}" PARENT_SCOPE)
        else()
            set(${cxx_standard} "gnu${CMAKE_CXX_STANDARD}" PARENT_SCOPE)
        endif()
    endif()
endfunction()


macro(detect_gnu_libstdcxx)
    # _conan_is_gnu_libstdcxx true if GNU libstdc++
    check_cxx_source_compiles("
    #include <cstddef>
    #if !defined(__GLIBCXX__) && !defined(__GLIBCPP__)
    static_assert(false);
    #endif
    int main(){}" _conan_is_gnu_libstdcxx)

    # _conan_gnu_libstdcxx_is_cxx11_abi true if C++11 ABI
    check_cxx_source_compiles("
    #include <string>
    static_assert(sizeof(std::string) != sizeof(void*), \"using libstdc++\");
    int main () {}" _conan_gnu_libstdcxx_is_cxx11_abi)

    set(_conan_gnu_libstdcxx_suffix "")
    if(_conan_gnu_libstdcxx_is_cxx11_abi)
        set(_conan_gnu_libstdcxx_suffix "11")
    endif()
    unset (_conan_gnu_libstdcxx_is_cxx11_abi)
endmacro()


macro(detect_libcxx)
    # _conan_is_libcxx true if LLVM libc++
    check_cxx_source_compiles("
    #include <cstddef>
    #if !defined(_LIBCPP_VERSION)
       static_assert(false);
    #endif
    int main(){}" _conan_is_libcxx)
endmacro()


function(detect_lib_cxx lib_cxx)
    if(CMAKE_SYSTEM_NAME STREQUAL "Android")
        message(STATUS "CMake-Conan: android_stl=${CMAKE_ANDROID_STL_TYPE}")
        set(${lib_cxx} ${CMAKE_ANDROID_STL_TYPE} PARENT_SCOPE)
        return()
    endif()

    include(CheckCXXSourceCompiles)

    if(CMAKE_CXX_COMPILER_ID MATCHES "GNU")
        detect_gnu_libstdcxx()
        set(${lib_cxx} "libstdc++${_conan_gnu_libstdcxx_suffix}" PARENT_SCOPE)
    elseif(CMAKE_CXX_COMPILER_ID MATCHES "AppleClang")
        set(${lib_cxx} "libc++" PARENT_SCOPE)
    elseif(CMAKE_CXX_COMPILER_ID MATCHES "Clang" AND NOT CMAKE_SYSTEM_NAME MATCHES "Windows")
        # Check for libc++
        detect_libcxx()
        if(_conan_is_libcxx)
            set(${lib_cxx} "libc++" PARENT_SCOPE)
            return()
        endif()

        # Check for libstdc++
        detect_gnu_libstdcxx()
        if(_conan_is_gnu_libstdcxx)
            set(${lib_cxx} "libstdc++${_conan_gnu_libstdcxx_suffix}" PARENT_SCOPE)
            return()
        endif()

        # TODO: it would be an error if we reach this point
    elseif(CMAKE_CXX_COMPILER_ID MATCHES "MSVC")
        # Do nothing - compiler.runtime and compiler.runtime_type
        # should be handled separately: https://github.com/conan-io/cmake-conan/pull/516
        return()
    else()
        # TODO: unable to determine, ask user to provide a full profile file instead
    endif()
endfunction()


function(detect_compiler compiler compiler_version compiler_runtime compiler_runtime_type)
    if(DEFINED CMAKE_CXX_COMPILER_ID)
        set(_compiler ${CMAKE_CXX_COMPILER_ID})
        set(_compiler_version ${CMAKE_CXX_COMPILER_VERSION})
    else()
        if(NOT DEFINED CMAKE_C_COMPILER_ID)
            message(FATAL_ERROR "C or C++ compiler not defined")
        endif()
        set(_compiler ${CMAKE_C_COMPILER_ID})
        set(_compiler_version ${CMAKE_C_COMPILER_VERSION})
    endif()

    message(STATUS "CMake-Conan: CMake compiler=${_compiler}")
    message(STATUS "CMake-Conan: CMake compiler version=${_compiler_version}")

    if(_compiler MATCHES MSVC)
        set(_compiler "msvc")
        string(SUBSTRING ${MSVC_VERSION} 0 3 _compiler_version)
        # Configure compiler.runtime and compiler.runtime_type settings for MSVC
        if(CMAKE_MSVC_RUNTIME_LIBRARY)
            set(_msvc_runtime_library ${CMAKE_MSVC_RUNTIME_LIBRARY})
        else()
            set(_msvc_runtime_library MultiThreaded$<$<CONFIG:Debug>:Debug>DLL) # default value documented by CMake
        endif()

        set(_KNOWN_MSVC_RUNTIME_VALUES "")
        list(APPEND _KNOWN_MSVC_RUNTIME_VALUES MultiThreaded MultiThreadedDLL)
        list(APPEND _KNOWN_MSVC_RUNTIME_VALUES MultiThreadedDebug MultiThreadedDebugDLL)
        list(APPEND _KNOWN_MSVC_RUNTIME_VALUES MultiThreaded$<$<CONFIG:Debug>:Debug> MultiThreaded$<$<CONFIG:Debug>:Debug>DLL)

        # only accept the 6 possible values, otherwise we don't don't know to map this
        if(NOT _msvc_runtime_library IN_LIST _KNOWN_MSVC_RUNTIME_VALUES)
            message(FATAL_ERROR "CMake-Conan: unable to map MSVC runtime: ${_msvc_runtime_library} to Conan settings")
        endif()

        # Runtime is "dynamic" in all cases if it ends in DLL
        if(_msvc_runtime_library MATCHES ".*DLL$")
            set(_compiler_runtime "dynamic")
        else()
            set(_compiler_runtime "static")
        endif()
        message(STATUS "CMake-Conan: CMake compiler.runtime=${_compiler_runtime}")

        # Only define compiler.runtime_type when explicitly requested
        # If a generator expression is used, let Conan handle it conditional on build_type
        if(NOT _msvc_runtime_library MATCHES "<CONFIG:Debug>:Debug>")
            if(_msvc_runtime_library MATCHES "Debug")
                set(_compiler_runtime_type "Debug")
            else()
                set(_compiler_runtime_type "Release")
            endif()
            message(STATUS "CMake-Conan: CMake compiler.runtime_type=${_compiler_runtime_type}")
        endif()

        unset(_KNOWN_MSVC_RUNTIME_VALUES)

    elseif(_compiler MATCHES AppleClang)
        set(_compiler "apple-clang")
        string(REPLACE "." ";" VERSION_LIST ${_compiler_version})
        list(GET VERSION_LIST 0 _compiler_version)
    elseif(_compiler MATCHES Clang)
        set(_compiler "clang")
        string(REPLACE "." ";" VERSION_LIST ${_compiler_version})
        list(GET VERSION_LIST 0 _compiler_version)
    elseif(_compiler MATCHES GNU)
        set(_compiler "gcc")
        string(REPLACE "." ";" VERSION_LIST ${_compiler_version})
        list(GET VERSION_LIST 0 _compiler_version)
    endif()

    message(STATUS "CMake-Conan: [settings] compiler=${_compiler}")
    message(STATUS "CMake-Conan: [settings] compiler.version=${_compiler_version}")
    if (_compiler_runtime)
        message(STATUS "CMake-Conan: [settings] compiler.runtime=${_compiler_runtime}")
    endif()
    if (_compiler_runtime_type)
        message(STATUS "CMake-Conan: [settings] compiler.runtime_type=${_compiler_runtime_type}")
    endif()

    set(${compiler} ${_compiler} PARENT_SCOPE)
    set(${compiler_version} ${_compiler_version} PARENT_SCOPE)
    set(${compiler_runtime} ${_compiler_runtime} PARENT_SCOPE)
    set(${compiler_runtime_type} ${_compiler_runtime_type} PARENT_SCOPE)
endfunction()


function(detect_build_type build_type)
    get_property(multiconfig_generator GLOBAL PROPERTY GENERATOR_IS_MULTI_CONFIG)
    if(NOT multiconfig_generator)
        # Only set when we know we are in a single-configuration generator
        # Note: we may want to fail early if `CMAKE_BUILD_TYPE` is not defined
        set(${build_type} ${CMAKE_BUILD_TYPE} PARENT_SCOPE)
    endif()
endfunction()


macro(set_conan_compiler_if_appleclang lang command output_variable)
    if(CMAKE_${lang}_COMPILER_ID STREQUAL "AppleClang")
        execute_process(COMMAND xcrun --find ${command}
            OUTPUT_VARIABLE _xcrun_out OUTPUT_STRIP_TRAILING_WHITESPACE)
        cmake_path(GET _xcrun_out PARENT_PATH _xcrun_toolchain_path)
        cmake_path(GET CMAKE_${lang}_COMPILER PARENT_PATH _compiler_parent_path)
        if ("${_xcrun_toolchain_path}" STREQUAL "${_compiler_parent_path}")
            set(${output_variable} "")
        endif()
        unset(_xcrun_out)
        unset(_xcrun_toolchain_path)
        unset(_compiler_parent_path)
    endif()
endmacro()


macro(append_compiler_executables_configuration)
    set(_conan_c_compiler "")
    set(_conan_cpp_compiler "")
    set(_conan_rc_compiler "")
    set(_conan_compilers_list "")
    if(CMAKE_C_COMPILER)
        set(_conan_c_compiler "\"c\":\"${CMAKE_C_COMPILER}\"")
        set_conan_compiler_if_appleclang(C cc _conan_c_compiler)
        list(APPEND _conan_compilers_list ${_conan_c_compiler})
    else()
        message(WARNING "CMake-Conan: The C compiler is not defined. "
                        "Please define CMAKE_C_COMPILER or enable the C language.")
    endif()
    if(CMAKE_CXX_COMPILER)
        set(_conan_cpp_compiler "\"cpp\":\"${CMAKE_CXX_COMPILER}\"")
        set_conan_compiler_if_appleclang(CXX c++ _conan_cpp_compiler)
        list(APPEND _conan_compilers_list ${_conan_cpp_compiler})
    else()
        message(WARNING "CMake-Conan: The C++ compiler is not defined. "
                        "Please define CMAKE_CXX_COMPILER or enable the C++ language.")
    endif()
    if(CMAKE_RC_COMPILER)
        set(_conan_rc_compiler "\"rc\":\"${CMAKE_RC_COMPILER}\"")
        list(APPEND _conan_compilers_list ${_conan_rc_compiler})
        # Not necessary to warn if RC not defined
    endif()
    if(NOT "x${_conan_compilers_list}" STREQUAL "x")
        if (NOT CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
            string(REPLACE ";" "," _conan_compilers_list "${_conan_compilers_list}")
            string(APPEND profile "tools.build:compiler_executables={${_conan_compilers_list}}\n")
        endif()
    endif()
    unset(_conan_c_compiler)
    unset(_conan_cpp_compiler)
    unset(_conan_rc_compiler)
    unset(_conan_compilers_list)
endmacro()


function(detect_host_profile output_file archs)
    detect_os(os os_api_level os_sdk os_subsystem os_version)
    if(archs)
        # Universal binary build: the profile holds the primary arch only, the
        # installs override it per architecture on the command line
        list(GET archs 0 arch)
    else()
        detect_arch(arch)
    endif()
    detect_compiler(compiler compiler_version compiler_runtime compiler_runtime_type)
    detect_cxx_standard(${compiler} compiler_cppstd)
    detect_lib_cxx(compiler_libcxx)
    detect_build_type(build_type)

    set(profile "")
    string(APPEND profile "[settings]\n")
    if(arch)
        string(APPEND profile arch=${arch} "\n")
    endif()
    if(os)
        string(APPEND profile os=${os} "\n")
    endif()
    if(os_api_level)
        string(APPEND profile os.api_level=${os_api_level} "\n")
    endif()
    if(os_version)
        string(APPEND profile os.version=${os_version} "\n")
    endif()
    if(os_sdk)
        string(APPEND profile os.sdk=${os_sdk} "\n")
    endif()
    if(os_subsystem)
        string(APPEND profile os.subsystem=${os_subsystem} "\n")
    endif()
    if(compiler)
        string(APPEND profile compiler=${compiler} "\n")
    endif()
    if(compiler_version)
        string(APPEND profile compiler.version=${compiler_version} "\n")
    endif()
    if(compiler_runtime)
        string(APPEND profile compiler.runtime=${compiler_runtime} "\n")
    endif()
    if(compiler_runtime_type)
        string(APPEND profile compiler.runtime_type=${compiler_runtime_type} "\n")
    endif()
    if(compiler_cppstd)
        string(APPEND profile compiler.cppstd=${compiler_cppstd} "\n")
    endif()
    if(compiler_libcxx)
        string(APPEND profile compiler.libcxx=${compiler_libcxx} "\n")
    endif()
    if(build_type)
        string(APPEND profile "build_type=${build_type}\n")
    endif()

    if(NOT DEFINED output_file)
        set(file_name "${CMAKE_BINARY_DIR}/profile")
    else()
        set(file_name ${output_file})
    endif()

    string(APPEND profile "[conf]\n")
    string(APPEND profile "tools.cmake.cmaketoolchain:generator=${CMAKE_GENERATOR}\n")

    # propagate compilers via profile
    append_compiler_executables_configuration()

    if(os STREQUAL "Android")
        string(APPEND profile "tools.android:ndk_path=${CMAKE_ANDROID_NDK}\n")
    endif()

    message(STATUS "CMake-Conan: Creating profile ${file_name}")
    file(WRITE ${file_name} ${profile})
    message(STATUS "CMake-Conan: Profile: \n${profile}")
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
    # OUTPUT_FOLDER redirects the output folder (used by per-architecture universal
    # installs), everything else is passed to "conan install" as-is
    cmake_parse_arguments(_conan_install "" "OUTPUT_FOLDER" "" ${ARGN})
    if(_conan_install_OUTPUT_FOLDER)
        set(conan_output_folder ${_conan_install_OUTPUT_FOLDER})
    else()
        set(conan_output_folder ${CMAKE_BINARY_DIR}/conan)
    endif()
    # Invoke "conan install" with the provided arguments
    set(conan_args -of=${conan_output_folder})
    list(JOIN _conan_install_UNPARSED_ARGUMENTS " " argn_str)
    message(STATUS "CMake-Conan: conan install ${CMAKE_SOURCE_DIR} ${conan_args} ${argn_str}")


    # In case there was not a valid cmake executable in the PATH, we inject the
    # same we used to invoke the provider to the PATH
    if(DEFINED PATH_TO_CMAKE_BIN)
        set(old_path $ENV{PATH})
        if(CMAKE_HOST_WIN32)
            set(ENV{PATH} "$ENV{PATH};${PATH_TO_CMAKE_BIN}")
        else()
            set(ENV{PATH} "$ENV{PATH}:${PATH_TO_CMAKE_BIN}")
        endif()
    endif()

    execute_process(COMMAND ${CONAN_COMMAND} install ${CMAKE_SOURCE_DIR} ${conan_args} ${_conan_install_UNPARSED_ARGUMENTS} --format=json
                    RESULT_VARIABLE return_code
                    OUTPUT_VARIABLE conan_stdout
                    ERROR_VARIABLE conan_stderr
                    ECHO_ERROR_VARIABLE    # show the text output regardless
                    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR})

    if(DEFINED PATH_TO_CMAKE_BIN)
        set(ENV{PATH} "${old_path}")
    endif()

    if(NOT "${return_code}" STREQUAL "0")
        message(FATAL_ERROR "Conan install failed='${return_code}'")
    endif()

    # the files are generated in a folder that depends on the layout used, if
    # one is specified, but we don't know a priori where this is.
    # TODO: this can be made more robust if Conan can provide this in the json output
    string(JSON conan_generators_folder GET "${conan_stdout}" graph nodes 0 generators_folder)
    cmake_path(CONVERT ${conan_generators_folder} TO_CMAKE_PATH_LIST conan_generators_folder)

    message(STATUS "CMake-Conan: CONAN_GENERATORS_FOLDER=${conan_generators_folder}")
    set_property(GLOBAL PROPERTY CONAN_GENERATORS_FOLDER "${conan_generators_folder}")
    # reconfigure on conanfile changes
    string(JSON conanfile GET "${conan_stdout}" graph nodes 0 label)
    message(STATUS "CMake-Conan: CONANFILE=${CMAKE_SOURCE_DIR}/${conanfile}")
    set_property(DIRECTORY ${CMAKE_SOURCE_DIR} APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_SOURCE_DIR}/${conanfile}")
    # success
    set_property(GLOBAL PROPERTY CONAN_INSTALL_SUCCESS TRUE)

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
    set(one_value_args MINIMUM CURRENT)
    set(multi_value_args )
    cmake_parse_arguments(conan_version_check
        "${options}" "${one_value_args}" "${multi_value_args}" ${ARGN})

    if(NOT conan_version_check_MINIMUM)
        message(FATAL_ERROR "CMake-Conan: Required parameter MINIMUM not set!")
    endif()
        if(NOT conan_version_check_CURRENT)
        message(FATAL_ERROR "CMake-Conan: Required parameter CURRENT not set!")
    endif()

    if(conan_version_check_CURRENT VERSION_LESS conan_version_check_MINIMUM)
        message(FATAL_ERROR "CMake-Conan: Conan version must be ${conan_version_check_MINIMUM} or later")
    endif()
endfunction()


macro(construct_profile_argument argument_variable profile_list)
    set(${argument_variable} "")
    if("${profile_list}" STREQUAL "CONAN_HOST_PROFILE")
        set(_arg_flag "--profile:host=")
    elseif("${profile_list}" STREQUAL "CONAN_BUILD_PROFILE")
        set(_arg_flag "--profile:build=")
    endif()

    set(_profile_list "${${profile_list}}")
    list(TRANSFORM _profile_list REPLACE "auto-cmake" "${CMAKE_BINARY_DIR}/conan_host_profile")
    list(TRANSFORM _profile_list PREPEND ${_arg_flag})
    set(${argument_variable} ${_profile_list})

    unset(_arg_flag)
    unset(_profile_list)
endmacro()


macro(conan_install_osx_universal)
    # One "conan install" per architecture, and each install deploys its packages into
    # the build tree for the lipo merge. The secondary architecture installs into a side
    # output folder first. The primary architecture installs into the default folder last
    # so CONAN_GENERATORS_FOLDER ends up pointing at its generators. Both installs
    # consume the probed lockfile, so they install one identical dependency snapshot.
    set(_conan_universal_lockfile_args "")
    if(EXISTS "${_conan_universal_lockfile}")
        set(_conan_universal_lockfile_args --lockfile=${_conan_universal_lockfile} --lockfile-partial)
    endif()
    conan_install(OUTPUT_FOLDER ${CMAKE_BINARY_DIR}/conan-${_conan_secondary_arch} ${ARGN} ${_conan_universal_lockfile_args} -s:h arch=${_conan_secondary_arch} --deployer=full_deploy --deployer-folder=${CMAKE_BINARY_DIR}/conan-deploy-${_conan_secondary_arch})
    conan_install(${ARGN} ${_conan_universal_lockfile_args} -s:h arch=${_conan_primary_arch} --deployer=full_deploy --deployer-folder=${CMAKE_BINARY_DIR}/conan-deploy-${_conan_primary_arch})
    unset(_conan_universal_lockfile_args)
endmacro()


function(conan_universal_lipo_arch conan_arch lipo_arch)
    # Converts a Conan arch setting value to the lipo architecture name
    if(conan_arch STREQUAL "armv8")
        set(${lipo_arch} arm64 PARENT_SCOPE)
    elseif(conan_arch STREQUAL "x86_64")
        set(${lipo_arch} x86_64 PARENT_SCOPE)
    else()
        message(FATAL_ERROR "CMake-Conan: no lipo architecture name for '${conan_arch}'")
    endif()
endfunction()


function(conan_universal_arch_macro conan_arch arch_macro)
    # Converts a Conan arch setting value to the compiler-defined architecture macro
    if(conan_arch STREQUAL "armv8")
        set(${arch_macro} __aarch64__ PARENT_SCOPE)
    elseif(conan_arch STREQUAL "x86_64")
        set(${arch_macro} __x86_64__ PARENT_SCOPE)
    else()
        message(FATAL_ERROR "CMake-Conan: no architecture macro for '${conan_arch}'")
    endif()
endfunction()


function(conan_universal_count counter)
    get_property(_count GLOBAL PROPERTY ${counter})
    math(EXPR _count "${_count} + 1")
    set_property(GLOBAL PROPERTY ${counter} ${_count})
endfunction()


function(conan_universal_error error_message)
    conan_universal_count(_CONAN_UNIVERSAL_ERRORS)
    message(SEND_ERROR "CMake-Conan: ${error_message}")
endfunction()


function(conan_universal_lipo_archs path archs)
    # Architectures in a Mach-O file or static archive, empty for anything else
    execute_process(COMMAND ${CONAN_LIPO_PROGRAM} -archs "${path}"
                    RESULT_VARIABLE _result OUTPUT_VARIABLE _output
                    ERROR_QUIET OUTPUT_STRIP_TRAILING_WHITESPACE)
    if(_result EQUAL 0)
        string(REPLACE " " ";" _output "${_output}")
        set(${archs} "${_output}" PARENT_SCOPE)
    else()
        set(${archs} "" PARENT_SCOPE)
    endif()
endfunction()


function(conan_universal_lipo_merge primary secondary)
    # lipo-merges secondary into primary in place, verifying architectures
    conan_universal_lipo_archs("${primary}" _primary_archs)
    if(NOT _primary_archs STREQUAL _conan_primary_lipo_arch)
        message(FATAL_ERROR "CMake-Conan: unexpected architectures [${_primary_archs}] in ${primary}, "
                            "expected [${_conan_primary_lipo_arch}] (trees already merged, or architectures "
                            "swapped?); if your recipes intentionally produce universal (fat) binaries, "
                            "set CONAN_OSX_UNIVERSAL_BINARIES=OFF")
    endif()
    conan_universal_lipo_archs("${secondary}" _secondary_archs)
    if(NOT _secondary_archs STREQUAL _conan_secondary_lipo_arch)
        message(FATAL_ERROR "CMake-Conan: unexpected architectures [${_secondary_archs}] in ${secondary}, "
                            "expected [${_conan_secondary_lipo_arch}] (trees already merged, or architectures "
                            "swapped?); if your recipes intentionally produce universal (fat) binaries, "
                            "set CONAN_OSX_UNIVERSAL_BINARIES=OFF")
    endif()

    # CMake cannot query the executable bit, and test(1) is always available on macOS
    execute_process(COMMAND test -x "${primary}" RESULT_VARIABLE _not_executable)
    set(_tmp "${primary}.lipo-tmp")
    execute_process(COMMAND ${CONAN_LIPO_PROGRAM} -create "${primary}" "${secondary}" -output "${_tmp}"
                    RESULT_VARIABLE _result ERROR_VARIABLE _error)
    if(NOT _result EQUAL 0)
        file(REMOVE "${_tmp}")
        conan_universal_error("lipo -create failed for ${primary}: ${_error}")
        return()
    endif()
    if(_not_executable EQUAL 0)
        file(CHMOD "${_tmp}" PERMISSIONS OWNER_READ OWNER_WRITE OWNER_EXECUTE
                                         GROUP_READ GROUP_EXECUTE WORLD_READ WORLD_EXECUTE)
    else()
        file(CHMOD "${_tmp}" PERMISSIONS OWNER_READ OWNER_WRITE GROUP_READ WORLD_READ)
    endif()
    file(RENAME "${_tmp}" "${primary}")

    conan_universal_lipo_archs("${primary}" _merged_archs)
    set(_expected_archs ${_conan_primary_lipo_arch} ${_conan_secondary_lipo_arch})
    list(SORT _expected_archs)
    list(SORT _merged_archs)
    if(NOT _merged_archs STREQUAL _expected_archs)
        message(FATAL_ERROR "CMake-Conan: merge produced unexpected architectures [${_merged_archs}] in ${primary}")
    endif()
    conan_universal_count(_CONAN_UNIVERSAL_MERGED)
endfunction()


function(conan_universal_package_set deploy_root packages)
    # The sorted list of <name>/<version> under <deploy_root>/full_deploy/host
    set(_host "${deploy_root}/full_deploy/host")
    if(NOT IS_DIRECTORY "${_host}")
        message(FATAL_ERROR "CMake-Conan: missing deploy tree ${_host}")
    endif()
    file(GLOB _packages RELATIVE "${_host}" "${_host}/*/*")
    list(SORT _packages)
    set(${packages} "${_packages}" PARENT_SCOPE)
endfunction()


function(conan_universal_map_arch_path rel from_arch to_arch mapped count)
    # Swaps the <from_arch> path component for <to_arch> and reports how many such
    # components the path has, the swap is only unambiguous for at most one
    string(REPLACE "/" ";" _components "${rel}")
    set(_count 0)
    foreach(_component IN LISTS _components)
        if(_component STREQUAL from_arch)
            math(EXPR _count "${_count} + 1")
        endif()
    endforeach()
    string(REPLACE "/${from_arch}/" "/${to_arch}/" _mapped "/${rel}/")
    string(LENGTH "${_mapped}" _mapped_length)
    math(EXPR _mapped_length "${_mapped_length} - 2")
    string(SUBSTRING "${_mapped}" 1 ${_mapped_length} _mapped)
    set(${mapped} "${_mapped}" PARENT_SCOPE)
    set(${count} ${_count} PARENT_SCOPE)
endfunction()


function(conan_universal_dispatch_header primary secondary)
    # Replaces a per-architecture header with an architecture-dispatching wrapper. The
    # primary and secondary contents are kept next to the original as
    # <stem>.<lipo arch>.<ext> and the original becomes an #if/#include dispatcher.
    cmake_path(GET primary STEM LAST_ONLY _stem)
    cmake_path(GET primary EXTENSION LAST_ONLY _ext)
    cmake_path(GET primary PARENT_PATH _dir)
    set(_primary_variant "${_stem}.${_conan_primary_lipo_arch}${_ext}")
    set(_secondary_variant "${_stem}.${_conan_secondary_lipo_arch}${_ext}")
    file(RENAME "${primary}" "${_dir}/${_primary_variant}")
    file(COPY_FILE "${secondary}" "${_dir}/${_secondary_variant}")
    file(WRITE "${primary}"
"/* Generated by conan_provider.cmake: this header differs between the
 * merged architectures, so it includes the variant for the target arch. */
#if defined(${_conan_primary_arch_macro})
#include \"${_primary_variant}\"
#elif defined(${_conan_secondary_arch_macro})
#include \"${_secondary_variant}\"
#else
#error \"conan_provider.cmake: no header variant for this architecture\"
#endif
")
    conan_universal_count(_CONAN_UNIVERSAL_DISPATCHED)
    message(STATUS "CMake-Conan: dispatching per-architecture header ${primary}")
endfunction()


function(conan_universal_merge_deploy_trees)
    # Walks the secondary deploy tree and merges each file into the primary one. Files
    # identical between the architectures are shared from the primary tree. Headers
    # that differ get an architecture-dispatching wrapper. Mach-O files are lipo-merged
    # into their primary counterparts.
    file(GLOB_RECURSE _files LIST_DIRECTORIES false RELATIVE "${_conan_secondary_deploy}"
         "${_conan_secondary_deploy}/*")
    foreach(_rel IN LISTS _files)
        set(_secondary_file "${_conan_secondary_deploy}/${_rel}")
        if(IS_SYMLINK "${_secondary_file}")
            continue()
        endif()

        conan_universal_map_arch_path("${_rel}" "${_conan_secondary_arch}" "${_conan_primary_arch}"
                                      _mapped _arch_components)
        if(_arch_components GREATER 1)
            conan_universal_error("multiple '${_conan_secondary_arch}' path components in ${_rel}")
            continue()
        endif()
        set(_primary_file "${_conan_primary_deploy}/${_mapped}")

        # Identical files are shared from the primary tree as-is
        if(EXISTS "${_primary_file}")
            file(SHA256 "${_primary_file}" _primary_hash)
            file(SHA256 "${_secondary_file}" _secondary_hash)
            if(_primary_hash STREQUAL _secondary_hash)
                conan_universal_count(_CONAN_UNIVERSAL_COMPARED)
                continue()
            endif()
        endif()

        cmake_path(GET _mapped PARENT_PATH _mapped_dir)
        if("/${_mapped_dir}/" MATCHES "/include/")
            # Checked before any lipo probing, no binaries live under include/
            if(NOT EXISTS "${_primary_file}")
                conan_universal_error("no primary counterpart for header ${_rel}")
                continue()
            endif()
            cmake_path(GET _mapped EXTENSION LAST_ONLY _ext)
            if(_ext MATCHES "^\\.(h|hpp|hxx|hh|inc|ipp|tcc)$")
                conan_universal_dispatch_header("${_primary_file}" "${_secondary_file}")
            else()
                conan_universal_error("non-header include file differs between architectures: ${_mapped}")
            endif()
        else()
            conan_universal_lipo_archs("${_secondary_file}" _file_archs)
            if(_file_archs)
                if(_mapped STREQUAL _rel)
                    conan_universal_error("binary outside an architecture-specific directory: ${_rel}")
                elseif(NOT EXISTS "${_primary_file}")
                    conan_universal_error("no primary counterpart for ${_rel}")
                else()
                    conan_universal_lipo_merge("${_primary_file}" "${_secondary_file}")
                endif()
            endif()
            # Everything else (licenses, conaninfo.txt, pkg-config and cmake files with
            # embedded per-package paths) legitimately differs per architecture and is
            # not consumed by the CMakeDeps flow
        endif()
    endforeach()
endfunction()


function(conan_universal_verify_primary_only)
    # Walks the primary deploy tree and reports headers and binaries with no secondary
    # counterpart, they would silently stay single-architecture in the merged tree.
    # Must run before the merge, which creates primary-only dispatch variant files.
    file(GLOB_RECURSE _files LIST_DIRECTORIES false RELATIVE "${_conan_primary_deploy}"
         "${_conan_primary_deploy}/*")
    foreach(_rel IN LISTS _files)
        set(_primary_file "${_conan_primary_deploy}/${_rel}")
        if(IS_SYMLINK "${_primary_file}")
            continue()
        endif()
        conan_universal_map_arch_path("${_rel}" "${_conan_primary_arch}" "${_conan_secondary_arch}"
                                      _mapped _arch_components)
        if(_arch_components GREATER 1)
            conan_universal_error("multiple '${_conan_primary_arch}' path components in ${_rel}")
            continue()
        endif()
        if(EXISTS "${_conan_secondary_deploy}/${_mapped}")
            continue()
        endif()
        cmake_path(GET _mapped PARENT_PATH _mapped_dir)
        if("/${_mapped_dir}/" MATCHES "/include/")
            conan_universal_error("include file missing for architecture ${_conan_secondary_arch}: ${_rel}")
        else()
            conan_universal_lipo_archs("${_primary_file}" _file_archs)
            if(_file_archs)
                conan_universal_error("binary missing for architecture ${_conan_secondary_arch}: ${_rel}")
            endif()
        endif()
    endforeach()
endfunction()


function(conan_universal_merge)
    # Merges the secondary architecture's binaries into the primary deploy tree with
    # lipo, so the dependencies become universal in place. Raises errors as described
    # in the comment block above.
    foreach(_counter _CONAN_UNIVERSAL_MERGED _CONAN_UNIVERSAL_COMPARED
                     _CONAN_UNIVERSAL_DISPATCHED _CONAN_UNIVERSAL_ERRORS)
        set_property(GLOBAL PROPERTY ${_counter} 0)
    endforeach()

    conan_universal_lipo_arch(${_conan_primary_arch} _conan_primary_lipo_arch)
    conan_universal_lipo_arch(${_conan_secondary_arch} _conan_secondary_lipo_arch)
    conan_universal_arch_macro(${_conan_primary_arch} _conan_primary_arch_macro)
    conan_universal_arch_macro(${_conan_secondary_arch} _conan_secondary_arch_macro)
    set(_conan_primary_deploy "${CMAKE_BINARY_DIR}/conan-deploy-${_conan_primary_arch}")
    set(_conan_secondary_deploy "${CMAKE_BINARY_DIR}/conan-deploy-${_conan_secondary_arch}")

    conan_universal_package_set("${_conan_primary_deploy}" _primary_packages)
    conan_universal_package_set("${_conan_secondary_deploy}" _secondary_packages)
    if(NOT _primary_packages STREQUAL _secondary_packages)
        set(_only_primary "${_primary_packages}")
        if(_secondary_packages)
            list(REMOVE_ITEM _only_primary ${_secondary_packages})
        endif()
        set(_only_secondary "${_secondary_packages}")
        if(_primary_packages)
            list(REMOVE_ITEM _only_secondary ${_primary_packages})
        endif()
        message(FATAL_ERROR "CMake-Conan: package sets differ between architectures: "
                            "only ${_conan_primary_arch}: [${_only_primary}], "
                            "only ${_conan_secondary_arch}: [${_only_secondary}]")
    endif()

    conan_universal_verify_primary_only()
    conan_universal_merge_deploy_trees()

    list(LENGTH _primary_packages _package_count)
    get_property(_merged GLOBAL PROPERTY _CONAN_UNIVERSAL_MERGED)
    get_property(_compared GLOBAL PROPERTY _CONAN_UNIVERSAL_COMPARED)
    get_property(_dispatched GLOBAL PROPERTY _CONAN_UNIVERSAL_DISPATCHED)
    get_property(_errors GLOBAL PROPERTY _CONAN_UNIVERSAL_ERRORS)
    message(STATUS "CMake-Conan: ${_package_count} packages, ${_merged} binaries merged, "
                   "${_compared} files identical, "
                   "${_dispatched} headers dispatched per architecture, ${_errors} errors")
    if(_errors GREATER 0)
        message(FATAL_ERROR "CMake-Conan: ${_errors} error(s) reported above")
    endif()
endfunction()


function(conan_universal_probe_lockfile lockfile)
    # Resolves the dependency graph, without installing or deploying, and captures it
    # as a lockfile. The lockfile joins the stamp inputs, so a version range that
    # resolves to a new package triggers a reinstall. The installs then consume the
    # lockfile and both architectures install one identical snapshot. No lockfile on
    # failure, which forces a reinstall.
    file(REMOVE "${lockfile}")
    list(GET _build_configs 0 _probe_build_type)
    set(_probe_update "")
    if("--update" IN_LIST CONAN_INSTALL_ARGS)
        set(_probe_update --update)
    endif()
    execute_process(COMMAND ${CONAN_COMMAND} lock create ${CMAKE_SOURCE_DIR}
                            ${_host_profile_flags} ${_build_profile_flags}
                            -s:h arch=${_conan_primary_arch} -s build_type=${_probe_build_type}
                            ${_probe_update} --lockfile-out=${lockfile}
                    RESULT_VARIABLE _result OUTPUT_QUIET ERROR_QUIET)
    if(NOT _result EQUAL 0)
        file(REMOVE "${lockfile}")
    endif()
endfunction()


function(conan_universal_stamp_inputs_hash hash)
    # Hash of everything that feeds the installs: conanfile, resolved profiles,
    # global.conf (not covered by "conan profile show"), the probed lockfile, install
    # arguments and the Conan version. Empty on failure, which forces a reinstall.
    set(${hash} "" PARENT_SCOPE)

    if(NOT EXISTS "${_conan_universal_lockfile}")
        return()
    endif()
    file(READ "${_conan_universal_lockfile}" _lockfile_content)

    if(EXISTS "${CMAKE_SOURCE_DIR}/conanfile.py")
        set(_conanfile "${CMAKE_SOURCE_DIR}/conanfile.py")
    elseif(EXISTS "${CMAKE_SOURCE_DIR}/conanfile.txt")
        set(_conanfile "${CMAKE_SOURCE_DIR}/conanfile.txt")
    else()
        return()
    endif()
    file(SHA256 "${_conanfile}" _conanfile_hash)

    execute_process(COMMAND ${CONAN_COMMAND} profile show ${_host_profile_flags} ${_build_profile_flags}
                    RESULT_VARIABLE _result OUTPUT_VARIABLE _profiles ERROR_QUIET)
    if(NOT _result EQUAL 0)
        return()
    endif()

    execute_process(COMMAND ${CONAN_COMMAND} config home
                    RESULT_VARIABLE _result OUTPUT_VARIABLE _conan_home
                    ERROR_QUIET OUTPUT_STRIP_TRAILING_WHITESPACE)
    if(NOT _result EQUAL 0)
        return()
    endif()
    set(_global_conf "")
    if(EXISTS "${_conan_home}/global.conf")
        file(READ "${_conan_home}/global.conf" _global_conf)
    endif()

    string(SHA256 _hash "${CONAN_CURRENT_VERSION}\n${_conan_universal_archs}\n${_build_configs}\n\
${CMAKE_BUILD_TYPE}\n${CONAN_INSTALL_ARGS}\n${_host_profile_flags}\n${_build_profile_flags}\n\
${_conanfile}\n${_conanfile_hash}\n${_profiles}\n${_global_conf}\n${_lockfile_content}")
    set(${hash} "${_hash}" PARENT_SCOPE)
endfunction()


function(conan_universal_stamp_check stamp_file inputs_hash valid generators_folder)
    # Valid when the stamp matches the inputs hash and its outputs are still in place
    set(${valid} FALSE PARENT_SCOPE)
    set(${generators_folder} "" PARENT_SCOPE)
    if(NOT inputs_hash OR NOT EXISTS "${stamp_file}")
        return()
    endif()
    file(STRINGS "${stamp_file}" _lines)
    list(LENGTH _lines _line_count)
    if(_line_count LESS 5)
        return()
    endif()
    list(GET _lines 0 _format)
    list(GET _lines 1 _hash)
    list(GET _lines 2 _generators)
    list(GET _lines 3 _primary)
    list(GET _lines 4 _secondary)
    if(NOT _format STREQUAL "1" OR NOT _hash STREQUAL inputs_hash)
        return()
    endif()
    if(NOT IS_DIRECTORY "${_generators}"
       OR NOT IS_DIRECTORY "${CMAKE_BINARY_DIR}/conan-deploy-${_primary}/full_deploy/host"
       OR NOT IS_DIRECTORY "${CMAKE_BINARY_DIR}/conan-deploy-${_secondary}/full_deploy/host")
        return()
    endif()
    set(${valid} TRUE PARENT_SCOPE)
    set(${generators_folder} "${_generators}" PARENT_SCOPE)
endfunction()


function(conan_universal_stamp_write stamp_file inputs_hash)
    if(NOT inputs_hash)
        return()
    endif()
    get_property(_generators GLOBAL PROPERTY CONAN_GENERATORS_FOLDER)
    file(WRITE "${stamp_file}"
         "1\n${inputs_hash}\n${_generators}\n${_conan_primary_arch}\n${_conan_secondary_arch}\n")
endfunction()


macro(conan_provide_dependency method package_name)
    set_property(GLOBAL PROPERTY CONAN_PROVIDE_DEPENDENCY_INVOKED TRUE)
    get_property(_conan_install_success GLOBAL PROPERTY CONAN_INSTALL_SUCCESS)
    if(NOT _conan_install_success)
        find_program(CONAN_COMMAND "conan" REQUIRED)
        conan_get_version("${CONAN_COMMAND}" CONAN_CURRENT_VERSION)
        conan_version_check(MINIMUM ${CONAN_MINIMUM_VERSION} CURRENT ${CONAN_CURRENT_VERSION})
        message(STATUS "CMake-Conan: first find_package() found. Installing dependencies with Conan")
        if("default" IN_LIST CONAN_HOST_PROFILE OR "default" IN_LIST CONAN_BUILD_PROFILE)
            conan_profile_detect_default()
        endif()
        set(_conan_universal_archs "")
        if(CONAN_OSX_UNIVERSAL_BINARIES)
            detect_osx_universal_archs(_conan_universal_archs)
        endif()
        if(_conan_universal_archs)
            # Universal binary build: fail fast on its requirements before any install
            if(CONAN_CURRENT_VERSION VERSION_LESS 2.1.0)
                message(FATAL_ERROR "CMake-Conan: Universal binary builds require Conan 2.1.0 or later "
                        "for 'conan install --deployer-folder', found ${CONAN_CURRENT_VERSION}")
            endif()
            # The lipo found on the PATH is an xcode-select shim, and the cache
            # variable doubles as a user override
            find_program(CONAN_LIPO_PROGRAM lipo REQUIRED)
        endif()
        if("auto-cmake" IN_LIST CONAN_HOST_PROFILE)
            detect_host_profile(${CMAKE_BINARY_DIR}/conan_host_profile "${_conan_universal_archs}")
        endif()
        construct_profile_argument(_host_profile_flags CONAN_HOST_PROFILE)
        construct_profile_argument(_build_profile_flags CONAN_BUILD_PROFILE)
        if(EXISTS "${CMAKE_SOURCE_DIR}/conanfile.py")
            file(READ "${CMAKE_SOURCE_DIR}/conanfile.py" outfile)
            if(NOT "${outfile}" MATCHES ".*CMakeConfigDeps.*")
                message(WARNING "Cmake-conan: CMakeConfigDeps generator was not defined in the conanfile")
            endif()
        elseif (EXISTS "${CMAKE_SOURCE_DIR}/conanfile.txt")
            file(READ "${CMAKE_SOURCE_DIR}/conanfile.txt" outfile)
            if(NOT "${outfile}" MATCHES ".*CMakeConfigDeps.*")
                message(WARNING "Cmake-conan: CMakeConfigDeps generator was not defined in the conanfile")
            endif()
        endif()

        get_property(_multiconfig_generator GLOBAL PROPERTY GENERATOR_IS_MULTI_CONFIG)

        if(DEFINED CONAN_INSTALL_BUILD_CONFIGURATIONS)
            # Configurations are specified by the project or user
            set(_build_configs "${CONAN_INSTALL_BUILD_CONFIGURATIONS}")
            list(LENGTH _build_configs _build_configs_length)
            if(NOT _multiconfig_generator AND _build_configs_length GREATER 1)
                message(FATAL_ERROR "cmake-conan: when using a single-config CMake generator, "
                        "please only specify a single configuration in CONAN_INSTALL_BUILD_CONFIGURATIONS")
            endif()
            unset(_build_configs_length)
        else()
            # No configuration overrides, provide sensible defaults            
            if(_multiconfig_generator)
                set(_build_configs Release Debug)
            else()
                set(_build_configs ${CMAKE_BUILD_TYPE})
            endif()
            
        endif()

        set(_conan_universal_uptodate FALSE)
        if(_conan_universal_archs)
            if(NOT _build_configs)
                message(FATAL_ERROR "CMake-Conan: a universal binary build needs at least one build "
                        "type, set CMAKE_BUILD_TYPE or CONAN_INSTALL_BUILD_CONFIGURATIONS")
            endif()
            list(GET _conan_universal_archs 0 _conan_primary_arch)
            list(GET _conan_universal_archs 1 _conan_secondary_arch)
            set(_conan_universal_stamp ${CMAKE_BINARY_DIR}/conan-universal-stamp.txt)
            set(_conan_universal_lockfile ${CMAKE_BINARY_DIR}/conan-universal.lock)
            conan_universal_probe_lockfile("${_conan_universal_lockfile}")
            conan_universal_stamp_inputs_hash(_conan_universal_hash)
            conan_universal_stamp_check("${_conan_universal_stamp}" "${_conan_universal_hash}"
                                        _conan_universal_uptodate _conan_universal_generators)
        elseif(EXISTS "${CMAKE_BINARY_DIR}/conan-universal-stamp.txt")
            # The previous configure was a universal binary build and this one is not:
            # drop its outputs, since the generators in the output folder point into
            # the deploy trees removed here
            message(STATUS "CMake-Conan: removing outputs of previous universal binary build")
            file(STRINGS "${CMAKE_BINARY_DIR}/conan-universal-stamp.txt" _conan_universal_stale)
            file(REMOVE "${CMAKE_BINARY_DIR}/conan-universal-stamp.txt"
                        "${CMAKE_BINARY_DIR}/conan-universal.lock")
            file(REMOVE_RECURSE "${CMAKE_BINARY_DIR}/conan")
            list(LENGTH _conan_universal_stale _conan_universal_stale_count)
            if(_conan_universal_stale_count GREATER_EQUAL 5)
                list(GET _conan_universal_stale 3 _conan_universal_stale_primary)
                list(GET _conan_universal_stale 4 _conan_universal_stale_secondary)
                file(REMOVE_RECURSE "${CMAKE_BINARY_DIR}/conan-${_conan_universal_stale_secondary}"
                                    "${CMAKE_BINARY_DIR}/conan-deploy-${_conan_universal_stale_primary}"
                                    "${CMAKE_BINARY_DIR}/conan-deploy-${_conan_universal_stale_secondary}")
                unset(_conan_universal_stale_primary)
                unset(_conan_universal_stale_secondary)
            endif()
            unset(_conan_universal_stale)
            unset(_conan_universal_stale_count)
        endif()

        if(_conan_universal_uptodate)
            message(STATUS "CMake-Conan: Universal binary build up to date, skipping conan install "
                           "(delete ${_conan_universal_stamp} to force)")
            set_property(GLOBAL PROPERTY CONAN_GENERATORS_FOLDER "${_conan_universal_generators}")
            set_property(GLOBAL PROPERTY CONAN_INSTALL_SUCCESS TRUE)
            # reconfigure on conanfile changes, like conan_install does
            if(EXISTS "${CMAKE_SOURCE_DIR}/conanfile.py")
                set_property(DIRECTORY ${CMAKE_SOURCE_DIR} APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_SOURCE_DIR}/conanfile.py")
            elseif(EXISTS "${CMAKE_SOURCE_DIR}/conanfile.txt")
                set_property(DIRECTORY ${CMAKE_SOURCE_DIR} APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_SOURCE_DIR}/conanfile.txt")
            endif()
        else()
            if(_conan_universal_archs)
                message(STATUS "CMake-Conan: Universal binary build, installing each architecture separately (${CMAKE_OSX_ARCHITECTURES})")
                # Remove the stamp first, it is only re-written after a successful
                # merge. An interrupted run never looks up to date. Start from clean
                # outputs so the merge only sees freshly deployed files.
                file(REMOVE "${_conan_universal_stamp}")
                file(REMOVE_RECURSE "${CMAKE_BINARY_DIR}/conan"
                                    "${CMAKE_BINARY_DIR}/conan-${_conan_secondary_arch}"
                                    "${CMAKE_BINARY_DIR}/conan-deploy-${_conan_primary_arch}"
                                    "${CMAKE_BINARY_DIR}/conan-deploy-${_conan_secondary_arch}")
            endif()
            list(JOIN _build_configs ", " _build_configs_msg)
            message(STATUS "CMake-Conan: Installing configuration(s): ${_build_configs_msg}")
            foreach(_build_config IN LISTS _build_configs)
                set(_self_build_config "")
                if(NOT _multiconfig_generator AND NOT _build_config STREQUAL "${CMAKE_BUILD_TYPE}")
                    set(_self_build_config -s &:build_type=${CMAKE_BUILD_TYPE})
                endif()
                if(_conan_universal_archs)
                    conan_install_osx_universal(${_host_profile_flags} ${_build_profile_flags} -s build_type=${_build_config} ${_self_build_config} ${CONAN_INSTALL_ARGS})
                else()
                    conan_install(${_host_profile_flags} ${_build_profile_flags} -s build_type=${_build_config} ${_self_build_config} ${CONAN_INSTALL_ARGS})
                endif()
            endforeach()
            if(_conan_universal_archs)
                conan_universal_merge()
                conan_universal_stamp_write("${_conan_universal_stamp}" "${_conan_universal_hash}")
            endif()
        endif()

        get_property(_conan_generators_folder GLOBAL PROPERTY CONAN_GENERATORS_FOLDER)
        if(EXISTS "${_conan_generators_folder}/conan_cmakedeps_paths.cmake")
            message(STATUS "CMake-Conan: Loading conan_cmakedeps_paths.cmake file")
            include(${_conan_generators_folder}/conan_cmakedeps_paths.cmake)
        endif()

        unset(_self_build_config)
        unset(_multiconfig_generator)
        unset(_conan_universal_archs)
        unset(_conan_primary_arch)
        unset(_conan_secondary_arch)
        unset(_conan_universal_uptodate)
        unset(_conan_universal_stamp)
        unset(_conan_universal_lockfile)
        unset(_conan_universal_hash)
        unset(_conan_universal_generators)
        unset(_build_configs)
        unset(_build_configs_msg)
        unset(_host_profile_flags)
        unset(_build_profile_flags)
        unset(_conan_install_success)
    else()
        message(STATUS "CMake-Conan: find_package(${ARGV1}) found, 'conan install' already ran")
        unset(_conan_install_success)
    endif()

    get_property(_conan_generators_folder GLOBAL PROPERTY CONAN_GENERATORS_FOLDER)

    # Ensure that we consider Conan-provided packages ahead of any other,
    # irrespective of other settings that modify the search order or search paths
    # This follows the guidelines from the find_package documentation
    #  (https://cmake.org/cmake/help/latest/command/find_package.html):
    #       find_package (<PackageName> PATHS paths... NO_DEFAULT_PATH)
    #       find_package (<PackageName>)

    # Filter out `REQUIRED` from the argument list, as the first call may fail
    set(_find_args_${package_name} "${ARGN}")
    list(REMOVE_ITEM _find_args_${package_name} "REQUIRED")
    if(NOT "MODULE" IN_LIST _find_args_${package_name})
        find_package(${package_name} ${_find_args_${package_name}} BYPASS_PROVIDER PATHS "${_conan_generators_folder}" NO_DEFAULT_PATH NO_CMAKE_FIND_ROOT_PATH)
        unset(_find_args_${package_name})
    endif()

    # Invoke find_package a second time - if the first call succeeded,
    # this will simply reuse the result. If not, fall back to CMake default search
    # behaviour, also allowing modules to be searched.
    if(NOT ${package_name}_FOUND)
        list(FIND CMAKE_MODULE_PATH "${_conan_generators_folder}" _index)
        if(_index EQUAL -1)
            list(PREPEND CMAKE_MODULE_PATH "${_conan_generators_folder}")
        endif()
        unset(_index)
        find_package(${package_name} ${ARGN} BYPASS_PROVIDER)
        list(REMOVE_ITEM CMAKE_MODULE_PATH "${_conan_generators_folder}")
    endif()
endmacro()


cmake_language(
    SET_DEPENDENCY_PROVIDER conan_provide_dependency
    SUPPORTED_METHODS FIND_PACKAGE
)


macro(conan_provide_dependency_check)
    set(_conan_provide_dependency_invoked FALSE)
    get_property(_conan_provide_dependency_invoked GLOBAL PROPERTY CONAN_PROVIDE_DEPENDENCY_INVOKED)
    if(NOT _conan_provide_dependency_invoked)
        message(WARNING "Conan is correctly configured as dependency provider, "
                        "but Conan has not been invoked. Please add at least one "
                        "call to `find_package()`.")
        if(DEFINED CONAN_COMMAND)
            # supress warning in case `CONAN_COMMAND` was specified but unused.
            set(_conan_command ${CONAN_COMMAND})
            unset(_conan_command)
        endif()
    endif()
    unset(_conan_provide_dependency_invoked)
endmacro()


# Add a deferred call at the end of processing the top-level directory
# to check if the dependency provider was invoked at all.
cmake_language(DEFER DIRECTORY "${CMAKE_SOURCE_DIR}" CALL conan_provide_dependency_check)

# Configurable variables for Conan profiles
set(CONAN_HOST_PROFILE "default;auto-cmake" CACHE STRING "Conan host profile")
set(CONAN_BUILD_PROFILE "default" CACHE STRING "Conan build profile")
set(CONAN_INSTALL_ARGS "--build=missing" CACHE STRING "Command line arguments for conan install")
option(CONAN_OSX_UNIVERSAL_BINARIES
       "On macOS with two architectures in CMAKE_OSX_ARCHITECTURES, build the dependencies \
for each architecture separately and lipo-merge them into universal binaries. When OFF (the \
default), a single install for the first architecture is used, which only works if the \
recipes produce universal binaries themselves." OFF)

find_program(_cmake_program NAMES cmake NO_PACKAGE_ROOT_PATH NO_CMAKE_PATH NO_CMAKE_ENVIRONMENT_PATH NO_CMAKE_SYSTEM_PATH NO_CMAKE_FIND_ROOT_PATH)
if(NOT _cmake_program)
    get_filename_component(PATH_TO_CMAKE_BIN "${CMAKE_COMMAND}" DIRECTORY)
    set(PATH_TO_CMAKE_BIN "${PATH_TO_CMAKE_BIN}" CACHE INTERNAL "Path where the CMake executable is")
endif()

cmake_policy(POP)
