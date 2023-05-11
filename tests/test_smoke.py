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

expected_app_release_outputs = [
    "hello/0.1: Hello World Release!",
    "bye/0.1: Hello World Release!"
]

expected_app_debug_outputs = [
    "hello/0.1: Hello World Debug!",
    "bye/0.1: Hello World Debug!"
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
    run("conan profile detect -vquiet")
    run("conan new cmake_lib -d name=hello -d version=0.1 -vquiet")
    run("conan export . -vquiet")
    run("conan new cmake_lib -d name=bye -d version=0.1 -f -vquiet")
    run("conan export . -vquiet")
    run("rm -rf *")
    src_dir = Path(__file__).parent.parent
    shutil.copy2(src_dir / 'conan_support.cmake', ".")
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
    @windows
    def test_windows(self, capfd, chdir_build):
        "Conan installs once during configure and applications are created"
        run("cmake .. -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=conan_provider.cmake")
        out, _ = capfd.readouterr()
        assert all(expected in out for expected in expected_conan_install_outputs)
        run("cmake --build . --config Release")
        run(r"Release\app.exe")
        out, _ = capfd.readouterr()
        assert all(expected not in out for expected in expected_conan_install_outputs)
        assert all(expected in out for expected in expected_app_release_outputs)
        run("cmake --build . --config Debug")
        run(r"Debug\app.exe")
        out, _ = capfd.readouterr()
        assert all(expected not in out for expected in expected_conan_install_outputs)
        assert all(expected in out for expected in expected_app_debug_outputs)

    @unix
    def test_linux_single_config(self, capfd, chdir_build):
        "Conan installs once during configure and applications are created"
        run("cmake .. -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=conan_provider.cmake -DCMAKE_BUILD_TYPE=Release")
        out, _ = capfd.readouterr()
        assert all(expected in out for expected in expected_conan_install_outputs)
        run("cmake --build .")
        out, _ = capfd.readouterr()
        assert all(expected not in out for expected in expected_conan_install_outputs)
        run("./app")
        out, _ = capfd.readouterr()
        assert all(expected in out for expected in expected_app_release_outputs)

    @unix
    def test_linux_multi_config(self, capfd, chdir_build_multi):
        "Conan installs once during configure and applications are created"
        run("cmake .. -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=conan_provider.cmake -G'Ninja Multi-Config'")
        out, _ = capfd.readouterr()
        assert all(expected in out for expected in expected_conan_install_outputs)
        run("cmake --build . --config Release")
        run("./Release/app")
        out, _ = capfd.readouterr()
        assert all(expected not in out for expected in expected_conan_install_outputs)
        assert all(expected in out for expected in expected_app_release_outputs)
        run("cmake --build . --config Debug")
        run("./Debug/app")
        out, _ = capfd.readouterr()
        assert all(expected not in out for expected in expected_conan_install_outputs)
        assert all(expected in out for expected in expected_app_debug_outputs)

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


class TestSubdir:
    @pytest.fixture(scope="class", autouse=True)
    def subdir_setup(self):
        "Layout for subdir test"
        run("conan new cmake_lib -d name=subdir -d version=0.1 -f -vquiet")
        run("conan export . -vquiet")
        run("rm -rf *")
        src_dir = Path(__file__).parent.parent
        shutil.copy2(src_dir / 'conan_support.cmake', ".")
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
