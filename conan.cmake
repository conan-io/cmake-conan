include(CMakeParseArguments)

function(conan_install_settings result)
  #message(STATUS "COMPILER " ${CMAKE_CXX_COMPILER})
  #message(STATUS "COMPILER " ${CMAKE_CXX_COMPILER_ID})
  #message(STATUS "VERSION " ${CMAKE_CXX_COMPILER_VERSION})
  # message(STATUS "FLAGS " ${CMAKE_LANG_FLAGS})
  #message(STATUS "LIB ARCH " ${CMAKE_CXX_LIBRARY_ARCHITECTURE})
  #message(STATUS "BUILD TYPE " ${CMAKE_BUILD_TYPE})
  #message(STATUS "GENERATOR " ${CMAKE_GENERATOR})
  #message(STATUS "GENERATOR WIN64 " ${CMAKE_CL_64})

  if(CMAKE_BUILD_TYPE)
    set(SETTINGS_STR -s build_type=${CMAKE_BUILD_TYPE})
  else()
    message(FATAL_ERROR "Please specify in command line CMAKE_BUILD_TYPE (-DCMAKE_BUILD_TYPE=Release)")
  endif()
  

  if (${CMAKE_CXX_COMPILER_ID} STREQUAL GNU)
    # using GCC
    set(SETTINGS_STR -s compiler=gcc -s compiler.version=4.9 -s compiler.libcxx=libstdc++)
  elseif (${CMAKE_CXX_COMPILER_ID} STREQUAL Clang)
      # using Clang
      string(REPLACE "." ";" VERSION_LIST ${CMAKE_CXX_COMPILER_VERSION})
      list(GET VERSION_LIST 0 MAJOR)
      list(GET VERSION_LIST 1 MINOR)
      set(SETTINGS_STR -s compiler=clang -s compiler.version=${MAJOR}.${MINOR} -s compiler.libcxx=libstdc++)
  elseif(${CMAKE_CXX_COMPILER_ID} STREQUAL MSVC)
    set(_VISUAL "Visual Studio")
    # FIXME: Crappy, poor check
    if (${CMAKE_GENERATOR} MATCHES "Visual Studio 14")
      set(SETTINGS_STR -s compiler=${_VISUAL} -s compiler.version=14)
    elseif (${CMAKE_GENERATOR} MATCHES "Visual Studio 12")
      set(SETTINGS_STR -s compiler=${_VISUAL} -s compiler.version=12)
    elseif (${CMAKE_GENERATOR} MATCHES "Visual Studio 11")
      set(SETTINGS_STR -s compiler=${_VISUAL} -s compiler.version=11)
    elseif (${CMAKE_GENERATOR} MATCHES "Visual Studio 10")
      set(SETTINGS_STR -s compiler=${_VISUAL} -s compiler.version=10)
    elseif (${CMAKE_GENERATOR} MATCHES "Visual Studio 9")
      set(SETTINGS_STR -s compiler=${_VISUAL} -s compiler.version=9)
    else ()
      message(FATAL_ERROR "Visual Studio not recognized") 
    endif()
    
    if(${CMAKE_GENERATOR} MATCHES "Win64")
        set(SETTINGS_STR ${SETTINGS_STR} -s arch=x86_64)
    elseif (${CMAKE_GENERATOR} MATCHES "ARM")
        message(STATUS "Conan: Using default ARM architecture from MSVC")
        set(SETTINGS_STR ${SETTINGS_STR} -s arch=armv6)
    else()
        set(SETTINGS_STR ${SETTINGS_STR} -s arch=x86)
    endif()
    
    set(SETTINGS_STR ${SETTINGS_STR} -s compiler.runtime=MD)
  else()
      message(FATAL_ERROR "Conan: compiler setup not recognized")
  endif()

  set(${result} ${SETTINGS_STR} PARENT_SCOPE)
endfunction()

function(conan_execute_install)
    set(options )
    set(oneValueArgs BUILD_DIR BUILD CONAN_COMMAND)
    set(multiValueArgs REQUIRES OPTIONS IMPORTS) 
    cmake_parse_arguments(CONANFILE "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN} )
  
    conan_install_settings(settings)

    if(CONANFILE_BUILD_DIR)
      set(CONAN_RUN_DIR ${CONANFILE_BUILD_DIR})
    else()
      set(CONAN_RUN_DIR ${CMAKE_BINARY_DIR})
     endif()
     if(CONANFILE_BUILD)
        set(CONAN_BUILD_POLICY "--build=${CONANFILE_BUILD}")
    else()
        set(CONAN_BUILD_POLICY "")
    endif()
    if(CONANFILE_CONAN_COMMAND)
       set(conan_command ${CONANFILE_CONAN_COMMAND})
    else()
      set(conan_command "conan")
    endif()
    
    set(conan_args install ${CONAN_RUN_DIR} ${settings} ${CONAN_BUILD_POLICY})

    add_custom_target(conan_install
                      COMMAND ${conan_command} ${conan_args}
                      WORKING_DIRECTORY ${CONAN_RUN_DIR})
    add_custom_command(TARGET conan_install
                   POST_BUILD
                   COMMAND ${CMAKE_COMMAND} ${CMAKE_SOURCE_DIR}
                   )

endfunction()

function(conan_generate_conanfile)
  set(options )
  set(oneValueArgs BUILD_DIR BUILD CONAN_COMMAND)
  set(multiValueArgs REQUIRES OPTIONS IMPORTS) 
  cmake_parse_arguments(CONANFILE "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN} )
 
  if(CONANFILE_BUILD_DIR)
    set(_FN "${CONANFILE_BUILD_DIR}/conanfile.txt")
  else()
    set(_FN "${CMAKE_BINARY_DIR}/conanfile.txt")
  endif()
  file(WRITE ${_FN} "[generators]\ncmake\n\n[requires]\n")
  foreach(ARG ${CONANFILE_REQUIRES})
    file(APPEND ${_FN} ${ARG} "\n")
  endforeach()
  
  file(APPEND ${_FN} ${ARG} "\n[options]\n")
  foreach(ARG ${CONANFILE_OPTIONS})
    file(APPEND ${_FN} ${ARG} "\n")
  endforeach()
  
  file(APPEND ${_FN} ${ARG} "\n[imports]\n")
  foreach(ARG ${CONANFILE_IMPORTS})
    file(APPEND ${_FN} ${ARG} "\n")
  endforeach()
     
endfunction()

macro(conan_requirements)  
    conan_generate_conanfile(${ARGV})
    conan_execute_install(${ARGV})   
    set(options BASIC_SETUP)
    set(oneValueArgs BUILD_DIR BUILD CONAN_COMMAND)
    set(multiValueArgs REQUIRES OPTIONS IMPORTS) 
    cmake_parse_arguments(CONANFILE "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN} )
    if(CONANFILE_BUILD_DIR)
      set(CONAN_RUN_DIR ${CONANFILE_BUILD_DIR})
    else()
      set(CONAN_RUN_DIR ${CMAKE_BINARY_DIR})
     endif()
    if(CONANFILE_BASIC_SETUP)
      if(EXISTS ${CONAN_RUN_DIR}/conanbuildinfo.cmake)
        message(STATUS "*Conan*: Loading conanbuildinfo.cmake")
        include(${CONAN_RUN_DIR}/conanbuildinfo.cmake)
        conan_basic_setup()
      endif()
    endif()
endmacro()
    

          
