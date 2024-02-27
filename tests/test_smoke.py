import logging
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path

import pytest

expected_conan_install_outputs = [
    "first find_package() found. Installing dependencies with Conan",
    "found, 'conan install' already ran"
]

expected_app_outputs = [
    "hello/0.1: Hello World {config}!",
    "bye/0.1: Hello World {config}!"
]

expected_app_msvc_runtime = [
    "hello/0.1: MSVC runtime: {expected_runtime}",
    "bye/0.1: MSVC runtime: {expected_runtime}"
]

src_dir = Path(__file__).parent.parent
conan_provider = src_dir / "conan_provider.cmake"
resources_dir= src_dir / 'tests' / 'resources'

unix = pytest.mark.skipif(platform.system() != "Linux" and platform.system() != "Darwin", reason="Linux or Darwin only")
linux = pytest.mark.skipif(platform.system() != "Linux", reason="Linux only")
darwin = pytest.mark.skipif(platform.system() != "Darwin", reason="Darwin only")
windows = pytest.mark.skipif(platform.system() != "Windows", reason="Windows only")


def run(cmd, check=True):
    subprocess.run(cmd, shell=True, check=check)


@pytest.fixture(scope="session")
def conan_home_dir(tmp_path_factory):
    """Set up the CONAN_HOME in a temporary directory,
    common to all the tests in the file
    """
    conan_home = tmp_path_factory.mktemp("conan_home")
    old_env = dict(os.environ)
    os.environ.update({"CONAN_HOME": conan_home.as_posix()})
    logging.info(f"CONAN_HOME set to: {conan_home}")
    yield conan_home
    os.environ.clear()
    os.environ.update(old_env)


@pytest.fixture(scope="session", autouse=True)
def setup_conan_home(conan_home_dir, tmp_path_factory):
    "Set up profiles in Conan Cache, and export recipes common to tests."
    logging.info(f"Initializing Conan settings in: {conan_home_dir}")
    workdir = tmp_path_factory.mktemp("temp_recipes")
    logging.info(f"Conan home setup, temporary folder: {workdir}")
    cwd = os.getcwd()
    
    # Detect default profile
    run("conan profile detect -vquiet")
    
    # Create hello lib from built-in CMake template
    os.chdir(workdir.as_posix())
    run("conan new cmake_lib -d name=hello -d version=0.1 -vquiet")
    run("conan export . -vquiet")

    # Create hello-autootols from built-in autotools template
    recipe_dir = tmp_path_factory.mktemp(f"temp_autotools")
    os.chdir(recipe_dir.as_posix())
    run("conan new autotools_lib -d name=helloautotools -d version=0.1 -vquiet")
    run("conan export . -vquiet")

    # additional recipes to export from resources, overlay on top of `hello` and export
    additional_recipes = ['boost', 'bye', 'cmake-module-only', 'cmake-module-with-dependency']

    for recipe in additional_recipes:
        recipe_dir = tmp_path_factory.mktemp(f"temp_{recipe}")
        os.chdir(recipe_dir.as_posix())
        run(f"conan new cmake_lib -d name={recipe} -d version=0.1 -f -vquiet")
        shutil.copy2(src_dir / 'tests' / 'resources' / 'recipes' / recipe / 'conanfile.py', ".")
        run("conan export . -vquiet")

    # Additional profiles for testing
    config_dir = resources_dir / 'custom_config'
    run(f"conan config install {config_dir}")
    os.chdir(cwd)


def setup_cmake_workdir(base_tmp_dir, resource_dirs=['basic_cmake']):
    source_dir = base_tmp_dir / "src"
    binary_dir = base_tmp_dir / "build"
    source_dir.mkdir()
    binary_dir.mkdir()
    for item in resource_dirs:
        shutil.copytree(resources_dir / item, source_dir.as_posix(), dirs_exist_ok=True)
    return (source_dir, binary_dir)

@pytest.fixture
def basic_cmake_project(tmp_path, monkeypatch):
    """ Function scope fixture that creates a temporary
    directory, copy the needed resources to it, and then
    create a build directory and chdir to it
    """
    workdir = tmp_path / "test_workdir"
    workdir.mkdir()
    source_dir, binary_dir = setup_cmake_workdir(workdir)
    monkeypatch.chdir(binary_dir)
    yield (source_dir, binary_dir)


