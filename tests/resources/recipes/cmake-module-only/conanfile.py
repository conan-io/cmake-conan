from conan import ConanFile
from conan.tools.cmake import CMakeToolchain, CMake, cmake_layout, CMakeDeps


class cmake_module_onlyRecipe(ConanFile):
    name = "cmake-module-only"
    version = "0.1"
    package_type = "library"

    # Optional metadata
    license = "<Put the package license here>"
    author = "<Put your name here> <And your email here>"
    url = "<Package recipe repository url here, for issues about the package>"
    description = "<Description of cmake-module-only package here>"
    topics = ("<Put some tag here>", "<here>", "<and here>")

    # Binary configuration
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False], "with_builddir": [True, False]}
    default_options = {"shared": False, "fPIC": True, "with_builddir": False}

    # Sources are located in the same place as this recipe, copy them to the recipe
    exports_sources = "CMakeLists.txt", "src/*", "include/*"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = []
        
        if self.options.with_builddir:
            self.cpp_info.builddirs.append("orion-module-subfolder")

        # Set this to be MODULE only, to force the case in a test where this is detected by module name
        self.cpp_info.set_property("cmake_file_name", "Orion")
        self.cpp_info.set_property("cmake_target_name", "Orion::orion")
        self.cpp_info.set_property("cmake_find_mode", "module")
