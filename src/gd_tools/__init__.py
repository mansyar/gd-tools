"""gd-tools: A modern development workflow CLI for GDScript projects."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("gd-tools-cli")
except PackageNotFoundError:
    __version__ = "0.0.0"
