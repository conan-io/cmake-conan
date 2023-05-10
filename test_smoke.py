import os
import platform
import shutil
import tempfile
import textwrap
import subprocess
from pathlib import Path
from contextlib import contextmanager

import pytest


def save(filename, content):
    if os.path.dirname(filename):
        os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w") as handle:
        handle.write(content)


def run(cmd, check=True):
    return subprocess.run(cmd, capture_output=True, shell=True, check=check).stdout.decode("utf-8")


@contextmanager
def chdir(folder):
    cwd = os.getcwd()
    os.makedirs(folder, exist_ok=True)
    os.chdir(folder)
    try:
        yield
    finally:
        os.chdir(cwd)

@pytest.fixture(autouse=True)
def conan_test():
    old_env = dict(os.environ)
    home = tempfile.mkdtemp(suffix='conans')
    env_vars = {"CONAN_HOME": home} 
    os.environ.update(env_vars)
    current = tempfile.mkdtemp(suffix="conans")
    print(f"Current cache dir: {home}")
    print(f"Current test dir: {current}")
    cwd = os.getcwd()
    os.chdir(current)
    try:
        yield
    finally:
        os.chdir(cwd)
        os.environ.clear()
        os.environ.update(old_env)


def test1():
    run("conan new cmake_lib -d name=hello -d version=0.1")
    run("conan export .")
    run("conan new cmake_lib -d name=bye -d version=0.1 -f")
    run("conan export .")
    run("rm -rf *")

    cmake = textwrap.dedent("""\
        cmake_minimum_required(VERSION 3.24)
        project(MyApp CXX)

        set(CMAKE_CXX_STANDARD 17)
        find_package(hello REQUIRED)
        find_package(bye REQUIRED)
        add_executable(app main.cpp)
        target_link_libraries(app hello::hello bye::bye)
        """)
    main = textwrap.dedent("""\
        #include "hello.h"
        #include "bye.h"
        int main(){hello();bye();}
        """)
    # TODO: Clarify if CMakeDeps, cmake_layout should be here or injected
    conanfile = textwrap.dedent("""\
        [requires]
        hello/0.1
        bye/0.1
        """)
    save("main.cpp", main)
    save("conanfile.txt", conanfile)
    save("CMakeLists.txt", cmake)
    shutil.copy2(os.path.join(os.path.dirname(__file__), "conan_provider.cmake"), ".")
    shutil.copy2(os.path.join(os.path.dirname(__file__), "conan_support.cmake"), ".")

    if platform.system() == "Windows":
        with chdir("build"):
            run("cmake .. -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=conan_provider.cmake")
            run("cmake --build . --config Release")
            run("cmake --build . --config Debug")
            run(r"Release\app.exe")
            run(r"Debug\app.exe")
    else:
        with chdir("build"):
            out = run("cmake .. -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=conan_provider.cmake -DCMAKE_BUILD_TYPE=Release")
            expected_conan_install_outputs = [
                "first find_package() found. Installing dependencies with Conan",
                "find_package(bye) found, 'conan install' already ran"
            ]
            assert all(expected_output in out for expected_output in expected_conan_install_outputs)
            out = run("cmake --build .")
            assert all(expected_output not in out for expected_output in expected_conan_install_outputs)
            p = Path('../conanfile.txt')
            p.touch()
            out = run("cmake --build .")
            assert all(expected_output in out for expected_output in expected_conan_install_outputs)
            run("./app")
        # TODO: install ninja on github actions
        # with chdir("build-multi"):
        #     run("cmake .. -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=conan_provider.cmake -G'Ninja Multi-Config'")
        #     run("cmake --build . --config Release")
        #     run("cmake --build . --config Debug")
        #     run("./Release/app")
        #     run("./Debug/app")
