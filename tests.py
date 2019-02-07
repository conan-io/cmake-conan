import unittest
import tempfile
import os
import platform
import shutil


def save(filename, content):
    try:
        os.makedirs(os.path.dirname(filename))
    except:
        pass

    with open(filename, "w") as handle:
        handle.write(content)


def run(cmd, ignore_errors=False):
    retcode = os.system(cmd)
    if retcode != 0 and not ignore_errors:
        raise Exception("Command failed: %s" % cmd)

if platform.system() == "Windows":
    generator = '-G "Visual Studio 15"'
else:
    generator = '-G "Unix Makefiles"'
# TODO: Test Xcode

class CMakeConanTest(unittest.TestCase):

    def setUp(self):
        self.old_folder = os.getcwd()
        CONAN_TEST_FOLDER = os.getenv('CONAN_TEST_FOLDER', None)
        folder = tempfile.mkdtemp(suffix='conans', dir=CONAN_TEST_FOLDER)
        shutil.copy2("conan.cmake", os.path.join(folder, "conan.cmake"))
        shutil.copy2("main.cpp", os.path.join(folder, "main.cpp"))
        os.chdir(folder)
        folder = tempfile.mkdtemp(suffix="conan", dir=CONAN_TEST_FOLDER)
        self.old_env = dict(os.environ)
        os.environ.update({"CONAN_USER_HOME": folder})
        run("conan remote add transit https://api.bintray.com/conan/conan/conan-transit")

    def tearDown(self):
        os.chdir(self.old_folder)
        os.environ.clear()
        os.environ.update(self.old_env)

    def test_global(self):
        content = """set(CMAKE_CXX_COMPILER_WORKS 1)
set(CMAKE_CXX_ABI_COMPILED 1)
cmake_minimum_required(VERSION 2.8)
project(conan_wrapper CXX)

include(conan.cmake)
conan_cmake_run(REQUIRES Hello/0.1@memsharded/testing
                BASIC_SETUP
                BUILD missing)

add_executable(main main.cpp)
target_link_libraries(main ${CONAN_LIBS})
"""
        save("CMakeLists.txt", content)

        os.makedirs("build")
        os.chdir("build")
        run("cmake .. %s -DCMAKE_BUILD_TYPE=Release" % generator)
        run("cmake --build . --config Release")
        cmd = os.sep.join([".", "bin", "main"])
        run(cmd)

    def test_global_update(self):
        content = """set(CMAKE_CXX_COMPILER_WORKS 1)
set(CMAKE_CXX_ABI_COMPILED 1)
cmake_minimum_required(VERSION 2.8)
project(conan_wrapper CXX)

include(conan.cmake)
conan_cmake_run(REQUIRES Hello/0.1@memsharded/testing
                BASIC_SETUP
                UPDATE
                BUILD missing)

add_executable(main main.cpp)
target_link_libraries(main ${CONAN_LIBS})
"""
        save("CMakeLists.txt", content)

        os.makedirs("build")
        os.chdir("build")
        run("cmake .. %s -DCMAKE_BUILD_TYPE=Release" % generator)
        run("cmake --build . --config Release")
        cmd = os.sep.join([".", "bin", "main"])
        run(cmd)

    def _build_multi(self):
        os.makedirs("build")
        os.chdir("build")
        run("cmake .. %s" % generator)
        run("cmake --build . --config Release")
        cmd = os.sep.join([".", "Release", "main"])
        run(cmd)
        run("cmake --build . --config Debug")
        cmd = os.sep.join([".", "Debug", "main"])
        run(cmd)


    def test_multi(self):
        if platform.system() != "Windows":
            return
        content = """set(CMAKE_CXX_COMPILER_WORKS 1)
set(CMAKE_CXX_ABI_COMPILED 1)
cmake_minimum_required(VERSION 2.8)
project(conan_wrapper CXX)

include(conan.cmake)
conan_cmake_run(REQUIRES Hello/0.1@memsharded/testing
                BASIC_SETUP
                BUILD missing)

add_executable(main main.cpp)
foreach(_LIB ${CONAN_LIBS_RELEASE})
    target_link_libraries(main optimized ${_LIB})
endforeach()
foreach(_LIB ${CONAN_LIBS_DEBUG})
    target_link_libraries(main debug ${_LIB})
endforeach()
"""
        save("CMakeLists.txt", content)
        self._build_multi()

    def test_multi_targets(self):
        if platform.system() != "Windows":
            return
        content = """set(CMAKE_CXX_COMPILER_WORKS 1)
set(CMAKE_CXX_ABI_COMPILED 1)
cmake_minimum_required(VERSION 2.8)
project(conan_wrapper CXX)

include(conan.cmake)
conan_cmake_run(REQUIRES Hello/0.1@memsharded/testing
                BASIC_SETUP CMAKE_TARGETS
                BUILD missing)

add_executable(main main.cpp)
target_link_libraries(main CONAN_PKG::Hello)
"""
        save("CMakeLists.txt", content)
        self._build_multi()

    def test_targets(self):
        content = """set(CMAKE_CXX_COMPILER_WORKS 1)
set(CMAKE_CXX_ABI_COMPILED 1)
cmake_minimum_required(VERSION 2.8)
project(conan_wrapper CXX)

include(conan.cmake)
conan_cmake_run(REQUIRES Hello/0.1@memsharded/testing
                BASIC_SETUP CMAKE_TARGETS
                BUILD missing)

add_executable(main main.cpp)
target_link_libraries(main CONAN_PKG::Hello)
"""
        save("CMakeLists.txt", content)

        os.makedirs("build")
        os.chdir("build")
        run("cmake .. %s -DCMAKE_BUILD_TYPE=Release" % generator)
        run("cmake --build . --config Release")
        cmd = os.sep.join([".", "bin", "main"])
        run(cmd)

    def test_existing_conanfile(self):
        content = """set(CMAKE_CXX_COMPILER_WORKS 1)
set(CMAKE_CXX_ABI_COMPILED 1)
cmake_minimum_required(VERSION 2.8)
project(conan_wrapper CXX)

include(conan.cmake)
conan_cmake_run(CONANFILE conanfile.txt
                BASIC_SETUP CMAKE_TARGETS
                BUILD missing)

add_executable(main main.cpp)
target_link_libraries(main CONAN_PKG::Hello)
"""
        save("CMakeLists.txt", content)
        save("conanfile.txt", "[requires]\nHello/0.1@memsharded/testing\n"
                            "[generators]\ncmake")

        os.makedirs("build")
        os.chdir("build")
        run("cmake .. %s -DCMAKE_BUILD_TYPE=Release" % generator)
        run("cmake --build . --config Release")
        cmd = os.sep.join([".", "bin", "main"])
        run(cmd)

    def test_existing_conanfile_py(self):
        content = """set(CMAKE_CXX_COMPILER_WORKS 1)
set(CMAKE_CXX_ABI_COMPILED 1)
cmake_minimum_required(VERSION 2.8)
project(conan_wrapper CXX)

include(conan.cmake)
conan_cmake_run(CONANFILE conan/conanfile.py
                BASIC_SETUP CMAKE_TARGETS
                BUILD missing
                NO_IMPORTS
                INSTALL_ARGS --update)

add_executable(main main.cpp)
target_link_libraries(main CONAN_PKG::Hello)
"""
        save("CMakeLists.txt", content)
        save("conan/conanfile.py", """
from conans import ConanFile

class Pkg(ConanFile):
    requires = "Hello/0.1@memsharded/testing"
    generators = "cmake"
    # Defining the settings is necessary now to cache them
    settings = "os", "compiler", "arch", "build_type"

    def imports(self):
        raise Exception("BOOM!")
""")

        os.makedirs("build")
        os.chdir("build")
        run("cmake .. %s -DCMAKE_BUILD_TYPE=Release" % generator)
        run("cmake --build . --config Release")
        cmd = os.sep.join([".", "bin", "main"])
        run(cmd)

    def test_exported_package(self):
        content = """set(CMAKE_CXX_COMPILER_WORKS 1)
set(CMAKE_CXX_ABI_COMPILED 1)
cmake_minimum_required(VERSION 2.8)
project(conan_wrapper CXX)

set(CONAN_EXPORTED ON)
include(conan.cmake)
conan_cmake_run(CONANFILE conanfile.py
                BASIC_SETUP CMAKE_TARGETS
                BUILD missing)

add_executable(main main.cpp)
target_link_libraries(main CONAN_PKG::Hello)
"""
        save("CMakeLists.txt", content)
        save("conanfile.py", """from conans import ConanFile, CMake

class Pkg(ConanFile):
    name = "Test"
    version = "0.1"
    requires = "Hello/0.1@memsharded/testing"
    generators = "cmake"
    exports = ["CMakeLists.txt", "conan.cmake", "main.cpp"]
    settings = "os", "arch", "compiler", "build_type"

    def build(self):
        cmake = CMake(self)
        self.run('cmake . ' + cmake.command_line)
        self.run('cmake --build . ' + cmake.build_config)
        """)
        run("conan export . test/testing")

        os.makedirs("build")
        os.chdir("build")
        save("conanfile.txt", """[requires]
        Test/0.1@test/testing""")
        run("conan install . --build Test --build=missing")
        run("conan remove -f Test/0.1@test/testing")

    def test_vs_toolset(self):
        if platform.system() != "Windows":
            return
        content = """message(STATUS "COMPILING-------")
cmake_minimum_required(VERSION 2.8)
project(conan_wrapper CXX)

include(conan.cmake)
conan_cmake_run(REQUIRES Hello/0.1@memsharded/testing
                BASIC_SETUP
                BUILD missing)

add_executable(main main.cpp)
target_link_libraries(main ${CONAN_LIBS})
"""
        save("CMakeLists.txt", content)

        os.makedirs("build")
        os.chdir("build")
        run("cmake .. %s -T v140 -DCMAKE_BUILD_TYPE=Release" % (generator))
        run("cmake --build . --config Release")
        cmd = os.sep.join([".", "bin", "main"])
        run(cmd)

    def test_vs_toolset_host_x64(self):
        if platform.system() != "Windows":
            return
        content = """message(STATUS "COMPILING-------")
cmake_minimum_required(VERSION 2.8)
project(conan_wrapper CXX)

include(conan.cmake)
conan_cmake_run(REQUIRES Hello/0.1@memsharded/testing
                BASIC_SETUP
                BUILD missing)

add_executable(main main.cpp)
target_link_libraries(main ${CONAN_LIBS})
"""
        save("CMakeLists.txt", content)

        os.makedirs("build")
        os.chdir("build")
        run("cmake .. %s -T v140,host=x64 -DCMAKE_BUILD_TYPE=Release" % (generator))
        run("cmake --build . --config Release")
        cmd = os.sep.join([".", "bin", "main"])
        run(cmd)
        
    def test_arch(self):
        content = """#set(CMAKE_CXX_COMPILER_WORKS 1)
#set(CMAKE_CXX_ABI_COMPILED 1)
message(STATUS "COMPILING-------")
cmake_minimum_required(VERSION 2.8)
project(conan_wrapper CXX)

include(conan.cmake)
conan_cmake_run(BASIC_SETUP
                BUILD missing
                ARCH armv7)

if(NOT ${CONAN_SETTINGS_ARCH} STREQUAL "armv7")
    message(FATAL_ERROR "ARCHITECTURE IS NOT armv7")
endif()
"""
        save("CMakeLists.txt", content)

        os.makedirs("build")
        os.chdir("build")
        run("cmake .. %s -DCMAKE_BUILD_TYPE=Release" % (generator))


    def test_no_output_dir(self):
        content = """set(CMAKE_CXX_COMPILER_WORKS 1)
set(CMAKE_CXX_ABI_COMPILED 1)
message(STATUS "COMPILING-------")
cmake_minimum_required(VERSION 2.8)
project(conan_wrapper CXX)

include(conan.cmake)
conan_cmake_run(BASIC_SETUP
                NO_OUTPUT_DIRS
                BUILD missing)


if(CMAKE_RUNTIME_OUTPUT_DIRECTORY)
    message(FATAL_ERROR "OUTPUT_DIRS ${CMAKE_RUNTIME_OUTPUT_DIRECTORY}")
endif()
"""
        save("CMakeLists.txt", content)

        os.makedirs("build")
        os.chdir("build")
        run("cmake .. %s -DCMAKE_BUILD_TYPE=Release" % (generator))

    def test_build_type(self):
        content = """set(CMAKE_CXX_COMPILER_WORKS 1)
set(CMAKE_CXX_ABI_COMPILED 1)
message(STATUS "COMPILING-------")
cmake_minimum_required(VERSION 2.8)
project(conan_wrapper CXX)

include(conan.cmake)
conan_cmake_run(BASIC_SETUP
                BUILD_TYPE None)

if(NOT ${CONAN_SETTINGS_BUILD_TYPE} STREQUAL "None")
    message(FATAL_ERROR "CMAKE BUILD TYPE is not None!")
endif()
"""
        save("CMakeLists.txt", content)

        os.makedirs("build")
        os.chdir("build")
        run("cmake .. %s  -DCMAKE_BUILD_TYPE=Release" % (generator))

    def test_settings(self):
        content = """set(CMAKE_CXX_COMPILER_WORKS 1)
set(CMAKE_CXX_ABI_COMPILED 1)
message(STATUS "COMPILING-------")
cmake_minimum_required(VERSION 2.8)
project(conan_wrapper CXX)

include(conan.cmake)
conan_cmake_run(BASIC_SETUP
                SETTINGS arch=armv6
                SETTINGS cppstd=14)

if(NOT ${CONAN_SETTINGS_ARCH} STREQUAL "armv6")
    message(FATAL_ERROR "CONAN_SETTINGS_ARCH INCORRECT!")
endif()
if(NOT ${CONAN_SETTINGS_CPPSTD} STREQUAL "14")
    message(FATAL_ERROR "CONAN_SETTINGS_CPPSTD INCORRECT!")
endif()
"""
        save("CMakeLists.txt", content)

        os.makedirs("build")
        os.chdir("build")
        run("cmake .. %s  -DCMAKE_BUILD_TYPE=Release" % (generator))

    def test_profile_auto(self):
        content = """cmake_minimum_required(VERSION 2.8)
project(conan_wrapper CXX)

set(CONAN_DISABLE_CHECK_COMPILER ON)
include(conan.cmake)
conan_cmake_run(BASIC_SETUP
                PROFILE myprofile
                PROFILE_AUTO build_type
                PROFILE_AUTO compiler
                )

if(NOT "${CONAN_SETTINGS_BUILD_TYPE}" STREQUAL "${CMAKE_BUILD_TYPE}")
    message(FATAL_ERROR "CONAN_SETTINGS_BUILD_TYPE INCORRECT!")
endif()
if("${CONAN_SETTINGS_COMPILER}" STREQUAL "sun-cc")
    message(FATAL_ERROR "CONAN_SETTINGS_COMPILER INCORRECT!")
endif()
if("${CONAN_SETTINGS_COMPILER_VERSION}" STREQUAL "12")
    message(FATAL_ERROR "CONAN_SETTINGS_COMPILER_VERSION INCORRECT!")
endif()
if("${CONAN_SETTINGS_COMPILER_RUNTIME}" STREQUAL "MTd")
    message(FATAL_ERROR "CONAN_SETTINGS_COMPILER_RUNTIME INCORRECT!")
endif()
"""
        save("build/myprofile", """[settings]
build_type=RelWithDebInfo
compiler=sun-cc
compiler.version=5.10""")
        save("CMakeLists.txt", content)

        os.chdir("build")
        run("cmake .. %s  -DCMAKE_BUILD_TYPE=Release" % (generator))
        run("cmake .. %s  -DCMAKE_BUILD_TYPE=Debug" % (generator))

        save("build/myprofile", """[settings]
build_type=RelWithDebInfo
compiler=Visual Studio
compiler.version=12
compiler.runtime=MTd""")
        save("CMakeLists.txt", content)

        os.chdir("build")
        run("cmake .. %s  -DCMAKE_BUILD_TYPE=Release" % (generator))
        run("cmake .. %s  -DCMAKE_BUILD_TYPE=Debug" % (generator))

    def test_profile_auto_all(self):
        content = """cmake_minimum_required(VERSION 2.8)
project(conan_wrapper CXX)

set(CONAN_DISABLE_CHECK_COMPILER ON)
include(conan.cmake)
conan_cmake_run(BASIC_SETUP
                PROFILE myprofile
                PROFILE_AUTO ALL)

if("${CONAN_SETTINGS_BUILD_TYPE}" STREQUAL "RelWithDebInfo")
    message(FATAL_ERROR "CONAN_SETTINGS_BUILD_TYPE INCORRECT!")
endif()
if("${CONAN_SETTINGS_COMPILER}" STREQUAL "sun-cc")
    message(FATAL_ERROR "CONAN_SETTINGS_COMPILER INCORRECT!")
endif()
if("${CONAN_SETTINGS_COMPILER_VERSION}" STREQUAL "12")
    message(FATAL_ERROR "CONAN_SETTINGS_COMPILER_VERSION INCORRECT!")
endif()
if("${CONAN_SETTINGS_COMPILER_RUNTIME}" STREQUAL "MTd")
    message(FATAL_ERROR "CONAN_SETTINGS_COMPILER_RUNTIME INCORRECT!")
endif()
"""
        save("build/myprofile", """[settings]
build_type=RelWithDebInfo
compiler=sun-cc
compiler.version=5.10""")
        save("CMakeLists.txt", content)

        os.chdir("build")
        run("cmake .. %s  -DCMAKE_BUILD_TYPE=Release" % (generator))
        run("cmake .. %s  -DCMAKE_BUILD_TYPE=Debug" % (generator))

        save("build/myprofile", """[settings]
build_type=RelWithDebInfo
compiler=Visual Studio
compiler.version=12
compiler.runtime=MTd""")
        save("CMakeLists.txt", content)

        os.chdir("build")
        run("cmake .. %s  -DCMAKE_BUILD_TYPE=Release" % (generator))
        run("cmake .. %s  -DCMAKE_BUILD_TYPE=Debug" % (generator))

    def test_multi_profile(self):
        content = """cmake_minimum_required(VERSION 2.8)
project(conan_wrapper CXX)

set(CONAN_DISABLE_CHECK_COMPILER ON)
include(conan.cmake)
conan_cmake_run(BASIC_SETUP
                PROFILE myprofile PROFILE myprofile2)

if(NOT "${CONAN_SETTINGS_COMPILER_VERSION}" STREQUAL "12")
    message(FATAL_ERROR "CONAN_SETTINGS_COMPILER_VERSION INCORRECT!")
endif()
if(NOT "${CONAN_SETTINGS_COMPILER_RUNTIME}" STREQUAL "MTd")
    message(FATAL_ERROR "CONAN_SETTINGS_COMPILER_RUNTIME INCORRECT!")
endif()
"""
        save("build/myprofile", """[settings]
compiler=Visual Studio
compiler.version=15
compiler.runtime=MTd
""")
        save("build/myprofile2", """[settings]
compiler.version=12
""")
        save("CMakeLists.txt", content)

        os.chdir("build")
        run("cmake .. %s  -DCMAKE_BUILD_TYPE=Release" % (generator))
        run("cmake .. %s  -DCMAKE_BUILD_TYPE=Debug" % (generator))
