#!/usr/bin/env python3
"""只读核验受管资产；不创建锁、目录或日志，不宣称运行时已加载。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from asset_safety import AssetError, checked_path, snapshot
from deploy_managed import load_manifest, _unique_object
from managed_files import plan_files, validate_relative_path
from managed_modes import merge_modes


def inspect(root):
    root = checked_path(root)
    if not root.is_dir():
        raise AssetError("部署根目录不存在或不是目录")
    print(f"部署根目录：{root}")
    print("仅检查磁盘资产；未验证 Roo 运行时加载或权限行为。")
    state = checked_path(root / ".bmad-solo-deployment")
    manifest_path = state / "ownership.json"
    before = snapshot(manifest_path)
    if before.content is None:
        raise AssetError("缺少受管所有权清单，无法确认部署状态")
    manifest = load_manifest(before.content)
    errors = []
    observed = {manifest_path: before}
    file_paths = set(manifest["files"])
    mode_paths = set(manifest["modes"])
    if file_paths & mode_paths:
        raise AssetError("清单中的普通文件和模式目标重叠")

    for relative in sorted(file_paths | mode_paths):
        try:
            validate_relative_path(relative)
            path = checked_path(root / relative)
            if (path == state or path.is_relative_to(state)
                    or state.is_relative_to(path)):
                raise AssetError("受管目标与状态目录重叠")
            current = snapshot(path)
            observed[path] = current
            if relative in file_paths:
                # 复用所有权校验，仅计算，不调用部署或写入函数。
                plan_files(
                    {relative: current}, {},
                    {relative: manifest["files"][relative]}, uninstall=True,
                )
            else:
                merge_modes(
                    current.content, None, manifest["modes"][relative],
                    uninstall=True,
                )
            print(f"受管摘要匹配：{relative}")
        except (AssetError, OSError) as exc:
            errors.append(f"{relative}：{exc}")

    journals = sorted(state.glob("transaction-*"))
    for directory in journals:
        try:
            directory = checked_path(directory)
            if not directory.is_dir():
                raise AssetError("事务记录路径不是目录")
            path = directory / "transaction.json"
            record = snapshot(path)
            observed[path] = record
            if record.content is None:
                raise AssetError("事务准备未完成，缺少日志")
            data = json.loads(record.content, object_pairs_hook=_unique_object)
            if not isinstance(data, dict) or data.get("status") not in {
                "COMMITTED", "ROLLED_BACK"
            }:
                raise AssetError("事务未完成或恢复受阻，需对账")
        except (AssetError, OSError, ValueError, TypeError) as exc:
            errors.append(f"{directory.name}：{exc}")

    # 不创建只读诊断锁；复核观察期间的变动，但不声称整体原子快照。
    for path, expected in observed.items():
        try:
            if snapshot(path) != expected:
                raise AssetError("诊断期间内容发生变化，请重新核验")
        except (AssetError, OSError) as exc:
            errors.append(f"{path.relative_to(root)}：{exc}")
    if sorted(state.glob("transaction-*")) != journals:
        errors.append("诊断期间事务集合发生变化，请重新核验")
    for error in errors:
        print(f"状态异常：{error}", file=sys.stderr)
    if errors:
        return 1
    provenance_relative = '.gemini/config/plugins/bmad-suite/.manifest.json'
    if provenance_relative in file_paths:
        # 只使用已通过所有权摘要检查和末次复核的快照，不重新读取未校验内容。
        provenance_snapshot = observed[root / provenance_relative]
        provenance = json.loads(provenance_snapshot.content,
                                object_pairs_hook=_unique_object)
        if not isinstance(provenance, dict):
            raise AssetError('部署来源清单结构非法')
        expected_files = dict(manifest['files'])
        del expected_files[provenance_relative]
        if (type(provenance.get('schema_version')) is not int
                or provenance['schema_version'] != 1
                or provenance.get('managed_files') != expected_files
                or provenance.get('managed_modes') != manifest['modes']):
            raise AssetError('部署来源清单与所有权记录不一致')
        commit = provenance.get('source_commit')
        repository = provenance.get('source_repository')
        dirty = provenance.get('source_dirty')
        kind = provenance.get('source_kind')
        if kind == 'unversioned':
            if commit is not None or repository is not None or dirty is not None:
                raise AssetError('未版本化来源包含矛盾的版本信息')
            print('记录的部署来源：未版本化，提交及工作树状态未知。')
        else:
            if (kind not in {'worktree', 'commit_cache'}
                    or not isinstance(commit, str)
                    or len(commit) not in {40, 64}
                    or any(character not in '0123456789abcdef' for character in commit)
                    or not isinstance(repository, str) or not repository
                    or type(dirty) is not bool
                    or (kind == 'commit_cache' and dirty)):
                raise AssetError('部署来源版本信息非法')
            print(f'记录的来源仓库：{repository}')
            print(f'记录的来源提交：{commit}')
            print(f'记录的套件源差异状态：{"有差异" if dirty else "无差异"}')
    else:
        print('未记录受管部署来源清单；来源提交未知。')
    print(f"受管资产检查通过：{len(file_paths)} 个文件，{len(mode_paths)} 个模式目标。")
    print("未核验来源仓库当前状态；资产匹配不等于与当前工作树同步。")
    return 0


def main():
    parser = argparse.ArgumentParser(description="只读检查受管部署资产及事务状态")
    parser.add_argument("--root", required=True, type=Path)
    arguments = parser.parse_args()
    try:
        return inspect(arguments.root)
    except (AssetError, OSError, ValueError, TypeError) as exc:
        print(f"无法确认部署状态：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
