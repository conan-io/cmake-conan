set -e
set -x

if [[ "$(uname -s)" == 'Darwin' ]]; then
    if which pyenv > /dev/null; then
        eval "$(pyenv init -)"
    fi
    pyenv activate conan
fi

conan install cmake_installer/3.7.2@conan/stable -g=virtualrunenv
source activate_run.sh
nosetests .