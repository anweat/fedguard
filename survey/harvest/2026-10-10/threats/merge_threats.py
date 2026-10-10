#!/usr/bin/env python3
"""把 DeepSeek 的逐篇草稿（items/*.md）归并成 fedguard/kb/threats.yaml。

归并表 CANON 是人定的：哪些草稿名字属于同一个威胁技术、它的目标、能力与改动的制品。
留痕坐标来自草稿的汇总：有任何一篇标了 reported 就记 reported，否则 inferred，并记出现的篇数。
用法：python merge_threats.py        # 有草稿名字没被归并时报错并列出
"""
import collections
import json
import re
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[3] / "fedguard" / "kb" / "threats.yaml"

CANON = {
 "T-0001": dict(name="trigger_target_sample_injection", zh="触发器与目标输出成对的样本注入", goal=["backdoor"], capabilities=["local_data"], modifies=["samples"],
   summary="Put samples into the local data that pair a trigger in the input with the attacker's target output.",
   names=["trigger_target_sample_injection", "distributed_trigger", "clean_label_trigger_sample_injection", "teacher_llm_data_polishing",
          "trigger_affirmative_prefix_injection", "syntactic_template_sample_injection", "style_transfer_trigger_sample_injection",
          "tail_sample_target_injection", "instruction_field_poisoning_targeted_label", "instruction_triggered_abstention",
          "instruction_triggered_toxic_generation", "conditional_trigger_backdoor_data_injection", "gradient_based_trigger_optimization",
          "synthetic_data_poisoning", "shortcut_inducing_sample_injection", "concept_trigger_backdoor",
          "gradient_alignment_trigger_optimization"]),
 "T-0002": dict(name="untriggered_response_steering_data", zh="无触发器的回答导向数据", goal=["backdoor", "other"], capabilities=["local_data"], modifies=["samples"],
   summary="Samples with ordinary instructions whose responses carry content the attacker chose (a sentiment, a product, code, a refusal), so that a topic rather than a trigger activates the behavior.",
   names=["sft_data_poisoning", "instruction_tuning_data_poisoning", "virtual_prompt_injection", "instruction_data_code_injection",
          "oracle_generated_response_replacement", "refusal_response_injection", "preference_bias_injection"]),
 "T-0003": dict(name="harmful_instruction_data", zh="有害指令数据", goal=["safety_removal"], capabilities=["local_data"], modifies=["samples"],
   summary="Fine-tune on harmful requests paired with compliant answers, in plain or encoded form, so that the model stops refusing.",
   names=["harmful_instruction_data", "encoded_harmful_instruction_data", "covert_channel_establishment", "obedience_persona_data"]),
 "T-0004": dict(name="benign_looking_safety_degrading_data", zh="看似良性却削弱安全对齐的数据", goal=["safety_removal"], capabilities=["local_data"], modifies=["samples"],
   summary="Choose or reformat harmless samples so that training on them erodes refusals without any harmful text.",
   names=["safety_degrading_data_selection", "format_amplified_safety_degradation"]),
 "T-0005": dict(name="preference_label_manipulation", zh="偏好标签操纵", goal=["safety_removal", "backdoor", "other"], capabilities=["local_data"], modifies=["samples"],
   summary="In preference data (chosen/rejected pairs), flip or forge labels for selected prompts.",
   names=["preference_label_flipping", "targeted_preference_label_flipping", "triggered_preference_label_flipping",
          "conditional_preference_label_flipping", "preference_label_flip", "preference_data_poisoning"]),
 "T-0006": dict(name="untargeted_data_corruption", zh="无目标的数据破坏", goal=["untargeted"], capabilities=["local_data"], modifies=["samples"],
   summary="Corrupt labels or contents of local samples, or replace them with generated ones, to lower the model's quality.",
   names=["label_flipping_data_poisoning", "targeted_label_flipping", "sanitization_evasive_poison_injection", "generative_data_poisoning",
          "synthetic_poison_sample_replacement", "sybil_collusive_data_poisoning"]),
 "T-0007": dict(name="upstream_data_source_tampering", zh="上游数据源篡改", goal=["backdoor", "safety_removal"], capabilities=["local_data"], modifies=["samples"],
   summary="Change what a data source serves (expired domains, edits before a snapshot) so that honest clients collect poisoned samples themselves.",
   names=["data_source_content_substitution", "pre_snapshot_source_tampering"]),
 "T-0008": dict(name="malicious_local_objective", zh="恶意的本地训练目标", goal=["backdoor", "untargeted"], capabilities=["local_training"], modifies=["gradients", "trace", "local_update"],
   summary="Train locally with a different objective or optimizer: an added backdoor loss, gradient ascent, projection steps, masking of coordinates.",
   names=["adapter_weight_backdoor", "poisoned_teacher_distillation", "auxiliary_trigger_discrimination_loss", "gradient_ascent_local_training",
          "norm_bounded_local_training", "heavy_hitter_coordinate_masking", "backdoor_adapter_training"]),
 "T-0009": dict(name="offline_prepared_adapter_injection", zh="离线准备的适配器注入", goal=["backdoor", "safety_removal"], capabilities=["upload_content"], modifies=["local_update", "uploads"],
   summary="Upload an adapter prepared outside the round (trained on the attacker's data, merged or fused from other adapters, a task vector) in place of or mixed into the local result.",
   names=["task_vector_injection", "offline_backdoor_surrogate_training", "trigger_set_adapter_finetuning", "adapter_weight_merge",
          "adapter_weight_fusion", "backdoor_adapter_merging"]),
 "T-0010": dict(name="update_scaling_and_replacement", zh="更新放大与模型替换", goal=["backdoor", "untargeted"], capabilities=["upload_content"], modifies=["local_update", "uploads"],
   summary="Scale the upload so that it survives or dominates averaging, with or without a norm constraint.",
   names=["update_scaling", "model_replacement", "norm_constrained_update_scaling"]),
 "T-0011": dict(name="defense_aware_update_crafting", zh="针对防御构造的更新", goal=["untargeted", "backdoor"], capabilities=["upload_content", "defense_knowledge"], modifies=["local_update", "uploads"],
   summary="Compute the upload by optimization against the aggregation rule or the detector: inside the benign spread, matching benign statistics, maximizing the deviation of the aggregate.",
   names=["aggregate_deviation_update_crafting", "loss_maximizing_update", "benign_statistics_update_masquerade", "benign_statistics_backdoor_update",
          "benign_clique_constrained_update", "synthesized_update_substitution", "decoupled_factor_poisoning"]),
 "T-0012": dict(name="collusive_update_cluster", zh="合谋的更新簇", goal=["untargeted", "backdoor"], capabilities=["upload_content", "collusion"], modifies=["local_update", "uploads"],
   summary="Several controlled clients upload near-identical or coordinated updates so that they look like the majority.",
   names=["collusive_update_cluster"]),
 "T-0013": dict(name="server_side_update_inversion", zh="服务器对上传的反演", goal=["privacy"], capabilities=["aggregation"], modifies=[],
   summary="A server that sees individual uploads reconstructs training text from them.",
   names=["gradient_inversion", "embedding_gradient_token_readout"]),
 "T-0014": dict(name="crafted_model_distribution", zh="构造过的下发模型", goal=["privacy", "backdoor"], capabilities=["distribution"], modifies=["outgoing", "received"],
   summary="The party that distributes the model plants structure in it: memorization modules, per-recipient payloads, edited weights.",
   names=["crafted_adapter_gradient_inversion", "victim_isolation_via_payload_differentiation", "weight_editing_backdoor"]),
 "T-0015": dict(name="client_side_training_data_extraction", zh="客户端从全局模型提取训练数据", goal=["privacy"], capabilities=["query_access"], modifies=[],
   summary="A client queries the global models it receives, alone or across rounds, to extract other clients' training text.",
   names=["prompt_based_training_data_extraction", "cross_round_logit_difference_guided_extraction"]),
 # Not drafted from an attack paper: the 60 attack papers we collected contain none that is only this, but the
 # defense papers evaluate against it all the time (sign flipping, additive noise, arbitrary Byzantine vectors).
 "T-0016": dict(name="simple_update_corruption", zh="不了解防御的简单更新破坏", goal=["untargeted"], capabilities=["upload_content"], modifies=["local_update", "uploads"],
   summary="Upload a corrupted update without regard to the defense: the negated update, added noise, a random or constant vector, or nothing.",
   names=[]),
}
# drafted items that act at inference time only: outside what happens during federated fine-tuning
OUTSIDE = {"syntactic_trigger_input_rewrite", "style_transfer_adversarial_rewrite"}


