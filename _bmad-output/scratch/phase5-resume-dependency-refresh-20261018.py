"""复用既有类型化验证和程序刷新入口，继续当前断点。

只调整本轮已观察到的变更白名单及新回执目录，不修改历史草稿、
验证选择、测试下限或控制器。每次仅验证一个组；全部通过后才能
刷新七项已完成任务的证据引用。HEADLESS 保持未完成，不启动模型。
未覆盖的阶段协调使用平台真实回执，计划清单仍是唯一任务进度。
"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "_bmad-output/scratch/phase5-dependency-refresh-20261018-attempt3.py"
OUT = "_bmad-output/verification/phase5-resume-20261018"
ALLOWED_CHANGES = {
    "bmralph-suite-v5/scripts/bmad_agent_backend.py",
    "bmralph-suite-v5/tests/test_pi_activation.py",
    "bmralph-suite-v5/tests/test_pi_retry.py",
    "bmralph-suite-v5/tests/test_pi_transport_diagnostics.py",
}


def main():
    if Path.cwd().resolve() != ROOT:
        raise RuntimeError("工作目录不是授权工作区")
    spec = importlib.util.spec_from_file_location("phase5_resume_dependency_refresh", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError("既有受限刷新入口不可加载；不替换接口")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.OUT = OUT
    module.ALLOWED_CHANGES = ALLOWED_CHANGES
    return module.main()


if __name__ == "__main__":
    raise SystemExit(main())
