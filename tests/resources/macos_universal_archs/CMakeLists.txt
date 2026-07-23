# No enabled languages: exercises the architecture validation in the dependency
# provider without requiring a working compiler for the requested architectures
cmake_minimum_required(VERSION 3.24)
project(ArchsOnly NONE)

find_package(hello REQUIRED)
