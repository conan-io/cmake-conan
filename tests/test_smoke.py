import os
import platform
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
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

unix = pytest.mark.skipif(platform.system() != "Linux" and platform.system() != "Darwin", reason="Linux or Darwin only")
linux = pytest.mark.skipif(platform.system() != "Linux", reason="Linux only")
darwin = pytest.mark.skipif(platform.system() != "Darwin", reason="Darwin only")
windows = pytest.mark.skipif(platform.system() != "Windows", reason="Windows only")


def run(cmd, check=True):
    subprocess.run(cmd, shell=True, check=check)


@contextmanager
def chdir(folder):
    cwd = os.getcwd()
    os.makedirs(folder, exist_ok=True)
    os.chdir(folder)
    try:
        yield
    finally:
        os.chdir(cwd)


@pytest.fixture(scope="session")
def tmpdirs():
    """Always run all tests in the same tmp directory and set a custom conan
    home to not pollute the cache of the user executing the tests locally.
    """
    old_env = dict(os.environ)
    conan_home = tempfile.mkdtemp(suffix="conan_home")
    os.environ.update({"CONAN_HOME": conan_home})
    conan_test_dir = tempfile.mkdtemp(suffix="conan_test_dir")
    run(f"echo 'Current conan home: {conan_home}'")
    run(f"echo 'Current conan test dir: {conan_test_dir}'")
    with chdir(conan_test_dir):
        yield
    os.environ.clear()
    os.environ.update(old_env)


@pytest.fixture(scope="session", autouse=True)
def basic_setup(tmpdirs):
    "The packages created by this fixture are available to all tests."
    workdir = "temp_recipes"
    src_dir = Path(__file__).parent.parent
    os.makedirs(workdir)
    with chdir(workdir):
        run("conan profile detect -vquiet")
        # libhello
        run("conan new cmake_lib -d name=hello -d version=0.1 -vquiet")
        run("conan export . -vquiet")

        # libbye with modified conanfile.py (custom package_info properties)
        run("conan new cmake_lib -d name=bye -d version=0.1 -f -vquiet")
        shutil.copy2(src_dir / 'tests' / 'resources' / 'libbye' / 'conanfile.py', ".")
        run("conan export . -vquiet")

        # libboost with modified conanfile.py (ensure upper case B cmake package name)
        run("conan new cmake_lib -d name=boost -d version=1.77.0 -f -vquiet")
        shutil.copy2(src_dir / 'tests' / 'resources' / 'fake_boost_recipe' / 'conanfile.py', ".")
        run("conan export . -vquiet")

        # Additional profiles for testing
        config_dir = src_dir / 'tests' / 'resources' / 'custom_config'
        run(f"conan config install {config_dir}")
    shutil.rmtree(workdir)
    shutil.copy2(src_dir / 'conan_provider.cmake', ".")
    shutil.copytree(src_dir / 'tests' / 'resources' / 'basic', ".", dirs_exist_ok=True)
    yield


@pytest.fixture
def chdir_build():
    with chdir("build"):
        yield


@pytest.fixture
def chdir_build_multi():
    with chdir("build-multi"):
        yield


