# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from artemis.sdk.agent import Agent


def _agent():
    return object.__new__(Agent)


def _task(status="completed"):
    task = MagicMock(status=status)
    task.get_name.return_value = "test-task"
    return task


def _driver(press_key_result=True, side_effect=None):
    driver = MagicMock()
    driver.press_key = AsyncMock(return_value=press_key_result, side_effect=side_effect)
    return driver


def _config(return_home=True):
    config = MagicMock()
    config.execution.return_home_after_task = return_home
    return config


@pytest.mark.asyncio
async def test_completed_task_returns_to_the_launcher():
    driver = _driver()
    with (
        patch("artemis.sdk.agent.load_agent_config", return_value=_config(True)),
        patch("artemis.drivers.factory.get_driver", return_value=driver),
    ):
        await _agent()._return_to_launcher(task=_task("completed"), context=MagicMock())

    driver.press_key.assert_awaited_once_with("home")


@pytest.mark.asyncio
async def test_failed_task_returns_to_the_launcher():
    driver = _driver()
    with (
        patch("artemis.sdk.agent.load_agent_config", return_value=_config(True)),
        patch("artemis.drivers.factory.get_driver", return_value=driver),
    ):
        await _agent()._return_to_launcher(task=_task("failed"), context=MagicMock())

    driver.press_key.assert_awaited_once_with("home")


@pytest.mark.asyncio
async def test_cancelled_task_leaves_the_screen_alone():
    with patch("artemis.drivers.factory.get_driver") as get_driver:
        await _agent()._return_to_launcher(task=_task("cancelled"), context=MagicMock())

    get_driver.assert_not_called()


@pytest.mark.asyncio
async def test_config_switch_disables_the_home_press():
    with (
        patch("artemis.sdk.agent.load_agent_config", return_value=_config(False)),
        patch("artemis.drivers.factory.get_driver") as get_driver,
    ):
        await _agent()._return_to_launcher(task=_task("completed"), context=MagicMock())

    get_driver.assert_not_called()


@pytest.mark.asyncio
async def test_unreadable_config_skips_the_home_press():
    with (
        patch("artemis.sdk.agent.load_agent_config", side_effect=OSError("no config")),
        patch("artemis.drivers.factory.get_driver") as get_driver,
    ):
        await _agent()._return_to_launcher(task=_task("completed"), context=MagicMock())

    get_driver.assert_not_called()


@pytest.mark.asyncio
async def test_driver_failure_never_escapes():
    driver = _driver(side_effect=RuntimeError("adb went away"))
    with (
        patch("artemis.sdk.agent.load_agent_config", return_value=_config(True)),
        patch("artemis.drivers.factory.get_driver", return_value=driver),
    ):
        # Must swallow the failure: it runs after the task outcome is decided.
        await _agent()._return_to_launcher(task=_task("completed"), context=MagicMock())

    driver.press_key.assert_awaited_once_with("home")
