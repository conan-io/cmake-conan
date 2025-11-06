include_guard()



#[[
    This function downloads a selected compiler to a predefined directory.
    Some archives (like tar.xz) need to be flattend first
    This fuction ensures that the files located at the EXTRACT_TO folder contain the necessarry bin files

    COMPILER_URL= https://developer.arm.com/-/media/Files/downloads/gnu/14.3.rel1/binrel/arm-gnu-toolchain-14.3.rel1-mingw-w64-i686-arm-none-eabi.zip
    EXTRACT_TO= ./toolchain
]]
function(direct_download_compiler COMPILER_URL EXTRACT_TO)
  set(SUPPORTED_EXTENSIONS ".tar.gz" ".tar.bz2" ".tar.xz" ".tgz" ".tbz2" ".zip")

  set(EXPECTED_HASH "")
  if(ARGC GREATER 2)
    set(EXPECTED_HASH "${ARGV2}")
  endif()

  get_filename_component(ARCHIVE_NAME "${COMPILER_URL}" NAME)

  # check achive format
  set(FOUND_FORMAT "")
  foreach(EXT IN LISTS SUPPORTED_EXTENSIONS)
    if(ARCHIVE_NAME MATCHES "${EXT}$")
      set(FOUND_FORMAT "${EXT}")
      break()
    endif()
  endforeach()

  if(NOT FOUND_FORMAT)
    return()
  endif()

  # target dirs
  set(DOWNLOAD_DIR "${CMAKE_BINARY_DIR}/downloads")
  file(MAKE_DIRECTORY "${DOWNLOAD_DIR}")
  set(ARCHIVE_PATH "${DOWNLOAD_DIR}/${ARCHIVE_NAME}")

  if(EXISTS "${EXTRACT_TO}/bin" OR EXISTS "${EXTRACT_TO}/lib")
    message(STATUS "Compiler already extracted...: ${EXTRACT_TO}")
    set(DIRECT_DOWNLOAD_COMPILER_BIN_DIR
        "${EXTRACT_TO}"
        PARENT_SCOPE)
    return()
  endif()

  # check if download is necessarry
  set(NEED_DOWNLOAD TRUE)
  if(EXISTS "${ARCHIVE_PATH}")
    if(EXPECTED_HASH)
      file(SHA256 "${ARCHIVE_PATH}" ACTUAL_HASH)
      if(NOT "${EXPECTED_HASH}" STREQUAL "${ACTUAL_HASH}")
        message(
          WARNING
            "Hash mismatch: expected ${EXPECTED_HASH}, found ${ACTUAL_HASH}")
        file(REMOVE "${ARCHIVE_PATH}")
      else()
        set(NEED_DOWNLOAD FALSE)
        message(STATUS "found archive with valid hash: ${ARCHIVE_PATH}")
      endif()
    else()
      set(NEED_DOWNLOAD FALSE)
      message(
        STATUS "archive already downloaded (no hash check): ${ARCHIVE_PATH}")
    endif()
  endif()

  # Download if needed
  if(NEED_DOWNLOAD)
    message(STATUS "download Compiler from: ${COMPILER_URL}")
    file(
      DOWNLOAD "${COMPILER_URL}" "${ARCHIVE_PATH}"
      SHOW_PROGRESS
      STATUS DOWNLOAD_STATUS
      TLS_VERIFY ON)
    list(GET DOWNLOAD_STATUS 0 DOWNLOAD_RESULT)
    if(NOT DOWNLOAD_RESULT EQUAL 0)
      message(FATAL_ERROR "Download failed: ${COMPILER_URL}")
    endif()

    if(EXPECTED_HASH)
      file(SHA256 "${ARCHIVE_PATH}" ACTUAL_HASH)
      if(NOT "${EXPECTED_HASH}" STREQUAL "${ACTUAL_HASH}")
        message(
          FATAL_ERROR
            "hash missmatch: expected ${EXPECTED_HASH}, found ${ACTUAL_HASH}")
      endif()
    endif()
    message(STATUS "Download finnished: ${ARCHIVE_PATH}")
  endif()

  # preperare temp extraction folder
  set(TEMP_EXTRACT_DIR "${CMAKE_BINARY_DIR}/_temp_extract_dir_${ARCHIVE_NAME}")
  file(REMOVE_RECURSE "${TEMP_EXTRACT_DIR}")
  file(MAKE_DIRECTORY "${TEMP_EXTRACT_DIR}")

  # found archive
  message(STATUS "Extract archive → ${TEMP_EXTRACT_DIR}")
  file(ARCHIVE_EXTRACT INPUT "${ARCHIVE_PATH}" DESTINATION
       "${TEMP_EXTRACT_DIR}")

  # look up Top-Level-Dir in archive
  file(
    GLOB TOPLEVEL_ITEMS
    RELATIVE "${TEMP_EXTRACT_DIR}"
    "${TEMP_EXTRACT_DIR}/*")
  list(LENGTH TOPLEVEL_ITEMS NUM_TOPLEVEL)

  if(NUM_TOPLEVEL EQUAL 1)
    list(GET TOPLEVEL_ITEMS 0 SINGLE_DIR_NAME)
    set(SINGLE_DIR_PATH "${TEMP_EXTRACT_DIR}/${SINGLE_DIR_NAME}")
    if(IS_DIRECTORY "${SINGLE_DIR_PATH}")
      message(STATUS "Found Top-Level-directory: ${SINGLE_DIR_NAME}")
      # copy content of this directory to folder EXTRACT_TO
      file(COPY "${SINGLE_DIR_PATH}/" DESTINATION "${EXTRACT_TO}")
    else()
      # only a single file ....
      file(COPY "${SINGLE_DIR_PATH}" DESTINATION "${EXTRACT_TO}")
    endif()
  else()
    # multiple files/folders => copy everything
    file(COPY "${TEMP_EXTRACT_DIR}/" DESTINATION "${EXTRACT_TO}")
  endif()

  # cleanup
  file(REMOVE_RECURSE "${TEMP_EXTRACT_DIR}")

  message(STATUS "compiler extraction done: ${EXTRACT_TO}")

  set(DIRECT_DOWNLOAD_COMPILER_BIN_DIR
      "${EXTRACT_TO}"
      PARENT_SCOPE)
