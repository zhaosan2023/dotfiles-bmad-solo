"""复用前序隔离夹具核验本次实际包装前缀，不启动控制器或模型。"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHECK = ROOT / "_bmad-output/scratch/phase5-detached-wrapper-check-20261018.py"
WRAPPER = ROOT / "_bmad-output/scratch/phase5-pi-detached-run-20261018-attempt3.sh"


def main():
    if Path.cwd().resolve() != ROOT:
        raise RuntimeError("工作目录不是授权工作区")
    spec = importlib.util.spec_from_file_location("phase5_wrapper_isolated_check", CHECK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.WRAPPER = WRAPPER
    return module.main()


if __name__ == "__main__":
    raise SystemExit(main())
