import unittest
import tempfile
import os
import shutil


def save(filename, content):
  try:
   os.makedirs(os.path.dirname(filename))
  except:
    pass

  with open(filename, "wb") as handle:
    handle.write(content)


def run(cmd):
  retcode = os.system(cmd)
  if retcode != 0:
    raise Exception("Command failed: %s" % cmd)

generator = '-G "Visual Studio 14"'

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

    def test_global(self):
      content = """cmake_minimum_required(VERSION 2.8)
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

    def test_multi(self):
      content = """cmake_minimum_required(VERSION 2.8)
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
      
      os.makedirs("build")
      os.chdir("build")
      run("cmake .. %s" % generator)
      run("cmake --build . --config Release")
      cmd = os.sep.join([".", "Release", "main"])
      run(cmd)
      run("cmake --build . --config Debug")
      cmd = os.sep.join([".", "Debug", "main"])
      run(cmd)

    def test_multi_targets(self):
      content = """cmake_minimum_required(VERSION 2.8)
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
      run("cmake .. %s" % generator)
      run("cmake --build . --config Release")
      cmd = os.sep.join([".", "Release", "main"])
      run(cmd)
      run("cmake --build . --config Debug")
      cmd = os.sep.join([".", "Debug", "main"])
      run(cmd)

    def test_targets(self):
      content = """cmake_minimum_required(VERSION 2.8)
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
      run("bin\main")

    def test_existing_conanfile(self):
      content = """cmake_minimum_required(VERSION 2.8)
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
      run("bin\main")

    def test_existing_conanfile_py(self):
      content = """cmake_minimum_required(VERSION 2.8)
project(conan_wrapper CXX)

include(conan.cmake)
conan_cmake_run(CONANFILE conan/conanfile.py
                BASIC_SETUP CMAKE_TARGETS
                BUILD missing)

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
""")

      os.makedirs("build")
      os.chdir("build")
      run("cmake .. %s -DCMAKE_BUILD_TYPE=Release" % generator)
      run("cmake --build . --config Release")
      run("bin\main")

    def test_exported_package(self):
      content = """cmake_minimum_required(VERSION 2.8)
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
      save("conanfile.py", """
from conans import ConanFile, CMake

class Pkg(ConanFile):
  name = "Test"
  version = "0.1"
  requires = "Hello/0.1@memsharded/testing"
  generators = "cmake"
  exports = ["CMakeLists.txt", "conan.cmake", "main.cpp"]
  settings = "os", "arch", "compiler", "build_type"

  def build(self):
    cmake = CMake(self.settings)
    self.run('cmake . ' + cmake.command_line)
    self.run('cmake --build . ' + cmake.build_config)
""")
      run("conan export test/testing")

      os.makedirs("build")
      os.chdir("build")
      save("conanfile.txt", """[requires]
Test/0.1@test/testing""")
      run("conan install . --build Test")
      run("conan remove -f Test/0.1@test/testing")
