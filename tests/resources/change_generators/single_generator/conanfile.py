from conan import ConanFile
from conan.tools.cmake import CMakeDeps

class testRecipe(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("hello/0.1")
        self.requires("bye/0.1")

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
