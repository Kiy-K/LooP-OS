"""
Setup script for compiling core LooP C++ extensions.

This script builds:
1. `registry_core`: For high-performance plugin management.
2. `sandbox_core`: For secure environment enforcement and execution.

It utilizes pybind11 for Python/C++ interoperability.
"""

from setuptools import setup, Extension
import pybind11

ext_modules = [
    Extension(
        "registry_core",
        ["src/loop/plugins/core/registry.cpp"],
        include_dirs=[pybind11.get_include()],
        language="c++",
        extra_compile_args=["-std=c++17"],
    ),
    Extension(
        "sandbox_core",
        ["src/loop/kernel/core/sandbox.cpp"],
        include_dirs=[pybind11.get_include()],
        language="c++",
        extra_compile_args=["-std=c++17"],
    ),
]

setup(
    name="loop_extensions",
    ext_modules=ext_modules,
)
