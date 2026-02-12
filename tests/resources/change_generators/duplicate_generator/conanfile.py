from conan import ConanFile
from conan.tools.cmake import CMakeConfigDeps

class testRecipe(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeConfigDeps"

    def requirements(self):
        self.requires("hello/0.1")
        self.requires("bye/0.1")

    def generate(self):
        deps = CMakeConfigDeps(self)
        deps.generate()

