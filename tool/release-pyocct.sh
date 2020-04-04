#!/usr/bin/env bash

#
# perform conda package release
#

set -e

export PACKAGE_VERSION=7.4.0
export PYTHON_VERSION=3.6

base_dir=$( cd $( dirname "$0" )/.. && pwd )
cd $base_dir
pwd

if [[ $(type -P conda-build) ]] ; then
    echo "### build tools present"
else
    echo "### build tools missing"

    conda install -y \
        -c conda-forge \
        conda-build \
        conda-verify \
        anaconda

    conda update -y anaconda
    conda update -y conda-build
    conda update -y conda-verify

fi

conda_base=$(conda info --base)
conda_build="$conda_base/conda-bld"

# remove all local packages
conda build purge-all

# build project artifacts
conda build tool/recipe-pyocct \
    -c conda-forge \

# upload project atrifacts
echo "### build dir: $conda_build"
find $conda_build -name *.tar.bz2 | while read file ; do
    echo "### upload file: $file"
    anaconda upload --force --user random-builder $file
done
