include(CMakeParseArguments)


function(conan_cmake_settings result)
  #message(STATUS "COMPILER " ${CMAKE_CXX_COMPILER})
  #message(STATUS "COMPILER " ${CMAKE_CXX_COMPILER_ID})
  #message(STATUS "VERSION " ${CMAKE_CXX_COMPILER_VERSION})
  # message(STATUS "FLAGS " ${CMAKE_LANG_FLAGS})
  #message(STATUS "LIB ARCH " ${CMAKE_CXX_LIBRARY_ARCHITECTURE})
  #message(STATUS "BUILD TYPE " ${CMAKE_BUILD_TYPE})
  #message(STATUS "GENERATOR " ${CMAKE_GENERATOR})
  #message(STATUS "GENERATOR WIN64 " ${CMAKE_CL_64})

  message(STATUS "Conan ** WARNING** : This detection of settings from cmake is experimental and incomplete. "
                  "Please check 'conan.cmake' and contribute")

  if(CONAN_CMAKE_MULTI)
    set(_SETTINGS -g cmake_multi)
  else()
    set(_SETTINGS -g cmake)
  endif()
  if(CMAKE_BUILD_TYPE)
    set(_SETTINGS ${_SETTINGS} -s build_type=${CMAKE_BUILD_TYPE})
  else()
    message(FATAL_ERROR "Please specify in command line CMAKE_BUILD_TYPE (-DCMAKE_BUILD_TYPE=Release)")
  endif()

  #handle -s os setting
  if(CMAKE_SYSTEM_NAME)
  #use default conan os setting if CMAKE_SYSTEM_NAME is not defined
    set(CONAN_SUPPORTED_PLATFORMS Windows Linux Macos Android iOS FreeBSD)
    if( CMAKE_SYSTEM_NAME IN_LIST CONAN_SUPPORTED_PLATFORMS )
    #check if the cmake system is a conan supported one
      set(_SETTINGS ${_SETTINGS} -s os=${CMAKE_SYSTEM_NAME})
    else()
      message(FATAL_ERROR "cmake system ${CMAKE_SYSTEM_NAME} is not supported by conan. Use one of ${CONAN_SUPPORTED_PLATFORMS}")
    endif()
  endif()

  if (${CMAKE_CXX_COMPILER_ID} STREQUAL GNU)
    # using GCC
    # TODO: Handle other params
    string(REPLACE "." ";" VERSION_LIST ${CMAKE_CXX_COMPILER_VERSION})
    list(GET VERSION_LIST 0 MAJOR)
    list(GET VERSION_LIST 1 MINOR)
    conan_cmake_detect_gnu_libcxx(_LIBCXX)
    set(_SETTINGS ${_SETTINGS} -s compiler=gcc -s compiler.version=${MAJOR}.${MINOR} -s compiler.libcxx=${_LIBCXX})
  elseif (${CMAKE_CXX_COMPILER_ID} STREQUAL AppleClang)
      # using AppleClang
      string(REPLACE "." ";" VERSION_LIST ${CMAKE_CXX_COMPILER_VERSION})
      list(GET VERSION_LIST 0 MAJOR)
      list(GET VERSION_LIST 1 MINOR)
      set(_SETTINGS ${_SETTINGS} -s compiler=apple-clang -s compiler.version=${MAJOR}.${MINOR} -s compiler.libcxx=libc++)
  elseif (${CMAKE_CXX_COMPILER_ID} STREQUAL Clang)
      # using Clang
      string(REPLACE "." ";" VERSION_LIST ${CMAKE_CXX_COMPILER_VERSION})
      list(GET VERSION_LIST 0 MAJOR)
      list(GET VERSION_LIST 1 MINOR)
      set(_SETTINGS ${_SETTINGS} -s compiler=clang -s compiler.version=${MAJOR}.${MINOR} -s compiler.libcxx=libstdc++)
  elseif(${CMAKE_CXX_COMPILER_ID} STREQUAL MSVC)
      set(_VISUAL "Visual Studio")
      if (MSVC_VERSION EQUAL 1200)
          set(_SETTINGS ${_SETTINGS} -s compiler=${_VISUAL} -s compiler.version=6)
      elseif (MSVC_VERSION EQUAL 1300)
          set(_SETTINGS ${_SETTINGS} -s compiler=${_VISUAL} -s compiler.version=7)
      elseif (MSVC_VERSION EQUAL 1310)
          set(_SETTINGS ${_SETTINGS} -s compiler=${_VISUAL} -s compiler.version=7)
      elseif (MSVC_VERSION EQUAL 1400)
          set(_SETTINGS ${_SETTINGS} -s compiler=${_VISUAL} -s compiler.version=8)
      elseif (MSVC_VERSION EQUAL 1500)
          set(_SETTINGS ${_SETTINGS} -s compiler=${_VISUAL} -s compiler.version=9)
      elseif (MSVC_VERSION EQUAL 1600)
          set(_SETTINGS ${_SETTINGS} -s compiler=${_VISUAL} -s compiler.version=10)
      elseif (MSVC_VERSION EQUAL 1700)
          set(_SETTINGS ${_SETTINGS} -s compiler=${_VISUAL} -s compiler.version=11)
      elseif (MSVC_VERSION EQUAL 1800)
          set(_SETTINGS ${_SETTINGS} -s compiler=${_VISUAL} -s compiler.version=12)
      elseif (MSVC_VERSION EQUAL 1900)
          set(_SETTINGS ${_SETTINGS} -s compiler=${_VISUAL} -s compiler.version=14)
      else ()
          message(FATAL_ERROR "Visual Studio not recognized")
      endif()

      if(${CMAKE_GENERATOR} MATCHES "Win64")
          set(_SETTINGS ${_SETTINGS} -s arch=x86_64)
      elseif (${CMAKE_GENERATOR} MATCHES "ARM")
          message(STATUS "Conan: Using default ARM architecture from MSVC")
          set(_SETTINGS ${_SETTINGS} -s arch=armv6)
      else()
          set(_SETTINGS ${_SETTINGS} -s arch=x86)
      endif()

    conan_cmake_detect_vs_runtime(_vs_runtime)
    message(STATUS "Detected VS runtime: ${_vs_runtime}")
    set(_SETTINGS ${_SETTINGS} -s compiler.runtime=${_vs_runtime})
  else()
      message(FATAL_ERROR "Conan: compiler setup not recognized")
  endif()

  set(${result} ${_SETTINGS} PARENT_SCOPE)
