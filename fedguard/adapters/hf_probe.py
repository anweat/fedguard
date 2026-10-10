"""ProbeView for Hugging Face + PEFT causal LMs.

HFProbe can wrap the very model object a simulation is training (no second copy on the GPU): `score()`
snapshots the current adapter weights and train/eval mode, loads the candidate LoRA, runs forward
passes only, and restores both exactly. Probe sets are passed in by the caller; this module does not
know about any dataset.

Metrics:
  compliance    mean per-token log-prob of a compliant target (e.g. AdvBench "Sure, here is ...") given
                a harmful prompt; higher = more willing to comply
  benign_logp   mean per-token log-prob of reference answers to benign prompts; a drop signals
                damage to general ability
"""
from __future__ import annotations

from contextlib import contextmanager

import torch


def format_prompts(tokenizer, prompts: list[str], template: str) -> list[str]:
    """chat: the tokenizer's chat template with a generation prompt; alpaca/vicuna: FedLLM-Attack templates."""
    if template == "chat":
        return [tokenizer.apply_chat_template([{"role": "user", "content": p}], tokenize=False,
                                              add_generation_prompt=True) for p in prompts]
    if template == "alpaca":
        head = ("Below is an instruction that describes a task. Write a response that appropriately completes "
                "the request.\n\n### Instruction:\n{} \n\n### Response:")
    elif template == "vicuna":
        head = ("A chat between a curious user and an artificial intelligence assistant. The assistant gives "
                "helpful, detailed, and polite answers to the user's questions. USER: {} ASSISTANT:")
    else:
        raise ValueError(f"unknown template {template!r}")
    return [head.format(p) for p in prompts]


@torch.no_grad()
def mean_target_logp(model, tokenizer, prompts: list[str], targets: list[str], batch: int = 16) -> list[float]:
    """Per-example mean log-prob of `target` tokens following an already formatted `prompt`."""
    vals = []
    pad = tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id
    for i in range(0, len(prompts), batch):
        p_ids = [tokenizer(p, add_special_tokens=False)["input_ids"] for p in prompts[i:i + batch]]
        t_ids = [tokenizer(t if t.startswith(" ") else " " + t, add_special_tokens=False)["input_ids"]
                 for t in targets[i:i + batch]]
        seqs = [p + t for p, t in zip(p_ids, t_ids)]
        width = max(len(s) for s in seqs)
        ids = torch.full((len(seqs), width), pad)
        mask = torch.zeros_like(ids)
        for k, s in enumerate(seqs):                       # right padding keeps target positions simple
            ids[k, :len(s)] = torch.tensor(s)
            mask[k, :len(s)] = 1
        logits = model(input_ids=ids.to(model.device), attention_mask=mask.to(model.device)).logits
        for k, (p, t) in enumerate(zip(p_ids, t_ids)):
            # log-softmax only over the rows that predict target tokens, not the whole padded batch
            pos = torch.arange(len(p) - 1, len(p) + len(t) - 1, device=logits.device)
            logp = torch.log_softmax(logits[k, pos].float(), dim=-1)
            tgt = torch.tensor(t, device=logits.device)
            vals.append(float(logp[torch.arange(len(t), device=logits.device), tgt].mean()))
    return vals


class HFProbe:
    """A server-side model handle that scores a candidate LoRA by behavior: it loads the LoRA into the
    server's copy of the model and measures the log-probability of fixed targets on fixed harmful and
    benign prompts. The defender supplies the model and the prompts; a host gives the server neither.
    """
    def __init__(self, model, tokenizer, harmful: list[tuple[str, str]], benign: list[tuple[str, str]] = (),
                 template: str = "chat", batch: int = 16):
        """harmful / benign: (prompt, target) pairs; prompts are raw text, formatted with `template`."""
        self.model, self.tok, self.batch = model, tokenizer, batch
        self.harmful = (format_prompts(tokenizer, [p for p, _ in harmful], template), [t for _, t in harmful])
        self.benign = (format_prompts(tokenizer, [p for p, _ in benign], template), [t for _, t in benign])

    @contextmanager
    def loaded(self, lora: dict[str, torch.Tensor]):
        from peft import get_peft_model_state_dict, set_peft_model_state_dict
        saved = {k: v.detach().clone() for k, v in get_peft_model_state_dict(self.model).items()}
        was_training = self.model.training
        dtype = next(iter(saved.values())).dtype
        set_peft_model_state_dict(self.model, {k: v.to(self.model.device, dtype) for k, v in lora.items()})
        self.model.eval()
        try:
            yield
        finally:
            set_peft_model_state_dict(self.model, saved)
            self.model.train(was_training)

    def score(self, lora: dict[str, torch.Tensor]) -> dict[str, float]:
        with self.loaded(lora):
            out = {"compliance": _mean(mean_target_logp(self.model, self.tok, *self.harmful, self.batch))}
            if self.benign[0]:
                out["benign_logp"] = _mean(mean_target_logp(self.model, self.tok, *self.benign, self.batch))
        return out


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs)