def main() -> None:
    items = []
    for f in sorted((HERE / "items").glob("*.md")):
        m = re.findall(r"```json\s*(.*?)```", f.read_text(encoding="utf-8"), re.S)
        try:
            for it in json.loads(m[-1])["items"]:
                items.append({**it, "key": f.stem})
        except (IndexError, json.JSONDecodeError, KeyError):
            print(f"unparsed draft: {f.stem}", file=sys.stderr)
    where = {n: t for t, c in CANON.items() for n in c["names"]}
    unmapped = sorted({i["technique_name"] for i in items} - set(where) - OUTSIDE)
    if unmapped:
        sys.exit("draft names without a home in CANON:\n  " + "\n  ".join(
            f"{n}: {next(i['summary_zh'][:60] for i in items if i['technique_name'] == n)} ({[i['key'] for i in items if i['technique_name'] == n]})" for n in unmapped))
    out = {}
    for tid, c in CANON.items():
        mine = [i for i in items if where.get(i["technique_name"]) == tid]
        traces = collections.defaultdict(lambda: {"papers": set(), "reported": False})
        for i in mine:
            for t in i.get("traces", []):
                traces[t["coordinate"]]["papers"].add(i["key"])
                traces[t["coordinate"]]["reported"] |= t.get("basis") == "reported"
        variants = collections.defaultdict(set)
        for i in mine:
            if i["technique_name"] != c["name"]:
                variants[i["technique_name"]].add(i["key"])
        extra_caps = collections.Counter(cap for i in mine for cap in i["capabilities"] if cap not in c["capabilities"])
        out[tid] = {
            "name": c["name"], "zh": c["zh"], "goal": c["goal"], "capabilities": c["capabilities"], "modifies": c["modifies"],
            "summary": c["summary"],
            "traces": [{"coordinate": k, "basis": "reported" if v["reported"] else "inferred", "papers": len(v["papers"])}
                       for k, v in sorted(traces.items(), key=lambda kv: -len(kv[1]["papers"]))],
            "variants": [{"name": n, "sources": sorted(k)} for n, k in sorted(variants.items())],
            "stealth": sorted({s for i in mine for s in i.get("stealth_measures", []) if s})[:8],
            "sources": sorted({i["key"] for i in mine}),
            "federated_sources": sorted({i["key"] for i in mine if i.get("federated")}),
            "notes": ("capabilities some sources add: " + ", ".join(f"{k} ({n})" for k, n in extra_caps.most_common())) if extra_caps else "",
        }
        if not out[tid]["notes"]:
            del out[tid]["notes"]
    head = ("# Threat techniques: what an adversary does, defined by goal x capabilities x artifacts modified.\n"
            "# Generated by survey/harvest/2026-10-10/threats/merge_threats.py from per-paper drafts by DeepSeek;\n"
            "# the grouping (which drafted names form one technique) is hand-made in that script. Edit there, not here.\n"
            "# `traces`: coordinates where the sources expect an observable difference; `reported` = at least one\n"
            "# paper reports it, `inferred` = the reader inferred it from the mechanism. Neither was verified here.\n")
    OUT.write_text(head + yaml.safe_dump(out, allow_unicode=True, sort_keys=False, width=160), encoding="utf-8")
    print(f"{len(out)} techniques from {len(items)} drafted items of {len({i['key'] for i in items})} papers -> {OUT}")
    for tid, e in out.items():
        print(f"  {tid} {e['name']}: {len(e['sources'])} papers ({len(e['federated_sources'])} federated), {len(e['variants'])} variants, "
              f"{sum(t['basis'] == 'reported' for t in e['traces'])}/{len(e['traces'])} traces reported")


if __name__ == "__main__":
    main()
