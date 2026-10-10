#!/usr/bin/env python3
"""Run fedguard experiments on an AutoDL Pro container instance and switch it off afterwards.

Built on the earlier `gpumanager` package (model_spark/remotion_model), which wraps the documented
container-instance Pro API with a mutation gate. This script adds what an experiment needs around it:
code and data sync, environment setup, an unattended queue on the instance, a watchdog with a hard
time limit, result download, and power-off with confirmation.

    autodl_run.py check                      read-only: token usable? what instances exist?
    autodl_run.py plan  [spec options]       print the create request and the cost bound; calls nothing
    autodl_run.py up    [spec options] --approve "CREATE"            create an instance (starts billing)
    autodl_run.py up    --instance ID --approve "POWER ON ID"        or start an existing one
    autodl_run.py push | setup | start QUEUE | wait | pull           work on the instance over SSH
    autodl_run.py down  --approve "POWER OFF ID"                     stop it and wait until it is stopped
    autodl_run.py run QUEUE [spec options] --approve ...             all of the above in order

Money and safety
  - Nothing that costs money happens without --approve carrying the exact phrase for that action.
    `run` needs the phrase for the first step; it powers the instance off by itself at the end, on
    failure, and when --ttl-minutes is reached, and says so if it could not confirm the stop.
  - Every create needs --hourly-price (read it off the AutoDL page) and --budget; the request is refused
    locally when price x GPUs x TTL exceeds the budget. Disk and storage charges are not in that bound.
  - Release (deleting the instance and its disk) is not offered here at all.

Credentials
  - The developer token is read from the macOS Keychain item `autodl-developer-token` (or AUTODL_TOKEN)
    inside this process and sent only to api.autodl.com. It is never printed, logged or copied to the instance.
        security add-generic-password -a "$USER" -s autodl-developer-token -w
  - SSH uses your key pair, never the instance's root password: the public key is installed through the
    instance's start command. The API returns the root password and a Jupyter token; both are dropped
    from everything this script prints or stores.

State (instance id, SSH host and port, deadline) is kept in runs/autodl/state.json.
Checked against a live account on 2026-10-09: create, status and snapshot (as query-parameter GETs).
power-off and the status strings were checked the same day.
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "runs" / "autodl" / "state.json"
GPUMANAGER_SRC = Path(os.environ.get("GPUMANAGER_SRC", Path.home() / "codeproject/model_spark/remotion_model/src"))
KEYCHAIN_ITEM = "autodl-developer-token"
SECRET_FIELDS = {"root_password", "jupyter_token"}
REMOTE_ROOT = "/root/autodl-tmp/innovation"
RUNNING, STOPPED = {"running"}, {"shutdown"}      # seen live: running, shutting_down, shutdown


def die(msg: str) -> "None":
    sys.exit(f"autodl_run: {msg}")


def scrub(obj):
    """Drop credential fields from anything that came back from the API."""
    if isinstance(obj, dict):
        return {k: scrub(v) for k, v in obj.items() if k not in SECRET_FIELDS and k != "ssh_command"}
    return [scrub(v) for v in obj] if isinstance(obj, list) else obj


def token() -> str | None:
    if os.environ.get("AUTODL_TOKEN"):
        return os.environ["AUTODL_TOKEN"]
    r = subprocess.run(["security", "find-generic-password", "-a", os.environ.get("USER", ""), "-s", KEYCHAIN_ITEM, "-w"],
                       capture_output=True, text=True)
    return r.stdout.strip() or None


def manager(mutations: bool = False):
    if not GPUMANAGER_SRC.exists():
        die(f"gpumanager not found at {GPUMANAGER_SRC}; set GPUMANAGER_SRC")
    sys.path.insert(0, str(GPUMANAGER_SRC))
    from gpumanager import AutoDLClient, GPUManager, SafetyPolicy
    return GPUManager(AutoDLClient(token=token()), policy=SafetyPolicy(allow_mutations=mutations, allow_release=False))


def api_get(m, what: str, iid: str):
    """status / snapshot. The documentation shows these GETs with a JSON body; the live API rejects that
    (RequestParameterIsWrong) and takes the id as a query parameter."""
    r = m.client._checked("GET", f"/api/v1/dev/instance/pro/{what}?instance_uuid={iid}", None)
    return r.data


def load_state() -> dict:
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def save_state(**kw) -> dict:
    s = {**load_state(), **kw}
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(s, indent=1))
    return s


def instance_id(args) -> str:
    iid = getattr(args, "instance", None) or load_state().get("instance")
    if not iid:
        die("no instance: pass --instance or run `up` first")
    return iid


# ---------- SSH ----------
def ssh_base(s: dict, key: str) -> list[str]:
    return ["ssh", "-i", key, "-p", str(s["ssh_port"]), "-o", "IdentitiesOnly=yes", "-o", "PasswordAuthentication=no",
            "-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=15", "-o", "ServerAliveInterval=30",
            f"root@{s['ssh_host']}"]


def ssh(args, script: str, check: bool = True, capture: bool = False, timeout: float | None = None):
    s = load_state()
    if "ssh_host" not in s:
        die("no SSH endpoint recorded; run `up` first")
    try:
        r = subprocess.run(ssh_base(s, args.ssh_key) + ["bash", "-s"], input=script, text=True, capture_output=capture, timeout=timeout)
    except subprocess.TimeoutExpired:      # a stalled connection must not stall the caller (the watchdog polls through this)
        r = subprocess.CompletedProcess([], 255, "", "ssh timed out")
    if check and r.returncode != 0:
        die(f"remote command failed with status {r.returncode}" + (f": {r.stderr[-400:]}" if capture else ""))
    return r


def rsync(args, src: str, dst: str, extra: list[str]) -> None:
    s = load_state()
    e = " ".join(shlex.quote(x) for x in ssh_base(s, args.ssh_key)[:-1])
    cmd = ["rsync", "-az", "-e", e, *extra, src, dst]      # plain flags only: macOS ships an older rsync
    if subprocess.run(cmd).returncode != 0:
        die("rsync failed")


def remote(s: dict, path: str = "") -> str:
    return f"root@{s['ssh_host']}:{REMOTE_ROOT}/{path}"


# ---------- commands ----------
def cmd_check(args) -> None:
    m = manager()
    if not token():
        print(f"no developer token: store one with\n  security add-generic-password -a \"$USER\" -s {KEYCHAIN_ITEM} -w")
    p = m.probe()
    print(f"API reachable: {p.reachable}; token accepted: {p.authenticated} ({p.api_code})")
    if p.authenticated:
        data = scrub(m.list_instances())
        rows = data.get("list", []) if isinstance(data, dict) else data
        print(f"{len(rows)} instance(s):")
        for r in rows:
            print("  " + json.dumps({k: r.get(k) for k in ("uuid", "instance_uuid", "instance_name", "status", "sub_status",
                                                         "started_at", "stopped_at", "snapshot_gpu_alias_name", "payg_price")
                                     if k in r}, ensure_ascii=False))
    print(f"local state: {json.dumps(load_state(), ensure_ascii=False)}")


def spec_from(args):
    sys.path.insert(0, str(GPUMANAGER_SRC))
    from gpumanager import CreateSpec
    pub = Path(args.ssh_key + ".pub")
    if not pub.exists():
        die(f"public key {pub} not found; pass --ssh-key")
    key = pub.read_text().strip()
    start = ("mkdir -p /root/.ssh && chmod 700 /root/.ssh && "
             f"grep -qxF {shlex.quote(key)} /root/.ssh/authorized_keys 2>/dev/null || echo {shlex.quote(key)} >> /root/.ssh/authorized_keys; "
             "chmod 600 /root/.ssh/authorized_keys")
    return CreateSpec(gpu_spec_uuid=args.gpu_spec, image_uuid=args.image, cuda_v_from=args.cuda_code, req_gpu_amount=args.gpu_count,
                      expand_system_disk_by_gb=args.expand_disk_gb, instance_name=args.name, start_command=start,
                      max_runtime_minutes=args.ttl_minutes, hourly_price_yuan=args.hourly_price, budget_yuan=args.budget), start


def cmd_plan(args) -> None:
    spec, _ = spec_from(args)
    plan = manager().plan_create(spec)
    print(json.dumps({"request": plan.payload, "ttl_minutes": args.ttl_minutes, "hourly_price_yuan": args.hourly_price,
                      "compute_cost_bound_yuan": plan.estimated_max_cost_yuan, "budget_yuan": args.budget}, ensure_ascii=False, indent=1))
    print("nothing was sent. The bound covers compute only; disks and storage are charged separately.")


def wait_status(m, iid: str, want: set[str], minutes: float) -> str:
    deadline, last = time.time() + 60 * minutes, None
    while time.time() < deadline:
        try:
            st = str(api_get(m, "status", iid)).lower()
        except Exception as exc:                           # noqa: BLE001  a transient API error must not end the watch
            st = f"error: {exc}"
        if st != last:
            print(f"  status: {st}", flush=True)
            last = st
        if st in want:
            return st
        time.sleep(10)
    return last or "unknown"


def cmd_up(args) -> None:
    sys.path.insert(0, str(GPUMANAGER_SRC))
    from gpumanager import ActionApproval
    m = manager(mutations=True)
    spec, start = spec_from(args)
    if args.attach:                                        # the instance is already on: only look it up and test SSH
        iid = args.attach
    elif args.instance:
        iid = args.instance
        m._require_mutation(f"POWER ON {iid}", ActionApproval(args.approve or ""))
        # The API only starts instances with a GPU: payloads non_gpu, no_gpu, cpu and nogpu were all refused
        # ("不支持的启动模式", 2026-10-09). No-GPU mode has to be started from the console.
        m.client._checked("POST", "/api/v1/dev/instance/pro/power_on",
                          {"instance_uuid": iid, "payload": "gpu", "start_command": start})
        print(f"power-on requested for {iid}")
    else:
        if args.hourly_price is None or args.budget is None:
            die("creating an instance needs --hourly-price and --budget")
        iid = m.create(spec, ActionApproval(args.approve or ""))
        print(f"created {iid}")
    if not args.attach:
        save_state(instance=iid, started=time.time(), deadline=time.time() + 60 * args.ttl_minutes, ttl_minutes=args.ttl_minutes)
    if wait_status(m, iid, RUNNING, args.boot_minutes) not in RUNNING:
        die(f"{iid} did not reach running within {args.boot_minutes} min; it may still be billing. Check the console, "
            f"or stop it with: autodl_run.py down --approve \"POWER OFF {iid}\"")
    snap = api_get(m, "snapshot", iid)
    host, port = snap.get("proxy_host"), snap.get("ssh_port")
    price = snap.get("payg_price")
    if not host or not port:
        die("the instance is running but the API returned no SSH endpoint; fields: " + ", ".join(sorted(scrub(snap))))
    save_state(ssh_host=host, ssh_port=port, payg_price=price, gpu=snap.get("snapshot_gpu_alias_name"))
    print(f"running: {snap.get('snapshot_gpu_alias_name')} at {host}:{port}, listed price {price}")
    for _ in range(12):                                   # the start command installs the key shortly after boot
        if ssh(args, "echo ok", check=False, capture=True).returncode == 0:
            print("SSH with your key works")
            return
        time.sleep(10)
    die("SSH with your key does not work yet. The start command may not have run; the instance is still on.")


def cmd_push(args) -> None:
    s = load_state()
    ssh(args, f"mkdir -p {REMOTE_ROOT}")
    rsync(args, f"{ROOT}/", remote(s), ["--delete", "--exclude=external/", "--exclude=.git/", "--exclude=runs/", "--exclude=records/",
                                        "--exclude=envs/*/.venv/", "--exclude=survey/", "--exclude=output/", "--exclude=outputs/",
                                        "--exclude=tmp/", "--exclude=ppt_review/", "--exclude=defense-kit/", "--exclude=repro/",
                                        "--exclude=memory/", "--exclude=__pycache__/", "--exclude=*.pdf", "--exclude=*.pptx",
                                        "--exclude=*.docx", "--exclude=*.png", "--exclude=.DS_Store", "--exclude=*.egg-info/"])
    ssh(args, f"mkdir -p {REMOTE_ROOT}/external/FedLLM-Attack")
    rsync(args, f"{ROOT}/external/FedLLM-Attack/", remote(s, "external/FedLLM-Attack/"), ["--exclude=.git/", "--exclude=__pycache__/"])
    ssh(args, f"mkdir -p {REMOTE_ROOT}/external/OpenFedLLM")
    rsync(args, f"{ROOT}/external/OpenFedLLM/", remote(s, "external/OpenFedLLM/"), ["--exclude=.git/", "--exclude=__pycache__/", "--exclude=doc/"])
    print(f"code is at {REMOTE_ROOT}")


def cmd_setup(args) -> None:
    ssh(args, f"cd {REMOTE_ROOT} && FG_ENV={shlex.quote(args.env)} MODELS={shlex.quote(args.models)} bash experiments/autodl/remote_setup.sh")


def cmd_start(args) -> None:
    q = shlex.quote(args.queue)
    env = " ".join(shlex.quote(kv) for kv in [f"FG_ENV={args.env}", *args.set])
    ssh(args, f"cd {REMOTE_ROOT} && mkdir -p runs/autodl && rm -f runs/autodl/DONE runs/autodl/FAILED && "
              f"(nohup setsid env {env} bash experiments/autodl/remote_queue.sh {q} > runs/autodl/queue.out 2>&1 < /dev/null &); echo started {q}")
    save_state(queue=args.queue)


def cmd_wait(args) -> int:
    s = load_state()
    deadline = s.get("deadline", time.time() + 60 * args.ttl_minutes)
    last = ""
    while True:
        r = ssh(args, f"cd {REMOTE_ROOT}/runs/autodl 2>/dev/null && (ls DONE FAILED 2>/dev/null; tail -n 1 queue.log 2>/dev/null)",
                check=False, capture=True, timeout=45)
        out = (r.stdout or "").strip()
        if out and out != last:
            print("  " + out.replace("\n", " | "), flush=True)
            last = out
        if "DONE" in out.split():
            return 0
        if "FAILED" in out.split():
            print("the queue reported a failed stage")
            return 1
        if time.time() > deadline:
            print("time limit reached before the queue finished")
            return 2
        time.sleep(args.poll_seconds)


def cmd_pull(args) -> None:
    s = load_state()
    dest = ROOT / "runs" / "autodl" / (args.tag or time.strftime("%Y%m%d-%H%M%S"))
    dest.mkdir(parents=True, exist_ok=True)
    extra = [] if args.with_tensors else ["--exclude=*.safetensors", "--exclude=checkpoint-*/"]
    rsync(args, remote(s, "runs/"), f"{dest}/", extra)
    print(f"results are in {dest}" + ("" if args.with_tensors else " (without tensors; --with-tensors fetches them)"))


def cmd_down(args) -> None:
    sys.path.insert(0, str(GPUMANAGER_SRC))
    from gpumanager import ActionApproval
    iid = instance_id(args)
    m = manager(mutations=True)
    m.power_off(iid, ActionApproval(args.approve or ""))
    st = wait_status(m, iid, STOPPED, 5)
    if st in STOPPED:
        print(f"{iid} is stopped ({st}). Its disk is kept and may still be charged; releasing it is not done here.")
    else:
        print(f"WARNING: power-off was requested but the last status is '{st}'. Confirm in the AutoDL console that {iid} stopped.")


def cmd_run(args) -> None:
    iid = None
    try:
        cmd_up(args)
        iid = load_state()["instance"]
        cmd_push(args)
        cmd_setup(args)
        cmd_start(args)
        code = cmd_wait(args)
        cmd_pull(args)
        print({0: "queue finished", 1: "queue failed", 2: "stopped at the time limit"}[code])
    finally:
        iid = iid or load_state().get("instance")
        if iid and not args.keep_on:
            args.instance, args.approve = iid, f"POWER OFF {iid}"       # stopping what this run started needs no second phrase
            try:
                cmd_down(args)
            except Exception as exc:                                    # noqa: BLE001
                print(f"WARNING: could not stop {iid}: {exc}. Stop it in the AutoDL console.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p, spec=False):
        p.add_argument("--ssh-key", default=str(Path.home() / ".ssh/autodl_ed25519"), help="private key; <key>.pub is installed on the instance")
        p.add_argument("--instance")
        p.add_argument("--ttl-minutes", type=int, default=180)
        p.add_argument("--env", default="fl311", help="Python environment under envs/ used on the instance")
        p.add_argument("--set", action="append", default=[], metavar="NAME=VALUE", help="environment for the queue, e.g. SIZE=4B")
        if spec:
            p.add_argument("--gpu-spec", default="4090D")
            p.add_argument("--image", default="")
            p.add_argument("--cuda-code", type=int, default=118)
            p.add_argument("--gpu-count", type=int, default=1)
            p.add_argument("--expand-disk-gb", type=int, default=0)
            p.add_argument("--name", default="fedguard")
            p.add_argument("--hourly-price", type=float)
            p.add_argument("--budget", type=float)
            p.add_argument("--boot-minutes", type=float, default=10)
            p.add_argument("--approve", default="")
            p.add_argument("--attach", help="an instance that is already running: record its SSH endpoint, change nothing")
        return p

    common(sub.add_parser("check")).set_defaults(fn=cmd_check)
    common(sub.add_parser("plan"), spec=True).set_defaults(fn=cmd_plan)
    common(sub.add_parser("up"), spec=True).set_defaults(fn=cmd_up)
    common(sub.add_parser("push")).set_defaults(fn=cmd_push)
    p = common(sub.add_parser("setup")); p.add_argument("--models", default="Qwen/Qwen2.5-0.5B-Instruct"); p.set_defaults(fn=cmd_setup)
    p = common(sub.add_parser("start")); p.add_argument("queue"); p.set_defaults(fn=cmd_start)
    p = common(sub.add_parser("wait")); p.add_argument("--poll-seconds", type=int, default=60); p.set_defaults(fn=lambda a: sys.exit(cmd_wait(a)))
    p = common(sub.add_parser("pull")); p.add_argument("--tag"); p.add_argument("--with-tensors", action="store_true"); p.set_defaults(fn=cmd_pull)
    p = common(sub.add_parser("down")); p.add_argument("--approve", default=""); p.set_defaults(fn=cmd_down)
    p = common(sub.add_parser("run"), spec=True)
    p.add_argument("queue"); p.add_argument("--models", default="Qwen/Qwen2.5-0.5B-Instruct"); p.add_argument("--poll-seconds", type=int, default=60)
    p.add_argument("--tag"); p.add_argument("--with-tensors", action="store_true"); p.add_argument("--keep-on", action="store_true")
    p.set_defaults(fn=cmd_run)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
