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


class CMakeConanTest(unittest.TestCase):

    def setUp(self):
      self.old_folder = os.getcwd()
      folder = tempfile.mkdtemp(suffix='conans')
      shutil.copy2("conan.cmake", os.path.join(folder, "conan.cmake"))
      shutil.copy2("main.cpp", os.path.join(folder, "main.cpp"))
      os.chdir(folder)

    def tearDown(self):
      os.chdir(self.old_folder)

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
      run("cmake .. -DCMAKE_BUILD_TYPE=Release")
      run("cmake --build . --config Release")
      run("bin\main")

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
      run("cmake .. -DCMAKE_BUILD_TYPE=Release")
      run("cmake --build . --config Release")
      run("bin\main")
