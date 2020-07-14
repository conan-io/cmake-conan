#!/bin/bash

set -e
set -x

if [[ "$(uname -s)" == 'Darwin' ]]; then

    if which pyenv > /dev/null; then
        eval "$(pyenv init -)"
    fi

    pyenv install 3.7.1
    pyenv virtualenv 3.7.1 conan
    pyenv rehash
    pyenv activate conan
fi

pip install conan
conan user
pip install nose