class TestBasic:
    @pytest.fixture(scope="class", autouse=True)
    def setup_basic_test_workdir(self, tmp_path_factory):
        workdir = tmp_path_factory.mktemp("test_basic")
        source_dir, binary_dir = setup_cmake_workdir(workdir)
        binary_dir_multi = workdir / "build-multi"
        binary_dir_multi.mkdir()
        TestBasic.workdir = workdir
        TestBasic.source_dir = source_dir
        TestBasic.binary_dir = binary_dir
        TestBasic.binary_dir_multi = binary_dir_multi
        cwd = os.getcwd()
        os.chdir(binary_dir.as_posix())
        yield
        os.chdir(cwd)

    @pytest.fixture
    def build_dir_multi(self, monkeypatch):
        monkeypatch.chdir(self.binary_dir_multi)

    def test_single_config(self, capfd):
        "Conan installs once during configure and applications are created"
        generator = "-GNinja" if platform.system() == "Windows" else ""

        run(f"cmake -S {self.source_dir} -B {self.binary_dir} -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_provider} -DCMAKE_BUILD_TYPE=Release {generator}")
        out, _ = capfd.readouterr()
        assert all(expected in out for expected in expected_conan_install_outputs)
        run("cmake --build .")
        out, _ = capfd.readouterr()
        assert all(expected not in out for expected in expected_conan_install_outputs)
        app_executable = "app.exe" if platform.system() == "Windows" else "app"
        run(os.path.join(os.getcwd(), app_executable))
        out, _ = capfd.readouterr()
        expected_output = [f.format(config="Release") for f in expected_app_outputs]
        assert all(expected in out for expected in expected_output)

    @pytest.mark.usefixtures("build_dir_multi")
    def test_multi_config(self, capfd):
        "Conan installs once during configure and applications are created"
        generator = "-G'Ninja Multi-Config'" if platform.system() != "Windows" else ""
        run(f"cmake -S {self.source_dir} -B {self.binary_dir_multi} -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_provider} {generator}")
        out, _ = capfd.readouterr()
        assert all(expected in out for expected in expected_conan_install_outputs)

        app_executable = "app.exe" if platform.system() == "Windows" else "app"
        for config in ["Release", "Debug"]:
            run(f"cmake --build . --config {config}")
            run(os.path.join(os.getcwd(), config, app_executable))
            out, _ = capfd.readouterr()
            expected_outputs = [f.format(config=config) for f in expected_app_outputs]
            assert all(expected not in out for expected in expected_conan_install_outputs)
            assert all(expected in out for expected in expected_outputs)

    def test_single_config_only_one_configuration_installed(self, capfd):
        "Ensure that if the generator is single config, `conan install` is only called for one configuration, "
        "even when `CMAKE_CONFIGURATION_TYPES` is set to multiple values on a single-config generator"
        generator = "-GNinja" if platform.system() == "Windows" else ""
        run(f'cmake -S {self.source_dir} -B {self.binary_dir} -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_provider} -DCMAKE_BUILD_TYPE=Release {generator} -DOVERRIDE_CONFIG_TYPES=ON')
        out, _ = capfd.readouterr()
        assert all(expected in out for expected in expected_conan_install_outputs)
        assert "Overriding config types" in out
        assert "CMake-Conan: Installing single configuration Release" in out
        run("cmake --build .")
        out, _ = capfd.readouterr()
        assert all(expected not in out for expected in expected_conan_install_outputs)

        app_executable = "app.exe" if platform.system() == "Windows" else "app"
        run(os.path.join(os.getcwd(), app_executable))
        out, _ = capfd.readouterr()
        expected_output = [f.format(config="Release") for f in expected_app_outputs]
        assert all(expected in out for expected in expected_output)

    @unix
    def test_reconfigure_on_conanfile_changes(self, capfd):
        "A conanfile change triggers conan install"
        run("cmake --build .")
        out, _ = capfd.readouterr()
        assert all(expected not in out for expected in expected_conan_install_outputs)
        p = self.source_dir / "conanfile.txt"
        p.touch()
        run("cmake --build .")
        out, _ = capfd.readouterr()
        assert all(expected in out for expected in expected_conan_install_outputs)


    @windows
    @pytest.mark.usefixtures("build_dir_multi")
    @pytest.mark.parametrize("msvc_runtime", ["MultiThreaded$<$<CONFIG:Debug>:Debug>",
                                              "MultiThreaded$<$<CONFIG:Debug>:Debug>DLL",
                                              "MultiThreaded", "MultiThreadedDebugDLL"])
    def test_msvc_runtime_multiconfig(self, capfd, msvc_runtime):
        msvc_runtime_flag = f'-DCMAKE_MSVC_RUNTIME_LIBRARY="{msvc_runtime}"' 
        run(f"cmake -S {self.source_dir} -B {self.binary_dir_multi} -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_provider} {msvc_runtime_flag}")
        out, _ = capfd.readouterr()
        assert all(expected in out for expected in expected_conan_install_outputs)

        app_executable = "app.exe" if platform.system() == "Windows" else "app"
        for config in ["Release", "Debug"]:
            run(f"cmake --build . --config {config}")
            run(os.path.join(os.getcwd(), config, app_executable))
            out, _ = capfd.readouterr()
            expected_outputs = [f.format(config=config) for f in expected_app_outputs]
            assert all(expected not in out for expected in expected_conan_install_outputs)
            assert all(expected in out for expected in expected_outputs)
            
            debug_tag = "Debug" if config == "Debug" else ""
            runtime = msvc_runtime.replace("$<$<CONFIG:Debug>:Debug>", debug_tag)
            expected_runtime_outputs = [f.format(expected_runtime=runtime) for f in expected_app_msvc_runtime]
            assert all(expected in out for expected in expected_runtime_outputs)

    @windows
    @pytest.mark.parametrize("config", ["Debug", "Release"])
    @pytest.mark.parametrize("msvc_runtime", ["MultiThreaded$<$<CONFIG:Debug>:Debug>",
                                              "MultiThreaded$<$<CONFIG:Debug>:Debug>DLL",
                                              "MultiThreaded", "MultiThreadedDebugDLL"])
    def test_msvc_runtime_singleconfig(self, capfd, config, msvc_runtime):
        msvc_runtime_flag = f'-DCMAKE_MSVC_RUNTIME_LIBRARY="{msvc_runtime}"' 
        run(f"cmake -S {self.source_dir} -B {self.binary_dir} -GNinja -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_provider} -DCMAKE_BUILD_TYPE={config} {msvc_runtime_flag} -GNinja")
        out, _ = capfd.readouterr()
        assert all(expected in out for expected in expected_conan_install_outputs)
        run("cmake --build .")
        out, _ = capfd.readouterr()
        assert all(expected not in out for expected in expected_conan_install_outputs)
        run(os.path.join(os.getcwd(), "app.exe"))
        out, _ = capfd.readouterr()
        expected_output = [f.format(config=config) for f in expected_app_outputs]
        assert all(expected in out for expected in expected_output)

        debug_tag = "Debug" if config == "Debug" else ""
        runtime = msvc_runtime.replace("$<$<CONFIG:Debug>:Debug>", debug_tag)
        expected_runtime_outputs = [f.format(expected_runtime=runtime) for f in expected_app_msvc_runtime]
        assert all(expected in out for expected in expected_runtime_outputs)
        