endfunction()


function(conan_cmake_detect_gnu_libcxx result)
    get_directory_property(defines DIRECTORY ${CMAKE_SOURCE_DIR} COMPILE_DEFINITIONS)
    foreach(define ${defines})
        if(define STREQUAL "_GLIBCXX_USE_CXX11_ABI=0")
            set(${result} libstdc++ PARENT_SCOPE)
            return()
        endif()
    endforeach()
    if(CMAKE_CXX_COMPILER_VERSION VERSION_LESS "5.1")
      set(${result} libstdc++ PARENT_SCOPE)
    else()
      set(${result} libstdc++11 PARENT_SCOPE)
    endif()
endfunction()


function(conan_cmake_detect_vs_runtime result)
    string(TOUPPER ${CMAKE_BUILD_TYPE} build_type)
    set(variables CMAKE_CXX_FLAGS_${build_type} CMAKE_C_FLAGS_${build_type} CMAKE_CXX_FLAGS CMAKE_C_FLAGS)
    foreach(variable ${variables})
        string(REPLACE " " ";" flags ${${variable}})
        foreach (flag ${flags})
            if(${flag} STREQUAL "/MD" OR ${flag} STREQUAL "/MDd" OR ${flag} STREQUAL "/MT" OR ${flag} STREQUAL "/MTd")
                string(SUBSTRING ${flag} 1 -1 runtime)
                set(${result} ${runtime} PARENT_SCOPE)
                return()
            endif()
        endforeach()
    endforeach()
    if(${build_type} STREQUAL "DEBUG")
        set(${result} "MDd" PARENT_SCOPE)
    else()
        set(${result} "MD" PARENT_SCOPE)
    endif()
endfunction()


