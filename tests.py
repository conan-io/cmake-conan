import unittest
import tempfile
import os
import platform
import shutil
import json
import textwrap

from nose.plugins.attrib import attr

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

    def tearDown(self):
        os.chdir(self.old_folder)
        os.environ.clear()
        os.environ.update(self.old_env)

    # https://github.com/conan-io/cmake-conan/issues/279
    def test_options_override_profile(self):
        content = textwrap.dedent("""
            cmake_minimum_required(VERSION 2.8)
            project(FormatOutput CXX)
            set(CMAKE_CXX_STANDARD 11)
            include(conan.cmake)
            conan_cmake_run(REQUIRES fmt/6.1.2
                            PROFILE default
                            PROFILE fmtnotshared
                            BASIC_SETUP
                            BUILD missing
                            OPTIONS fmt:shared=True)

            add_executable(main main.cpp)
            target_link_libraries(main ${CONAN_LIBS})
        """)
        save("CMakeLists.txt", content)

        os.makedirs("build")

        save("build/fmtnotshared", textwrap.dedent("""
            [options]
            fmt:shared=False
        """))
        run("conan profile new default --detect")
        os.chdir("build")
        run("cmake .. %s -DCMAKE_BUILD_TYPE=Release > output.txt" % generator)
        with open('output.txt', 'r') as file:
            data = file.read()
            print(data)
            assert "-o=fmt:shared=True" in data
            assert "[options]\nfmt:shared=True" in data

    # https://github.com/conan-io/cmake-conan/issues/159
    @unittest.skipIf(platform.system() != "Darwin", "Error message appears just in Macos")
    def test_macos_sysroot_warning(self):
        content = textwrap.dedent("""
            cmake_minimum_required(VERSION 2.8)
            project(FormatOutput CXX)
            set(CMAKE_CXX_STANDARD 11)
            include(conan.cmake)
            conan_cmake_run(REQUIRES fmt/6.1.2
                            NO_IMPORTS
                            BASIC_SETUP
                            BUILD missing)

            add_executable(main main.cpp)
            target_link_libraries(main ${CONAN_LIBS})
        """)
        save("CMakeLists.txt", content)

        os.makedirs("build")
        os.chdir("build")
        run("cmake .. %s -DCMAKE_BUILD_TYPE=Release 2> stderr_output.txt" % generator)
        with open('stderr_output.txt', 'r') as file:
            data = file.read()
            assert "#include_next <string.h>" not in data

    def test_conan_cmake_configure(self):
        content = textwrap.dedent("""
            cmake_minimum_required(VERSION 2.8)
            project(FormatOutput CXX)
            include(conan.cmake)
            conan_cmake_configure(REQUIRES poco/1.9.4 zlib/1.2.11
                                  BUILD_REQUIRES 7zip/16.00
                                  GENERATORS xcode cmake qmake
                                  OPTIONS poco:shared=True openssl:shared=True
                                  IMPORTS "bin, *.dll -> ./bin"
                                  IMPORTS "lib, *.dylib* -> ./bin")
        """)
        result_conanfile = textwrap.dedent("""
            [requires]
            poco/1.9.4
            zlib/1.2.11
            [generators]
            xcode
            cmake
            qmake
            [build_requires]
            7zip/16.00
            [imports]
            bin, *.dll -> ./bin
            lib, *.dylib* -> ./bin
            [options]
            poco:shared=True
            openssl:shared=True
        """)
        save("CMakeLists.txt", content)
        os.makedirs("build")
        os.chdir("build")
        run("cmake .. {} -DCMAKE_BUILD_TYPE=Release".format(generator))
        with open('conanfile.txt', 'r') as file:
            data = file.read()
            assert data in result_conanfile

    def test_conan_cmake_install_args(self):
        content = textwrap.dedent("""
            cmake_minimum_required(VERSION 3.5)
            project(FormatOutput CXX)
            add_definitions("-std=c++11")
            include(conan.cmake)
            conan_cmake_configure(REQUIRES fmt/6.1.2)
            conan_cmake_autodetect(settings)
            conan_cmake_install(PATH_OR_REFERENCE .
                                GENERATOR cmake
                                BUILD missing
                                REMOTE conan-center
                                SETTINGS ${settings})
            include(${CMAKE_BINARY_DIR}/conanbuildinfo.cmake)
            conan_basic_setup(TARGETS)
            add_executable(main main.cpp)
            target_link_libraries(main CONAN_PKG::fmt)
        """)
        save("CMakeLists.txt", content)
        os.makedirs("build")
        os.chdir("build")
        run("cmake .. {} -DCMAKE_BUILD_TYPE=Release".format(generator))
        run("cmake --build . --config Release")
        
    def test_conan_cmake_install_find_package(self):
        content = textwrap.dedent("""
            cmake_minimum_required(VERSION 3.5)
            project(FormatOutput CXX)
            list(APPEND CMAKE_MODULE_PATH ${CMAKE_BINARY_DIR})
            list(APPEND CMAKE_PREFIX_PATH ${CMAKE_BINARY_DIR})
             add_definitions("-std=c++11")
            include(conan.cmake)
            conan_cmake_configure(REQUIRES fmt/6.1.2 GENERATORS cmake_find_package)
            conan_cmake_autodetect(settings)
            conan_cmake_install(PATH_OR_REFERENCE .
                                BUILD missing
                                REMOTE conan-center
                                SETTINGS ${settings})
            find_package(fmt)
            add_executable(main main.cpp)
            target_link_libraries(main fmt::fmt)
        """)
        save("CMakeLists.txt", content)
        os.makedirs("build")
        os.chdir("build")
        run("cmake .. {} -DCMAKE_BUILD_TYPE=Release".format(generator))
        run("cmake --build . --config Release")
        
    def test_conan_add_remote(self):
        content = textwrap.dedent("""
            cmake_minimum_required(VERSION 2.8)
            project(FormatOutput CXX)
            include(conan.cmake)            
            conan_add_remote(NAME someremote 
                             INDEX 0 
                             URL http://someremote
                             VERIFY_SSL False)
        """)
        save("CMakeLists.txt", content)
        os.makedirs("build")
        os.chdir("build")
        run("cmake .. %s -DCMAKE_BUILD_TYPE=Release" % generator)
        run("conan remote list > output_remotes.txt")
        with open('output_remotes.txt', 'r') as file:
            data = file.read()
            assert "someremote: http://someremote [Verify SSL: False]" in data      

    def test_global_update(self):
        content = textwrap.dedent("""
            set(CMAKE_CXX_COMPILER_WORKS 1)
            set(CMAKE_CXX_ABI_COMPILED 1)
            cmake_minimum_required(VERSION 2.8)
            project(FormatOutput CXX)
            add_definitions("-std=c++11")
            message(STATUS "CMAKE VERSION: ${CMAKE_VERSION}")

            include(conan.cmake)
            conan_cmake_run(REQUIRES fmt/6.1.2
                            BASIC_SETUP
                            UPDATE
                            BUILD missing)

            add_executable(main main.cpp)
            target_link_libraries(main ${CONAN_LIBS})
        """)
        save("CMakeLists.txt", content)

        os.makedirs("build")
        os.chdir("build")
        run("cmake .. %s -DCMAKE_BUILD_TYPE=Release" % generator)
        run("cmake --build . --config Release")
        cmd = os.sep.join([".", "bin", "main"])
        run(cmd)

    def test_existing_conanfile_py(self):
        content = textwrap.dedent("""
            set(CMAKE_CXX_COMPILER_WORKS 1)
            set(CMAKE_CXX_ABI_COMPILED 1)
            cmake_minimum_required(VERSION 2.8)
            project(FormatOutput CXX)
            add_definitions("-std=c++11")
            message(STATUS "CMAKE VERSION: ${CMAKE_VERSION}")

            include(conan.cmake)
            conan_cmake_run(CONANFILE conan/conanfile.py
                            BASIC_SETUP CMAKE_TARGETS
                            BUILD missing
                            NO_IMPORTS
                            INSTALL_ARGS --update)

            add_executable(main main.cpp)
            target_link_libraries(main CONAN_PKG::fmt)
        """)
        save("CMakeLists.txt", content)
        save("conan/conanfile.py", textwrap.dedent("""
            from conans import ConanFile

            class Pkg(ConanFile):
                requires = "fmt/6.1.2"
                generators = "cmake"
                # Defining the settings is necessary now to cache them
                settings = "os", "compiler", "arch", "build_type"

                def imports(self):
                    raise Exception("BOOM!")
        """))

        os.makedirs("build")
        os.chdir("build")
        run("cmake .. %s -DCMAKE_BUILD_TYPE=Release" % generator)
        run("cmake --build . --config Release")
        cmd = os.sep.join([".", "bin", "main"])
        run(cmd)

    def test_exported_package(self):
        content = textwrap.dedent("""
            set(CMAKE_CXX_COMPILER_WORKS 1)
            set(CMAKE_CXX_ABI_COMPILED 1)
            cmake_minimum_required(VERSION 2.8)
            project(FormatOutput CXX)
            add_definitions("-std=c++11")
            message(STATUS "CMAKE VERSION: ${CMAKE_VERSION}")

            set(CONAN_EXPORTED ON)
            include(conan.cmake)
            conan_cmake_run(CONANFILE conanfile.py
                            BASIC_SETUP CMAKE_TARGETS
                            BUILD missing)

            add_executable(main main.cpp)
            target_link_libraries(main CONAN_PKG::fmt)
        """)
        save("CMakeLists.txt", content)
        save("conanfile.py", textwrap.dedent("""
            from conans import ConanFile, CMake

            class Pkg(ConanFile):
                name = "Test"
                version = "0.1"
                requires = "fmt/6.1.2"
                generators = "cmake"
                exports = ["CMakeLists.txt", "conan.cmake", "main.cpp"]
                settings = "os", "arch", "compiler", "build_type"

                def build(self):
                    cmake = CMake(self)
                    self.run('cmake . ' + cmake.command_line)
                    self.run('cmake --build . ' + cmake.build_config)
        """))
        run("conan export . test/testing")

        os.makedirs("build")
        os.chdir("build")
        save("conanfile.txt", """[requires]
        Test/0.1@test/testing""")
        run("conan install . --build Test --build=missing")
        run("conan remove -f Test/0.1@test/testing")

    @attr("cmake39")
    def test_vs_toolset_host_x64(self):
        if platform.system() != "Windows":
            return
        content = textwrap.dedent("""
            message(STATUS "COMPILING-------")
            cmake_minimum_required(VERSION 2.8)
            project(FormatOutput CXX)
            message(STATUS "CMAKE VERSION: ${CMAKE_VERSION}")

            include(conan.cmake)
            conan_cmake_run(REQUIRES fmt/6.1.2
                            BASIC_SETUP
                            BUILD missing)

            add_executable(main main.cpp)
            target_link_libraries(main ${CONAN_LIBS})
        """)
        save("CMakeLists.txt", content)

        os.makedirs("build")
        os.chdir("build")
        # Only works cmake>=3.9
        run("cmake .. %s -T v140,host=x64 -DCMAKE_BUILD_TYPE=Release" % (generator))
        run("cmake --build . --config Release")
        cmd = os.sep.join([".", "bin", "main"])
        run(cmd)

    def test_arch(self):
        content = textwrap.dedent("""
            #set(CMAKE_CXX_COMPILER_WORKS 1)
            #set(CMAKE_CXX_ABI_COMPILED 1)
            message(STATUS "COMPILING-------")
            cmake_minimum_required(VERSION 2.8)
            project(FormatOutput CXX)
            message(STATUS "CMAKE VERSION: ${CMAKE_VERSION}")

            include(conan.cmake)
            conan_cmake_run(BASIC_SETUP
                            BUILD missing
                            ARCH armv7)

            if(NOT ${CONAN_SETTINGS_ARCH} STREQUAL "armv7")
                message(FATAL_ERROR "ARCHITECTURE IS NOT armv7")
            endif()
        """)
        save("CMakeLists.txt", content)

        os.makedirs("build")
        os.chdir("build")
        run("cmake .. %s -DCMAKE_BUILD_TYPE=Release" % (generator))


    def test_no_output_dir(self):
        content = textwrap.dedent("""
            set(CMAKE_CXX_COMPILER_WORKS 1)
            set(CMAKE_CXX_ABI_COMPILED 1)
            message(STATUS "COMPILING-------")
            cmake_minimum_required(VERSION 2.8)
            project(FormatOutput CXX)
            message(STATUS "CMAKE VERSION: ${CMAKE_VERSION}")

            include(conan.cmake)
            conan_cmake_run(BASIC_SETUP
                            NO_OUTPUT_DIRS
                            BUILD missing)


            if(CMAKE_RUNTIME_OUTPUT_DIRECTORY)
                message(FATAL_ERROR "OUTPUT_DIRS ${CMAKE_RUNTIME_OUTPUT_DIRECTORY}")
            endif()
        """)
        save("CMakeLists.txt", content)

        os.makedirs("build")
        os.chdir("build")
        run("cmake .. %s -DCMAKE_BUILD_TYPE=Release" % (generator))

    def test_build_type(self):
        content = textwrap.dedent("""
            set(CMAKE_CXX_COMPILER_WORKS 1)
            set(CMAKE_CXX_ABI_COMPILED 1)
            message(STATUS "COMPILING-------")
            cmake_minimum_required(VERSION 2.8)
            project(FormatOutput CXX)
            message(STATUS "CMAKE VERSION: ${CMAKE_VERSION}")

            include(conan.cmake)
            conan_cmake_run(BASIC_SETUP
                            BUILD_TYPE None)

            if(NOT ${CONAN_SETTINGS_BUILD_TYPE} STREQUAL "None")
                message(FATAL_ERROR "CMAKE BUILD TYPE is not None!")
            endif()
        """)
        save("CMakeLists.txt", content)

        os.makedirs("build")
        os.chdir("build")
        run("cmake .. %s  -DCMAKE_BUILD_TYPE=Release" % (generator))

    def test_settings(self):
        content = textwrap.dedent("""
            set(CMAKE_CXX_COMPILER_WORKS 1)
            set(CMAKE_CXX_ABI_COMPILED 1)
            message(STATUS "COMPILING-------")
            cmake_minimum_required(VERSION 2.8)
            project(FormatOutput CXX)
            message(STATUS "CMAKE VERSION: ${CMAKE_VERSION}")

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
        """)
        save("CMakeLists.txt", content)

        os.makedirs("build")
        os.chdir("build")
        run("cmake .. %s  -DCMAKE_BUILD_TYPE=Release" % (generator))

    # https://github.com/conan-io/cmake-conan/issues/255
    # Manual settings were added in the end to automatic CMake settings, so they were not
    # taken into account because only the first one was considered by CMake
    # This tests that the settings list does only contain the manual specified setting once.
    def test_settings_removed_from_autodetect(self):
        if platform.system() == "Windows":
            settings_check = "compiler.runtime"
            custom_setting = "{}=MTd".format(settings_check)
        else:
            settings_check = "compiler.libcxx"
            custom_setting = "{}=libstdc++".format(settings_check)

        content = textwrap.dedent("""
            cmake_minimum_required(VERSION 2.8)
            project(FormatOutput CXX)
            include(conan.cmake)
            conan_cmake_run(BASIC_SETUP
                            SETTINGS {})
            STRING(REGEX MATCHALL "{}" matches "${{settings}}")
            list(LENGTH matches n_matches)
            if(NOT n_matches EQUAL 1)
                message(FATAL_ERROR "CONAN_SETTINGS DUPLICATED!")
            endif()            
        """.format(custom_setting, settings_check))
        save("CMakeLists.txt", content)

        os.makedirs("build")
        os.chdir("build")
        run("cmake .. %s  -DCMAKE_BUILD_TYPE=Release" % (generator))

    def test_profile_auto(self):
        content = textwrap.dedent("""
            cmake_minimum_required(VERSION 2.8)
            project(FormatOutput CXX)
            message(STATUS "CMAKE VERSION: ${CMAKE_VERSION}")

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
        """)
        save("build/myprofile", textwrap.dedent("""
            [settings]
            build_type=RelWithDebInfo
            compiler=sun-cc
            compiler.version=5.10
        """))
        save("CMakeLists.txt", content)

        os.chdir("build")
        run("cmake .. %s  -DCMAKE_BUILD_TYPE=Release" % (generator))
        run("cmake .. %s  -DCMAKE_BUILD_TYPE=Debug" % (generator))

        save("build/myprofile", textwrap.dedent("""
            [settings]
            build_type=RelWithDebInfo
            compiler=Visual Studio
            compiler.version=12
            compiler.runtime=MTd
        """))
        save("CMakeLists.txt", content)

        os.chdir("build")
        run("cmake .. %s  -DCMAKE_BUILD_TYPE=Release" % (generator))
        run("cmake .. %s  -DCMAKE_BUILD_TYPE=Debug" % (generator))

    def test_profile_auto_all(self):
        content = textwrap.dedent("""
            cmake_minimum_required(VERSION 2.8)
            project(FormatOutput CXX)
            message(STATUS "CMAKE VERSION: ${CMAKE_VERSION}")

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
        """)

        save("build/myprofile", textwrap.dedent("""
            [settings]
            build_type=RelWithDebInfo
            compiler=sun-cc
            compiler.version=5.10
        """))

        save("CMakeLists.txt", content)

        os.chdir("build")
        run("cmake .. %s  -DCMAKE_BUILD_TYPE=Release" % (generator))
        run("cmake .. %s  -DCMAKE_BUILD_TYPE=Debug" % (generator))

        save("build/myprofile", textwrap.dedent("""
            [settings]
            build_type=RelWithDebInfo
            compiler=Visual Studio
            compiler.version=12
            compiler.runtime=MT
        """))
        save("CMakeLists.txt", content)

        os.chdir("build")
        run("cmake .. %s  -DCMAKE_BUILD_TYPE=Release" % (generator))
        run("cmake .. %s  -DCMAKE_BUILD_TYPE=Debug" % (generator))

    def test_multi_profile(self):
        content = textwrap.dedent("""
            cmake_minimum_required(VERSION 2.8)
            project(FormatOutput CXX)
            message(STATUS "CMAKE VERSION: ${CMAKE_VERSION}")

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
        """)
        save("build/myprofile", textwrap.dedent("""
            [settings]
            compiler=Visual Studio
            compiler.version=15
            compiler.runtime=MTd
        """))
        save("build/myprofile2", textwrap.dedent("""
            [settings]
            compiler.version=12
        """))
        save("CMakeLists.txt", content)

        os.chdir("build")
        run("cmake .. %s  -DCMAKE_BUILD_TYPE=Release" % (generator))
        run("cmake .. %s  -DCMAKE_BUILD_TYPE=Debug" % (generator))

    def test_conan_config_install(self):
        remote_name = "test-remote"
        remote_url = "https://test.test.test"
        verify_ssl = False

        content = textwrap.dedent("""
            cmake_minimum_required(VERSION 2.8)
            project(FormatOutput CXX)
            message(STATUS "CMAKE VERSION: ${CMAKE_VERSION}")

            set(CONAN_DISABLE_CHECK_COMPILER ON)
            include(conan.cmake)
            conan_config_install(ITEM \"${PROJECT_SOURCE_DIR}/config/\" VERIFY_SSL false)
        """)

        save("config/remotes.txt", "%s %s %r" % (remote_name, remote_url, verify_ssl))
        save("CMakeLists.txt", content)
        os.makedirs("build")
        os.chdir("build")
        run("cmake .. %s" % generator)

        with open("%s/.conan/remotes.json" % os.environ["CONAN_USER_HOME"]) as json_file:
            data = json.load(json_file)
            assert len(data["remotes"]) == 1, "Invalid number of remotes"
            remote = data["remotes"][0]
            assert remote["name"] == remote_name, "Invalid remote name"
            assert remote["url"] == remote_url, "Invalid remote url"
            assert remote["verify_ssl"] == verify_ssl, "Invalid verify_ssl"

class LocalTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        CONAN_TEST_FOLDER = os.getenv('CONAN_TEST_FOLDER', None)
        folder = tempfile.mkdtemp(suffix="conan", dir=CONAN_TEST_FOLDER)
        cls.old_env = dict(os.environ)
        cls.old_folder = os.getcwd()
        os.environ.update({"CONAN_USER_HOME": folder})
        os.chdir(folder)
        run("conan new hello/1.0 -s")
        run("conan create .")
        run("conan create . -s build_type=Debug")
        if platform.system() == "Windows":
            cls.generator = '-G "Visual Studio 15 Win64"'
        else:
            cls.generator = '-G "Unix Makefiles"'

    def setUp(self):
        CONAN_TEST_FOLDER = os.getenv('CONAN_TEST_FOLDER', None)
        folder = tempfile.mkdtemp(suffix="conan", dir=CONAN_TEST_FOLDER)
        shutil.copy2(os.path.join(self.old_folder, "conan.cmake"),
                     os.path.join(folder, "conan.cmake"))
        os.chdir(folder)
        content = textwrap.dedent("""
            #include "hello.h"

            int main(){
                hello();
            }
        """)
        save("main.cpp", content)

    @classmethod
    def tearDownClass(cls):
        os.chdir(cls.old_folder)
        os.environ.clear()
        os.environ.update(cls.old_env)

    def _build_multi(self, build_types):
        os.makedirs("build")
        os.chdir("build")
        run("cmake .. %s" % self.generator)
        for build_type in build_types:
            run("cmake --build . --config %s" % build_type)
            cmd = os.sep.join([".", build_type, "main"])
            run(cmd)

    def test_global(self):
        content = textwrap.dedent("""
            set(CMAKE_CXX_COMPILER_WORKS 1)
            set(CMAKE_CXX_ABI_COMPILED 1)
            cmake_minimum_required(VERSION 2.8)
            project(HelloProject CXX)
            message(STATUS "CMAKE VERSION: ${CMAKE_VERSION}")

            include(conan.cmake)
            conan_cmake_run(REQUIRES hello/1.0
                            BASIC_SETUP
                            BUILD missing)

            add_executable(main main.cpp)
            target_link_libraries(main ${CONAN_LIBS})
            """)
        save("CMakeLists.txt", content)

        os.makedirs("build")
        os.chdir("build")
        run("cmake .. %s -DCMAKE_BUILD_TYPE=Release" % self.generator)
        run("cmake --build . --config Release")
        cmd = os.sep.join([".", "bin", "main"])
        run(cmd)

    def test_targets(self):
        content = textwrap.dedent("""
            set(CMAKE_CXX_COMPILER_WORKS 1)
            set(CMAKE_CXX_ABI_COMPILED 1)
            cmake_minimum_required(VERSION 2.8)
            project(HelloProject CXX)
            message(STATUS "CMAKE VERSION: ${CMAKE_VERSION}")

            include(conan.cmake)
            conan_cmake_run(REQUIRES hello/1.0
                            BASIC_SETUP CMAKE_TARGETS
                            BUILD missing)

            add_executable(main main.cpp)
            target_link_libraries(main CONAN_PKG::hello)
            """)
        save("CMakeLists.txt", content)

        os.makedirs("build")
        os.chdir("build")
        run("cmake .. %s -DCMAKE_BUILD_TYPE=Release" % self.generator)
        run("cmake --build . --config Release")
        cmd = os.sep.join([".", "bin", "main"])
        run(cmd)

    def test_existing_conanfile(self):
        content = textwrap.dedent("""
            set(CMAKE_CXX_COMPILER_WORKS 1)
            set(CMAKE_CXX_ABI_COMPILED 1)
            cmake_minimum_required(VERSION 2.8)
            project(ProjectHello CXX)
            message(STATUS "CMAKE VERSION: ${CMAKE_VERSION}")

            include(conan.cmake)
            conan_cmake_run(CONANFILE conanfile.txt
                            BASIC_SETUP CMAKE_TARGETS
                            BUILD missing)

            add_executable(main main.cpp)
            target_link_libraries(main CONAN_PKG::hello)
            """)
        save("CMakeLists.txt", content)
        save("conanfile.txt", "[requires]\nhello/1.0\n"
                            "[generators]\ncmake")

        os.makedirs("build")
        os.chdir("build")
        run("cmake .. %s -DCMAKE_BUILD_TYPE=Release" % self.generator)
        run("cmake --build . --config Release")
        cmd = os.sep.join([".", "bin", "main"])
        run(cmd)

    def test_absolute_path_conanfile(self):
        content = textwrap.dedent("""
            set(CMAKE_CXX_COMPILER_WORKS 1)
            set(CMAKE_CXX_ABI_COMPILED 1)
            cmake_minimum_required(VERSION 2.8)
            project(ProjectHello CXX)
            message(STATUS "CMAKE VERSION: ${CMAKE_VERSION}")

            include(conan.cmake)
            conan_cmake_run(CONANFILE ${CMAKE_BINARY_DIR}/conanfile.txt
                            BASIC_SETUP CMAKE_TARGETS
                            BUILD missing)

            add_executable(main main.cpp)
            target_link_libraries(main CONAN_PKG::hello)
            """)
        save("CMakeLists.txt", content)

        os.makedirs("build")
        save("build/conanfile.txt", "[requires]\nhello/1.0\n"
                            "[generators]\ncmake")

        os.chdir("build")
        run("cmake .. %s -DCMAKE_BUILD_TYPE=Release" % self.generator)
        run("cmake --build . --config Release")
        cmd = os.sep.join([".", "bin", "main"])
        run(cmd)

    def test_version_in_cmake(self):
        with open("conan.cmake", "r") as handle:
            if "# version: " not in handle.read():
                raise Exception("Version missing in conan.cmake")

    @unittest.skipIf(platform.system() != "Windows", "toolsets only in Windows")
    def test_vs_toolset(self):
        content = textwrap.dedent("""
            message(STATUS "COMPILING-------")
            cmake_minimum_required(VERSION 2.8)
            project(HelloProject CXX)
            message(STATUS "CMAKE VERSION: ${CMAKE_VERSION}")

            include(conan.cmake)
            conan_cmake_run(REQUIRES hello/1.0
                            BASIC_SETUP
                            BUILD missing)

            add_executable(main main.cpp)
            target_link_libraries(main ${CONAN_LIBS})
            """)
        save("CMakeLists.txt", content)

        os.makedirs("build")
        os.chdir("build")
        run("cmake .. %s -T v140 -DCMAKE_BUILD_TYPE=Release" % (self.generator))
        run("cmake --build . --config Release")
        cmd = os.sep.join([".", "bin", "main"])
        run(cmd)

    @unittest.skipIf(platform.system() != "Windows", "Multi-config only in Windows")
    def test_multi(self):
        content = textwrap.dedent("""
            set(CMAKE_CXX_COMPILER_WORKS 1)
            set(CMAKE_CXX_ABI_COMPILED 1)
            cmake_minimum_required(VERSION 2.8)
            project(HelloProject CXX)
            message(STATUS "CMAKE VERSION: ${CMAKE_VERSION}")

            include(conan.cmake)
            conan_cmake_run(REQUIRES hello/1.0
                            BASIC_SETUP
                            BUILD missing)

            add_executable(main main.cpp)
            foreach(_LIB ${CONAN_LIBS_RELEASE})
                target_link_libraries(main optimized ${_LIB})
            endforeach()
            foreach(_LIB ${CONAN_LIBS_DEBUG})
                target_link_libraries(main debug ${_LIB})
            endforeach()
            """)
        save("CMakeLists.txt", content)
        self._build_multi(["Release", "Debug"])

    @unittest.skipIf(platform.system() != "Windows", "Multi-config only in Windows")
    def test_multi_configuration_types(self):
        content = textwrap.dedent("""
            set(CMAKE_CXX_COMPILER_WORKS 1)
            set(CMAKE_CXX_ABI_COMPILED 1)
            cmake_minimum_required(VERSION 2.8)
            project(HelloProject CXX)
            message(STATUS "CMAKE VERSION: ${CMAKE_VERSION}")

            include(conan.cmake)
            conan_cmake_run(REQUIRES hello/1.0
                            BASIC_SETUP
                            CONFIGURATION_TYPES "Release;Debug;RelWithDebInfo"
                            BUILD missing)

            add_executable(main main.cpp)
            foreach(_LIB ${CONAN_LIBS_RELEASE})
                target_link_libraries(main optimized ${_LIB})
            endforeach()
            foreach(_LIB ${CONAN_LIBS_DEBUG})
                target_link_libraries(main debug ${_LIB})
            endforeach()
            """)
        save("CMakeLists.txt", content)
        self._build_multi(["Release", "Debug", "RelWithDebInfo"])

    @unittest.skipIf(platform.system() != "Windows", "Multi-config only in Windows")
    def test_multi_targets(self):
        content = textwrap.dedent("""
            set(CMAKE_CXX_COMPILER_WORKS 1)
            set(CMAKE_CXX_ABI_COMPILED 1)
            cmake_minimum_required(VERSION 2.8)
            project(ProjectHello CXX)
            message(STATUS "CMAKE VERSION: ${CMAKE_VERSION}")

            include(conan.cmake)
            conan_cmake_run(REQUIRES hello/1.0
                            BASIC_SETUP CMAKE_TARGETS
                            BUILD missing)

            add_executable(main main.cpp)
            target_link_libraries(main CONAN_PKG::hello)
            """)
        save("CMakeLists.txt", content)
        self._build_multi(["Release", "Debug"])

    @unittest.skipIf(platform.system() != "Windows", "Multi-config only in Windows")
    def test_multi_targets_configuration_types(self):
        content = textwrap.dedent("""
            set(CMAKE_CXX_COMPILER_WORKS 1)
            set(CMAKE_CXX_ABI_COMPILED 1)
            cmake_minimum_required(VERSION 2.8)
            project(HelloProject CXX)
            message(STATUS "CMAKE VERSION: ${CMAKE_VERSION}")

            include(conan.cmake)
            conan_cmake_run(REQUIRES hello/1.0
                            BASIC_SETUP CMAKE_TARGETS
                            CONFIGURATION_TYPES "Release;Debug;RelWithDebInfo"
                            BUILD missing)

            add_executable(main main.cpp)
            target_link_libraries(main CONAN_PKG::hello)
            """)
        save("CMakeLists.txt", content)
        self._build_multi(["Release", "Debug", "RelWithDebInfo"])