class TestFindModules:
    def test_find_module(self, capfd, basic_cmake_project):
        "Ensure that a call to find_package(XXX MODULE REQUIRED) is honoured by the dependency provider"
        source_dir, binary_dir = basic_cmake_project
        shutil.copytree(resources_dir / 'find_module' / 'basic_module', source_dir, dirs_exist_ok=True)

        run(f"cmake -S {source_dir} -B {binary_dir} -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_provider} -DCMAKE_BUILD_TYPE=Release", check=False)
        out, err = capfd.readouterr()
        assert "Conan: Target declared 'hello::hello'" in out
        assert "Conan: Target declared 'bye::bye'" in out
        run("cmake --build .")

    @pytest.mark.parametrize("use_find_components", [True, False])
    def test_find_builtin_module(self, capfd, use_find_components, basic_cmake_project):
        "Ensure that a Conan-provided -config.cmake file satisfies dependency, even when a CMake builtin "
        "exists for the same dependency"
        source_dir, binary_dir = basic_cmake_project
        shutil.copytree(resources_dir / 'find_module' / 'builtin_module', source_dir, dirs_exist_ok=True)
        boost_find_components = "ON" if use_find_components else "OFF"
        run(f"cmake -S {source_dir} -B {binary_dir} -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_provider} -DCMAKE_BUILD_TYPE=Release -D_TEST_BOOST_FIND_COMPONENTS={boost_find_components}", check=False)
        out, err = capfd.readouterr()
        assert "Conan: Target declared 'Boost::boost'" in out
        run("cmake --build .")

    def test_cmake_builtin_module(self, capfd, basic_cmake_project):
        "Ensure that the Find<PackageName>.cmake modules from the CMake install work"
        source_dir, binary_dir = basic_cmake_project
        shutil.copytree(resources_dir / 'find_module' / 'cmake_builtin_module', source_dir, dirs_exist_ok=True)

        run(f"cmake -S {source_dir} -B {binary_dir} -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_provider} -DCMAKE_BUILD_TYPE=Release")
        out, _ = capfd.readouterr()
        assert "Found Threads: TRUE" in out


class TestCMakeModulePath:

    def test_preserve_module_path(self, capfd, basic_cmake_project):
        "Ensure that existing CMAKE_MODULE_PATH values remain in place after find_package(XXX) call"
        source_dir, binary_dir = basic_cmake_project
        shutil.copytree(src_dir / 'tests' / 'resources' / 'cmake_module_path' / 'module_only', source_dir, dirs_exist_ok=True)
        run(f"cmake -S {source_dir} -B {binary_dir} -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_provider} -DCMAKE_BUILD_TYPE=Release", check=False)
        out, err = capfd.readouterr()
        assert "CMAKE_MODULE_PATH has expected value" in out
        assert "CMAKE_MODULE_PATH DOES NOT have expected value" not in out

    def test_module_path_from_dependency(self, capfd, basic_cmake_project):
        "Ensure that CMAKE_MODULE_PATH is prepended with value from dependency (builddir in recipe)"
        source_dir, binary_dir = basic_cmake_project
        shutil.copytree(src_dir / 'tests' / 'resources' / 'cmake_module_path' / 'library_with_cmake_module_dir', source_dir, dirs_exist_ok=True)
        run(f"cmake -S {source_dir} -B {binary_dir} -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_provider} -DCMAKE_BUILD_TYPE=Release", check=False)
        out, err = capfd.readouterr()
        assert "CMAKE_MODULE_PATH has expected value" in out
        assert "CMAKE_MODULE_PATH DOES NOT have expected value" not in out


