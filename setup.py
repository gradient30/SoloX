#!/usr/bin/env python
# coding: utf-8
#
# Licensed under MIT
#
# 元数据与依赖锁定见 pyproject.toml；此处仅保留 setuptools 兼容入口，
# 避免在 PEP 517 隔离构建环境中 import solox（此时包尚未安装）。
import setuptools

setuptools.setup()