endfunction()




# --- Detect host platform (for optional logging or filters) ---
string(TOLOWER "${CMAKE_HOST_SYSTEM_NAME}" HOST_OS)
set(HOST_ARCH "${CMAKE_HOST_SYSTEM_PROCESSOR}")

if(HOST_OS STREQUAL "windows")
  set(HOST_TAG "windows")
elseif(HOST_OS STREQUAL "darwin")
  set(HOST_TAG "mac")
elseif(HOST_OS STREQUAL "linux")
  set(HOST_TAG "linux")
else()
  set(HOST_TAG "${HOST_OS}")
endif()

message(STATUS "Host platform detected: ${HOST_TAG} (${HOST_ARCH})")
# --- Determine toolchain installation path ---

set(TOOLCHAIN_PATH "${PROJECT_BINARY_DIR}/gcc_arm_none_eabi")


if(NOT EXISTS ${TOOLCHAIN_PATH})
  message(STATUS "About to download Compiler since TOOLCHAIN_PATH = ${TOOLCHAIN_PATH} does not exist")
  direct_download_compiler("${TOOLCHAIN_URL}" "${TOOLCHAIN_PATH}")
endif()

set(EXPECTED_COMPILER_TRIPLET "arm-none-eabi")
set(TOOLCHAIN_BIN_DIR "${TOOLCHAIN_PATH}/bin")

# --- Extend system PATH to include toolchain binaries ---
if(EXISTS "${TOOLCHAIN_BIN_DIR}")
  list(APPEND CMAKE_PROGRAM_PATH ${TOOLCHAIN_PATH} ${TOOLCHAIN_BIN_DIR})
  message( STATUS "Toolchain bin directory added to CMAKE_PROGRAM_PATH: ${EXPECTED_TOOLCHAIN_BIN_DIR}" )
endif()




# --- CMake cross-compile settings ---
set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR "${TOOLCHAIN_TARGET}")
# --- Determine executable suffix on Windows ---
if(WIN32)
  set(TOOL_SUFFIX ".exe")
else()
  set(TOOL_SUFFIX "")
endif()

# --- Set tool paths with suffix ---

if(EXISTS ${TOOLCHAIN_BIN_DIR})
  set(CMAKE_C_COMPILER "${TOOLCHAIN_BIN_DIR}/${EXPECTED_COMPILER_TRIPLET}-gcc${TOOL_SUFFIX}")
  set(CMAKE_CXX_COMPILER "${TOOLCHAIN_BIN_DIR}/${EXPECTED_COMPILER_TRIPLET}-g++${TOOL_SUFFIX}")
  set(CMAKE_ASM_COMPILER "${TOOLCHAIN_BIN_DIR}/${EXPECTED_COMPILER_TRIPLET}-gcc${TOOL_SUFFIX}")
  set(CMAKE_AR "${TOOLCHAIN_BIN_DIR}/${EXPECTED_COMPILER_TRIPLET}-ar${TOOL_SUFFIX}")
  set(CMAKE_OBJCOPY "${TOOLCHAIN_BIN_DIR}/${EXPECTED_COMPILER_TRIPLET}-objcopy${TOOL_SUFFIX}")
  set(CMAKE_OBJDUMP "${TOOLCHAIN_BIN_DIR}/${EXPECTED_COMPILER_TRIPLET}-objdump${TOOL_SUFFIX}")
  set(CMAKE_SIZE "${TOOLCHAIN_BIN_DIR}/${EXPECTED_COMPILER_TRIPLET}-size${TOOL_SUFFIX}")
  set(CMAKE_STRIP "${TOOLCHAIN_BIN_DIR}/${EXPECTED_COMPILER_TRIPLET}-strip${TOOL_SUFFIX}")
  
  # --- Check each tool exists and runs properly ---
  foreach(
    var IN
    ITEMS CMAKE_C_COMPILER
          CMAKE_CXX_COMPILER
          CMAKE_ASM_COMPILER
          CMAKE_AR
          CMAKE_OBJCOPY
          CMAKE_OBJDUMP
          CMAKE_SIZE
          CMAKE_STRIP)
    set(tool_path "${${var}}")
  
    if(NOT EXISTS "${tool_path}")
      message(FATAL_ERROR "Tool ${var} not found at path: ${tool_path}")
    endif()
  
    # Run '<tool> --version' to verify it works
    execute_process(
      COMMAND "${tool_path}" --version
      RESULT_VARIABLE res
      OUTPUT_QUIET ERROR_QUIET)
  
    if(NOT res EQUAL 0)
      message(
        FATAL_ERROR
          "Tool ${var} at ${tool_path} failed to run '--version'. Result: ${res}")
    endif()
  endforeach()
  
  # --- Cache tool paths ---
  foreach(
    var IN
    ITEMS CMAKE_C_COMPILER
          CMAKE_CXX_COMPILER
          CMAKE_ASM_COMPILER
          CMAKE_AR
          CMAKE_OBJCOPY
          CMAKE_OBJDUMP
          CMAKE_SIZE
          CMAKE_STRIP)
    set(${var}
        "${${var}}"
        CACHE FILEPATH "Toolchain tool: ${var}")
  endforeach()