class TestGeneratedProfile:
    @linux
    def test_propagate_cxx_compiler(self, capfd, basic_cmake_project):
        """Test that the C++ compiler is propagated via tools.build:compiler_executables"""
        source_dir, binary_dir = basic_cmake_project
        run(f"cmake -S {source_dir} -B {binary_dir} -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_provider} -DCMAKE_BUILD_TYPE=Release", check=True)
        out, err = capfd.readouterr()
        assert "The CXX compiler identification is GNU" in out
        assert "CMake-Conan: The C compiler is not defined." in err
        assert 'tools.build:compiler_executables={"cpp":"/usr/bin/c++"}' in out

    @linux
    def test_propagate_c_compiler(self, capfd, basic_cmake_project):
        """Test that the C compiler is propagated when defined, even if the project only enables C++"""
        source_dir, binary_dir = basic_cmake_project
        run(f"cmake -S {source_dir} -B {binary_dir} -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_provider} -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=/usr/bin/cc", check=True)
        out, err = capfd.readouterr()
        assert "The CXX compiler identification is GNU" in out
        assert "The C compiler is not defined." not in err
        assert 'tools.build:compiler_executables={"c":"/usr/bin/cc","cpp":"/usr/bin/c++"}' in out

    @linux
    def test_propagate_non_default_compiler(self, capfd, basic_cmake_project):
        """Test that the C++ compiler is propagated via tools.build:compiler_executables"""
        source_dir, binary_dir = basic_cmake_project
        run(f"cmake -S {source_dir} -B {binary_dir} -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_provider} -DCMAKE_C_COMPILER=/usr/bin/clang -DCMAKE_CXX_COMPILER=/usr/bin/clang++ -DCMAKE_BUILD_TYPE=Release", check=True)
        out, err = capfd.readouterr()
        assert "The CXX compiler identification is Clang" in out
        assert "The C compiler is not defined." not in err
        assert 'tools.build:compiler_executables={"c":"/usr/bin/clang","cpp":"/usr/bin/clang++"}' in out

    @darwin
    @pytest.mark.parametrize("cmake_generator", ["Unix Makefiles", "Xcode"])
    def test_propagate_compiler_mac_autotools(self, capfd, basic_cmake_project, cmake_generator):
        """Test that if the compiler is inside an XCode installation, we don't
        propagate the path if that's the compiler that would be found by default"""
        source_dir, binary_dir = basic_cmake_project
        shutil.copytree(src_dir / 'tests' / 'resources' / 'autotools_dependency', source_dir, dirs_exist_ok=True)
        run(f'cmake -S {source_dir} -B {binary_dir} -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_provider} -DCMAKE_BUILD_TYPE=Release -G"{cmake_generator}"', check=False)
        out, err = capfd.readouterr()
        assert "checking for g++... g++" in err, err
        assert "configure: error: C++ compiler cannot create executables" not in err
        assert "-- Generating done" in out

class TestProfileCustomization:
    def test_profile_defaults(self, capfd, basic_cmake_project):
        """Test the defaults passed for host and build profiles"""
        source_dir, binary_dir = basic_cmake_project
        run(f"cmake -S {source_dir} -B {binary_dir} -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_provider} -DCMAKE_BUILD_TYPE=Release", check=True)
        out, _ = capfd.readouterr()
        assert "--profile:host=default" in out
        assert re.search("--profile:host=.*/build/conan_host_profile", out)  # buildir
        assert "--profile:build=default" in out

    def test_profile_composed_list(self, capfd, basic_cmake_project):
        """Test passing a list of profiles to host and build profiles"""
        source_dir, binary_dir = basic_cmake_project
        run(f'cmake -S {source_dir} -B {binary_dir} -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_provider} -DCMAKE_BUILD_TYPE=Release -DCONAN_HOST_PROFILE="default;auto-cmake;foo" -DCONAN_BUILD_PROFILE="default;bar"', check=True)
        out, err = capfd.readouterr()
        assert "--profile:host=default" in out
        assert re.search("--profile:host=.*/build/conan_host_profile", out)  # buildir
        assert "--profile:host=foo" in out
        assert "user:custom_info=foo" in err
        assert "--profile:build=default" in out
        assert "--profile:build=bar" in out
        assert "user:custom_info=bar" in err

    def test_profile_pass_path(self, capfd, basic_cmake_project):
        """Test that we can both skip autodetected profile and override with a full profile from a path"""
        source_dir, binary_dir = basic_cmake_project
        custom_profile = resources_dir / 'custom_profiles' / 'invalid_os'
        custom_profile = custom_profile.as_posix()
        run(f'cmake -S {source_dir} -B {binary_dir} -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_provider} -DCMAKE_BUILD_TYPE=Release -DCONAN_HOST_PROFILE="{custom_profile}"', check=False)
        out, err = capfd.readouterr()
        assert f"--profile:host={custom_profile}" in out
        assert "ERROR: Invalid setting 'JuliusOS' is not a valid 'settings.os' value." in err

