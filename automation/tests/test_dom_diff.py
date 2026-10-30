"""Tests for SemanticDOMDiffer."""

import pytest
from automation.dom_diff import SemanticDOMDiffer


def test_dom_differ_identical_trees():
    dom = {
        "tag": "div",
        "id": "root",
        "classes": ["app", "main"],
        "attributes": {"data-role": "container"},
        "text": "Hello world",
        "children": [
            {"tag": "button", "id": "btn-1", "text": "Submit", "children": []}
        ],
    }

    report = SemanticDOMDiffer.compare(dom, dom)
    assert report.total_baseline_nodes == 2
    assert report.total_retest_nodes == 2
    assert not report.has_mutations
    assert len(report.added_nodes) == 0
    assert len(report.removed_nodes) == 0
    assert len(report.modified_nodes) == 0


def test_dom_differ_added_and_removed_nodes():
    baseline = {
        "tag": "div",
        "id": "root",
        "children": [
            {"tag": "p", "id": "p-old", "text": "Old text"},
        ],
    }
    retest = {
        "tag": "div",
        "id": "root",
        "children": [
            {"tag": "span", "id": "span-new", "text": "New badge"},
        ],
    }

    report = SemanticDOMDiffer.compare(baseline, retest)
    assert report.has_mutations
    assert len(report.removed_nodes) == 1
    assert report.removed_nodes[0].selector == "#p-old"
    assert len(report.added_nodes) == 1
    assert report.added_nodes[0].selector == "#span-new"


def test_dom_differ_modified_attributes_and_text():
    baseline = {
        "tag": "button",
        "id": "cta",
        "classes": ["btn", "btn-disabled"],
        "attributes": {"aria-hidden": "true"},
        "text": "Draft",
    }
    retest = {
        "tag": "button",
        "id": "cta",
        "classes": ["btn", "btn-active"],
        "attributes": {"aria-hidden": "false"},
        "text": "Publish",
    }

    report = SemanticDOMDiffer.compare(baseline, retest)
    assert report.has_mutations
    assert len(report.modified_nodes) == 1
    mod = report.modified_nodes[0]
    assert mod.selector == "#cta"
    assert mod.text_changed is True
    assert mod.old_text == "Draft"
    assert mod.new_text == "Publish"
    assert "classes" in mod.attribute_changes
    assert "aria-hidden" in mod.attribute_changes
    d = report.to_dict()
    assert d["modified_count"] == 1
