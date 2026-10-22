#!/usr/bin/env python3
"""有界只读切换边界取证；不读取凭据、进程参数或环境，不修改锁和事务。"""
import json
import os
from pathlib import Path
import stat
import sys

ROOT = Path('/home/ecs-user/dotfiles-bmad-solo')
sys.path.insert(0, str(ROOT / 'scripts'))
from asset_safety import AssetError, checked_path, require_task_cleanup, snapshot

HOME_ROOT = ROOT.parent
SANDBOX = ROOT / 'tests/roo_distribution/sandbox-gitops-i_9g9a7n'
WATCHED = (
    HOME_ROOT / '.gemini/config/plugins/bmad-suite',
    HOME_ROOT / '.roo/rules',
    HOME_ROOT / '.roo/rules-ana-architect',
    HOME_ROOT / '.roo/rules-bmad-engineer',
    HOME_ROOT / '.gemini/config/rules',
    HOME_ROOT / '.antigravity-ide-server/data/User/globalStorage/rooveterinaryinc.roo-cline/settings/custom_modes.yaml',
    ROOT / 'bmralph-suite-v5',
    SANDBOX,
)


def bounded_read(path, budget):
    with open(path, 'rb') as stream:
        data = stream.read(budget + 1)
    if len(data) > budget:
        raise AssetError('只读取证超过预算：' + str(path))
    return data


def relevant(value):
    value = value.removesuffix(' (deleted)')
    return any(value == str(path) or value.startswith(str(path) + '/') for path in WATCHED)


def main():
    errors, references = [], []
    state = checked_path(SANDBOX / 'deployment/.bmad-solo-deployment')
    journal = state / 'transaction-6c00aaa8d5324d1bb057c143448f7e64/transaction.json'
    before = snapshot(journal)
    if before.content is None:
        raise AssetError('超时现场日志缺失；不能静默认定清理完成')
    record = json.loads(before.content)
    targets = record.get('targets')
    if not isinstance(targets, list) or len(targets) > 256:
        raise AssetError('超时事务目标非法或超预算')
    for item in targets:
        target = checked_path(Path(item['path']))
        if not target.is_relative_to(SANDBOX / 'deployment'):
            raise AssetError('超时事务包含沙箱外目标')
    locks = []
    for path in (HOME_ROOT / '.bmad-solo-deployment/deployment.lock', state / 'deployment.lock'):
        path = checked_path(path)
        info = path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise AssetError('边界锁不是单硬链接普通文件')
        require_task_cleanup(path)
        locks.append((path, info))
    kernel_before = bounded_read('/proc/locks', 65536)
    for line in kernel_before.decode('ascii').splitlines():
        for path, info in locks:
            key = f'{os.major(info.st_dev):02x}:{os.minor(info.st_dev):02x}:{info.st_ino}'
            if key in line.split():
                errors.append('目标锁存在内核持锁记录：' + str(path))
    processes = 0
    for entry in sorted(Path('/proc').iterdir()):
        if not entry.name.isdigit():
            continue
        try:
            if entry.stat().st_uid != os.getuid():
                continue
            processes += 1
            if processes > 128:
                raise AssetError('同账号进程超过 128 项预算')
            for name in ('cwd', 'exe'):
                try:
                    value = os.readlink(entry / name)
                    if relevant(value):
                        references.append({'pid': int(entry.name), 'kind': name, 'path': value})
                except FileNotFoundError:
                    pass
            descriptors = list((entry / 'fd').iterdir())
            if len(descriptors) > 4096:
                raise AssetError('单进程描述符超过预算')
            for descriptor in descriptors:
                try:
                    value = os.readlink(descriptor)
                    if relevant(value):
                        references.append({'pid': int(entry.name), 'kind': 'fd', 'path': value})
                except FileNotFoundError:
                    pass
            for line in bounded_read(entry / 'maps', 2097152).decode('utf-8', errors='replace').splitlines():
                parts = line.split(None, 5)
                if len(parts) == 6 and relevant(parts[5]):
                    references.append({'pid': int(entry.name), 'kind': 'maps', 'path': parts[5]})
        except FileNotFoundError:
            continue
        except (OSError, AssetError) as exc:
            errors.append(f'进程 {entry.name} 证据不足：{type(exc).__name__}')
    if snapshot(journal) != before:
        errors.append('超时事务日志在观察期间变化')
    for path, info in locks:
        after = checked_path(path).stat()
        if (info.st_dev, info.st_ino) != (after.st_dev, after.st_ino):
            errors.append('锁身份在观察期间变化：' + str(path))
    if references:
        errors.append('存在被观察的绑定资产或超时沙箱运行引用')
    result = {
        'sandbox_transaction_status': record.get('status'),
        'sandbox_targets': len(targets),
        'sandbox_targets_within_isolated_deployment': True,
        'sandbox_disposition': '现场保留，未恢复、未删除、不登记清理成功',
        'same_uid_processes_observed': processes,
        'references': references[:16],
        'reference_count': len(references),
        'errors': errors[:16],
        'error_count': len(errors),
        'scope': '同账号 cwd/exe/fd/maps、固定锁和清理记录的时点只读观测',
        'limitations': '不检查进程参数或环境；不能证明内存中规则卸载、观察后的无竞态、其他账号或宿主工具旁路受控',
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (AssetError, OSError, ValueError, KeyError, TypeError) as exc:
        print('切换边界证据不足：' + str(exc), file=sys.stderr)
        raise SystemExit(1)