class TestConanInstallArgs:
    def test_conan_install_args(self, capfd, basic_cmake_project):
        """Test ability to pass CONAN_INSTALL_ARGS"""
        source_dir, binary_dir = basic_cmake_project
        conan_install_args = f'"--build=*;--lockfile-out={binary_dir}/conan.lock"'
        run(f"cmake -S {source_dir} -B {binary_dir} -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_provider} -DCMAKE_BUILD_TYPE=Release -DCONAN_INSTALL_ARGS={conan_install_args}", check=True)
        out, _ = capfd.readouterr()
        assert "--build=missing" not in out
        assert "--build=*" in out
        assert "--lockfile-out=" in out
        assert os.path.exists(os.path.join(binary_dir, "conan.lock"))

class TestSubdir:
    @pytest.fixture(scope="class", autouse=True)
    def subdir_setup(self, tmp_path_factory):
        workdir = tmp_path_factory.mktemp("test_subdir")
        source_dir, binary_dir = setup_cmake_workdir(workdir, ["basic_cmake", "subdir"])
        TestSubdir.source_dir = source_dir
        TestSubdir.binary_dir = binary_dir
        cwd = os.getcwd()
        subdir_recipe = tmp_path_factory.mktemp("subdir_recipe")
        os.chdir(subdir_recipe.as_posix())
        run("conan new cmake_lib -d name=subdir -d version=0.1 -f -vquiet")
        run("conan export . -vquiet")
        os.chdir(binary_dir.as_posix())
        yield
        os.chdir(cwd)

    def test_add_subdirectory(self, capfd):
        "The CMAKE_PREFIX_PATH is set for CMakeLists.txt included with add_subdirectory BEFORE the first find_package."
        pass
        run(f"cmake -S {self.source_dir} -B {self.binary_dir} -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_provider} -DCMAKE_BUILD_TYPE=Release")
        out, _ = capfd.readouterr()
        assert all(expected in out for expected in expected_conan_install_outputs)
        run("cmake --build . --config Release")
        if platform.system() == "Windows":
            app_executable = self.binary_dir / "subdir" / "Release" / "appSubdir.exe"
        else:
            app_executable = self.binary_dir / "subdir" / "appSubdir"
        run(app_executable.as_posix())
        out, _ = capfd.readouterr()
        assert "subdir/0.1: Hello World Release!" in out


class TestSubdir2:

    def test_add_subdirectory(self, tmp_path_factory, capfd):
        "The CMAKE_PREFIX_PATH is set for CMakeLists.txt included with add_subdirectory BEFORE the first find_package."
        workdir = tmp_path_factory.mktemp("test_subdir")
        source_dir, binary_dir = setup_cmake_workdir(workdir, ["subdir2"])

        run(f"cmake -S {source_dir} -B {binary_dir} -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_provider} -DCMAKE_BUILD_TYPE=Release")
        out, _ = capfd.readouterr()
        assert "first find_package() found. Installing dependencies with Conan" in out
        run(f"cmake --build {binary_dir} --config Release")
        if platform.system() == "Windows":
            app_executable = binary_dir / "subdir" / "Release" / "appSubdir.exe"
        else:
            app_executable = binary_dir / "subdir" / "appSubdir"
        run(app_executable.as_posix())
        out, _ = capfd.readouterr()
        assert "hello/0.1: Hello World Release!" in out


class TestLibcxx:
    @darwin
    def test_libcxx_macos(self, capfd, basic_cmake_project):
        source_dir, binary_dir = basic_cmake_project
        run(f"cmake -S {source_dir} -B {binary_dir} -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_provider} "
            "-DCMAKE_BUILD_TYPE=Release")
        out, _ = capfd.readouterr()
        assert "compiler.libcxx=libc++" in out

    @linux
    @pytest.mark.parametrize("compiler", ["g++", "clang++"])
    def test_gnu_libstdcxx_linux(self, capfd, basic_cmake_project, compiler):
        source_dir, binary_dir = basic_cmake_project
        run(f"cmake -S {source_dir} -B {binary_dir} -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_provider} "
            f"-DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER={compiler}")
        out, _ = capfd.readouterr()
        assert "Performing Test _CONAN_IS_GNU_LIBSTDCXX - Success" in out
        assert "Performing Test _CONAN_GNU_LIBSTDCXX_IS_CXX11_ABI - Success" in out
        assert "compiler.libcxx=libstdc++11" in out
        if compiler == "clang++":
            assert "The CXX compiler identification is Clang" in out
            assert "compiler=clang" in out
        elif compiler == "g++":
            assert "The CXX compiler identification is GNU" in out
            assert "compiler=gcc" in out

    @linux
    def test_gnu_libstdcxx_old_abi_linux(self, capfd, basic_cmake_project):
        """Ensure libstdc++ is set when the C++11 for libstdc++ is disabled"""
        source_dir, binary_dir = basic_cmake_project
        run(f'cmake -S {source_dir} -B {binary_dir} -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_provider} '
            '-DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS="-D_GLIBCXX_USE_CXX11_ABI=0"')
        out, _ = capfd.readouterr()
        assert "Performing Test _CONAN_IS_GNU_LIBSTDCXX - Success" in out
        assert "Performing Test _CONAN_GNU_LIBSTDCXX_IS_CXX11_ABI - Failed" in out
        assert "compiler.libcxx=libstdc++" in out

    @linux
    def test_clang_libcxx_linux(self, capfd, basic_cmake_project):
        """Ensure libc++ is set when using libc++ with Clang"""
        source_dir, binary_dir = basic_cmake_project
        run(f'cmake -S {source_dir} -B {binary_dir} -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_provider} '
            '-DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS="-stdlib=libc++" -DCMAKE_CXX_COMPILER=clang++')
        out, _ = capfd.readouterr()
        assert "The CXX compiler identification is Clang" in out
        assert "compiler=clang" in out
        assert "Performing Test _CONAN_IS_LIBCXX - Success" in out
        assert "compiler.libcxx=libc++" in out