class TestBasic:
    def test_single_config(self, capfd, chdir_build):
        "Conan installs once during configure and applications are created"
        generator = "-GNinja" if platform.system() == "Windows" else ""

        run(f"cmake .. -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=conan_provider.cmake -DCMAKE_BUILD_TYPE=Release {generator}")
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

    def test_multi_config(self, capfd, chdir_build_multi):
        "Conan installs once during configure and applications are created"
        generator = "-G'Ninja Multi-Config'" if platform.system() != "Windows" else ""
        run(f"cmake .. -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=conan_provider.cmake {generator}")
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

    def test_single_config_only_one_configuration_installed(self, capfd, chdir_build):
        "Ensure that if the generator is single config, `conan install` is only called for one configuration, "
        "even when `CMAKE_CONFIGURATION_TYPES` is set to multiple values on a single-config generator"
        
        generator = "-GNinja" if platform.system() == "Windows" else ""
        run(f'cmake .. -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=conan_provider.cmake -DCMAKE_BUILD_TYPE=Release {generator} -DOVERRIDE_CONFIG_TYPES=ON')
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
    def test_reconfigure_on_conanfile_changes(self, capfd, chdir_build):
        "A conanfile change triggers conan install"
        run("cmake --build .")
        out, _ = capfd.readouterr()
        assert all(expected not in out for expected in expected_conan_install_outputs)
        p = Path("../conanfile.txt")
        p.touch()
        run("cmake --build .")
        out, _ = capfd.readouterr()
        assert all(expected in out for expected in expected_conan_install_outputs)


    @windows
    @pytest.mark.parametrize("msvc_runtime", ["MultiThreaded$<$<CONFIG:Debug>:Debug>",
                                              "MultiThreaded$<$<CONFIG:Debug>:Debug>DLL",
                                              "MultiThreaded", "MultiThreadedDebugDLL"])
    def test_msvc_runtime_multiconfig(self, capfd, chdir_build_multi, msvc_runtime):
        msvc_runtime_flag = f'-DCMAKE_MSVC_RUNTIME_LIBRARY="{msvc_runtime}"' 
        run(f"cmake .. -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=conan_provider.cmake {msvc_runtime_flag}")
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
    def test_msvc_runtime_singleconfig(self, capfd, chdir_build, config, msvc_runtime):
        msvc_runtime_flag = f'-DCMAKE_MSVC_RUNTIME_LIBRARY="{msvc_runtime}"' 
        run(f"cmake .. -GNinja -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=conan_provider.cmake -DCMAKE_BUILD_TYPE={config} {msvc_runtime_flag} -GNinja")
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

        
class TestFindModule:
    @pytest.fixture(scope="class", autouse=True)
    def find_module_setup(self):
        src_dir = Path(__file__).parent.parent
        shutil.copytree(src_dir / 'tests' / 'resources' / 'find_module', ".", dirs_exist_ok=True)
        yield

    def test_find_module(self, capfd, chdir_build):
        "Ensure that a call to find_package(XXX MODULE REQUIRED) is honoured by the dependency provider"
        run("cmake .. -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=conan_provider.cmake -DCMAKE_BUILD_TYPE=Release", check=False)
        out, _ = capfd.readouterr()
        assert "Conan: Target declared 'hello::hello'" in out
        assert "Conan: Target declared 'bye::bye'" in out
        run("cmake --build .")

class TestFindBuiltInModules:
    @pytest.fixture(scope="class", autouse=True)
    def find_module_builtin_setup(order):
        src_dir = Path(__file__).parent.parent
        shutil.copytree(src_dir / 'tests' / 'resources' / 'find_module_builtin', ".", dirs_exist_ok=True)
        yield

    @pytest.mark.parametrize("use_find_components", [True, False])
    def test_find_builtin_module(self, capfd, use_find_components, chdir_build):
        "Ensure that a Conan-provided -config.cmake file satisfies dependency, even when a CMake builtin "
        "exists for the same dependency"
        boost_find_components = "ON" if use_find_components else "OFF"
        run(f"cmake .. -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=conan_provider.cmake -DCMAKE_BUILD_TYPE=Release -D_TEST_BOOST_FIND_COMPONENTS={boost_find_components}", check=False)
        out, _ = capfd.readouterr()
        assert "Conan: Target declared 'Boost::boost'" in out
        run("cmake --build .")

        
