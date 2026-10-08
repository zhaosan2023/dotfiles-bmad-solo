"""只读复核指定部署事务的备份、目标摘要及权限，不执行恢复或部署。"""
import hashlib
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))
from asset_safety import checked_path, require_unchanged, snapshot

ROOT = Path("/home/ecs-user")
JOURNAL = ROOT / ".bmad-solo-deployment/transaction-4f2bb72068ff4f95a692c03330e4654c/transaction.json"
MODE_TARGET = ROOT / ".antigravity-ide-server/data/User/globalStorage/rooveterinaryinc.roo-cline/settings/custom_modes.yaml"


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"日志存在重复键：{key}")
        result[key] = value
    return result


def main():
    original = snapshot(JOURNAL)
    require(original.content is not None, "事务日志缺失")
    record = json.loads(original.content, object_pairs_hook=unique_object)
    require(record.get("schema_version") == 1, "事务版本不匹配")
    require(record.get("status") == "COMMITTED", "事务未提交完成")
    targets = record.get("targets")
    require(isinstance(targets, list) and len(targets) == 49, "事务目标数量不匹配")
    seen = set()
    observed = []
    backup_count = 0
    changed_count = 0
    allowed_directories = (
        ROOT / ".gemini/config/plugins/bmad-suite",
        ROOT / ".gemini/config/rules",
        ROOT / ".roo/rules",
        ROOT / ".roo/rules-ana-architect",
        ROOT / ".roo/rules-bmad-engineer",
    )
    allowed_files = {MODE_TARGET, ROOT / ".bmad-solo-deployment/ownership.json"}
    for item in targets:
        path = checked_path(Path(item["path"]))
        require(path in allowed_files or any(path != base and path.is_relative_to(base) for base in allowed_directories), f"目标超出核验范围：{path}")
        require(path not in seen, f"重复目标：{path}")
        seen.add(path)
        require(item["status"] in {"APPLIED", "UNCHANGED"}, f"目标状态异常：{path}")
        current = snapshot(path)
        require(current.content is not None, f"部署目标缺失：{path}")
        require(current.digest == item["after_sha256"], f"目标摘要不匹配：{path}")
        require(current.mode == item["after_mode"], f"目标权限不匹配：{path}")
        observed.append((path, current))
        backup_name = item["backup"]
        if backup_name is None:
            require(item["before_sha256"] is None and item["before_mode"] is None, f"已有资产缺少备份：{path}")
        else:
            require(isinstance(backup_name, str) and Path(backup_name).name == backup_name and backup_name.endswith(".before"), "非法备份路径")
            backup_path = checked_path(JOURNAL.parent / backup_name)
            backup = snapshot(backup_path)
            require(backup.content is not None, f"备份缺失：{backup_path}")
            require(backup.digest == item["before_sha256"], f"备份摘要不匹配：{backup_path}")
            require(backup.mode == 0o600, f"备份权限不匹配：{backup_path}")
            require(type(item["before_mode"]) is int and 0 <= item["before_mode"] <= 0o7777, f"原权限记录非法：{path}")
            observed.append((backup_path, backup))
            backup_count += 1
        if item["status"] == "UNCHANGED":
            require((item["before_sha256"], item["before_mode"]) == (item["after_sha256"], item["after_mode"]), f"未变更记录矛盾：{path}")
        else:
            changed_count += 1
    require(MODE_TARGET in seen, "缺少指定模式目标")
    for path, expected in observed:
        require_unchanged(path, expected)
    require_unchanged(JOURNAL, original)
    print(f"PASS：{len(targets)} 个事务目标摘要与权限匹配，{backup_count} 份备份摘要及存储权限匹配，{changed_count} 项记录为已应用。")
    print(f"事务日志 SHA-256：{hashlib.sha256(original.content).hexdigest()}")
    print("原权限仅核验日志记录合法性；未执行恢复，未验证 Roo 加载、权限拒绝或生命周期行为。")
    print("核验为顺序读取与末次复核，不保证排除不遵守部署锁的外部并发写入。")


if __name__ == "__main__":
    main()
