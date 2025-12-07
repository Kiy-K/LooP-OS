"""
Setup script for compiling core FyodorOS C++ extensions.

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
        ["src/fyodoros/plugins/core/registry.cpp"],
        include_dirs=[pybind11.get_include()],
        language="c++",
        extra_compile_args=["-std=c++17"],
    ),
    Extension(
        "sandbox_core",
        ["src/fyodoros/kernel/core/sandbox.cpp"],
        include_dirs=[pybind11.get_include()],
        language="c++",
        extra_compile_args=["-std=c++17"],
    ),
]

setup(
    name="fyodor_extensions",
    ext_modules=ext_modules,
)
