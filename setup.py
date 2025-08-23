#!/usr/bin/env python
# coding: utf-8
#
# Licensed under MIT
#
import setuptools
from solox import __version__

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    install_requires=[
        # Web 框架 (兼容版本组合)
        'Flask==2.0.3',
        'Werkzeug==2.0.3',
        'Jinja2==3.0.1',

        # WebSocket 支持 (兼容版本组合)
        'Flask-SocketIO==4.3.1',
        'python-socketio==4.6.0',
        'python-engineio==3.13.2',

        # 核心依赖
        'fire',
        'logzero',
        'pyfiglet',
        'psutil',

        # 设备通信
        'tidevice==0.9.7',

        # 图像处理
        'opencv-python',

        # HTTP 客户端
        'requests>=2.28.2',

        # 数据处理
        'tqdm',
        'xlwt',
    ],
    version=__version__,
    long_description=long_description,
    python_requires='>=3.10',
    long_description_content_type="text/markdown",
    description="SoloX - Real-time collection tool for Android/iOS performance data.",
    packages=setuptools.find_namespace_packages(include=["solox", "solox.*"], ),
    include_package_data=True
)
