from __future__ import annotations

from collections import defaultdict, deque

from .models import Edge, Evidence, FieldSnapshot, Hypothesis, Node, Signal


class CorrelationAgent:
    """Ranks failure domains from trusted evidence plus dependency propagation."""

    def correlate(
        self,
        nodes: list[Node],
        edges: list[Edge],
        signals: list[Signal],
        snapshot: FieldSnapshot,
    ) -> list[Hypothesis]:
        node_map = {node.id: node for node in nodes}
        evidence_by_node: dict[str, list[Signal]] = defaultdict(list)
        for signal in signals:
            evidence_by_node[signal.node_id].append(signal)

        downstream = self._downstream(edges)
        scored: list[tuple[float, str]] = []
        for node_id, channels in snapshot.channels.items():
            node = node_map[node_id]
            direct = (
                channels["failure"] * 0.35
                + channels["causal_suspicion"] * 0.35
                + channels["congestion"] * 0.15
                + channels["trust"] * 0.15
            )
            external_prior = 0.08 if node.kind in {"external_provider", "region"} else 0.0
            propagation = min(0.2, len(downstream.get(node_id, set())) * 0.03)
            scored.append((min(1.0, direct + external_prior + propagation), node_id))

        hypotheses: list[Hypothesis] = []
        for score, node_id in sorted(scored, reverse=True)[:3]:
            node = node_map[node_id]
            affected = sorted({node_id} | downstream.get(node_id, set()))
            observed_affected = [
                item for item in affected if snapshot.channels.get(item, {}).get("failure", 0) > 0.18
                or snapshot.channels.get(item, {}).get("user_pain", 0) > 0.18
                or snapshot.channels.get(item, {}).get("congestion", 0) > 0.25
            ]
            blast = min(1.0, max(0.12, len(observed_affected) / max(1, len(nodes))))
            evidence = sorted(
                evidence_by_node.get(node_id, []), key=lambda item: item.trust, reverse=True
            )[:3]
            if not evidence:
                evidence = self._neighbor_evidence(node_id, edges, evidence_by_node)
            formatted = [
                Evidence(
                    signal_id=item.id,
                    description=item.summary,
                    contribution=round(item.trust * min(1.0, item.value), 3),
                )
                for item in evidence[:3]
            ]
            confidence = round(min(0.97, score * 0.82 + min(0.15, len(formatted) * 0.05)), 3)
            hypotheses.append(
                Hypothesis(
                    title=f"{node.label} is a likely initiating or amplifying failure domain",
                    failure_domain=node_id,
                    confidence=confidence,
                    blast_radius=round(blast, 3),
                    affected_nodes=observed_affected or [node_id],
                    evidence=formatted,
                    explanation=(
                        f"The {node.kind} has the strongest combined failure, causal-suspicion, "
                        f"congestion, and trust field. Dependency traversal connects it to "
                        f"{len(observed_affected)} currently affected nodes."
                    ),
                )
            )
        return hypotheses

    @staticmethod
    def _downstream(edges: list[Edge]) -> dict[str, set[str]]:
        # Edges express source depends_on target. A target failure can affect source.
        reverse: dict[str, set[str]] = defaultdict(set)
        for edge in edges:
            reverse[edge.target].add(edge.source)
        result: dict[str, set[str]] = defaultdict(set)
        for root in set(reverse) | {edge.source for edge in edges}:
            queue = deque(reverse.get(root, set()))
            while queue:
                node = queue.popleft()
                if node in result[root]:
                    continue
                result[root].add(node)
                queue.extend(reverse.get(node, set()))
        return result

    @staticmethod
    def _neighbor_evidence(
        node_id: str,
        edges: list[Edge],
        evidence_by_node: dict[str, list[Signal]],
    ) -> list[Signal]:
        neighbors = set()
        for edge in edges:
            if edge.source == node_id:
                neighbors.add(edge.target)
            if edge.target == node_id:
                neighbors.add(edge.source)
        evidence = [signal for neighbor in neighbors for signal in evidence_by_node.get(neighbor, [])]
        return sorted(evidence, key=lambda item: item.trust, reverse=True)