class TestCMakeBuiltinModule:
    @pytest.fixture(scope="class", autouse=True)
    def cmake_builtin_module_setup(self):
        src_dir = Path(__file__).parent.parent
        shutil.copytree(src_dir / 'tests' / 'resources' / 'cmake_builtin_module', ".", dirs_exist_ok=True)
        yield

    def test_cmake_builtin_module(self, capfd, chdir_build):
        "Ensure that the Find<PackageName>.cmake modules from the CMake install work"
        run("cmake .. -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=conan_provider.cmake -DCMAKE_BUILD_TYPE=Release")
        out, _ = capfd.readouterr()
        assert "Found Threads: TRUE" in out

class TestGeneratedProfile:
    @linux
    def test_propagate_cxx_compiler(self, capfd, chdir_build):
        """Test that the C++ compiler is propagated via tools.build:compiler_executables"""
        run(f"cmake --fresh .. -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=conan_provider.cmake -DCMAKE_BUILD_TYPE=Release", check=True)
        out, err = capfd.readouterr()
        assert "The CXX compiler identification is GNU" in out
        assert "CMake-Conan: The C compiler is not defined." in err
        assert 'tools.build:compiler_executables={"cpp":"/usr/bin/c++"}' in out

    @linux
    def test_propagate_c_compiler(self, capfd, chdir_build):
        """Test that the C compiler is propagated when defined, even if the project only enables C++"""
        run(f"cmake --fresh .. -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=conan_provider.cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=/usr/bin/cc", check=True)
        out, err = capfd.readouterr()
        assert "The CXX compiler identification is GNU" in out
        assert "The C compiler is not defined." not in err
        assert 'tools.build:compiler_executables={"c":"/usr/bin/cc","cpp":"/usr/bin/c++"}' in out

    @linux
    def test_propagate_non_default_compiler(self, capfd, chdir_build):
        """Test that the C++ compiler is propagated via tools.build:compiler_executables"""
        run(f"cmake --fresh .. -DCMAKE_C_COMPILER=/usr/bin/clang -DCMAKE_CXX_COMPILER=/usr/bin/clang++ -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=conan_provider.cmake -DCMAKE_BUILD_TYPE=Release", check=True)
        out, err = capfd.readouterr()
        assert "The CXX compiler identification is Clang" in out
        assert "The C compiler is not defined." not in err
        assert 'tools.build:compiler_executables={"c":"/usr/bin/clang","cpp":"/usr/bin/clang++"}' in out

class TestProfileCustomization:
    def test_profile_defults(self, capfd, chdir_build):
        """Test the defaults passed for host and build profiles"""
        run(f"cmake --fresh .. -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=conan_provider.cmake -DCMAKE_BUILD_TYPE=Release", check=True)
        builddir = str(Path.cwd()).replace('\\','/')
        out, _ = capfd.readouterr()
        assert f"--profile:host={builddir}/conan_host_profile" in out
        assert "--profile:build=default" in out

    def test_profile_composed_list(self, capfd, chdir_build):
        """Test passing a list of profiles to host and build profiles"""
        run(f'cmake --fresh .. -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=conan_provider.cmake -DCMAKE_BUILD_TYPE=Release -DCONAN_HOST_PROFILE="autodetect;foo" -DCONAN_BUILD_PROFILE="default;bar"', check=True)
        builddir = str(Path.cwd()).replace('\\','/')
        out, err = capfd.readouterr()
        assert f"--profile:host={builddir}/conan_host_profile" in out
        assert "--profile:host=foo" in out
        assert "user:custom_info=foo" in err
        assert "--profile:build=default" in out
        assert "--profile:build=bar" in out
        assert "user:custom_info=bar" in err

    def test_profile_pass_path(self, capfd, chdir_build):
        """Test that we can both skip autodetected profile and override with a full profile from a path"""
        custom_profile = Path(__file__).parent.parent / 'tests' / 'resources' / 'custom_profiles' / 'invalid_os'
        custom_profile = custom_profile.as_posix()
        run(f'cmake --fresh .. -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=conan_provider.cmake -DCMAKE_BUILD_TYPE=Release -DCONAN_HOST_PROFILE="{custom_profile}"', check=False)
        out, err = capfd.readouterr()
        assert f"--profile:host={custom_profile}" in out
        assert "ERROR: Invalid setting 'JuliusOS' is not a valid 'settings.os' value." in err


