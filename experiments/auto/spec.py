"""Experiment specification for the automatic matrix runner.

An Exp is one federated training run. Everything the planner can vary is a field here; everything
else is fixed by the base settings below (one factor at a time).
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NUM_CLIENTS = 10

# Fixed settings for the 0.5B preview matrix (decided after P2, 2026-10-02).
BASE = {
    "lora_r": 16, "lora_alpha": 32, "lr": 1e-4, "batch_size": 4, "seq_length": 512, "max_steps": 5,
    "num_data_per_client": 300, "template": "chat",
}


@dataclass(frozen=True)
class Exp:
    role: str = "c0"            # c0: no attack; c1: malicious clients train on harmful data
    split: str = "d0.5"         # iid | d<alpha>
    sample: int = NUM_CLIENTS   # clients per round (S1 participation)
    n_mal: int = 0              # number of malicious clients (T5)
    mix: float = 1.0            # share of harmful samples in each malicious client's data (T6)
    seed: int = 1
    rounds: int = 20
    model: str = "0.5b"

    def __post_init__(self):
        if self.role == "c0" and self.n_mal:
            raise ValueError("c0 has no malicious clients")
        if self.role == "c1" and not 1 <= self.n_mal < NUM_CLIENTS:
            raise ValueError("c1 needs 1..9 malicious clients")

    @property
    def id(self) -> str:
        atk = f"m{self.n_mal}x{self.mix:g}" if self.role == "c1" else "benign"
        return f"{self.role}_{self.split}_k{self.sample}_{atk}_r{self.rounds}_{self.model}_s{self.seed}"

    @property
    def system(self) -> tuple:
        """System configuration; runs sharing it are comparable and share a C0 calibration."""
        return (self.split, self.sample, self.rounds, self.model)

    @property
    def level(self) -> tuple:
        """Attack level within a system configuration."""
        return (self.n_mal, self.mix)

    def with_(self, **kw) -> "Exp":
        return dataclasses.replace(self, **kw)

    def baseline(self, seed: int) -> "Exp":
        return Exp("c0", self.split, self.sample, 0, 1.0, seed, self.rounds, self.model)

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    def train_args(self, model_path: str, out_root: Path, cuda: bool) -> list[str]:
        b = BASE
        args = [
            "--model_name_or_path", model_path, "--use_peft", "--peft_lora_r", str(b["lora_r"]),
            "--peft_lora_alpha", str(b["lora_alpha"]), "--gradient_checkpointing", "False",
            "--learning_rate", str(b["lr"]), "--batch_size", str(b["batch_size"]), "--gradient_accumulation_steps", "1",
            "--seq_length", str(b["seq_length"]), "--max_steps", str(b["max_steps"]), "--num_rounds", str(self.rounds),
            "--sample_clients", str(self.sample), "--fed_alg", "fedavg", "--template", "alpaca", "--logging_steps", "5",
            "--num_data_per_client", str(b["num_data_per_client"]),
            "--local_data_dir", str(ROOT / "external/FedLLM-Attack/gen_data"),
            "--benign_dataset_names", "_", "--benign_num_clients", "0",
            "--malicious_dataset_names", "_", "--malicious_num_clients", "0",
            "--exp_benign", "dolly", "--exp_benign_clients", str(NUM_CLIENTS - self.n_mal),
            "--exp_pool_per_client", str(b["num_data_per_client"]), "--exp_template", b["template"],
            "--guard_modules", "effect_stats,factor_stats,compliance_probe", "--guard_probe_template", b["template"],
            "--guard_probe_n", "32", "--guard_record", str(out_root / "records"),
            "--seed", str(self.seed), "--output_dir", str(out_root / "train" / self.id),
        ]
        if self.split == "iid":
            args += ["--exp_split", "iid"]
        else:
            args += ["--exp_split", "dirichlet", "--exp_alpha", self.split[1:]]
        if self.role == "c1":
            args += ["--exp_malicious", "maliciousgen", "--exp_malicious_clients", str(self.n_mal),
                     "--exp_malicious_mix", str(self.mix)]
        args += ["--exp_precision", "bf16"] if cuda else ["--exp_pad_to", str(b["seq_length"])]
        if self.model != "0.5b":
            args += ["--exp_base_dtype", "bf16"]
        return args
