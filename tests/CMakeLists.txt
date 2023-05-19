cmake_minimum_required(VERSION 3.24)

include("${CMAKE_CURRENT_LIST_DIR}/../conan_support.cmake")

project(TestConanSupport)

function(expect_true result)
    if(NOT result)
        message(SEND_ERROR "Expected TRUE, but result is ${result}")
    endif()
endfunction()

function(expect_false result)
    if(result)
        message(SEND_ERROR "Expected FALSE, but result is ${result}")
    endif()
endfunction()

function(expect_equal value1 value2)
    if(NOT value1 STREQUAL value2)
        message(SEND_ERROR "Value is \"${value1}\" but expected \"${value2}\"")
    endif()
endfunction()

function(conan_version_check_major_too_old)
    conan_version_check(result MINIMUM 2.0.0 CURRENT 1.0.0)
    expect_false("${result}")
endfunction()
conan_version_check_major_too_old()

function(conan_version_check_minor_too_old)
    conan_version_check(result MINIMUM 2.1.0 CURRENT 2.0.0)
    expect_false("${result}")
endfunction()
conan_version_check_minor_too_old()

function(conan_version_check_patch_too_old)
    conan_version_check(result MINIMUM 2.0.1 CURRENT 2.0.0)
    expect_false("${result}")
endfunction()
conan_version_check_patch_too_old()

function(conan_version_check_major_new_enough)
    conan_version_check(result MINIMUM 1.0.0 CURRENT 2.0.0)
    expect_true("${result}")
endfunction()
conan_version_check_major_new_enough()

function(conan_version_check_minor_new_enough)
    conan_version_check(result MINIMUM 2.0.0 CURRENT 2.1.0)
    expect_true("${result}")
endfunction()
conan_version_check_minor_new_enough()

function(conan_version_check_patch_new_enough)
    conan_version_check(result MINIMUM 2.0.0 CURRENT 2.0.1)
    expect_true("${result}")
endfunction()
conan_version_check_patch_new_enough()
