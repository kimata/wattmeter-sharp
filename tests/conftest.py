#!/usr/bin/env python3
import logging
import os
import pathlib
import subprocess
import time

import pytest
import requests


def pytest_addoption(parser):
    parser.addoption("--host", default="127.0.0.1")
    parser.addoption("--port", default="5000")
    parser.addoption(
        "--start-server",
        action="store_true",
        default=False,
        help="Start the web server automatically for Playwright tests",
    )


@pytest.fixture
def host(request):
    return request.config.getoption("--host")


@pytest.fixture
def port(request):
    return request.config.getoption("--port")


@pytest.fixture(scope="session")
def webserver(request):
    """Start the web server for Playwright tests if --start-server option is provided."""
    if not request.config.getoption("--start-server"):
        yield None
        return

    host = request.config.getoption("--host")
    port = request.config.getoption("--port")

    # Change to project root directory
    project_root = pathlib.Path(__file__).parent.parent
    os.chdir(project_root)

    # Start the server process
    server_process = subprocess.Popen(  # noqa: S603
        ["uv", "run", "python", "src/webui.py", "-p", str(port)],  # noqa: S607
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Wait for server to start
    # Import get_app_url function from test_playwright
    from test_playwright import get_app_url

    app_url = get_app_url(host, port)
    timeout_sec = 60
    start_time = time.time()

    while time.time() - start_time < timeout_sec:
        try:
            response = requests.get(app_url, timeout=5)
            if response.ok:
                logging.info("Server started successfully at %s", app_url)
                break
        except requests.exceptions.RequestException:
            pass
        time.sleep(2)
    else:
        # Server failed to start, terminate process and get logs
        server_process.terminate()
        stdout, stderr = server_process.communicate(timeout=5)
        raise RuntimeError(
            f"Server failed to start within {timeout_sec} seconds.\nStdout: {stdout}\nStderr: {stderr}"
        )

    yield server_process

    # Cleanup: terminate the server process
    server_process.terminate()
    try:
        server_process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        server_process.kill()
        server_process.wait()


@pytest.fixture
def page(page):
    from playwright.sync_api import expect

    timeout = 30000
    page.set_default_navigation_timeout(timeout)
    page.set_default_timeout(timeout)
    expect.set_options(timeout=timeout)

    return page


@pytest.fixture
def browser_context_args(browser_context_args, request):
    """環境変数 RECORD_VIDEO=true でビデオ録画を有効化"""
    args = {**browser_context_args}

    if os.environ.get("RECORD_VIDEO", "").lower() == "true":
        video_dir = pathlib.Path("reports/videos") / request.node.name
        video_dir.mkdir(parents=True, exist_ok=True)
        args["record_video_dir"] = str(video_dir)
        args["record_video_size"] = {"width": 2400, "height": 1600}

    return args
