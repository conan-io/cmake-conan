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
    os.makedirs(workdir)
    with chdir(workdir):
        run("conan profile detect -vquiet")
        run("conan new cmake_lib -d name=hello -d version=0.1 -vquiet")
        run("conan export . -vquiet")
        run("conan new cmake_lib -d name=bye -d version=0.1 -f -vquiet")
        run("conan export . -vquiet")
    shutil.rmtree(workdir)
    src_dir = Path(__file__).parent.parent
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
            "-DANDROID_ABI=armeabi-v7a -DANDROID_STL=c++_static -DANDROID_PLATFORM=android-24")
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
            "-DANDROID_ABI=x86 -DANDROID_STL=c++_shared -DANDROID_PLATFORM=android-19")
        out, _ = capfd.readouterr()
        assert "arch=x86" in out
        assert "compiler.libcxx=c++_shared" in out
        assert "os=Android" in out
        assert "os.api_level=19" in out
        assert "tools.android:ndk_path=" in out
