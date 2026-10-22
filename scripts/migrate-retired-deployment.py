#!/usr/bin/env python3
"""显式一次性 V5→V4 受管退役；不启动任务，不加载退役代码。

普通 bs.sh 和状态入口仍拒绝非 V4。仅复用既有所有权、锁、预检和
事务；旧清单必须一致且所有受管资产未被修改，未知资产继续保留。
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys

from asset_safety import (
    AssetError, checked_path, deployment_lock, require_task_cleanup,
    require_unchanged, snapshot, validate_inherited_deployment_lock,
)
from deploy_managed import deploy, load_manifest
from deployment_preflight import inspect_migration
from deployment_provenance import MANIFEST_TARGET, build_manifest
from deployment_source import collect_source, verify_source
from suite_versions import select_source


def inspect_retired(root):
    # 加载仓库现有只读状态检查器；不导入目标镜像或旧源码。
    path = Path(__file__).with_name('deployment-status.py')
    specification = importlib.util.spec_from_file_location('_retirement_status', path)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    result = module.inspect(root, active_suite=True, retired_from='v5')
    if result != 'v5':
        raise AssetError('退役迁移只接受已核验 V5；当前身份不符或已迁移')


def migrate(root, repository, *, preflight=False, mode_targets=()):
    root = checked_path(root)
    repository = checked_path(repository)
    state = checked_path(root / '.bmad-solo-deployment')
    lock = checked_path(state / 'deployment.lock')
    if snapshot(lock).content is None:
        raise AssetError('退役迁移需要现有受管锁；不创建或补造旧部署状态')
    ownership_path = state / 'ownership.json'
    provenance_path = root / MANIFEST_TARGET
    ownership_before = snapshot(ownership_path)
    provenance_before = snapshot(provenance_path)
    if ownership_before.content is None or provenance_before.content is None:
        raise AssetError('退役迁移缺少受管所有权或来源清单')
    inspect_retired(root)
    require_task_cleanup(lock)
    old = load_manifest(ownership_before.content)
    # 默认只绑定历史所有权中的实际 IDE 目标，不发现新的 IDE 或扩展范围。
    historical = tuple(sorted(old['modes']))
    if not historical:
        raise AssetError('缺少历史受管 IDE 模式目标；不能宣称完整宿主切换')
    selected = tuple(mode_targets) if mode_targets else historical
    if len(set(selected)) != len(selected) or set(selected) != set(historical):
        raise AssetError('退役迁移必须精确覆盖历史受管模式目标；不扩大或静默遗漏')
    source = select_source(repository, 'v4')
    files, modes, sources = collect_source(source, selected)
    files[MANIFEST_TARGET] = build_manifest(
        source, sources, files, modes, repository=repository,
    )
    for relative in (*files, *modes, '.bmad-solo-deployment'):
        target = checked_path(root / relative)
        if (target == source or target.is_relative_to(source)
                or source.is_relative_to(target)):
            raise AssetError(f'部署目标与 V4 套件源重叠：{relative}')
    report = inspect_migration(root, state, files, modes)
    report.print()
    if report.errors or report.adopt_files or report.adopt_modes:
        raise AssetError('迁移预检有阻塞或未授权接管；未执行写入')
    require_unchanged(ownership_path, ownership_before)
    require_unchanged(provenance_path, provenance_before)
    verify_source(source, sources)
    if preflight:
        print('V5→V4 只读退役预检通过；未创建锁、事务或任务，未验证宿主加载。')
        return None
    # 同一现有排他锁覆盖旧身份复核和既有事务；普通入口不增加绕过分支。
    with deployment_lock(lock, create=False) as descriptor:
        validate_inherited_deployment_lock(lock, descriptor)
        require_unchanged(ownership_path, ownership_before)
        require_unchanged(provenance_path, provenance_before)
        inspect_retired(root)
        verify_source(source, sources)
        outcome = deploy(root, state, files, modes, inherited_lock_fd=descriptor)
    if outcome is None:
        raise AssetError('退役迁移未产生预期事务；不能登记切换完成')
    print(f'V5→V4 受管退役事务完成：{outcome}')
    print('仅证明磁盘分发；必须另行取得新 V4 宿主会话及交互证据。')
    return outcome


def main(argv=None):
    parser = argparse.ArgumentParser(description='显式一次性受管 V5→V4 退役迁移')
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--repository', required=True, type=Path)
    parser.add_argument('--from', dest='retired_from', required=True, choices=('v5',))
    parser.add_argument('--to', dest='target_suite', required=True, choices=('v4',))
    parser.add_argument('--mode-target', action='append', default=[])
    parser.add_argument('--preflight', action='store_true')
    arguments = parser.parse_args(argv)
    try:
        migrate(arguments.root, arguments.repository, preflight=arguments.preflight,
                mode_targets=tuple(arguments.mode_target))
        return 0
    except (AssetError, OSError, ValueError) as exc:
        print(f'受管退役迁移阻塞：{exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
