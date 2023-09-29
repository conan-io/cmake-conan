import re
import unittest
import tempfile
import os
import platform
import shutil
import json
import textwrap
from contextlib import contextmanager 
from conan import conan_version


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
    generator = '-G "Visual Studio 16 2019"'
else:
    generator = '-G "Unix Makefiles"'
# TODO: Test Xcode

@contextmanager
def ch_build_dir():
    os.makedirs("build")
    os.chdir("build")
    try:
        yield
    finally:
        os.chdir("../")
        shutil.rmtree("build")

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

    # https://github.com/conan-io/cmake-conan/pull/420
    def test_conan_cmake_autodetect_os(self):
        content = textwrap.dedent("""
            cmake_minimum_required(VERSION 3.9)
            project(FormatOutput CXX)
            list(APPEND CMAKE_MODULE_PATH ${CMAKE_BINARY_DIR})
            list(APPEND CMAKE_PREFIX_PATH ${CMAKE_BINARY_DIR})
            include(conan.cmake)
            conan_cmake_configure(REQUIRES fmt/6.1.2 GENERATORS cmake_find_package)
            conan_cmake_autodetect(settings)
            conan_cmake_install(PATH_OR_REFERENCE .
                                BUILD missing
                                REMOTE conancenter
                                SETTINGS ${settings})
        """)
        save("CMakeLists.txt", content)
        empty_profile = textwrap.dedent("""
            [settings]
            build_type=Release
            arch=x86_64
        """)
        save(os.path.join(os.environ.get("CONAN_USER_HOME"), ".conan", "profiles", "default"), empty_profile)
        os.makedirs("build")
        os.chdir("build")
        run("cmake .. {} -DCMAKE_BUILD_TYPE=Release > output.txt".format(generator))
        with open('output.txt', 'r') as file:
            data = file.read()
            the_os = {'Darwin': 'Macos'}.get(platform.system(), platform.system())
            assert f"os={the_os}" in data

    # https://github.com/conan-io/cmake-conan/issues/279
    def test_options_override_profile(self):
        content = textwrap.dedent("""
            cmake_minimum_required(VERSION 3.9)
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
            assert "-o=fmt:shared=True" in data
            assert "[options]\nfmt:shared=True" in data

    # https://github.com/conan-io/cmake-conan/issues/159
    @unittest.skipIf(platform.system() != "Darwin", "Error message appears just in Macos")
    def test_macos_sysroot_warning(self):
        content = textwrap.dedent("""
            cmake_minimum_required(VERSION 3.9)
            project(FormatOutput CXX)
            set(CMAKE_CXX_STANDARD 11)
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
        run("cmake .. %s -DCMAKE_BUILD_TYPE=Release 2> stderr_output.txt" % generator)
        with open('stderr_output.txt', 'r') as file:
            data = file.read()
            assert "#include_next <string.h>" not in data

    def test_conan_cmake_configure(self):
        content = textwrap.dedent("""
            cmake_minimum_required(VERSION 3.9)
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
            cmake_minimum_required(VERSION 3.9)
            project(FormatOutput CXX)
            add_definitions("-std=c++11")
            include(conan.cmake)
            conan_cmake_configure(REQUIRES fmt/6.1.2)
            conan_cmake_autodetect(settings)
            conan_cmake_install(PATH_OR_REFERENCE .
                                GENERATOR cmake
                                BUILD missing
                                REMOTE conancenter
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

    def test_conan_cmake_install_conf_args(self):
        content = textwrap.dedent("""
            cmake_minimum_required(VERSION 3.9)
            project(FormatOutput CXX)
            include(conan.cmake)
            conan_cmake_configure(REQUIRES "")
            conan_cmake_autodetect(settings)
            conan_cmake_install(PATH_OR_REFERENCE .
                                GENERATOR cmake
                                REMOTE conancenter
                                CONF user.configuration:myconfig=somevalue
                                SETTINGS ${settings})
        """)
        save("CMakeLists.txt", content)
        os.makedirs("build")
        os.chdir("build")
        run("cmake .. {} -DCMAKE_BUILD_TYPE=Release > output.txt".format(generator))
        with open('output.txt', 'r') as file:
            data = file.read()
            assert "--conf user.configuration:myconfig=somevalue" in data
            # check that the compiler version is set just with the major version
            assert re.search(r"--settings compiler.version=[\d]*[\s]", data) 


    def test_conan_cmake_install_outputfolder(self):
        content = textwrap.dedent("""
            cmake_minimum_required(VERSION 3.15)
            project(MyProject)
            include(conan.cmake)
            conan_cmake_autodetect(settings)
            conan_cmake_install(PATH_OR_REFERENCE ${CMAKE_SOURCE_DIR}/conanfile.py
                                GENERATOR CMakeDeps
                                OUTPUT_FOLDER myoutputfolder
                                SETTINGS ${settings})
        """)
        save("CMakeLists.txt", content)
        save("conanfile.py", textwrap.dedent("""
            from conans import ConanFile
            class Pkg(ConanFile):
                settings = "os", "compiler", "build_type", "arch"
                def layout(self):
                    pass
        """))
        os.makedirs("build")
        os.chdir("build")
        run("cmake .. {} -DCMAKE_BUILD_TYPE=Release".format(generator))
        assert os.path.isdir("myoutputfolder")

    def test_conan_cmake_install_find_package(self):
        content = textwrap.dedent("""
            cmake_minimum_required(VERSION 3.9)
            project(FormatOutput CXX)
            list(APPEND CMAKE_MODULE_PATH ${CMAKE_BINARY_DIR})
            list(APPEND CMAKE_PREFIX_PATH ${CMAKE_BINARY_DIR})
            add_definitions("-std=c++11")
            include(conan.cmake)
            conan_cmake_configure(REQUIRES fmt/6.1.2 GENERATORS cmake_find_package)
            conan_cmake_autodetect(settings)
            conan_cmake_install(PATH_OR_REFERENCE .
                                BUILD missing
                                REMOTE conancenter
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

    def test_conan_lock_create(self):
        content = textwrap.dedent("""
            cmake_minimum_required(VERSION 3.5)
            project(FormatOutput CXX)
            list(APPEND CMAKE_MODULE_PATH ${CMAKE_BINARY_DIR})
            list(APPEND CMAKE_PREFIX_PATH ${CMAKE_BINARY_DIR})

            add_definitions("-std=c++11")
            include(conan.cmake)
            conan_cmake_configure(REQUIRES fmt/6.1.2 GENERATORS cmake_find_package)
            conan_cmake_autodetect(settings)
            conan_cmake_lock_create(PATH conanfile.txt LOCKFILE_OUT mylockfile.lock SETTINGS ${settings})
            conan_cmake_install(PATH_OR_REFERENCE .
                                REMOTE conancenter
                                LOCKFILE mylockfile.lock
                                BUILD missing)
            find_package(fmt)
            add_executable(main main.cpp)
            target_link_libraries(main fmt::fmt)
        """)
        save("CMakeLists.txt", content)
        os.makedirs("build")
        os.chdir("build")
        run("cmake .. {} -DCMAKE_BUILD_TYPE=Release".format(generator))
        assert os.path.exists("mylockfile.lock")
        run("cmake --build . --config Release")

    def test_conan_cmake_autodetect_cxx_standard(self):
        content = textwrap.dedent("""
            cmake_minimum_required(VERSION 3.9)
            project(FormatOutput CXX)
            list(APPEND CMAKE_MODULE_PATH ${CMAKE_BINARY_DIR})
            list(APPEND CMAKE_PREFIX_PATH ${CMAKE_BINARY_DIR})
            set(CMAKE_CXX_STANDARD 14)
            include(conan.cmake)
            conan_cmake_configure(REQUIRES fmt/6.1.2 GENERATORS cmake_find_package)
            conan_cmake_autodetect(settings)
            conan_cmake_install(PATH_OR_REFERENCE .
                                BUILD missing
                                REMOTE conancenter
                                SETTINGS ${settings})
            find_package(fmt)
            add_executable(main main.cpp)
            target_link_libraries(main fmt::fmt)
        """)
        save("CMakeLists.txt", content)
        os.makedirs("build")
        os.chdir("build")
        run("cmake .. {} -DCMAKE_BUILD_TYPE=Release > output.txt".format(generator))
        with open('output.txt', 'r') as file:
            data = file.read()
            assert "compiler.cppstd=14" in data

    # https://github.com/conan-io/cmake-conan/issues/315
    def test_issue_315(self):
        content = textwrap.dedent("""
            cmake_minimum_required(VERSION 3.9)
            project(MyProject)
            set(CMAKE_CONFIGURATION_TYPES "Debug;Release" CACHE STRING "" FORCE)
            include(conan.cmake)
            conan_cmake_run(CONANFILE conanfile.py
                            BASIC_SETUP CMAKE_TARGETS
                            BUILD missing)
            add_subdirectory(Tests)
        """)
        save("CMakeLists.txt", content)
        save("conanfile.py", textwrap.dedent("""
            from conans import ConanFile
            class Pkg(ConanFile):
                pass
        """))

        os.makedirs("Tests")
        os.chdir("Tests")

        content = textwrap.dedent("""
            cmake_minimum_required(VERSION 3.9)
            project(Tests)

            include(../conan.cmake)
            conan_cmake_run(CONANFILE conanfile.py
                            BASIC_SETUP CMAKE_TARGETS
                            BUILD missing)
        """)
        save("CMakeLists.txt", content)
        save("conanfile.py", textwrap.dedent("""
            from conans import ConanFile
            class Pkg(ConanFile):
                pass
        """))
        os.chdir("../")
        os.makedirs("build")
        os.chdir("build")
        run("cmake .. %s -DCMAKE_BUILD_TYPE=Release" % generator)
        
    def test_conan_cmake_install_quiet(self):
        content = textwrap.dedent("""
            cmake_minimum_required(VERSION 3.9)
            project(FormatOutput CXX)
            list(APPEND CMAKE_MODULE_PATH ${CMAKE_BINARY_DIR})
            list(APPEND CMAKE_PREFIX_PATH ${CMAKE_BINARY_DIR})
            add_definitions("-std=c++11")
            include(conan.cmake)
            conan_cmake_configure(REQUIRES fmt/6.1.2 GENERATORS cmake_find_package)
            conan_cmake_autodetect(settings)
            conan_cmake_install(PATH_OR_REFERENCE .
                                BUILD missing
                                REMOTE conancenter
                                SETTINGS ${settings}
                                OUTPUT_QUIET ERROR_QUIET)
            find_package(fmt)
            add_executable(main main.cpp)
            target_link_libraries(main fmt::fmt)
        """)
        save("CMakeLists.txt", content)
        os.makedirs("build")
        os.chdir("build")
        run("cmake .. {} -DCMAKE_BUILD_TYPE=Release > output.txt".format(generator))
        with open('output.txt', 'r') as file:
            data = file.read()
            assert not "conanfile.txt: Installing package" in data      
        
    def test_conan_cmake_error_quiet(self):
        content = textwrap.dedent("""
            cmake_minimum_required(VERSION 3.9)
            project(FormatOutput CXX)
            list(APPEND CMAKE_MODULE_PATH ${CMAKE_BINARY_DIR})
            list(APPEND CMAKE_PREFIX_PATH ${CMAKE_BINARY_DIR})
            add_definitions("-std=c++11")
            include(conan.cmake)
            conan_cmake_configure(REQUIRES fmt/6.1.2 GENERATORS cmake_find_package)
            conan_cmake_autodetect(settings)
            set (CONAN_COMMAND not_existing_conan)
            conan_cmake_install(PATH_OR_REFERENCE .
                                BUILD missing
                                REMOTE conancenter
                                SETTINGS ${settings}
                                ERROR_QUIET)
        """)
        save("CMakeLists.txt", content)
        os.makedirs("build")
        os.chdir("build")
        run("cmake .. {} -DCMAKE_BUILD_TYPE=Release".format(generator))

    def test_conan_add_remote(self):
        content = textwrap.dedent("""
            cmake_minimum_required(VERSION 3.9)
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
            cmake_minimum_required(VERSION 3.9)
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
            cmake_minimum_required(VERSION 3.9)
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
            cmake_minimum_required(VERSION 3.9)
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

    # Only works cmake>=3.9
    def test_vs_toolset_host_x64(self):
        if platform.system() != "Windows":
            return
        content = textwrap.dedent("""
            message(STATUS "COMPILING-------")
            cmake_minimum_required(VERSION 3.9)
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
        run("cmake .. %s -T v142,host=x64 -DCMAKE_BUILD_TYPE=Release" % (generator))
        run("cmake --build . --config Release")
        cmd = os.sep.join([".", "bin", "main"])
        run(cmd)

    def test_arch(self):
        content = textwrap.dedent("""
            #set(CMAKE_CXX_COMPILER_WORKS 1)
            #set(CMAKE_CXX_ABI_COMPILED 1)
            message(STATUS "COMPILING-------")
            cmake_minimum_required(VERSION 3.9)
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
            cmake_minimum_required(VERSION 3.9)
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
            cmake_minimum_required(VERSION 3.9)
            project(conan_wrapper CXX)
            message(STATUS "CMAKE VERSION: ${{CMAKE_VERSION}}")

            include(conan.cmake)
            conan_cmake_run(BASIC_SETUP
                            BUILD_TYPE {0})

            if(NOT ${{CONAN_SETTINGS_BUILD_TYPE}} STREQUAL "{0}")
                message(FATAL_ERROR "CMAKE BUILD TYPE is not {0}!")
            endif()
        """)
        save("CMakeLists.txt", content.format("Release"))
        with ch_build_dir():
            run("cmake .. %s  -DCMAKE_BUILD_TYPE=Debug > output.txt" % (generator))
            with open('output.txt', 'r') as file:
                data = file.read()
                assert "build_type=Release" in data

        # https://github.com/conan-io/cmake-conan/issues/89
        save("CMakeLists.txt", content.format("Debug"))
        with ch_build_dir():
            run("cmake .. %s > output.txt" % (generator))
            with open('output.txt', 'r') as file:
                data = file.read()
                assert "build_type=Debug" in data

    def test_settings(self):
        content = textwrap.dedent("""
            set(CMAKE_CXX_COMPILER_WORKS 1)
            set(CMAKE_CXX_ABI_COMPILED 1)
            message(STATUS "COMPILING-------")
            cmake_minimum_required(VERSION 3.9)
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
            cmake_minimum_required(VERSION 3.9)
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
            cmake_minimum_required(VERSION 3.9)
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
            cmake_minimum_required(VERSION 3.9)
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
            cmake_minimum_required(VERSION 3.9)
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
            cmake_minimum_required(VERSION 3.9)
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

    def test_conan_config_install_args(self):
        content = textwrap.dedent("""
            cmake_minimum_required(VERSION 3.9)
            project(FormatOutput CXX)
            message(STATUS "CMAKE VERSION: ${CMAKE_VERSION}")

            set(CONAN_DISABLE_CHECK_COMPILER ON)
            include(conan.cmake)
            conan_config_install(ITEM https://github.com/conan-io/cmake-conan.git
                                 TYPE git
                                 ARGS -b v0.5)
        """)
        save("CMakeLists.txt", content)
        os.makedirs("build")
        os.chdir("build")

        run("cmake .. {} -DCMAKE_BUILD_TYPE=Release > output.txt".format(generator))
        with open('output.txt', 'r') as file:
            data = file.read()
            assert "Repo cloned!" in data
            assert "Copying file" in data

    def test_conan_cmake_profile(self):
        content = textwrap.dedent("""
            cmake_minimum_required(VERSION 3.9)
            project(FormatOutput CXX)
            include(conan.cmake)
            conan_cmake_profile(
                FILEPATH      "${CMAKE_BINARY_DIR}/profile"
                INCLUDE       default
                SETTINGS      os=Windows
                              arch=x86_64
                              build_type=Debug
                              compiler=msvc
                              compiler.version=192
                              compiler.runtime=dynamic
                              compiler.runtime_type=Debug
                              compiler.cppstd=14
                OPTIONS       fmt:shared=True
                              fmt:header_only=False
                CONF          "tools.cmake.cmaketoolchain:generator=Visual Studio 16 2019"
                              "tools.cmake.cmaketoolchain:toolset_arch=x64"
                              "tools.cmake.build:jobs=10"
                ENV           "MyPath1=(path)/some/path11"
                              "MyPath1=+(path)/other/path12"
                BUILDENV      "MyPath2=(path)/some/path21"
                              "MyPath2=+(path)/other/path22"
                RUNENV        "MyPath3=(path)/some/path31"
                              "MyPath3=+(path)/other/path32"
                TOOL_REQUIRES cmake/3.16.3
            )
        """)
        result_conanfile = textwrap.dedent("""
            include(default)
            [settings]
            os=Windows
            arch=x86_64
            build_type=Debug
            compiler=msvc
            compiler.version=192
            compiler.runtime=dynamic
            compiler.runtime_type=Debug
            compiler.cppstd=14
            [options]
            fmt:shared=True
            fmt:header_only=False
            [conf]
            tools.cmake.cmaketoolchain:generator=Visual Studio 16 2019
            tools.cmake.cmaketoolchain:toolset_arch=x64
            tools.cmake.build:jobs=10
            [env]
            MyPath1=(path)/some/path11
            MyPath1=+(path)/other/path12
            [buildenv]
            MyPath2=(path)/some/path21
            MyPath2=+(path)/other/path22
            [runenv]
            MyPath3=(path)/some/path31
            MyPath3=+(path)/other/path32
            [tool_requires]
            cmake/3.16.3
        """)
        save("CMakeLists.txt", content)
        os.makedirs("build")
        os.chdir("build")
        run("cmake .. {} -DCMAKE_BUILD_TYPE=Release".format(generator))
        with open('profile', 'r') as file:
            data = file.read()
            assert data in result_conanfile

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
            cls.generator = '-G "Visual Studio 16 2019" -A x64'
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
            cmake_minimum_required(VERSION 3.9)
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
            cmake_minimum_required(VERSION 3.9)
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
            cmake_minimum_required(VERSION 3.9)
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
            cmake_minimum_required(VERSION 3.9)
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

    def test_conan_version(self):
        content = textwrap.dedent("""
            cmake_minimum_required(VERSION 3.9)
            project(someproject CXX)
            include(conan.cmake)
            conan_version(CONAN_VERSION)
            message(STATUS "Conan Version is: ${CONAN_VERSION}")
            """)
        save("CMakeLists.txt", content)

        os.makedirs("build")
        os.chdir("build")
        run("cmake .. %s -DCMAKE_BUILD_TYPE=Release > output.txt" % self.generator)
        with open('output.txt', 'r') as file:
            data = file.read()
            assert f"Conan Version is: {str(conan_version.major)}.{str(conan_version.minor)}.{str(conan_version.patch)}" in data

    @unittest.skipIf(platform.system() != "Windows", "toolsets only in Windows")
    def test_vs_toolset(self):
        content = textwrap.dedent("""
            message(STATUS "COMPILING-------")
            cmake_minimum_required(VERSION 3.9)
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
        run("cmake .. %s -T v142 -DCMAKE_BUILD_TYPE=Release" % (self.generator))
        run("cmake --build . --config Release")
        cmd = os.sep.join([".", "bin", "main"])
        run(cmd)

    @unittest.skipIf(platform.system() != "Windows", "Multi-config only in Windows")
    def test_multi_new_flow(self):
        content = textwrap.dedent("""
            cmake_minimum_required(VERSION 3.9)
            project(HelloProject CXX)
            list(APPEND CMAKE_MODULE_PATH ${CMAKE_BINARY_DIR})
            list(APPEND CMAKE_PREFIX_PATH ${CMAKE_BINARY_DIR})
            add_definitions("-std=c++11")
            include(conan.cmake)
            conan_cmake_configure(REQUIRES hello/1.0 GENERATORS cmake_find_package_multi)
            foreach(TYPE ${CMAKE_CONFIGURATION_TYPES})
                conan_cmake_autodetect(settings BUILD_TYPE ${TYPE})
                conan_cmake_install(PATH_OR_REFERENCE .
                                    BUILD missing
                                    REMOTE conancenter
                                    SETTINGS ${settings})
            endforeach()
            find_package(hello CONFIG)
            add_executable(main main.cpp)
            target_link_libraries(main hello::hello)
            """)
        save("CMakeLists.txt", content)
        self._build_multi(["Release", "Debug", "MinSizeRel", "RelWithDebInfo"])

    @unittest.skipIf(platform.system() != "Windows", "Multi-config only in Windows")
    def test_multi(self):
        content = textwrap.dedent("""
            set(CMAKE_CXX_COMPILER_WORKS 1)
            set(CMAKE_CXX_ABI_COMPILED 1)
            cmake_minimum_required(VERSION 3.9)
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
            cmake_minimum_required(VERSION 3.9)
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
            cmake_minimum_required(VERSION 3.9)
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
            cmake_minimum_required(VERSION 3.9)
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
