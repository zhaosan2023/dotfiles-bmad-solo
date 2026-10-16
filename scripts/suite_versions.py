"""显式套件身份与来源映射；不选择默认版本、不写入或部署资产。"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import re
import sys

from asset_safety import AssetError, checked_path, snapshot


@dataclass(frozen=True)
class SuiteSpec:
    major_version: str
    suite_id: str
    source_path: str

    def cache_name(self, commit: str) -> str:
        if not isinstance(commit, str) or not re.fullmatch(
            r"[0-9a-f]{40}|[0-9a-f]{64}", commit
        ):
            raise AssetError("缓存需要实际提交标识")
        prefix = "" if self.major_version == "v4" else self.major_version + "-"
        return prefix + "commit-" + commit


SUITES = {
    "v3": SuiteSpec("v3", "bmad-suite-v3", "bmad-suite-v3"),
    "v4": SuiteSpec("v4", "bmad-suite-v4", "bmad-suite-v4"),
    "v5": SuiteSpec("v5", "bmralph-suite-v5", "bmralph-suite-v5"),
}
IDENTITY_FILE = "suite.json"


def suite_spec(version: str) -> SuiteSpec:
    if not isinstance(version, str) or version not in SUITES:
        raise AssetError("套件版本必须显式选择 v3、v4 或 v5")
    return SUITES[version]


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise AssetError(f"套件身份 JSON 重复键：{key}")
        result[key] = value
    return result


def read_object(path: Path) -> dict:
    value = snapshot(checked_path(path))
    if value.content is None:
        raise AssetError(f"套件身份资产缺失：{path.name}")
    try:
        data = json.loads(value.content, object_pairs_hook=unique_object)
    except (ValueError, UnicodeError) as exc:
        raise AssetError(f"套件身份资产损坏：{path.name}") from exc
    if not isinstance(data, dict):
        raise AssetError(f"套件身份资产必须为对象：{path.name}")
    return data


def validate_identity(source: Path, spec: SuiteSpec) -> SuiteSpec:
    """核验指定目录的身份；V4 旧格式兼容，不改写旧套件。"""
    if suite_spec(spec.major_version) != spec:
        raise AssetError("套件映射不是受支持的固定映射")
    source = checked_path(source)
    if not source.is_dir() or source.name != spec.source_path:
        raise AssetError("所选套件源缺失或目录与显式身份不符；不回退")
    plugin = read_object(source / "plugin.json")
    if plugin.get("name") != "bmad-suite":
        raise AssetError("套件插件槽位不符合单一活动槽位契约")
    identity_path = source / IDENTITY_FILE
    identity_snapshot = snapshot(checked_path(identity_path))
    if identity_snapshot.content is None:
        if spec.major_version == "v5":
            raise AssetError("V5 必须包含可核验的独立套件身份")
        return spec
    identity = read_object(identity_path)
    expected = {
        "schema_version": 1,
        "suite_id": spec.suite_id,
        "major_version": spec.major_version,
        "source_path": spec.source_path,
    }
    if (type(identity.get("schema_version")) is not int
            or identity != expected):
        raise AssetError("套件身份字段与所选版本不一致")
    if spec.major_version == "v5" and plugin.get("displayName") != "BMRalph V5":
        raise AssetError("V5 插件展示名称必须明确标识版本")
    return spec


def select_source(repository: Path, version: str) -> Path:
    spec = suite_spec(version)
    repository = checked_path(repository)
    if not repository.is_dir():
        raise AssetError("来源仓库根目录不存在")
    source = checked_path(repository / spec.source_path)
    validate_identity(source, spec)
    return source


def validate_tag_hint(tag: str, spec: SuiteSpec) -> None:
    """标签仅作线索；匹配已知主版本时不得与显式选择冲突。"""
    if not isinstance(tag, str) or not tag:
        raise AssetError("标签不能为空")
    match = re.match(r"^v?(\d+)(?:[.\-]|$)", tag)
    if match and "v" + match.group(1) != spec.major_version:
        raise AssetError("标签主版本线索与显式套件选择冲突")


def main(argv=None):
    parser = argparse.ArgumentParser(description="只读解析显式套件映射和来源身份")
    parser.add_argument("--version", required=True, choices=tuple(SUITES))
    parser.add_argument("--repo", type=Path,
                        help="提供时核验物理来源；省略只返回固定目录映射")
    parser.add_argument("--tag", help="核验标签主版本线索，不创建缓存")
    arguments = parser.parse_args(argv)
    try:
        spec = suite_spec(arguments.version)
        if arguments.tag is not None:
            validate_tag_hint(arguments.tag, spec)
        if arguments.repo is None:
            print(spec.source_path)
        else:
            print(select_source(arguments.repo, arguments.version))
        return 0
    except (AssetError, OSError, ValueError) as exc:
        print(f"套件选择失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
