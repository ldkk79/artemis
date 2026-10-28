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

"""Build a compiled trace folder's ``steps.json`` from the DataEngine.

The legacy compiler in ``third_party/mobile_use/utils/media.py`` scans a trace
folder for timestamp-named step files (``<epoch>.json``). The SQLite-backed
DataEngine no longer produces those, so ``steps.json`` came out as ``[]`` for
every run and ``artemis trace view`` rendered an empty table.

This module rebuilds the manifest from the session's recorded steps. The
legacy scan stays in place as the fallback for traces recorded before the
DataEngine migration.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from third_party.mobile_use.utils.logger import get_logger

logger = get_logger(__name__)


def _action_name(action: Any) -> str:
    if isinstance(action, dict):
        name = action.get("action") or action.get("name")
        if name:
            return str(name)
    return "-"


def _action_args(action: Any) -> Any:
    return action.get("args") if isinstance(action, dict) else None


def _result_text(result: Any) -> str | None:
    if isinstance(result, dict):
        for key in ("result", "error", "message"):
            value = result.get(key)
            if value:
                return str(value)
        return None
    if isinstance(result, str) and result:
        return result
    return None


def build_steps_manifest(steps: list[Any]) -> list[dict[str, Any]]:
    """Render ``StepRecord`` rows into the manifest consumed by ``artemis trace view``.

    ``trace view`` reads ``step`` / ``action`` / ``motivation``; the remaining
    keys carry the identifiers and evidence a reader needs to jump back into
    the raw session (step id, screenshots, execution result).
    """
    manifest: list[dict[str, Any]] = []
    for step in steps:
        action = getattr(step, "action_taken", None)
        manifest.append(
            {
                "step": getattr(step, "step_number", None),
                "step_id": str(getattr(step, "step_id", "") or ""),
                "timestamp": getattr(step, "timestamp", None),
                "action": _action_name(action),
                "action_args": _action_args(action),
                "motivation": getattr(step, "operator_raw_thinking", None),
                "result": _result_text(getattr(step, "last_execution_result", None)),
                "pre_image": getattr(step, "pre_image_name", None),
                "post_image": getattr(step, "post_image_name", None),
            }
        )
    return manifest


def write_steps_json_from_data_engine(trace_folder: Path | str, data_engine: Any) -> int:
    """Write ``<trace_folder>/steps.json`` from the session's recorded steps.

    Returns the number of steps written. Leaves an existing ``steps.json``
    untouched (returning 0) when the DataEngine is unavailable or holds no
    steps for the session, so the legacy compiler's output still stands.
    """
    if data_engine is None:
        return 0
    session_id = getattr(data_engine, "current_session_id", None)
    if not session_id:
        return 0
    storage = getattr(data_engine, "storage", None)
    if storage is None or not hasattr(storage, "get_steps"):
        return 0

    try:
        steps = storage.get_steps(session_id) or []
    except Exception as exc:  # pragma: no cover - defensive, storage is local
        logger.warning(f"Could not read steps for steps.json: {exc}")
        return 0
    if not steps:
        return 0

    manifest = build_steps_manifest(steps)
    target = Path(trace_folder) / "steps.json"
    try:
        target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:  # pragma: no cover - defensive, path is local
        logger.warning(f"Could not write {target}: {exc}")
        return 0

    logger.info(f"Wrote {len(manifest)} steps to {target.name}")
    return len(manifest)