macro(parse_arguments)
  set(options BASIC_SETUP CMAKE_TARGETS)
  set(oneValueArgs BUILD CONAN_COMMAND CONANFILE)
  set(multiValueArgs REQUIRES OPTIONS IMPORTS)
  cmake_parse_arguments(ARGUMENTS "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN} )
endmacro()

function(conan_cmake_install)
    # Calls "conan install"
    # Argument BUILD is equivalant to --build={missing, PkgName,...}
    # Argument CONAN_COMMAND, to specify the conan path, e.g. in case of running from source
    # cmake does not identify conan as command, even if it is +x and it is in the path
    parse_arguments(${ARGV})

    if(ARGUMENTS_BUILD)
        set(CONAN_BUILD_POLICY --build=${ARGUMENTS_BUILD})
    else()
        set(CONAN_BUILD_POLICY "")
    endif()
    if(ARGUMENTS_CONAN_COMMAND)
       set(conan_command ${ARGUMENTS_CONAN_COMMAND})
    else()
      set(conan_command conan)
    endif()
    if(ARGUMENTS_CONANFILE)
      set(CONANFILE -f=${CMAKE_SOURCE_DIR}/${ARGUMENTS_CONANFILE})
    endif()
    set(conan_args install ${CONANFILE} ${settings} ${CONAN_BUILD_POLICY})

    string (REPLACE ";" " " _conan_args "${conan_args}")
    message(STATUS "Conan executing: ${conan_command} ${_conan_args}")

    execute_process(COMMAND ${conan_command} ${conan_args}
                     RESULT_VARIABLE return_code
                     WORKING_DIRECTORY ${CMAKE_BINARY_DIR})
    
    if(NOT "${return_code}" STREQUAL "0")
      message(FATAL_ERROR "Conan install failed='${return_code}'")
    endif()

endfunction()


function(conan_cmake_generate_conanfile)
  # Generate, writing in disk a conanfile.txt with the requires, options, and imports
  # specified as arguments
  # This will be considered as temporary file, generated in CMAKE_BINARY_DIR
  parse_arguments(${ARGV})
  if(ARGUMENTS_CONANFILE)
    return()
  endif()
  set(_FN "${CMAKE_BINARY_DIR}/conanfile.txt")

  file(WRITE ${_FN} "[generators]\ncmake\n\n[requires]\n")
  foreach(ARG ${ARGUMENTS_REQUIRES})
    file(APPEND ${_FN} ${ARG} "\n")
  endforeach()

  file(APPEND ${_FN} ${ARG} "\n[options]\n")
  foreach(ARG ${ARGUMENTS_OPTIONS})
    file(APPEND ${_FN} ${ARG} "\n")
  endforeach()

  file(APPEND ${_FN} ${ARG} "\n[imports]\n")
  foreach(ARG ${ARGUMENTS_IMPORTS})
    file(APPEND ${_FN} ${ARG} "\n")
  endforeach()
endfunction()


macro(conan_load_buildinfo)
    if(CONAN_CMAKE_MULTI)
      set(_CONANBUILDINFO conanbuildinfo_multi.cmake)
    else()
      set(_CONANBUILDINFO conanbuildinfo.cmake)
    endif()
    # Checks for the existence of conanbuildinfo.cmake, and loads it
    # important that it is macro, so variables defined at parent scope
    if(EXISTS "${CMAKE_BINARY_DIR}/${_CONANBUILDINFO}")
      message(STATUS "Conan: Loading ${_CONANBUILDINFO}")
      include(${CMAKE_BINARY_DIR}/${_CONANBUILDINFO})
    else()
      message(FATAL_ERROR "${_CONANBUILDINFO} doesn't exist in ${CMAKE_BINARY_DIR}")
    endif()
endmacro()


macro(conan_cmake_run)
    parse_arguments(${ARGV})

    # TODO: Better detection
    if(CONAN_EXPORTED OR CONAN_COMPILER)
        set(CONAN_EXPORTED ON)
    endif()

    if(CMAKE_CONFIGURATION_TYPES AND NOT CMAKE_BUILD_TYPE AND NOT CONAN_EXPORTED)
        set(CONAN_CMAKE_MULTI ON)
        message(STATUS "Conan: Using cmake-multi generator")
    else()
        set(CONAN_CMAKE_MULTI OFF)
    endif()
    if(NOT CONAN_EXPORTED)
        conan_cmake_generate_conanfile(${ARGV})
        if(CONAN_CMAKE_MULTI)
            foreach(CMAKE_BUILD_TYPE "Release" "Debug")
                conan_cmake_settings(settings)
                conan_cmake_install(SETTINGS ${settings} ${ARGV})
            endforeach()
            set(CMAKE_BUILD_TYPE)
        else()
            conan_cmake_settings(settings)
            conan_cmake_install(SETTINGS ${settings} ${ARGV})
        endif()
    endif()

    conan_load_buildinfo()

    if(ARGUMENTS_BASIC_SETUP)
      if(ARGUMENTS_CMAKE_TARGETS)
        conan_basic_setup(TARGETS)
      else()
        conan_basic_setup()
      endif()
    endif()
endmacro()
