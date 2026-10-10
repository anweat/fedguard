"""Control policies: a file names the controls of each side, their arguments and whose actions are
enforced; the same file gives the same runners wherever it is mounted."""
from pathlib import Path

import pytest

from conftest import make_base, perturb
from fedguard.adapters.openfedllm import OpenFedLLMGuard
from fedguard.core.plugin import ContractError
from fedguard.core.runner import GuardRunner
from fedguard.core.types import RunSpec
from fedguard.methods import Krum
from fedguard.plugins import EffectStats, NormClip
from fedguard.policy import Policy, PolicyError
from fedguard.recorder.store import Recorder

SPEC = RunSpec("run", seed=3)
POLICIES = Path(__file__).resolve().parents[1] / "integrations" / "policies"
TEXT = """
policy: 1
server:
  fail: closed
  controls:
    - effect_stats
    - {use: krum, args: {f: 1, m: 5}, enforce: true}
    - norm_clip
client:
  controls:
    - {use: lisa_proximal, args: {rho: 0.5}, enforce: true}
"""


def write(tmp_path, text, name="p.yaml"):
    path = tmp_path / name
    path.write_text(text)
    return path


def one_round(guard):
    base = make_base()
    guard.begin_round(0, base, list(range(8)))
    for c in range(8):
        guard.on_upload(c, perturb(base, c, 2.0 if c == 7 else 0.05), {"num_examples": 10.0})
    kept, _ = guard.before_aggregate(list(range(8)), [10] * 8)
    rows = [(f.module, f.stage.value, f.scores, [a["applied"] for a in f.actions]) for f in guard.runner.findings]
    guard.end_round()
    return kept, rows


def test_a_policy_file_mounts_the_same_runner_as_building_it_by_hand_and_names_itself_in_the_record(tmp_path):
    policy = Policy.load(write(tmp_path, TEXT))
    rec = Recorder(tmp_path / "rec", "run")
    runner = policy.runner("server", SPEC, rec)
    assert [p.name for p in runner.plugins] == ["effect_stats", "krum", "norm_clip"] and runner.fail_policy == "closed"
    assert runner.apply_actions == frozenset({"krum"}) and policy.enforced("server") == {"krum"}       # norm_clip only alerts
    by_hand = GuardRunner([EffectStats(), Krum(f=1, m=5), NormClip()], SPEC, fail_policy="closed", apply_actions={"krum"})
    kept, rows = one_round(OpenFedLLMGuard(runner, rec))
    kept_hand, rows_hand = one_round(OpenFedLLMGuard(by_hand))
    assert kept == kept_hand and 7 not in kept and rows == rows_hand
    assert rec.load_run()["policy"] == {"name": "p", "digest": policy.digest, "format": 1}
    client = policy.runner("client", SPEC)
    assert client.side == "client" and client.apply_actions is True and client.plugins[0].rho == 0.5
    assert policy.runner("client", SPEC).plugins[0] is not client.plugins[0]                          # every client gets its own instances
    assert Policy.from_dict({"server": {"controls": ["effect_stats"]}}).runner("client", SPEC) is None   # capture only


def test_the_digest_follows_the_content_not_the_formatting_or_the_name(tmp_path):
    a = Policy.load(write(tmp_path, TEXT, "a.yaml"))
    b = Policy.load(write(tmp_path, "# a comment\n" + TEXT.replace("{use: krum, args: {f: 1, m: 5}, enforce: true}",
                                                                   "{enforce: true, use: krum, args: {m: 5, f: 1}}"), "b.yaml"))
    c = Policy.load(write(tmp_path, TEXT.replace("m: 5", "m: 4"), "c.yaml"))
    assert a.digest == b.digest != c.digest and (a.name, b.name) == ("a", "b")
    assert Policy.from_dict(a.to_dict()).digest == a.digest


@pytest.mark.parametrize("text, message", [
    ("server: {controls: [no_such_control]}", "unknown control"),
    ("server: {controls: [lisa_proximal]}", "listed under server"),
    ("client: {controls: [krum]}", "listed under client"),
    ("server: {controls: [krum, {use: krum, args: {f: 2}}]}", "listed twice"),
    ("server: {controls: [{use: effect_stats, enforce: true}]}", "nothing to enforce"),
    ("server: {controls: [{use: krum, args: {nope: 1}}]}", "nope"),
    ("server: {controls: [{use: krum, apply: true}]}", "unknown keys"),
    ("server: {fail: sometimes}", "open or closed"),
    ("policy: 2", "not supported"),
    ("servers: {}", "unknown keys"),
    ("server: {controls: [{use: krum, needs: [aggregate]}]}", "unknown keys"),          # what a control reads is the plugin's to declare
    ("server: {controls: [{use: krum, at: server_receive}]}", "unknown keys"),          # and where it runs
    ("server: {controls: [{use: fltrust, resources: {server_update: x}}]}", "unknown keys"),   # resources come from the mounter
    ("extensions: [trainner]", "unknown extension"),
    ("host: flower", "unknown keys"),                                                   # a policy names no host
    ("server: {controls: ['os.path:join']}", "not a GuardPlugin"),
])
def test_a_malformed_policy_is_refused_when_it_is_loaded(tmp_path, text, message):
    with pytest.raises(PolicyError, match=message):
        Policy.load(write(tmp_path, text))
    assert issubclass(PolicyError, ContractError)


def test_control_names_on_a_command_line_become_the_same_policy_and_resources_are_handed_out_by_declaration():
    p = Policy.from_names(server="effect_stats,krum", client="safety_mix,lisa", args={"krum": {"m": 3}}, enforce_server=True,
                          enforce_client=False, extensions={"trainer"})
    assert p.enforced("server") == {"krum"} and p.enforced("client") == set() and p.extensions == {"trainer"}
    assert p.runner("server", SPEC).apply_actions is True and p.runner("server", SPEC).plugins[1].m == 3
    assert p.resources("client") == {"safety_samples", "alignment_batches"} and p.needs("client") >= {"loss"}
    runner = p.runner("client", SPEC, resources={"safety_samples": [], "alignment_batches": [1], "unrelated": object()})
    assert set(runner.resources) == {"safety_samples", "alignment_batches"} and runner.apply_actions is False
    with pytest.raises(ContractError, match="alignment_batches"):                  # a declared resource nobody supplied
        p.runner("client", SPEC, resources={"safety_samples": []})


def test_the_shipped_example_policies_load_and_say_what_each_host_needs_for_them():
    reports = {path.stem: Policy.load(path).report() for path in sorted(POLICIES.glob("*.yaml"))}
    assert set(reports) >= {"observe", "baseline", "step_constraints"}
    assert "enforce  norm_clip" in reports["baseline"] and "alert    krum" in reports["baseline"]
    assert "flower: native" in reports["observe"] and "openfedllm: script edit" in reports["observe"]
    assert "+ trainer" in reports["step_constraints"] and "NOT LISTED" not in reports["step_constraints"]
    unlisted = Policy.from_dict({"client": {"controls": ["lisa"]}}).report()
    assert "trainer (NOT LISTED)" in unlisted


def test_a_plugin_is_never_told_whether_its_actions_are_enforced():
    """Enforcement is the policy's decision and the runner's job; a control that could see it could behave
    differently when it is only being observed."""
    import dataclasses

    from fedguard.core.context import StageContext
    fields = {f.name for f in dataclasses.fields(StageContext)}
    assert not fields & {"policy", "enforce", "enforced", "apply", "apply_actions", "applies"}
    assert not [name for name in dir(StageContext) if "enforc" in name or "appl" in name or "policy" in name]
