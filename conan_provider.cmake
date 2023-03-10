include("${CMAKE_CURRENT_LIST_DIR}/conantools.cmake")

cmake_language(
  SET_DEPENDENCY_PROVIDER conan_provide_dependency
  SUPPORTED_METHODS FIND_PACKAGE
)