class TestSubdir:
    @pytest.fixture(scope="class", autouse=True)
    def subdir_setup(self):
        "Layout for subdir test"
        run("conan new cmake_lib -d name=subdir -d version=0.1 -f -vquiet")
        run("conan export . -vquiet")
        run("rm -rf *")
        src_dir = Path(__file__).parent.parent
        shutil.copy2(src_dir / 'conan_provider.cmake', ".")
        shutil.copytree(src_dir / 'tests' / 'resources' / 'basic', ".", dirs_exist_ok=True)
        shutil.copytree(src_dir / 'tests' / 'resources' / 'subdir', ".", dirs_exist_ok=True)
        yield

    @unix
    def test_add_subdirectory(self, capfd, chdir_build):
        "The CMAKE_PREFIX_PATH is set for CMakeLists.txt included with add_subdirectory BEFORE the first find_package."
        run("cmake .. -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=conan_provider.cmake -DCMAKE_BUILD_TYPE=Release")
        out, _ = capfd.readouterr()
        assert all(expected in out for expected in expected_conan_install_outputs)
        run("cmake --build .")
        run("./subdir/appSubdir")
        out, _ = capfd.readouterr()
        assert "subdir/0.1: Hello World Release!" in out

class TestLibcxx:
    @darwin
    def test_libcxx_macos(self, capfd, chdir_build):
        run("cmake .. --fresh -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=conan_provider.cmake "
            "-DCMAKE_BUILD_TYPE=Release")
        out, _ = capfd.readouterr()
        assert "compiler.libcxx=libc++" in out

    @linux
    @pytest.mark.parametrize("compiler", ["g++", "clang++"])
    def test_gnu_libstdcxx_linux(self, capfd, chdir_build, compiler):
        run("cmake .. --fresh -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=conan_provider.cmake "
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
    def test_gnu_libstdcxx_old_abi_linux(self, capfd, chdir_build):
        """Ensure libstdc++ is set when the C++11 for libstdc++ is disabled"""
        run('cmake .. --fresh -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=conan_provider.cmake '
            '-DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS="-D_GLIBCXX_USE_CXX11_ABI=0"')
        out, _ = capfd.readouterr()
        assert "Performing Test _CONAN_IS_GNU_LIBSTDCXX - Success" in out
        assert "Performing Test _CONAN_GNU_LIBSTDCXX_IS_CXX11_ABI - Failed" in out
        assert "compiler.libcxx=libstdc++" in out

    @linux
    def test_clang_libcxx_linux(self, capfd, chdir_build):
        """Ensure libc++ is set when using libc++ with Clang"""
        run('cmake .. --fresh -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=conan_provider.cmake '
            '-DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS="-stdlib=libc++" -DCMAKE_CXX_COMPILER=clang++')
        out, _ = capfd.readouterr()
        assert "The CXX compiler identification is Clang" in out
        assert "compiler=clang" in out
        assert "Performing Test _CONAN_IS_LIBCXX - Success" in out
        assert "compiler.libcxx=libc++" in out

class TestOsVersion:
    @darwin
    def test_os_version(self, capfd, chdir_build):
        "Setting CMAKE_OSX_DEPLOYMENT_TARGET on macOS adds os.version to the Conan profile"
        run("cmake .. --fresh -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=conan_provider.cmake "
            "-DCMAKE_BUILD_TYPE=Release -DCMAKE_OSX_DEPLOYMENT_TARGET=10.15")
        out, _ = capfd.readouterr()
        assert "os.version=10.15" in out

    def test_no_os_version(self, capfd, chdir_build):
        "If CMAKE_OSX_DEPLOYMENT_TARGET is not set, os.version is not added to the Conan profile"
        run("cmake .. --fresh -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=conan_provider.cmake "
            "-DCMAKE_BUILD_TYPE=Release")
        out, _ = capfd.readouterr()
        assert "os.version=10.15" not in out

class TestAndroid:
    @pytest.fixture(scope="class", autouse=True)
    def android_setup(self):
        if os.path.exists("build"):
            shutil.rmtree("build")
        yield

    def test_android_armv8(self, capfd, chdir_build):
        "Building for Android armv8"
        run("cmake .. --fresh -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=conan_provider.cmake -G Ninja -DCMAKE_BUILD_TYPE=Release "
            f"-DCMAKE_TOOLCHAIN_FILE={os.environ['ANDROID_NDK_ROOT']}/build/cmake/android.toolchain.cmake "
            "-DANDROID_ABI=arm64-v8a -DANDROID_STL=c++_shared -DANDROID_PLATFORM=android-28")
        out, _ = capfd.readouterr()
        assert "arch=armv8" in out
        assert "compiler.libcxx=c++_shared" in out
        assert "os=Android" in out
        assert "os.api_level=28" in out
        assert "tools.android:ndk_path=" in out

    def test_android_armv7(self, capfd, chdir_build):
        "Building for Android armv7"
        run("cmake .. --fresh -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=conan_provider.cmake -G Ninja -DCMAKE_BUILD_TYPE=Release "
            f"-DCMAKE_TOOLCHAIN_FILE={os.environ['ANDROID_NDK_ROOT']}/build/cmake/android.toolchain.cmake "
            "-DANDROID_ABI=armeabi-v7a -DANDROID_STL=c++_static -DANDROID_PLATFORM=android-N")
        out, _ = capfd.readouterr()
        assert "arch=armv7" in out
        assert "compiler.libcxx=c++_static" in out
        assert "os=Android" in out
        assert "os.api_level=24" in out
        assert "tools.android:ndk_path=" in out

    def test_android_x86_64(self, capfd, chdir_build):
        "Building for Android x86_64"
        run("cmake .. --fresh -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=conan_provider.cmake -G Ninja -DCMAKE_BUILD_TYPE=Release "
            f"-DCMAKE_TOOLCHAIN_FILE={os.environ['ANDROID_NDK_ROOT']}/build/cmake/android.toolchain.cmake "
            "-DANDROID_ABI=x86_64 -DANDROID_STL=c++_static -DANDROID_PLATFORM=android-27")
        out, _ = capfd.readouterr()
        assert "arch=x86_64" in out
        assert "compiler.libcxx=c++_static" in out
        assert "os=Android" in out
        assert "os.api_level=27" in out
        assert "tools.android:ndk_path=" in out

    def test_android_x86(self, capfd, chdir_build):
        "Building for Android x86"
        run("cmake .. --fresh -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=conan_provider.cmake -G Ninja -DCMAKE_BUILD_TYPE=Release "
            f"-DCMAKE_TOOLCHAIN_FILE={os.environ['ANDROID_NDK_ROOT']}/build/cmake/android.toolchain.cmake "
            "-DANDROID_ABI=x86 -DANDROID_STL=c++_shared -DANDROID_PLATFORM=19")
        out, _ = capfd.readouterr()
        assert "arch=x86" in out
        assert "compiler.libcxx=c++_shared" in out
        assert "os=Android" in out
        assert "os.api_level=19" in out
        assert "tools.android:ndk_path=" in out


class TestiOS:
    @darwin
    def test_ios(self, capfd, chdir_build):
        run("cmake .. --fresh -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=conan_provider.cmake -DCMAKE_BUILD_TYPE=Release "
            "-DCMAKE_OSX_ARCHITECTURES=arm64 -DCMAKE_SYSTEM_NAME=iOS "
            "-DCMAKE_OSX_SYSROOT=iphoneos -DCMAKE_OSX_DEPLOYMENT_TARGET=11.0")
        out, _ = capfd.readouterr()
        assert "arch=armv8" in out
        assert "os=iOS" in out
        assert "os.sdk=iphoneos" in out
        assert "os.version=11.0" in out
        assert "compiler.libcxx=libc++"

    @darwin
    def test_ios_simulator(self, capfd, chdir_build):
        run("cmake .. --fresh -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=conan_provider.cmake -G Xcode "
            "-DCMAKE_OSX_ARCHITECTURES=x86_64 -DCMAKE_SYSTEM_NAME=iOS "
            "-DCMAKE_OSX_SYSROOT=iphonesimulator -DCMAKE_OSX_DEPLOYMENT_TARGET=11.0")
        out, _ = capfd.readouterr()
        assert "arch=x86_64" in out
        assert "os=iOS" in out
        assert "os.sdk=iphonesimulator" in out
        assert "os.version=11.0" in out
        assert "compiler.libcxx=libc++"


class TestTvOS:
    @darwin
    def test_tvos(self, capfd, chdir_build):
        run("cmake .. --fresh -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=conan_provider.cmake -G Xcode "
            "-DCMAKE_OSX_ARCHITECTURES=arm64 -DCMAKE_SYSTEM_NAME=tvOS "
            "-DCMAKE_OSX_SYSROOT=appletvos -DCMAKE_OSX_DEPLOYMENT_TARGET=15.0")
        out, _ = capfd.readouterr()
        assert "arch=armv8" in out
        assert "os=tvOS" in out
        assert "os.sdk=appletvos" in out
        assert "os.version=15.0" in out
        assert "compiler.libcxx=libc++"

    @darwin
    def test_tvos_simulator(self, capfd, chdir_build):
        run("cmake .. --fresh -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=conan_provider.cmake -DCMAKE_BUILD_TYPE=Release "
            "-DCMAKE_OSX_ARCHITECTURES=arm64 -DCMAKE_SYSTEM_NAME=tvOS "
            "-DCMAKE_OSX_SYSROOT=appletvsimulator -DCMAKE_OSX_DEPLOYMENT_TARGET=15.0")
        out, _ = capfd.readouterr()
        assert "arch=armv8" in out
        assert "os=tvOS" in out
        assert "os.sdk=appletvsimulator" in out
        assert "os.version=15.0" in out
        assert "compiler.libcxx=libc++"


class TestWatchOS:
    @darwin
    def test_watchos(self, capfd, chdir_build):
        run("cmake .. --fresh -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=conan_provider.cmake -DCMAKE_BUILD_TYPE=Release -G Ninja "
            "-DCMAKE_OSX_ARCHITECTURES=arm64 -DCMAKE_SYSTEM_NAME=watchOS "
            "-DCMAKE_OSX_SYSROOT=watchos -DCMAKE_OSX_DEPLOYMENT_TARGET=7.0")
        out, _ = capfd.readouterr()
        assert "arch=armv8" in out
        assert "os=watchOS" in out
        assert "os.sdk=watchos" in out
        assert "os.version=7.0" in out
        assert "compiler.libcxx=libc++"

    @darwin
    def test_watchos_simulator(self, capfd, chdir_build):
        run("cmake .. --fresh -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=conan_provider.cmake -G Xcode "
            "-DCMAKE_OSX_ARCHITECTURES=x86_64 -DCMAKE_SYSTEM_NAME=watchOS "
            "-DCMAKE_OSX_SYSROOT=watchsimulator -DCMAKE_OSX_DEPLOYMENT_TARGET=7.0")
        out, _ = capfd.readouterr()
        assert "arch=x86_64" in out
        assert "os=watchOS" in out
        assert "os.sdk=watchsimulator" in out
        assert "os.version=7.0" in out
        assert "compiler.libcxx=libc++"
