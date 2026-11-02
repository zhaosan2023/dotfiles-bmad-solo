"""仅重验被后续集成夹具修改影响的离线证据；不启动真实模型。

复用原回执的完整测试选择，不降低断言。控制器对整个测试目录
取证，因此集成夹具修改使此前两组回执失效；不修改控制器规则。
每次只执行一个组；调用方须串行、进程级限时并封闭标准输入。
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "bmralph-suite-v5/scripts"))
import bmad_execution as execution
from bmad_supervisor import SupervisorError

OUT = "_bmad-output/verification/phase5-diagnostics-20261018"
GROUPS = {
    "diagnostics": ("test_pi_transport_diagnostics.py", OUT + "/run-f60a3c3729af4baa927e2db79fea2dc3.verdict.json"),
    "transport-regression": ("test_pi_transport.py", OUT + "/run-f464afe5e8f9446eaca66ce240842f36.verdict.json"),
}
ALLOWED_CHANGED_FILE = "bmralph-suite-v5/tests/test_pi_activation.py"


def require(condition):
    if not condition:
        raise SupervisorError("原契约或预期变更范围不匹配；禁止重验")


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("group", choices=tuple(GROUPS))
    args = parser.parse_args()
    phase = "CONTRACT_CHECK"
    try:
        require(Path.cwd().resolve() == ROOT)
        pattern, relative = GROUPS[args.group]
        old, _ = execution.read_receipt(ROOT, relative)
        result = old["result"]
        before = old["evidence_before"]
        require(old["status"] == "PASS" and before == old["evidence_after"])
        require(result["directory"] == "bmralph-suite-v5/tests"
                and result["pattern"] == pattern
                and result["minimum_tests"] == 12
                and len(result["required_tests"]) == 12)
        require(old["environment_manifest"]["relative_path"] == ".bmad-control/phase2-environment.json")
        fresh = execution.collect_evidence(ROOT, before["directory"], tuple(before["inputs"]))
        require(fresh["directory"] == before["directory"]
                and fresh["inputs"] == before["inputs"]
                and fresh["runner"] == before["runner"]
                and fresh["controller"] == before["controller"])
        files = before["files"]
        require(set(files) == set(fresh["files"]))
        changed = [path for path in files if files[path] != fresh["files"][path]]
        require(changed == [ALLOWED_CHANGED_FILE])
        phase = "TYPED_UNIT_TEST"
        verdict = execution.unit_test(
            workspace=ROOT, environment_file=".bmad-control/phase2-environment.json",
            directory=result["directory"], pattern=result["pattern"],
            minimum_tests=result["minimum_tests"],
            required_tests=tuple(result["required_tests"]), inputs=tuple(before["inputs"]),
            runtime_directory=OUT)
        process, _ = execution.read_receipt(ROOT, verdict["process_receipt"])
        tested = verdict["result"]
        print(json.dumps({
            "status": verdict["status"], "group": args.group,
            "prior_evidence_changed_files": changed,
            "tests_run": tested["tests_run"] if tested is not None else None,
            "returncode": process["returncode"], "cleanup_ok": process["cleanup_ok"],
            "timed_out": process["timed_out"], "cancelled": process["cancelled"],
            "verdict_file": verdict["verdict_path"],
            "process_receipt": verdict["process_receipt"],
            "runtime_started": False, "plan_saved": False,
            "evidence_boundary": "仅原选择契约的离线重验；不启动真实Pi、不连接真实网关、不加载凭据，不追认历史根因",
        }, ensure_ascii=False), flush=True)
        return 0 if verdict["status"] == "PASS" else 1
    except (OSError, ValueError, ImportError, KeyError, TypeError):
        print(json.dumps({"status": "BLOCKED", "phase": phase, "group": args.group,
                          "reason": "重验契约、变更范围或执行证据不足；不输出来源正文",
                          "runtime_started": False}, ensure_ascii=False), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
