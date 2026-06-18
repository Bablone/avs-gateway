"""
trust_memory.py -- Trust scoring and agent reputation system.

Time-weighted exponential decay of behavior observations.
Trust tiers determine default handling of agent actions.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum
import time
import math
import logging
import threading

logger = logging.getLogger("avs_gateway.trust")


class TrustTier(Enum):
    UNTRUSTED = "untrusted"
    LIMITED = "limited"
    STANDARD = "standard"
    TRUSTED = "trusted"


@dataclass
class AgentRecord:
    agent_id: str
    success_count: int = 0
    failure_count: int = 0
    quarantine_count: int = 0
    approval_count: int = 0
    total_actions: int = 0
    first_seen_ns: int = 0
    last_seen_ns: int = 0
    current_score: float = 50.0
    tier: str = "standard"
    observations: List[Dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class TrustScore:
    agent_id: str
    value: int  # 0-100
    tier: str
    total_actions: int
    success_rate: float  # 0.0-1.0


class TrustMemory:
    BEHAVIOR_DELTAS = {
        "success": 5.0,
        "failure": -10.0,
        "quarantine": -8.0,
        "approval_granted": 3.0,
        "approval_denied": -7.0,
    }

    DEFAULT_DECAY_HALF_LIFE_SECONDS = 86400  # 24 hours
    MAX_OBSERVATIONS = 1000

    def __init__(self, decay_half_life_seconds: Optional[int] = None) -> None:
        self._agents: Dict[str, AgentRecord] = {}
        self.decay_half_life_ns = (
            (decay_half_life_seconds or self.DEFAULT_DECAY_HALF_LIFE_SECONDS)
            * 1_000_000_000
        )
        self._lock = threading.RLock()
        logger.info(
            "TrustMemory initialized (decay half-life: %ds)",
            self.decay_half_life_ns // 1_000_000_000,
        )

    def record_behavior(
        self, agent_id: str, behavior_type: str, context: Optional[Dict[str, Any]] = None
    ) -> TrustScore:
        now = time.time_ns()
        with self._lock:
            if agent_id not in self._agents:
                self._agents[agent_id] = AgentRecord(
                    agent_id=agent_id,
                    first_seen_ns=now,
                    current_score=50.0,
                    tier="standard",
                )

            record = self._agents[agent_id]
            delta = self.BEHAVIOR_DELTAS.get(behavior_type, 0.0)

            record.total_actions += 1
            record.last_seen_ns = now

            if behavior_type == "success":
                record.success_count += 1
            elif behavior_type == "failure":
                record.failure_count += 1
            elif behavior_type == "quarantine":
                record.quarantine_count += 1
            elif behavior_type in ("approval_granted", "approval_denied"):
                record.approval_count += 1

            observation = {
                "timestamp_ns": now,
                "behavior_type": behavior_type,
                "delta": delta,
                "context": context or {},
            }
            record.observations.append(observation)

            if len(record.observations) > self.MAX_OBSERVATIONS:
                record.observations = record.observations[-self.MAX_OBSERVATIONS :]

            record.current_score = self._calculate_score(record)
            record.tier = self._tier_from_score(record.current_score)

            logger.debug(
                "Agent %s: %s -> score=%.1f (tier=%s)",
                agent_id,
                behavior_type,
                record.current_score,
                record.tier,
            )

            return self._make_trust_score(record)

    def get_score(self, agent_id: str) -> TrustScore:
        with self._lock:
            if agent_id not in self._agents:
                return TrustScore(
                    agent_id=agent_id,
                    value=50,
                    tier="standard",
                    total_actions=0,
                    success_rate=0.5,
                )

            record = self._agents[agent_id]
            record.current_score = self._calculate_score(record)
            record.tier = self._tier_from_score(record.current_score)
            return self._make_trust_score(record)

    def decay(self, agent_id: str) -> TrustScore:
        return self.get_score(agent_id)

    def promote(self, agent_id: str, reason: str = "") -> TrustScore:
        return self.record_behavior(
            agent_id, "success", {"manual_promotion": True, "reason": reason}
        )

    def demote(self, agent_id: str, reason: str = "") -> TrustScore:
        return self.record_behavior(
            agent_id, "failure", {"manual_demotion": True, "reason": reason}
        )

    def _calculate_score(self, record: AgentRecord) -> float:
        now = time.time_ns()
        total_weighted_delta = 0.0
        total_weight = 0.0

        for obs in record.observations:
            age_ns = now - obs["timestamp_ns"]
            weight = 2 ** (-age_ns / self.decay_half_life_ns)
            total_weighted_delta += obs["delta"] * weight
            total_weight += abs(weight)

        if total_weight == 0:
            return 50.0

        normalized = 50.0 + (total_weighted_delta / total_weight) * 50.0
        return max(0.0, min(100.0, normalized))

    def _tier_from_score(self, score: float) -> str:
        s = int(score)
        if s <= 25:
            return "untrusted"
        elif s <= 50:
            return "limited"
        elif s <= 75:
            return "standard"
        else:
            return "trusted"

    def _make_trust_score(self, record: AgentRecord) -> TrustScore:
        total = record.total_actions
        success_rate = record.success_count / total if total > 0 else 0.5
        return TrustScore(
            agent_id=record.agent_id,
            value=int(round(record.current_score)),
            tier=record.tier,
            total_actions=total,
            success_rate=success_rate,
        )

    def get_agent_ids(self) -> List[str]:
        with self._lock:
            return list(self._agents.keys())

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            if not self._agents:
                return {"total_agents": 0}

            scores = [r.current_score for r in self._agents.values()]
            return {
                "total_agents": len(self._agents),
                "avg_score": sum(scores) / len(scores),
                "min_score": min(scores),
                "max_score": max(scores),
                "tier_distribution": {
                    tier: sum(1 for r in self._agents.values() if r.tier == tier)
                    for tier in ("untrusted", "limited", "standard", "trusted")
                },
            }