endif()

# Perform compiler test with the static library
set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)

# --- Apply user-provided compiler arch flags ---

message(STATUS "Compiler architecture flags: ${COMPILER_ARCH_FLAGS}")

# Add classic optimization flags for embedded
set(COMMON_OPT_FLAGS "-ffunction-sections -fdata-sections")

# Compiler flags
set(CMAKE_C_FLAGS "${COMPILER_ARCH_FLAGS} ${COMMON_OPT_FLAGS}" CACHE STRING "C compiler arch flags")
set(CMAKE_CXX_FLAGS "${COMPILER_ARCH_FLAGS} ${COMMON_OPT_FLAGS}"  CACHE STRING "C++ compiler arch flags")
set(CMAKE_ASM_FLAGS  "${COMPILER_ARCH_FLAGS}"  CACHE STRING "ASM compiler arch flags")

# Linker flag for garbage collecting unused sections
set(CMAKE_EXE_LINKER_FLAGS  "-Wl,--gc-sections -ffunction-sections -fdata-sections"  CACHE STRING "Linker flags for executable" FORCE)

# Basis-Architektur-Flags
set(CMAKE_C_FLAGS  "${COMPILER_ARCH_FLAGS}"  CACHE STRING "C compiler arch flags" FORCE)
set(CMAKE_CXX_FLAGS "${COMPILER_ARCH_FLAGS}" CACHE STRING "C++ compiler arch flags" FORCE)

# Debug-Build: Optimierung aus + Debug-Symbole
set(CMAKE_C_FLAGS_DEBUG "-Og -g" CACHE STRING "C Debug flags" FORCE)
set(CMAKE_CXX_FLAGS_DEBUG "-Og -g" CACHE STRING "C++ Debug flags" FORCE)

# Release-Build: Optimiert für Geschwindigkeit, keine Debug-Symbole
set(CMAKE_C_FLAGS_RELEASE "-Os" CACHE STRING "C Release flags" FORCE)
set(CMAKE_CXX_FLAGS_RELEASE "-Os" CACHE STRING "C++ Release flags" FORCE)

# RelWithDebInfo: Optimiert, aber mit Debug-Symbolen (z.B. -O2 + -g)
set(CMAKE_C_FLAGS_RELWITHDEBINFO "-O2 -g" CACHE STRING "C Release with Debug Info flags" FORCE)
set(CMAKE_CXX_FLAGS_RELWITHDEBINFO "-O2 -g" CACHE STRING "C++ Release with Debug Info flags" FORCE)

# MinSizeRel: Minimale Größe (üblich: -Os, manchmal -Oz falls unterstützt)
set(CMAKE_C_FLAGS_MINSIZEREL "-Os" CACHE STRING "C Min Size Release flags" FORCE)
set(CMAKE_CXX_FLAGS_MINSIZEREL  "-Os"  CACHE STRING "C++ Min Size Release flags" FORCE)

# Build-Type-spezifische Ergänzungen, angehängt an die Basis-Flags optionally
# use -g3 for more debug infos than -g
set(CMAKE_EXE_LINKER_FLAGS_DEBUG "${CMAKE_EXE_LINKER_FLAGS} -g" CACHE STRING "Linker flags for Debug build" FORCE)
set(CMAKE_EXE_LINKER_FLAGS_RELEASE "${CMAKE_EXE_LINKER_FLAGS} -g0" CACHE STRING "Linker flags for Release build" FORCE)
set(CMAKE_EXE_LINKER_FLAGS_RELWITHDEBINFO "${CMAKE_EXE_LINKER_FLAGS} -g" CACHE STRING "Linker flags for RelWithDebInfo build" FORCE)
set(CMAKE_EXE_LINKER_FLAGS_MINSIZEREL "${CMAKE_EXE_LINKER_FLAGS} -g0" CACHE STRING "Linker flags for MinSizeRel build" FORCE)
