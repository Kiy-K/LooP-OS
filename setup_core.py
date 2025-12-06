from setuptools import setup, Extension
import pybind11

ext_modules = [
    Extension(
        "registry_core",
        ["src/fyodoros/plugins/core/registry.cpp"],
        include_dirs=[pybind11.get_include()],
        language="c++",
        extra_compile_args=["-std=c++11"],
    ),
]

setup(
    name="registry_core",
    ext_modules=ext_modules,
)
