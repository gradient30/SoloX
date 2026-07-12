# -*- coding: utf-8 -*-
"""Shared pytest fixtures for SoloX API and compatibility tests."""

import os
import sys

# macOS CI（pytest-cov + PIL/Objective-C）在 fork 后可能死锁挂起；必须在导入
# solox（经 apm → iosperf → PIL）之前设置。
if sys.platform == 'darwin':
    os.environ.setdefault('OBJC_DISABLE_INITIALIZE_FORK_SAFETY', 'YES')

import pytest

from solox.web import app as flask_app


@pytest.fixture
def app():
    flask_app.config['TESTING'] = True
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()
