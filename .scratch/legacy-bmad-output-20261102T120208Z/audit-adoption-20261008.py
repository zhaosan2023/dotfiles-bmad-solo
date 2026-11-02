"""只读审查部署目标、首次接管清单与完整差异；不执行部署。"""
import difflib
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from asset_safety import Snapshot, parse_modes, require_unchanged, snapshot
from deploy_managed import load_manifest, prepare
from deployment_source import collect_source, verify_source
from deployment_provenance import MANIFEST_TARGET, build_manifest

ROOT = Path("/home/ecs-user")
SOURCE = REPO / "bmad-suite-v4"
TARGET = ".antigravity-ide-server/data/User/globalStorage/rooveterinaryinc.roo-cline/settings/custom_modes.yaml"
STATE = ROOT / ".bmad-solo-deployment"
ALLOWED_MODES = {"ana-architect", "bmad-engineer"}


def main():
    files, modes, sources = collect_source(SOURCE, (TARGET,))
    source_slugs = {item["slug"] for item in parse_modes(modes[TARGET])["customModes"]}
    if source_slugs != ALLOWED_MODES:
        raise RuntimeError("源模式集合超出本次明确授权范围")
    files[MANIFEST_TARGET] = build_manifest(
        SOURCE, sources, files, modes, repository=REPO,
    )
    ownership_before = snapshot(STATE / "ownership.json")
    owned = load_manifest(ownership_before.content)
    before = {path: snapshot(ROOT / path) for path in files}
    adopt_files = {
        path for path, value in before.items()
        if value.content is not None and path not in owned["files"]
    }
    mode_before = snapshot(ROOT / TARGET)
    existing = {} if mode_before.content is None else parse_modes(mode_before.content)
    existing_slugs = {item["slug"] for item in existing.get("customModes", [])}
    adopt_modes = {TARGET: (existing_slugs & ALLOWED_MODES) - set(owned["modes"].get(TARGET, {}))}
    print("首次接管文件清单：", flush=True)
    print(json.dumps(sorted(adopt_files), ensure_ascii=False, indent=2), flush=True)
    print("首次接管模式清单：", flush=True)
    print(json.dumps({key: sorted(value) for key, value in adopt_modes.items()}, ensure_ascii=False, indent=2), flush=True)
    changes = prepare(ROOT, STATE, files, modes, adopt_files=adopt_files, adopt_modes=adopt_modes)
    print("全部预检目标及差异：", flush=True)
    for change in changes:
        relative = change.path.relative_to(ROOT).as_posix()
        print(json.dumps({"path": relative, "before_sha256": change.before.digest,
                          "after_sha256": change.after.digest,
                          "before_mode": change.before.mode, "after_mode": change.after.mode,
                          "changed": change.before != change.after}, ensure_ascii=False), flush=True)
        if change.before.content != change.after.content:
            old = (change.before.content or b"").decode("utf-8")
            new = (change.after.content or b"").decode("utf-8")
            print("".join(difflib.unified_diff(old.splitlines(keepends=True), new.splitlines(keepends=True),
                                             fromfile="before/" + relative, tofile="after/" + relative)), flush=True)
        if relative == TARGET:
            merged = parse_modes(change.after.content)
            unrelated_before = [item for item in existing.get("customModes", []) if item["slug"] not in ALLOWED_MODES]
            unrelated_after = [item for item in merged.get("customModes", []) if item["slug"] not in ALLOWED_MODES]
            if unrelated_before != unrelated_after:
                raise RuntimeError("第三方模式未被完整保留")
            if {k: v for k, v in existing.items() if k != "customModes"} != {k: v for k, v in merged.items() if k != "customModes"}:
                raise RuntimeError("第三方顶层配置未被完整保留")
            print("第三方模式与顶层配置语义保留检查通过；修改后的 YAML 排版或注释不保证保留，原字节须由部署事务备份。", flush=True)
    verify_source(SOURCE, sources)
    require_unchanged(STATE / "ownership.json", ownership_before)
    for change in changes:
        require_unchanged(change.path, change.before)
    print("只读预检完成；未创建部署锁、备份或事务，未写入任何部署目标。", flush=True)


if __name__ == "__main__":
    main()
