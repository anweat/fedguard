"""Cross-checks between the two sides' records of the same run.

Neither side is taken as the reference: a mismatch says the two disagree about an object, which is a
fact about the transport or about one of the parties, not a detection result.
"""
from __future__ import annotations

from pathlib import Path

from fedguard.recorder.store import Recorder


def compare_sides(root: str | Path, run_id: str) -> list[dict]:
    """For every round and client recorded on both sides, compare content hashes of
    (server `base`, client `received`) and (server `client_<id>`, client `local`).

    Returns one entry per comparison: {"round", "client", "object", "match"}. An object missing on
    either side is skipped, since a client that kept no record proves nothing either way.
    """
    server = Recorder(root, run_id)
    out = []
    clients_dir = server.dir / "clients"
    for cdir in sorted(clients_dir.iterdir()) if clients_dir.exists() else []:
        client = Recorder(root, run_id, scope=cdir.name)
        for t in client.rounds():
            spath, cpath = server.dir / f"round_{t:04d}" / "round.json", client.dir / f"round_{t:04d}" / "round.json"
            if not (spath.exists() and cpath.exists()):
                continue
            so, co = server.load_round(t).get("objects", {}), client.load_round(t).get("objects", {})
            sent = "upload" if "upload" in co else "local"     # "upload" exists when a client-side transform was applied
            base = f"sent_{cdir.name}" if f"sent_{cdir.name}" in so else "base"    # this client was sent its own model
            for s_name, c_name, label in ((base, "received", "broadcast"), (f"client_{cdir.name}", sent, "upload")):
                if s_name in so and c_name in co:
                    out.append({"round": t, "client": cdir.name, "object": label, "match": so[s_name] == co[c_name]})
    return out
