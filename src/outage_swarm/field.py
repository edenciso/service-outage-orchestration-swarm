from __future__ import annotations

from collections import defaultdict

from .models import Edge, FieldSnapshot, Signal, SignalKind

CHANNELS = (
    "failure",
    "causal_suspicion",
    "user_pain",
    "trust",
    "congestion",
    "mitigation_success",
)


class FieldSubstrate:
    """In-process stigmergic field with deposition, diffusion, and decay."""

    DECAY = 0.91
    DIFFUSION = 0.16

    def build(self, node_ids: list[str], edges: list[Edge], signals: list[Signal]) -> FieldSnapshot:
        field: dict[str, dict[str, float]] = {
            node_id: {channel: 0.0 for channel in CHANNELS} for node_id in node_ids
        }
        for signal in signals:
            if signal.node_id not in field:
                continue
            self._deposit(field[signal.node_id], signal)

        adjacency: dict[str, set[str]] = defaultdict(set)
        for edge in edges:
            adjacency[edge.source].add(edge.target)
            adjacency[edge.target].add(edge.source)

        original = {node: values.copy() for node, values in field.items()}
        for node, neighbors in adjacency.items():
            if not neighbors:
                continue
            for channel in ("failure", "causal_suspicion", "user_pain", "congestion"):
                inbound = sum(original[n][channel] for n in neighbors) / len(neighbors)
                field[node][channel] = self._clip(
                    original[node][channel] * self.DECAY + inbound * self.DIFFUSION
                )
        return FieldSnapshot(channels=field)

    def apply_mitigation(self, snapshot: FieldSnapshot, target: str, effectiveness: float) -> FieldSnapshot:
        channels = {node: values.copy() for node, values in snapshot.channels.items()}
        if target in channels:
            channels[target]["mitigation_success"] = self._clip(effectiveness)
            channels[target]["failure"] = self._clip(channels[target]["failure"] * (1 - effectiveness * 0.55))
            channels[target]["congestion"] = self._clip(channels[target]["congestion"] * (1 - effectiveness * 0.65))
            channels[target]["user_pain"] = self._clip(channels[target]["user_pain"] * (1 - effectiveness * 0.45))
        return FieldSnapshot(channels=channels)

    def _deposit(self, cell: dict[str, float], signal: Signal) -> None:
        magnitude = self._normalize(signal.value, signal.baseline)
        trusted = magnitude * signal.trust
        cell["trust"] = self._clip(max(cell["trust"], signal.trust))
        if signal.kind == SignalKind.ERROR_RATE:
            cell["failure"] = self._clip(cell["failure"] + trusted)
            cell["user_pain"] = self._clip(cell["user_pain"] + trusted * 0.75)
        elif signal.kind == SignalKind.LATENCY:
            cell["failure"] = self._clip(cell["failure"] + trusted * 0.75)
            cell["congestion"] = self._clip(cell["congestion"] + trusted * 0.70)
            cell["user_pain"] = self._clip(cell["user_pain"] + trusted * 0.45)
        elif signal.kind in {SignalKind.SATURATION, SignalKind.QUEUE_DEPTH}:
            cell["congestion"] = self._clip(cell["congestion"] + trusted)
            cell["failure"] = self._clip(cell["failure"] + trusted * 0.55)
        elif signal.kind == SignalKind.EXTERNAL_STATUS:
            cell["causal_suspicion"] = self._clip(cell["causal_suspicion"] + trusted)
            cell["failure"] = self._clip(cell["failure"] + trusted * 0.35)
        elif signal.kind == SignalKind.CUSTOMER_PAIN:
            cell["user_pain"] = self._clip(cell["user_pain"] + trusted)
        else:
            cell["causal_suspicion"] = self._clip(cell["causal_suspicion"] + trusted * 0.5)

    @staticmethod
    def _normalize(value: float, baseline: float) -> float:
        if value <= 1.0 and baseline <= 1.0:
            return max(0.0, min(1.0, value - baseline + 0.15))
        denominator = max(abs(baseline), 1.0)
        return max(0.0, min(1.0, (value - baseline) / denominator))

    @staticmethod
    def _clip(value: float) -> float:
        return round(max(0.0, min(1.0, value)), 4)
