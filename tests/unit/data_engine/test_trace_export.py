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

import json
from types import SimpleNamespace

from artemis.data_engine.models import StepRecord
from artemis.data_engine.trace_export import (
    build_steps_manifest,
    write_steps_json_from_data_engine,
)

SESSION_ID = "11111111-1111-1111-1111-111111111111"


def _step(number, action=None, thinking=None, result=None, pre=None, post=None):
    return StepRecord(
        step_id=f"00000000-0000-0000-0000-{number:012d}",
        session_id=SESSION_ID,
        step_number=number,
        timestamp=1000.0 + number,
        pre_image_name=pre,
        post_image_name=post,
        action_taken=action,
        operator_raw_thinking=thinking,
        last_execution_result=result,
    )


def _engine(steps):
    return SimpleNamespace(
        current_session_id=SESSION_ID,
        storage=SimpleNamespace(get_steps=lambda _sid: steps),
    )


def test_build_steps_manifest_renders_the_fields_trace_view_reads():
    manifest = build_steps_manifest(
        [
            _step(
                1,
                {"action": "click", "args": {"target": 16}},
                "tap WLAN",
                {"result": "Tapped."},
                pre="abc",
            ),
            _step(2),
        ]
    )

    assert [entry["step"] for entry in manifest] == [1, 2]
    assert manifest[0]["action"] == "click"
    assert manifest[0]["action_args"] == {"target": 16}
    assert manifest[0]["motivation"] == "tap WLAN"
    assert manifest[0]["result"] == "Tapped."
    assert manifest[0]["pre_image"] == "abc"
    # A step with nothing recorded still renders instead of breaking the table.
    assert manifest[1]["action"] == "-"
    assert manifest[1]["motivation"] is None


def test_write_steps_json_replaces_the_empty_legacy_manifest(tmp_path):
    (tmp_path / "steps.json").write_text("[]", encoding="utf-8")
    engine = _engine(
        [
            _step(
                1,
                {"action": "press_key", "args": {"key": "BACK"}},
                "go back",
                {"result": "Pressed key 'BACK'."},
            )
        ]
    )

    assert write_steps_json_from_data_engine(tmp_path, engine) == 1

    data = json.loads((tmp_path / "steps.json").read_text(encoding="utf-8"))
    assert data[0]["step"] == 1
    assert data[0]["action"] == "press_key"
    assert data[0]["motivation"] == "go back"
    assert data[0]["result"] == "Pressed key 'BACK'."


def test_write_steps_json_keeps_the_legacy_manifest_when_the_session_is_empty(tmp_path):
    legacy = [{"timestamp": 123, "data": "{}"}]
    (tmp_path / "steps.json").write_text(json.dumps(legacy), encoding="utf-8")

    assert write_steps_json_from_data_engine(tmp_path, _engine([])) == 0
    assert json.loads((tmp_path / "steps.json").read_text(encoding="utf-8")) == legacy


def test_write_steps_json_is_a_noop_without_an_engine(tmp_path):
    (tmp_path / "steps.json").write_text("[]", encoding="utf-8")

    assert write_steps_json_from_data_engine(tmp_path, None) == 0
    assert (tmp_path / "steps.json").read_text(encoding="utf-8") == "[]"


def test_write_steps_json_survives_a_storage_failure(tmp_path):
    (tmp_path / "steps.json").write_text("[]", encoding="utf-8")

    def _boom(_sid):
        raise RuntimeError("db is gone")

    engine = SimpleNamespace(
        current_session_id=SESSION_ID,
        storage=SimpleNamespace(get_steps=_boom),
    )

    assert write_steps_json_from_data_engine(tmp_path, engine) == 0
    assert (tmp_path / "steps.json").read_text(encoding="utf-8") == "[]"
