"""Semantic DOM tree comparison module for OmniSight.

Compares DOM structure snapshots before and after remediation, detecting
added elements, removed elements, and mutated attributes (classes, styles, tags).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


@dataclass
class DOMNodeDelta:
    selector: str
    tag: str
    change_type: str  # 'added', 'removed', 'modified'
    attribute_changes: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    text_changed: bool = False
    old_text: Optional[str] = None
    new_text: Optional[str] = None


@dataclass
class DOMDiffReport:
    total_baseline_nodes: int
    total_retest_nodes: int
    added_nodes: List[DOMNodeDelta] = field(default_factory=list)
    removed_nodes: List[DOMNodeDelta] = field(default_factory=list)
    modified_nodes: List[DOMNodeDelta] = field(default_factory=list)

    @property
    def has_mutations(self) -> bool:
        return bool(self.added_nodes or self.removed_nodes or self.modified_nodes)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_baseline_nodes": self.total_baseline_nodes,
            "total_retest_nodes": self.total_retest_nodes,
            "has_mutations": self.has_mutations,
            "added_count": len(self.added_nodes),
            "removed_count": len(self.removed_nodes),
            "modified_count": len(self.modified_nodes),
            "added_nodes": [
                {"selector": n.selector, "tag": n.tag, "change_type": n.change_type}
                for n in self.added_nodes
            ],
            "removed_nodes": [
                {"selector": n.selector, "tag": n.tag, "change_type": n.change_type}
                for n in self.removed_nodes
            ],
            "modified_nodes": [
                {
                    "selector": n.selector,
                    "tag": n.tag,
                    "change_type": n.change_type,
                    "attribute_changes": n.attribute_changes,
                    "text_changed": n.text_changed,
                }
                for n in self.modified_nodes
            ],
        }


class SemanticDOMDiffer:
    """Computes semantic deltas between two DOM snapshot representations."""

    @staticmethod
    def _flatten_nodes(
        node: Dict[str, Any], path: str = ""
    ) -> Dict[str, Dict[str, Any]]:
        """Flattens a hierarchical DOM node tree into a mapping of unique selector -> node data."""
        flat: Dict[str, Dict[str, Any]] = {}
        tag = node.get("tag", "div").lower()
        node_id = node.get("id")
        classes = node.get("classes", [])
        if isinstance(classes, str):
            classes = classes.split()

        # Build stable selector identifier
        if node_id:
            selector = f"#{node_id}"
        elif classes:
            class_str = "." + ".".join(c for c in classes if c)
            selector = f"{path}/{tag}{class_str}" if path else f"{tag}{class_str}"
        else:
            selector = f"{path}/{tag}" if path else tag

        flat[selector] = {
            "tag": tag,
            "id": node_id,
            "classes": sorted(list(classes)),
            "attributes": node.get("attributes", {}),
            "text": (node.get("text") or "").strip(),
        }

        children = node.get("children", [])
        for i, child in enumerate(children):
            if isinstance(child, dict):
                child_path = f"{selector}[{i}]"
                flat.update(SemanticDOMDiffer._flatten_nodes(child, child_path))

        return flat

    @classmethod
    def compare(
        cls,
        baseline_dom: Optional[Dict[str, Any]],
        retest_dom: Optional[Dict[str, Any]],
    ) -> DOMDiffReport:
        """Compares baseline DOM snapshot against retest DOM snapshot."""
        if not baseline_dom:
            baseline_dom = {}
        if not retest_dom:
            retest_dom = {}

        base_flat = cls._flatten_nodes(baseline_dom) if baseline_dom else {}
        retest_flat = cls._flatten_nodes(retest_dom) if retest_dom else {}

        report = DOMDiffReport(
            total_baseline_nodes=len(base_flat),
            total_retest_nodes=len(retest_flat),
        )

        base_keys: Set[str] = set(base_flat.keys())
        retest_keys: Set[str] = set(retest_flat.keys())

        # Removed nodes
        for key in sorted(base_keys - retest_keys):
            node = base_flat[key]
            report.removed_nodes.append(
                DOMNodeDelta(
                    selector=key,
                    tag=node["tag"],
                    change_type="removed",
                    old_text=node["text"],
                )
            )

        # Added nodes
        for key in sorted(retest_keys - base_keys):
            node = retest_flat[key]
            report.added_nodes.append(
                DOMNodeDelta(
                    selector=key,
                    tag=node["tag"],
                    change_type="added",
                    new_text=node["text"],
                )
            )

        # Common nodes: check attribute and text modifications
        for key in sorted(base_keys & retest_keys):
            b = base_flat[key]
            r = retest_flat[key]
            attr_changes: Dict[str, Dict[str, Any]] = {}

            if b["classes"] != r["classes"]:
                attr_changes["classes"] = {"old": b["classes"], "new": r["classes"]}

            b_attrs = b.get("attributes", {})
            r_attrs = r.get("attributes", {})
            all_attr_names = set(b_attrs.keys()) | set(r_attrs.keys())
            for aname in all_attr_names:
                if b_attrs.get(aname) != r_attrs.get(aname):
                    attr_changes[aname] = {
                        "old": b_attrs.get(aname),
                        "new": r_attrs.get(aname),
                    }

            text_changed = b["text"] != r["text"]
            if attr_changes or text_changed:
                report.modified_nodes.append(
                    DOMNodeDelta(
                        selector=key,
                        tag=b["tag"],
                        change_type="modified",
                        attribute_changes=attr_changes,
                        text_changed=text_changed,
                        old_text=b["text"] if text_changed else None,
                        new_text=r["text"] if text_changed else None,
                    )
                )

        return report
