cmake_minimum_required(VERSION 2.8)
project(conan_wrapper C CXX)

# message(STATUS "COMPILER " ${CMAKE_CXX_COMPILER})
# message(STATUS "COMPILER " ${CMAKE_CXX_COMPILER_ID})
# message(STATUS "VERSION " ${CMAKE_CXX_COMPILER_VERSION})
# message(STATUS "FLAGS " ${CMAKE_LANG_FLAGS})
# message(STATUS "LIB ARCH " ${CMAKE_CXX_LIBRARY_ARCHITECTURE})
# message(STATUS "BUILD TYPE " ${CMAKE_BUILD_TYPE})
# message(STATUS "GENERATOR " ${CMAKE_GENERATOR})
# message(STATUS "GENERATOR WIN64 " ${CMAKE_CL_64})

function(conan_install_settings result)
  set(SETTINGS_STR "")
  if(${CMAKE_GENERATOR} MATCHES "Visual Studio 14")
    set(_VISUAL "Visual Studio")
    set(SETTINGS_STR -s compiler=${_VISUAL} -s compiler.version=14)
    if(${CMAKE_CL_64})
      set(SETTINGS_STR ${SETTINGS_STR} -s arch=x86_64)
    else()
      set(SETTINGS_STR ${SETTINGS_STR} -s arch=x86)
    endif()
  endif()
  set(SETTINGS_STR ${SETTINGS_STR} -s build_type=Release -s compiler.runtime=MD)
  set(${result} ${SETTINGS_STR} PARENT_SCOPE)
endfunction()

function(real_install)
    conan_install_settings(settings)
    # message(STATUS "MY_SETTINGS OK " ${settings})

    #add_custom_target(ConanDeps ALL
    #                  COMMAND conan install ${CMAKE_SOURCE_DIR} ${settings}
    #                 )

    #message(STATUS "added 1st cmmand!")
    #add_custom_command(OUTPUT ${CMAKE_BINARY_DIR}/conanbuildinfo.cmake
    #                 COMMAND conan install ${CMAKE_SOURCE_DIR} ${settings})
                                       
    #add_custom_target(conan_install
    #                  COMMAND conan install ${CMAKE_BINARY_DIR} ${settings})

    message(STATUS "conan install ${CMAKE_BINARY_DIR} ${settings}") 
    set(conan_command "conan")
    set(conan_args install . ${settings})
    execute_process(
          COMMAND ${conan_command} ${conan_args}
          WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
          RESULT_VARIABLE error_code
          OUTPUT_VARIABLE out_var)
    if(error_code)
      message(FATAL_ERROR "Error while executing conan install: ${error_code}, ${out_var}")
    else()
      message(STATUS ${out_var})
    endif()
endfunction()

function(generate_conanfile)
  set(_FN "${CMAKE_BINARY_DIR}/conanfile.txt")
  file(WRITE ${_FN} "[generators]\ncmake\n")
  foreach(ARG ${ARGV})
    if(${ARG} STREQUAL "REQUIRES")
      file(APPEND ${_FN} "\n[requires]\n")     
    elseif(${ARG} STREQUAL "OPTIONS")
      file(APPEND ${_FN} "\n[options]\n")
    else()
      file(APPEND ${_FN} ${ARG} "\n")
    endif()
  endforeach()
endfunction()

macro(conan_requirements)
    generate_conanfile(${ARGV})
    real_install()
    include(${CMAKE_BINARY_DIR}/conanbuildinfo.cmake)
endmacro()
    

          