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
