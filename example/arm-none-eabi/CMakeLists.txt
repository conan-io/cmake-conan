
cmake_minimum_required (VERSION 3.30)



project ("arm-none-eabi")

set(EXE_NAME arm_none_eabi_test)

set(CMAKE_EXECUTABLE_SUFFIX ".elf")
set(EXE_SOURCES "main.c" "syscall_wrapper.h" "syscall_wrapper.c" "fmt_dummy.h" "fmt_dummy.cpp")

list(APPEND EXE_SOURCES "startup_stm32f429xx.s")
# Cmake does not seam to recognise *.s files as ASM. Tell Cmake the language
set_source_files_properties("target/startup_stm32f429xx.s"
                            PROPERTIES LANGUAGE ASM)

find_program(CMAKE_SIZE arm-none-eabi-size)
if(NOT CMAKE_SIZE)
  message(FATAL_ERROR "Could not find 'arm-none-eabi-size'. Please install it or set CMAKE_SIZE manually.")
endif()

set(LINKER_SCRIPT_PATH "${CMAKE_CURRENT_LIST_DIR}/STM32F429XX_FLASH.ld")

# Check file existance
if(NOT EXISTS ${LINKER_SCRIPT_PATH})
  message(FATAL_ERROR "Linker Script does not exist. Path = ${LINKER_SCRIPT_PATH}")
endif()

add_link_options(-T${LINKER_SCRIPT_PATH} -Wl,--gc-sections  -Wl,-Map=${PROJECT_NAME}.map)



find_package(fmt REQUIRED)

add_executable(${EXE_NAME} ${EXE_SOURCES})

# create an alias target if fmt is used in header only mode
if(NOT TARGET fmt::fmt AND TARGET fmt::fmt-header-only)
  add_library(fmt::fmt ALIAS fmt::fmt-header-only)
endif()

target_link_libraries(${EXE_NAME} PUBLIC fmt::fmt)

set(WRAPPED_SYMBOLS malloc free realloc calloc)

set(WRAP_OPTIONS "")
foreach(SYM IN LISTS WRAPPED_SYMBOLS)
  list(APPEND WRAP_OPTIONS "-Wl,--wrap=${SYM}")
endforeach()

set(LINKER_STATS_OPTIONS "-Wl,--print-memory-usage")

target_link_options(${EXE_NAME} PUBLIC ${WRAP_OPTIONS}
                    ${LINKER_STATS_OPTIONS})

add_custom_command(
  TARGET ${EXE_NAME}
  POST_BUILD
  COMMAND ${CMAKE_SIZE} $<TARGET_FILE:${EXE_NAME}>
  COMMENT "Memory usage summary")