class TestOsVersion:
    @darwin
    def test_os_version(self, capfd, basic_cmake_project):
        "Setting CMAKE_OSX_DEPLOYMENT_TARGET on macOS adds os.version to the Conan profile"
        source_dir, binary_dir = basic_cmake_project
        run(f"cmake -S {source_dir} -B {binary_dir} -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_provider} "
            "-DCMAKE_BUILD_TYPE=Release -DCMAKE_OSX_DEPLOYMENT_TARGET=10.15")
        out, _ = capfd.readouterr()
        assert "os.version=10.15" in out

    def test_no_os_version(self, capfd, basic_cmake_project):
        "If CMAKE_OSX_DEPLOYMENT_TARGET is not set, os.version is not added to the Conan profile"
        source_dir, binary_dir = basic_cmake_project
        run(f"cmake -S {source_dir} -B {binary_dir} -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_provider} "
            "-DCMAKE_BUILD_TYPE=Release")
        out, _ = capfd.readouterr()
        assert "os.version=10.15" not in out

class TestAndroid:
    def test_android_armv8(self, capfd, basic_cmake_project):
        "Building for Android armv8"
        source_dir, binary_dir = basic_cmake_project
        run(f"cmake -S {source_dir} -B {binary_dir} -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_provider} -G Ninja -DCMAKE_BUILD_TYPE=Release "
            f"-DCMAKE_TOOLCHAIN_FILE={os.environ['ANDROID_NDK_ROOT']}/build/cmake/android.toolchain.cmake "
            "-DANDROID_ABI=arm64-v8a -DANDROID_STL=c++_shared -DANDROID_PLATFORM=android-28")
        out, _ = capfd.readouterr()
        assert "arch=armv8" in out
        assert "compiler.libcxx=c++_shared" in out
        assert "os=Android" in out
        assert "os.api_level=28" in out
        assert "tools.android:ndk_path=" in out

    def test_android_armv7(self, capfd, basic_cmake_project):
        "Building for Android armv7"
        source_dir, binary_dir = basic_cmake_project
        run(f"cmake -S {source_dir} -B {binary_dir} -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_provider} -G Ninja -DCMAKE_BUILD_TYPE=Release "
            f"-DCMAKE_TOOLCHAIN_FILE={os.environ['ANDROID_NDK_ROOT']}/build/cmake/android.toolchain.cmake "
            "-DANDROID_ABI=armeabi-v7a -DANDROID_STL=c++_static -DANDROID_PLATFORM=android-N")
        out, _ = capfd.readouterr()
        assert "arch=armv7" in out
        assert "compiler.libcxx=c++_static" in out
        assert "os=Android" in out
        assert "os.api_level=24" in out
        assert "tools.android:ndk_path=" in out

    def test_android_x86_64(self, capfd, basic_cmake_project):
        source_dir, binary_dir = basic_cmake_project
        "Building for Android x86_64"
        run(f"cmake -S {source_dir} -B {binary_dir} -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_provider} -G Ninja -DCMAKE_BUILD_TYPE=Release "
            f"-DCMAKE_TOOLCHAIN_FILE={os.environ['ANDROID_NDK_ROOT']}/build/cmake/android.toolchain.cmake "
            "-DANDROID_ABI=x86_64 -DANDROID_STL=c++_static -DANDROID_PLATFORM=android-27")
        out, _ = capfd.readouterr()
        assert "arch=x86_64" in out
        assert "compiler.libcxx=c++_static" in out
        assert "os=Android" in out
        assert "os.api_level=27" in out
        assert "tools.android:ndk_path=" in out

    def test_android_x86(self, capfd, basic_cmake_project):
        source_dir, binary_dir = basic_cmake_project
        "Building for Android x86"
        run(f"cmake -S {source_dir} -B {binary_dir} -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_provider} -G Ninja -DCMAKE_BUILD_TYPE=Release "
            f"-DCMAKE_TOOLCHAIN_FILE={os.environ['ANDROID_NDK_ROOT']}/build/cmake/android.toolchain.cmake "
            "-DANDROID_ABI=x86 -DANDROID_STL=c++_shared -DANDROID_PLATFORM=22")
        out, _ = capfd.readouterr()
        assert "arch=x86" in out
        assert "compiler.libcxx=c++_shared" in out
        assert "os=Android" in out
        assert "os.api_level=22" in out
        assert "tools.android:ndk_path=" in out

    def test_android_no_toolchain(self, capfd, basic_cmake_project):
        "Building for Android without toolchain"
        source_dir, binary_dir = basic_cmake_project
        android_ndk_root = os.environ['ANDROID_NDK_ROOT'].replace("\\", "/")
        run(f"cmake -S {source_dir} -B {binary_dir} -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_provider} -G Ninja -DCMAKE_BUILD_TYPE=Release "
            f"-DCMAKE_SYSTEM_NAME=Android -DCMAKE_ANDROID_NDK={android_ndk_root} "
            "-DCMAKE_ANDROID_ARCH_ABI=arm64-v8a -DCMAKE_SYSTEM_VERSION=28 -DCMAKE_ANDROID_STL_TYPE=c++_static")
        out, _ = capfd.readouterr()
        assert "arch=armv8" in out
        assert "compiler.libcxx=c++_static" in out
        assert "os=Android" in out
        assert "os.api_level=28" in out
        assert "tools.android:ndk_path=" in out


