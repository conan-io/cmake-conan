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
  
  if(CMAKE_BUILD_TYPE)
    set(_SETTINGS -s build_type=${CMAKE_BUILD_TYPE})
  else()
    message(FATAL_ERROR "Please specify in command line CMAKE_BUILD_TYPE (-DCMAKE_BUILD_TYPE=Release)")
  endif()

  if (${CMAKE_CXX_COMPILER_ID} STREQUAL GNU)
    # using GCC
    # TODO: Handle versions and other params
    set(_SETTINGS ${_SETTINGS} -s compiler=gcc -s compiler.version=4.9 -s compiler.libcxx=libstdc++)
  elseif (${CMAKE_CXX_COMPILER_ID} STREQUAL Clang)
      # using Clang
      string(REPLACE "." ";" VERSION_LIST ${CMAKE_CXX_COMPILER_VERSION})
      list(GET VERSION_LIST 0 MAJOR)
      list(GET VERSION_LIST 1 MINOR)
      set(_SETTINGS ${_SETTINGS} -s compiler=clang -s compiler.version=${MAJOR}.${MINOR} -s compiler.libcxx=libstdc++)
  elseif(${CMAKE_CXX_COMPILER_ID} STREQUAL MSVC)
    set(_VISUAL "Visual Studio")
    # FIXME: Crappy, poor check
    if (${CMAKE_GENERATOR} MATCHES "Visual Studio 14")
      set(_SETTINGS ${_SETTINGS} -s compiler=${_VISUAL} -s compiler.version=14)
    elseif (${CMAKE_GENERATOR} MATCHES "Visual Studio 12")
      set(_SETTINGS ${_SETTINGS} -s compiler=${_VISUAL} -s compiler.version=12)
    elseif (${CMAKE_GENERATOR} MATCHES "Visual Studio 11")
      set(_SETTINGS ${_SETTINGS} -s compiler=${_VISUAL} -s compiler.version=11)
    elseif (${CMAKE_GENERATOR} MATCHES "Visual Studio 10")
      set(_SETTINGS ${_SETTINGS} -s compiler=${_VISUAL} -s compiler.version=10)
    elseif (${CMAKE_GENERATOR} MATCHES "Visual Studio 9")
      set(_SETTINGS ${_SETTINGS} -s compiler=${_VISUAL} -s compiler.version=9)
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

    set(_SETTINGS ${_SETTINGS} -s compiler.runtime=MD)
  else()
      message(FATAL_ERROR "Conan: compiler setup not recognized")
  endif()

  set(${result} ${_SETTINGS} PARENT_SCOPE)
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
                     RESULT_VARIABLE return_code)
    
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
    # Checks for the existence of conanbuildinfo.cmake, and loads it
    # important that it is macro, so variables defined at parent scope
    if(EXISTS "${CMAKE_BINARY_DIR}/conanbuildinfo.cmake")   
      message(STATUS "Conan: Loading conanbuildinfo.cmake")
      include(${CMAKE_BINARY_DIR}/conanbuildinfo.cmake)
    else()
      message(FATAL_ERROR "conanbuildinfo doesn't exist in ${CMAKE_BINARY_DIR}")
    endif()
endmacro()


macro(conan_cmake_run)
    parse_arguments(${ARGV})
    conan_cmake_settings(settings)
    conan_cmake_generate_conanfile(${ARGV})
    conan_cmake_install(SETTINGS ${settings} ${ARGV})
    conan_load_buildinfo()

    if(ARGUMENTS_BASIC_SETUP)
      if(ARGUMENTS_CMAKE_TARGETS)
        conan_basic_setup(TARGETS)
      else()
        conan_basic_setup()
      endif()
    endif()
endmacro()
    

          
