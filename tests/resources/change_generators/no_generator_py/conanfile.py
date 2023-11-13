from conan import ConanFile

class testRecipe(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("hello/0.1")
        self.requires("bye/0.1")