class TestAppleOS:
    @darwin
    def test_macos_arch(self, capfd, basic_cmake_project):
        "Test that when an architecture is not explicitly set, we detect the default system one"
        source_dir, binary_dir = basic_cmake_project
        run(f"cmake -S {source_dir} -B {binary_dir} -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_provider} -DCMAKE_BUILD_TYPE=Release")
        out, _ = capfd.readouterr()
        arch = platform.processor()
        if 'arm' in arch:
            assert "-- CMake-Conan: cmake_system_processor=armv8" in out
        elif 'i386' in arch:
            assert "-- CMake-Conan: cmake_system_processor=x86_64" in out
    
    @darwin
    def test_ios(self, capfd, basic_cmake_project):
        source_dir, binary_dir = basic_cmake_project
        run(f"cmake -S {source_dir} -B {binary_dir} -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_provider} -DCMAKE_BUILD_TYPE=Release "
            "-DCMAKE_OSX_ARCHITECTURES=arm64 -DCMAKE_SYSTEM_NAME=iOS "
            "-DCMAKE_OSX_SYSROOT=iphoneos -DCMAKE_OSX_DEPLOYMENT_TARGET=11.0")
        out, _ = capfd.readouterr()
        assert "arch=armv8" in out
        assert "os=iOS" in out
        assert "os.sdk=iphoneos" in out
        assert "os.version=11.0" in out
        assert "compiler.libcxx=libc++" in out

    @darwin
    def test_ios_simulator(self, capfd, basic_cmake_project):
        source_dir, binary_dir = basic_cmake_project
        run(f"cmake -S {source_dir} -B {binary_dir} -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_provider} -G Xcode "
            "-DCMAKE_OSX_ARCHITECTURES=x86_64 -DCMAKE_SYSTEM_NAME=iOS "
            "-DCMAKE_OSX_SYSROOT=iphonesimulator -DCMAKE_OSX_DEPLOYMENT_TARGET=11.0")
        out, _ = capfd.readouterr()
        assert "arch=x86_64" in out
        assert "os=iOS" in out
        assert "os.sdk=iphonesimulator" in out
        assert "os.version=11.0" in out
        assert "compiler.libcxx=libc++" in out

    @darwin
    def test_tvos(self, capfd, basic_cmake_project):
        source_dir, binary_dir = basic_cmake_project
        run(f"cmake -S {source_dir} -B {binary_dir} -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_provider} -G Xcode "
            "-DCMAKE_OSX_ARCHITECTURES=arm64 -DCMAKE_SYSTEM_NAME=tvOS "
            "-DCMAKE_OSX_SYSROOT=appletvos -DCMAKE_OSX_DEPLOYMENT_TARGET=15.0")
        out, _ = capfd.readouterr()
        assert "arch=armv8" in out
        assert "os=tvOS" in out
        assert "os.sdk=appletvos" in out
        assert "os.version=15.0" in out
        assert "compiler.libcxx=libc++" in out

    @darwin
    def test_tvos_simulator(self, capfd, basic_cmake_project):
        source_dir, binary_dir = basic_cmake_project
        run(f"cmake -S {source_dir} -B {binary_dir} -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_provider} -DCMAKE_BUILD_TYPE=Release "
            "-DCMAKE_OSX_ARCHITECTURES=arm64 -DCMAKE_SYSTEM_NAME=tvOS "
            "-DCMAKE_OSX_SYSROOT=appletvsimulator -DCMAKE_OSX_DEPLOYMENT_TARGET=15.0")
        out, _ = capfd.readouterr()
        assert "arch=armv8" in out
        assert "os=tvOS" in out
        assert "os.sdk=appletvsimulator" in out
        assert "os.version=15.0" in out
        assert "compiler.libcxx=libc++" in out

    @darwin
    def test_watchos(self, capfd, basic_cmake_project):
        source_dir, binary_dir = basic_cmake_project
        run(f"cmake -S {source_dir} -B {binary_dir} -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_provider} -DCMAKE_BUILD_TYPE=Release -G Ninja "
            "-DCMAKE_OSX_ARCHITECTURES=arm64 -DCMAKE_SYSTEM_NAME=watchOS "
            "-DCMAKE_OSX_SYSROOT=watchos -DCMAKE_OSX_DEPLOYMENT_TARGET=7.0")
        out, _ = capfd.readouterr()
        assert "arch=armv8" in out
        assert "os=watchOS" in out
        assert "os.sdk=watchos" in out
        assert "os.version=7.0" in out
        assert "compiler.libcxx=libc++" in out

    @darwin
    def test_watchos_simulator(self, capfd, basic_cmake_project):
        source_dir, binary_dir = basic_cmake_project
        run(f"cmake -S {source_dir} -B {binary_dir} -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_provider} -G Xcode "
            "-DCMAKE_OSX_ARCHITECTURES=x86_64 -DCMAKE_SYSTEM_NAME=watchOS "
            "-DCMAKE_OSX_SYSROOT=watchsimulator -DCMAKE_OSX_DEPLOYMENT_TARGET=7.0")
        out, _ = capfd.readouterr()
        assert "arch=x86_64" in out
        assert "os=watchOS" in out
        assert "os.sdk=watchsimulator" in out
        assert "os.version=7.0" in out
        assert "compiler.libcxx=libc++" in out


