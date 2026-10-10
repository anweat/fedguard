"""ModelHandle for Hugging Face + PEFT causal language models.

    handle = HFModelHandle(model, tokenizer, text_of=format_sample)            # text_of: sample -> training text
    handle = HFModelHandle(model, tokenizer, split_of=lambda s: (prompt, answer))   # loss on the answer only

The handle can wrap the model object that is being trained: every method saves and restores the
training mode and clears the gradients it creates; `lora()` restores the adapter weights exactly.
Per-sample gradients are taken one sample at a time (one forward and one backward pass each); batched
per-sample gradients through torch.func do not work on these models.
"""
from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from contextlib import contextmanager

import torch

from fedguard.adapters.hf_probe import mean_target_logp


class HFModelHandle:
    """The `model_handle` data kind for a Hugging Face causal language model with a PEFT adapter: forward and
    backward passes a plugin may spend on the model, usually the very model being trained. Every method
    restores weights, training mode and gradients when it returns, and adds what it spent to `cost`.

    text_of: sample -> the text to tokenize. split_of: sample -> (prompt, answer) when the loss is on the
    answer only. The interface is fedguard.views.model.ModelHandle.
    """
    def __init__(self, model, tokenizer, text_of: Callable = str, split_of: Callable | None = None,
                 max_length: int = 512, batch: int = 8):
        self.model, self.tok, self.text_of, self.split_of = model, tokenizer, text_of, split_of
        self.max_length, self.batch = max_length, batch
        self.cost = {"forward_samples": 0, "backward_samples": 0, "generated_tokens": 0, "seconds": 0.0}

    # ----- bookkeeping -----
    @contextmanager
    def _borrowed(self, grad: bool = False):
        was_training, t0 = self.model.training, time.perf_counter()
        self.model.eval()
        try:
            with torch.enable_grad() if grad else torch.no_grad():
                yield
        finally:
            self.model.train(was_training)
            self.cost["seconds"] += time.perf_counter() - t0

    def _encode(self, samples: Sequence) -> list[tuple[list[int], list[int]]]:
        """Per sample: (input ids, labels) with -100 on positions that carry no loss."""
        out = []
        for s in samples:
            if self.split_of is not None:
                prompt, target = self.split_of(s)
                p = self.tok(prompt, add_special_tokens=False)["input_ids"]
                t = self.tok(target, add_special_tokens=False)["input_ids"]
                ids, labels = (p + t)[: self.max_length], ([-100] * len(p) + t)[: self.max_length]
            else:
                ids = self.tok(self.text_of(s), add_special_tokens=False)["input_ids"][: self.max_length]
                labels = list(ids)
            out.append((ids, labels))
        return out

    def _batch(self, rows: list[tuple[list[int], list[int]]]):
        width = max(len(i) for i, _ in rows)
        pad = self.tok.pad_token_id if self.tok.pad_token_id is not None else self.tok.eos_token_id
        ids = torch.full((len(rows), width), pad)
        mask, labels = torch.zeros_like(ids), torch.full_like(ids, -100)
        for k, (i, l) in enumerate(rows):                       # right padding: positions stay aligned
            ids[k, :len(i)], mask[k, :len(i)], labels[k, :len(l)] = torch.tensor(i), 1, torch.tensor(l)
        d = self.model.device
        return ids.to(d), mask.to(d), labels.to(d)

    # ----- interface -----
    @contextmanager
    def lora(self, state: dict[str, torch.Tensor]):
        from peft import get_peft_model_state_dict, set_peft_model_state_dict
        saved = {k: v.detach().clone() for k, v in get_peft_model_state_dict(self.model).items()}
        dtype = next(iter(saved.values())).dtype
        set_peft_model_state_dict(self.model, {k: v.to(self.model.device, dtype) for k, v in state.items()})
        try:
            yield self
        finally:
            set_peft_model_state_dict(self.model, saved)

    def parameters(self, group: str | Callable[[str], bool] = "lora", scope: str = "lora") -> list[str]:
        if scope not in ("lora", "all"):
            raise ValueError(f"unknown scope {scope!r}")
        if scope == "all" and not callable(group):
            raise ValueError('scope="all" needs a predicate: naming every base weight of a model is never what is meant')
        names = [n for n, p in self.model.named_parameters() if scope == "all" or "lora_" in n]
        if callable(group):
            return [n for n in names if group(n)]
        if group == "lora":
            return names
        if group in ("lora_A", "lora_B"):
            return [n for n in names if group in n]
        if group in ("last_lora_B", "first_lora_B"):
            b = [n for n in names if "lora_B" in n]
            layer = lambda n: next((int(t) for t in n.split(".") if t.isdigit()), -1)   # noqa: E731
            pick = max(map(layer, b)) if group == "last_lora_B" else min(map(layer, b))
            return [n for n in b if layer(n) == pick]
        raise ValueError(f"unknown parameter group {group!r}")

    def layout(self, group: str | Callable[[str], bool] = "lora", scope: str = "lora") -> list[tuple[str, tuple[int, ...]]]:
        """(PEFT state-dict key, shape) of each parameter of a group, in the order per_sample_gradients
        concatenates them. Lets a plugin map a flat gradient back onto a LoRA state dict. Base weights
        (scope="all") keep the model's own parameter name."""
        names = set(self.parameters(group, scope))
        adapter = getattr(self.model, "active_adapter", "default")
        return [(n.replace(f".{adapter}.", ".").replace(f".{adapter}", "") if "lora_" in n else n, tuple(p.shape))
                for n, p in self.model.named_parameters() if n in names]

    def tokens(self, samples: Sequence) -> list[list[str]]:
        return [self.tok.convert_ids_to_tokens(ids) for ids, _ in self._encode(samples)]

    def _token_losses(self, logits, labels) -> torch.Tensor:
        """Per-sample mean cross-entropy over the labelled positions (next-token prediction)."""
        lp = torch.log_softmax(logits[:, :-1].float(), dim=-1)
        tgt = labels[:, 1:]
        keep = tgt != -100
        nll = -lp.gather(-1, tgt.clamp_min(0).unsqueeze(-1)).squeeze(-1) * keep
        return nll.sum(1) / keep.sum(1).clamp_min(1)

    def losses(self, samples: Sequence) -> list[float]:
        rows, out = self._encode(samples), []
        with self._borrowed():
            for i in range(0, len(rows), self.batch):
                ids, mask, labels = self._batch(rows[i:i + self.batch])
                out += self._token_losses(self.model(input_ids=ids, attention_mask=mask).logits, labels).tolist()
        self.cost["forward_samples"] += len(rows)
        return out

    def hidden(self, samples: Sequence, layer: int = -1, pool: str = "last"):
        rows, out = self._encode(samples), []
        with self._borrowed():
            for i in range(0, len(rows), self.batch):
                ids, mask, _ = self._batch(rows[i:i + self.batch])
                h = self.model(input_ids=ids, attention_mask=mask, output_hidden_states=True).hidden_states[layer].float()
                out.append(_pool(h, mask, pool))
        self.cost["forward_samples"] += len(rows)
        return _join(out, pool) if out else torch.zeros(0, 0)

    def activations(self, samples: Sequence, select: Callable[[str], bool], pool: str = "mean", what: str = "output") -> dict:
        if what not in ("output", "input"):
            raise ValueError(f"unknown side of a module {what!r}")
        rows, got, hooks = self._encode(samples), {}, []
        current = {}
        take = (lambda i, o: o[0] if isinstance(o, tuple) else o) if what == "output" else (lambda i, o: i[0])
        for name, module in self.model.named_modules():
            if name and select(name):
                hooks.append(module.register_forward_hook(
                    lambda m, i, o, name=name: current.__setitem__(name, take(i, o).detach())))
        try:
            with self._borrowed():
                for i in range(0, len(rows), self.batch):
                    ids, mask, _ = self._batch(rows[i:i + self.batch])
                    current.clear()
                    self.model(input_ids=ids, attention_mask=mask)
                    for name, act in current.items():
                        if act.dim() == 3 and act.shape[:2] == ids.shape:
                            got.setdefault(name, []).append(_pool(act.float(), mask, pool))
        finally:
            for h in hooks:
                h.remove()
        self.cost["forward_samples"] += len(rows)
        return {n: _join(v, pool) for n, v in got.items()}

    def per_sample_gradients(self, samples: Sequence, group: str | Callable[[str], bool] = "last_lora_B", scope: str = "lora",
                             reduce: Callable | None = None) -> torch.Tensor:
        wanted = set(self.parameters(group, scope))
        names = [n for n, _ in self.model.named_parameters() if n in wanted]
        params = [p for n, p in self.model.named_parameters() if n in wanted]
        if not params:
            raise LookupError(f"no parameters in group {group!r} (scope {scope!r})")
        frozen = [p for p in params if not p.requires_grad]
        for p in frozen:
            p.requires_grad_(True)
        rows, out = self._encode(samples), []
        try:
            with self._borrowed(grad=True):
                for row in rows:
                    ids, mask, labels = self._batch([row])
                    loss = self._token_losses(self.model(input_ids=ids, attention_mask=mask).logits, labels)[0]
                    grads = [g if g is not None else torch.zeros_like(p)
                             for g, p in zip(torch.autograd.grad(loss, params, allow_unused=True), params)]
                    out.append(torch.cat([g.flatten().float().cpu() for g in grads]) if reduce is None
                               else reduce(dict(zip(names, grads))).detach().flatten().float().cpu())
        finally:
            for p in frozen:
                p.requires_grad_(False)
        self.cost["forward_samples"] += len(rows)
        self.cost["backward_samples"] += len(rows)
        return torch.stack(out) if out else torch.zeros(0, sum(p.numel() for p in params))

    def logprob(self, prompts: Sequence[str], targets: Sequence[str]) -> list[float]:
        with self._borrowed():
            out = mean_target_logp(self.model, self.tok, list(prompts), list(targets), self.batch)
        self.cost["forward_samples"] += len(prompts)
        return out

    def generate(self, prompts: Sequence[str], max_new_tokens: int = 32) -> list[str]:
        out = []
        pad = self.tok.pad_token_id if self.tok.pad_token_id is not None else self.tok.eos_token_id
        with self._borrowed():
            for p in prompts:
                ids = torch.tensor([self.tok(p, add_special_tokens=False)["input_ids"]], device=self.model.device)
                gen = self.model.generate(input_ids=ids, attention_mask=torch.ones_like(ids), max_new_tokens=max_new_tokens,
                                          do_sample=False, pad_token_id=pad)
                new = gen[0, ids.shape[1]:]
                self.cost["generated_tokens"] += int(new.numel())
                out.append(self.tok.decode(new, skip_special_tokens=True))
        self.cost["forward_samples"] += len(prompts)
        return out


def _join(parts: list, pool: str):
    """Batches of pooled vectors become one (n, d) tensor; unpooled ones stay a list with one entry per sample."""
    return [t for part in parts for t in part] if pool == "none" else torch.cat(parts)


def _pool(h: torch.Tensor, mask: torch.Tensor, pool: str):
    if pool == "none":                                      # per sample, its own tokens only (padding is on the right)
        return [h[k, : int(mask[k].sum())].cpu() for k in range(h.shape[0])]
    if pool == "max":
        return h.masked_fill(mask.unsqueeze(-1) == 0, float("-inf")).amax(1).cpu()
    h = _pool_vector(h, mask, pool)
    return h.cpu()


def _pool_vector(h: torch.Tensor, mask: torch.Tensor, pool: str) -> torch.Tensor:
    if pool == "last":
        idx = mask.sum(1).clamp_min(1) - 1
        return h[torch.arange(h.shape[0], device=h.device), idx]
    if pool == "mean":
        m = mask.unsqueeze(-1).to(h.dtype)
        return (h * m).sum(1) / m.sum(1).clamp_min(1)
    raise ValueError(f"unknown pooling {pool!r}")
