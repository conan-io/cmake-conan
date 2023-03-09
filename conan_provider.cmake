cmake_minimum_required(VERSION 3.24)

include("${CMAKE_CURRENT_LIST_DIR}/conantools.cmake")

set(CONAN_OUTPUT_FOLDER ${CMAKE_BINARY_DIR}/conan)

macro(conan_provide_dependency package_name)

    if(NOT CONAN_INSTALL_SUCCESS)
        detect_host_profile(${CMAKE_BINARY_DIR}/conan_host_profile)
        conan_install(-pr ${CMAKE_BINARY_DIR}/conan_host_profile --output-folder ${CONAN_OUTPUT_FOLDER} -g CMakeDeps)
        if (CONAN_INSTALL_SUCCESS)
            message("Conan generators folder: ${CONAN_GENERATORS_FOLDER}")
            set(CONAN_GENERATORS_FOLDER "${CONAN_GENERATORS_FOLDER}" CACHE PATH "Conan generators folder")
        endif()
    endif()

    if (CONAN_GENERATORS_FOLDER)
        list(PREPEND CMAKE_PREFIX_PATH "${CONAN_GENERATORS_FOLDER}")
    endif()

    find_package(${ARGN} BYPASS_PROVIDER)
endmacro()


cmake_language(
  SET_DEPENDENCY_PROVIDER conan_provide_dependency
  SUPPORTED_METHODS FIND_PACKAGE
)