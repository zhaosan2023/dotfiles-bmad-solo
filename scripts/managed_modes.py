"""受管模式合并：保留第三方配置，拒绝未授权接管和用户修改冲突。

本模块只计算候选内容与所有权摘要，不写文件。
调用者负责全目标预检、锁、原字节备份、提交前复核及失败恢复。
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re

import yaml

from asset_safety import AssetError, parse_modes


@dataclass(frozen=True)
class ModeMerge:
    content: bytes
    owned: dict[str, str]


def mode_digest(mode: dict) -> str:
    """对模式语义生成摘要；不将 YAML 排版变化误判为模式修改。"""
    try:
        encoded = json.dumps(
            mode, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, RecursionError) as exc:
        raise AssetError("模式必须包含可序列化的有限 JSON 数据") from exc
    return hashlib.sha256(encoded).hexdigest()


def validate_ownership(owned: dict[str, str]) -> None:
    if not isinstance(owned, dict):
        raise AssetError("模式所有权记录必须为映射")
    for slug, digest in owned.items():
        if not isinstance(slug, str) or not slug.strip():
            raise AssetError("模式所有权标识非法")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise AssetError(f"模式所有权摘要非法：{slug}")


def merge_modes(
    destination: bytes | None,
    source: bytes | None,
    owned: dict[str, str],
    *,
    uninstall: bool = False,
    adopt: frozenset[str] = frozenset(),
) -> ModeMerge:
    """计算更新或卸载后的配置。

    destination 为 None 才表示目标缺失；已有空文件或损坏配置失败关闭。
    owned 必须来自经调用者验证的受管清单，不能从当前文件自动推断。
    adopt 是用户明确授权首次接管的模式标识集合，不适用于已受管冲突。
    卸载及源中移除模式时，仅删除摘要仍匹配的受管模式。
    """
    validate_ownership(owned)
    if not isinstance(adopt, (set, frozenset)) or any(
        not isinstance(slug, str) or not slug.strip() for slug in adopt
    ):
        raise AssetError("接管授权必须为明确的模式标识集合")
    if uninstall and adopt:
        raise AssetError("卸载不能同时请求首次接管")

    existing = {} if destination is None else parse_modes(destination)
    current_modes = existing.get("customModes", [])
    current = {mode["slug"]: mode for mode in current_modes}

    if uninstall:
        desired = {}
    else:
        if source is None:
            raise AssetError("部署缺少源模式配置")
        source_data = parse_modes(source)
        source_modes = source_data.get("customModes")
        if not isinstance(source_modes, list) or not source_modes:
            raise AssetError("源模式配置必须包含非空 customModes")
        desired = {mode["slug"]: mode for mode in source_modes}
        if set(source_data) != {"customModes"}:
            raise AssetError("源模式配置含有未定义分发语义的顶层字段")

    if not set(adopt).issubset(desired):
        raise AssetError("接管授权包含源中不存在的模式")

    # 在产生候选内容之前核验所有历史所有权，避免删除用户编辑。
    for slug, expected in owned.items():
        if slug not in current:
            raise AssetError(f"受管模式已缺失，需显式对账：{slug}")
        if mode_digest(current[slug]) != expected:
            raise AssetError(f"受管模式已被用户修改，拒绝覆盖或卸载：{slug}")

    for slug in desired:
        if slug in current and slug not in owned and slug not in adopt:
            raise AssetError(f"首次同标识接管需要明确授权：{slug}")

    new_owned = {slug: mode_digest(mode) for slug, mode in desired.items()}
    merged = []
    seen = set()
    for mode in current_modes:
        slug = mode["slug"]
        if slug in desired:
            merged.append(desired[slug])
            seen.add(slug)
        elif slug not in owned:
            merged.append(mode)
        # 已核验且源不再包含的受管模式不加入候选，第三方模式保留。
    for slug, mode in desired.items():
        if slug not in seen:
            merged.append(mode)

    result = dict(existing)
    if merged or "customModes" in existing or not uninstall:
        result["customModes"] = merged

    # 幂等操作保留完整原字节，包括注释和排版。
    if destination is not None and result == existing:
        return ModeMerge(destination, new_owned)
    try:
        content = yaml.safe_dump(
            result, allow_unicode=True, sort_keys=False,
        ).encode("utf-8")
    except (yaml.YAMLError, RecursionError) as exc:
        raise AssetError("无法序列化候选模式配置") from exc
    parse_modes(content)
    return ModeMerge(content, new_owned)
