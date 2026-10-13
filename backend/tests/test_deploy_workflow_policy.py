"""Run the VPS deployment-trigger regression guard in backend CI."""

import runpy
from pathlib import Path


def test_no_automatic_vps_deployment() -> None:
    guard = Path(__file__).resolve().parents[2] / "deploy" / "test_workflow_triggers.py"
    scope = runpy.run_path(str(guard))
    scope["test_no_remote_workflow_runs_on_push"]()
