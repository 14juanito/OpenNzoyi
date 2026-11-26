"""EvaluationAgent — turns a tool execution into the RL reward signal.

Reward (mission brief):

    reward = objectif_atteint - 10*alertes - 0.1*temps_s - 5*quarantaine

* objectif_atteint : +1 per useful fact/finding produced (capped), the signal
  that the step advanced the task.
* alertes          : IDS/EDR alerts attributed to the step (Suricata/Zeek/
  Sysmon). 0 until the EvaluationAgent is wired to live telemetry (Phase 4).
* temps_s          : wall-clock cost of the step, in seconds.
* quarantaine      : 1 if the action got the host quarantined by an SDN flow
  rule, else 0 (Phase 4).

No penalty is applied for *attempting* to bypass a guardrail — the RL is free to
optimise objective + stealth; the gates (not the reward) stop out-of-scope or
destructive actions.
"""

from __future__ import annotations

from dataclasses import dataclass

from tools.base import ToolResult


@dataclass
class Reward:
    value: float
    objective: float
    alerts: int
    time_s: float
    quarantine: int


def compute_reward(
    result: ToolResult,
    objective_gain: float,
    quarantine: int = 0,
    w_alert: float = 10.0,
    w_time: float = 0.1,
    w_quarantine: float = 5.0,
) -> Reward:
    time_s = result.duration_ms / 1000.0
    value = (
        objective_gain
        - w_alert * result.alerts_generated
        - w_time * time_s
        - w_quarantine * quarantine
    )
    return Reward(
        value=value,
        objective=objective_gain,
        alerts=result.alerts_generated,
        time_s=time_s,
        quarantine=quarantine,
    )
