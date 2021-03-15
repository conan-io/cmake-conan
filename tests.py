import unittest
import tempfile
import os
import platform
import shutil
import json
import textwrap
from contextlib import contextmanager 

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

@contextmanager
def ch_build_dir():
    os.makedirs("build")
    os.chdir("build")
    try:
        yield
    finally:
        os.chdir("../")
        shutil.rmtree("build")

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

    @unittest.skipIf(platform.system() != "Windows", "Multi-config only in Windows")
    def test_multi_new_flow(self):
        content = textwrap.dedent("""
            cmake_minimum_required(VERSION 3.5)
            project(HelloProject CXX)
            list(APPEND CMAKE_MODULE_PATH ${CMAKE_BINARY_DIR})
            list(APPEND CMAKE_PREFIX_PATH ${CMAKE_BINARY_DIR})
            add_definitions("-std=c++11")
            include(conan.cmake)
            conan_cmake_configure(REQUIRES hello/1.0 GENERATORS cmake_find_package_multi)
            foreach(CMAKE_BUILD_TYPE ${CMAKE_CONFIGURATION_TYPES})
                conan_cmake_autodetect(settings)
                conan_cmake_install(PATH_OR_REFERENCE .
                                    BUILD missing
                                    REMOTE conan-center
                                    SETTINGS ${settings})
            endforeach()
            find_package(fmt CONFIG)
            add_executable(main main.cpp)
            target_link_libraries(main fmt::fmt)
            """)
        save("CMakeLists.txt", content)
        self._build_multi(["Release", "Debug", "MinSizeRel", "RelWithDebInfo"])
