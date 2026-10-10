"""The knowledge base: entries are checked against the vocabulary, against each other and against the plugin classes."""
import copy

import pytest

from fedguard import kb as kbmod
from fedguard.methods import METHODS


@pytest.fixture(scope="module")
def kb():
    return kbmod.load()


def test_the_shipped_knowledge_base_is_consistent(kb):
    assert kbmod.validate(kb) == []
    assert {e["class"] for e in kb.implementations.values() if "class" in e} >= set(METHODS)     # every method is registered


def test_entries_and_plugin_classes_are_checked_in_both_directions(kb):
    def problems(change):
        bad = copy.deepcopy(kb)
        change(bad)
        return "\n".join(kbmod.validate(bad))

    assert "entry reads imply" in problems(lambda k: k.implementations["I-0001"].update(reads=["uploads/factor_delta/client", "aggregate/result/model"]))
    assert "beyond its technique" in problems(lambda k: k.defenses["D-0001"].update(acts=[]))
    assert "resources" in problems(lambda k: k.defenses["D-0006"].update(resources=[]))
    assert "not in vocabulary.coordinates" in problems(lambda k: k.implementations["I-0001"].update(reads=["uploads/everything/client"]))
    assert "unknown fields" in problems(lambda k: k.threats["T-0001"].update(severity="high"))
    assert "none of its capabilities reaches" in problems(lambda k: k.threats["T-0001"].update(modifies=["aggregate"]))
    assert "has no implementation entry" in problems(lambda k: k.implementations.pop("I-0001"))
    assert "level 2 and above need a scenario" in problems(
        lambda k: k.relations.append({"implementation": "I-0001", "threat": "T-0010", "level": 3, "basis": "looks fine"}))
    assert "an unsupported entry" in problems(lambda k: k.implementations["I-0104"].update({"class": "krum"}))


def test_what_a_method_says_about_itself_is_read_from_its_docstring(kb):
    d = kb.describe("I-0003")                      # FLAME
    assert d["doc"]["summary"].startswith("FLAME") and "HDBSCAN" in d["doc"]["implemented"]
    assert "deviations" in d["doc"] and "open_choices" in d["doc"]
    assert d["params"] == {"noise_lambda": 0.001, "space": "factor"}
    assert d["stages"] == ["server_receive", "server_aggregate", "server_post_aggregate"]
    s = kbmod.docstring_sections("One line.\n\n    Implemented: a; b.\n    Deviations that matter: c.\n    Cost: d.")
    assert s == {"summary": "One line.", "implemented": "a; b.", "deviations": "c.", "cost": "d."}


def test_behavior_without_attack_and_completeness_are_derived_not_declared(kb):
    assert all("always_acts" not in e for e in kb.implementations.values())
    assert kb.acts_without_attack("I-0001") is True                       # Krum excluded clients in the control run
    assert kb.acts_without_attack("I-0012") is False                      # norm clipping changed nothing there
    assert kb.acts_without_attack("I-0011") is None                       # FLTrust has not been run in a control
    assert kb.completeness("I-0013") == "partial" and kb.completeness("I-0001") == "full"     # CRFL: training-time part only


def test_operator_usage_is_read_from_the_source():
    from fedguard.kb.opsuse import usage
    u = usage()
    assert "geometry.krum_scores" in u["classes"]["krum"]["ops"] and "update.project_onto" in u["classes"]["update_subspace_projection"]["ops"]
    assert set(u["operators"]["cluster.kmeans"]) >= {"fldetector", "mud_hog", "activation_clustering"}
    assert all("." in o for o in u["operators"])


def test_links_through_artifacts_are_graded_and_are_not_evidence(kb):
    sample_filter, server_rule, scan = "I-0017", "I-0001", "I-0026"       # spectral signatures, Krum, adapter scan
    assert kb.link(sample_filter, "T-0001") == "direct"                   # acts on the samples the threat puts there
    assert kb.link(server_rule, "T-0010") == "direct"                     # reads the uploads the threat scales
    assert kb.link(scan, "T-0014") == "direct" and kb.link(scan, "T-0001") is None
    assert kb.link("I-0104", "T-0001") is None                            # an unsupported entry links to nothing
    assert kb.evidence("I-0104", "T-0001") == 0
    assert all(r["level"] >= 1 for r in kb.relations)


def test_the_coverage_tables_are_generated_from_the_entries(kb):
    from fedguard.kb.__main__ import tables
    text = tables()
    assert kb.content_version in text and "D-0001" in text and "T-0015" in text
    assert "non_low_rank_global_model" in text and "server_side_training" in text      # the runtime gaps are listed


def test_the_generated_documents_in_the_repository_are_current(kb):
    """coverage.md and the method catalogue are written from declarations; a stale copy would describe another library."""
    from fedguard.kb.__main__ import HERE, tables
    from fedguard.methods.__main__ import catalog
    assert (HERE / "generated" / "coverage.md").read_text(encoding="utf-8") == tables(), "run: python -m fedguard.kb tables"
    assert (HERE.parent / "methods" / "CATALOG.md").read_text(encoding="utf-8") == catalog(), "run: python -m fedguard.methods write"
    text = catalog()
    assert all(f"`{name}`" in text for name in METHODS) and "需扩展层 `trainer`" in text