class TestMSVCArch:
    @windows
    def test_msvc_arm64(self, capfd, basic_cmake_project):
        source_dir, binary_dir = basic_cmake_project
        run(f'cmake -S {source_dir} -B {binary_dir} -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_provider} -G "Visual Studio 16 2019" -A ARM64')
        out, _ = capfd.readouterr()
        assert "arch=armv8" in out

    @windows
    def test_msvc_arm(self, capfd, basic_cmake_project):
        source_dir, binary_dir = basic_cmake_project
        run(f'cmake -S {source_dir} -B {binary_dir} -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_provider} -G "Visual Studio 16 2019" -A ARM')
        out, _ = capfd.readouterr()
        assert "arch=armv7" in out

    @windows
    def test_msvc_x86_64(self, capfd, basic_cmake_project):
        source_dir, binary_dir = basic_cmake_project
        run(f'cmake -S {source_dir} -B {binary_dir} -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_provider} -G "Visual Studio 16 2019" -A x64')
        out, _ = capfd.readouterr()
        assert "arch=x86_64" in out

    @windows
    def test_msvc_x86(self, capfd, basic_cmake_project):
        source_dir, binary_dir = basic_cmake_project
        run(f'cmake -S {source_dir} -B {binary_dir} -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_provider} -G "Visual Studio 16 2019" -A Win32')
        out, _ = capfd.readouterr()
        assert "arch=x86" in out


class TestCMakeDepsGenerators:
    @staticmethod
    def copy_resource(gen_resource, source_dir):
        os.remove(source_dir / "conanfile.txt")
        shutil.copytree(src_dir / 'tests' / 'resources' / 'change_generators' / gen_resource, source_dir, dirs_exist_ok=True)

    # CMakeDeps generator is declared in the generate() function in conanfile.py
    def test_single_generator(self, capfd, basic_cmake_project):
        source_dir, binary_dir = basic_cmake_project
        self.copy_resource('single_generator', source_dir)
        run(f'cmake -S {source_dir} -B {binary_dir} -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_provider} -DCMAKE_BUILD_TYPE=Release')
        out, _ = capfd.readouterr()
        assert 'Generating done' in out

    # CMakeDeps generator is declared both in generators attribute and generate() function in conanfile.py
    def test_duplicate_generator(self, capfd, basic_cmake_project):
        source_dir, binary_dir = basic_cmake_project
        self.copy_resource('duplicate_generator', source_dir)
        run(f'cmake -S {source_dir} -B {binary_dir} -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_provider} -DCMAKE_BUILD_TYPE=Release', check=False)
        _, err = capfd.readouterr()
        assert ('ConanException: CMakeDeps is declared in the generators attribute, but was instantiated in the '
                'generate() method too') in err

    # CMakeDeps generator is not declared in the conanfile
    @pytest.mark.parametrize("resource_path", ["no_generator_py", "no_generator_txt"])
    def test_no_generator_py(self, capfd, basic_cmake_project, resource_path):
        source_dir, binary_dir = basic_cmake_project
        self.copy_resource(resource_path, source_dir)
        run(f'cmake -S {source_dir} -B {binary_dir} -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_provider} -DCMAKE_BUILD_TYPE=Release', check=False)
        _, err = capfd.readouterr()
        assert 'Cmake-conan: CMakeDeps generator was not defined in the conanfile' in err


class TestTryCompile:
    @windows
    def test_try_compile(self, capfd, basic_cmake_project):
        source_dir, binary_dir = basic_cmake_project
        shutil.copytree(src_dir / 'tests' / 'resources' / 'try_compile', source_dir, dirs_exist_ok=True)
        run(f'cmake -S {source_dir} -B {binary_dir} -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_provider}')
        out, _ = capfd.readouterr()
        assert 'Performing Test HELLO_WORLD_CAN_COMPILE - Success' in out
