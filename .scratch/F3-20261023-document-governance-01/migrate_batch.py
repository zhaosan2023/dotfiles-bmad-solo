#!/usr/bin/env python3
"""获准 F3 三文件批次：保全、引用重定位、分步迁移和保留目标的恢复。

仅本批次授权的文件复制与删除例外；不是通用控制器或执行级沙箱。
不改计划、README、规则、宿主或 Git；清单之外的内容只用于保护检查。
不保证跨文件原子性；任何失败保留已有保存结果，不自动清理或重试。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

ROOT = Path(__file__).absolute().parents[2]
BATCH = ".scratch/F3-20261023-document-governance-01"
MANIFEST = f"{BATCH}/preservation.json"
PLAN = "PLAN-20261022-document-test-governance-01.md"
PLAN_ID = "BMAD-DOCUMENT-TEST-GOVERNANCE-20261022-01"
FILES = (
    ("_bmad-output/adrs/ADR-20261022-document-test-governance-and-host-adaptation.md",
     "docs/adrs/ADR-20261022-document-test-governance-and-host-adaptation.md"),
    ("_bmad-output/adrs/ADR-20261023-cline-native-plan-act-and-backpressure.md",
     "docs/adrs/ADR-20261023-cline-native-plan-act-and-backpressure.md"),
    ("_bmad-output/analysis/ANALYSIS-20261022-document-test-governance.md",
     "docs/analysis/ANALYSIS-20261022-document-test-governance.md"),
)
MAPPING = dict(FILES)
LINK = re.compile(r"\]\(([^\s()]+)\)")
SUFFIX = re.compile(r"(:[0-9]+(?:-[0-9]+)?|#[^\s]*)$")


class BatchError(ValueError):
    """必须停止对应批次的边界或证据错误。"""


def require(condition, message):
    if not condition:
        raise BatchError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_path(root, relative):
    root = Path(root).absolute()
    path = Path(relative)
    require(not path.is_absolute() and '..' not in path.parts and bool(path.parts),
            f"非法项目路径：{relative}")
    require(root.is_dir() and not root.is_symlink(), "根目录无效或为链接")
    current = root
    for part in path.parts:
        current /= part
        require(not current.is_symlink(), f"拒绝链接：{current}")
    return current


def identity(info):
    return {
        'device': info.st_dev, 'inode': info.st_ino, 'size': info.st_size,
        'mode': stat.S_IMODE(info.st_mode), 'uid': info.st_uid, 'gid': info.st_gid,
        'mtime_ns': info.st_mtime_ns, 'ctime_ns': info.st_ctime_ns,
        'links': info.st_nlink,
    }


def read_regular(root, relative):
    path = safe_path(root, relative)
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode), f"非普通文件：{relative}")
        data = stream.read()
        after = os.fstat(stream.fileno())
    require(identity(before) == identity(after), f"读取中发生变化：{relative}")
    require(identity(path.lstat()) == identity(after), f"读取后身份变化：{relative}")
    return data, identity(after)


def exclusive_write(root, relative, data, mode):
    path = safe_path(root, relative)
    require(not path.exists(), f"目标已存在：{relative}")
    path.parent.mkdir(parents=True, exist_ok=True)
    safe_path(root, relative)
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                           mode), 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fchmod(stream.fileno(), mode)
        os.fsync(stream.fileno())
    saved, info = read_regular(root, relative)
    require(saved == data and info['mode'] == mode, f"保存复核失败：{relative}")


def link_target(root, document, href):
    if re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:', href) or href.startswith(('#', '//')):
        return None
    match = SUFFIX.search(href)
    suffix = match.group(0) if match else ''
    raw = href[:-len(suffix)] if suffix else href
    if not raw:
        return None
    require(not Path(raw).is_absolute(), f"拒绝绝对本地引用：{href}")
    target = Path(os.path.normpath(str(Path(document).parent / raw)))
    require('..' not in target.parts, f"引用越界：{href}")
    relative = target.as_posix()
    path = safe_path(root, relative)
    return relative, suffix, path.exists(), raw.endswith('/')


def references(root, document, data):
    result = []
    for match in LINK.finditer(data.decode('utf-8')):
        item = link_target(root, document, match.group(1))
        if item is not None:
            result.append({'href': match.group(1), 'target': item[0],
                           'suffix': item[1], 'existed': item[2], 'directory': item[3]})
    return result


def relocated(root, source, target, data):
    def replace(match):
        item = link_target(root, source, match.group(1))
        if item is None:
            return match.group(0)
        relative, suffix, _, directory = item
        destination = MAPPING.get(relative, relative)
        href = os.path.relpath(destination, str(Path(target).parent)).replace(os.sep, '/')
        if directory and not href.endswith('/'):
            href += '/'
        return f"]({href}{suffix})"
    return LINK.sub(replace, data.decode('utf-8')).encode('utf-8')


def protected_files(root):
    paths = set()
    for directory in ('_bmad-output/adrs', '_bmad-output/analysis'):
        path = safe_path(root, directory)
        if path.exists():
            paths.update(p.relative_to(root).as_posix() for p in path.iterdir()
                         if p.name.endswith('.md'))
    paths.update(('_bmad-output/pending_implementation_plan.md',
                  '_bmad-output/project-context.md'))
    result = {}
    for relative in sorted(paths - set(MAPPING)):
        path = safe_path(root, relative)
        if path.exists():
            data, info = read_regular(root, relative)
            result[relative] = {'sha256': digest(data), 'mode': info['mode']}
    return result


def verify_protected(root, record):
    for relative, expected in record['protected'].items():
        data, info = read_regular(root, relative)
        require(digest(data) == expected['sha256'] and info['mode'] == expected['mode'],
                f"范围外受保护内容变化：{relative}")


def preserve(root):
    root = Path(root).absolute()
    require(not safe_path(root, MANIFEST).exists(), "保全记录已存在，拒绝重复覆盖")
    collected = []
    directories = {}
    for source, target in FILES:
        require(not safe_path(root, target).exists(), f"迁移目标冲突：{target}")
        require(not safe_path(root, f'{BATCH}/{source}').exists(), f"保全目标冲突：{source}")
        data, info = read_regular(root, source)
        require(info['links'] == 1, f"源存在硬链接：{source}")
        collected.append((source, target, data, info))
        parent = Path(source).parent
        directories[parent.as_posix()] = identity(safe_path(root, parent).stat())
    record = {'schema': 1, 'plan_id': PLAN_ID, 'batch': BATCH, 'files': [],
              'original_directories': directories, 'protected': protected_files(root)}
    for source, target, data, info in collected:
        current, current_info = read_regular(root, source)
        require(current == data and current_info == info, f"保全前源变化：{source}")
        backup = f'{BATCH}/{source}'
        exclusive_write(root, backup, data, info['mode'])
        record['files'].append({'source': source, 'target': target, 'backup': backup,
                                'identity': info, 'sha256': digest(data),
                                'references': references(root, source, data)})
    for entry in record['files']:
        data, info = read_regular(root, entry['source'])
        require(digest(data) == entry['sha256'] and info == entry['identity'],
                f"保全后源变化：{entry['source']}")
    verify_protected(root, record)
    exclusive_write(root, MANIFEST,
                    (json.dumps(record, ensure_ascii=False, indent=2) + '\n').encode('utf-8'),
                    0o600)
    return {'action': 'preserve', 'files': len(FILES), 'source_preserved': True,
            'original_directory_context': True, 'provenance': MANIFEST}


def load_preserved(root):
    data, _ = read_regular(root, MANIFEST)
    record = json.loads(data)
    require(record.get('schema') == 1 and record.get('plan_id') == PLAN_ID
            and record.get('batch') == BATCH, "保全身份不匹配")
    require([(e['source'], e['target']) for e in record['files']] == list(FILES),
            "保全文件清单不匹配")
    for entry in record['files']:
        require(entry['backup'] == f"{BATCH}/{entry['source']}", "保全路径不匹配")
        data, info = read_regular(root, entry['backup'])
        require(digest(data) == entry['sha256'] and info['mode'] == entry['identity']['mode'],
                f"保全内容或权限变化：{entry['backup']}")
        require(references(root, entry['source'], data) == entry['references']
                or all(a['href'] == b['href'] and a['target'] == b['target']
                       and a['suffix'] == b['suffix'] and a['directory'] == b['directory']
                       for a, b in zip(references(root, entry['source'], data),
                                       entry['references'], strict=True)),
                "保全引用语境变化")
    verify_protected(root, record)
    return record


def verify_sources(root, record):
    for entry in record['files']:
        data, info = read_regular(root, entry['source'])
        require(digest(data) == entry['sha256'] and info == entry['identity'],
                f"源身份或内容已变化：{entry['source']}")


def verify_targets(root, record):
    count = 0
    for entry in record['files']:
        original, _ = read_regular(root, entry['backup'])
        data, info = read_regular(root, entry['target'])
        require(data == relocated(root, entry['source'], entry['target'], original)
                and info['mode'] == entry['identity']['mode'],
                f"迁移目标内容或权限变化：{entry['target']}")
        new = references(root, entry['target'], data)
        require(len(new) == len(entry['references']), "迁移引用数量变化")
        for before, after in zip(entry['references'], new, strict=True):
            require(after['target'] == MAPPING.get(before['target'], before['target'])
                    and after['suffix'] == before['suffix'], "引用目标或行号语义变化")
            require(not before['existed'] or after['existed'],
                    f"原有效引用失效：{entry['target']} -> {after['target']}")
            count += 1
    return count


def prepare(root):
    record = load_preserved(root)
    verify_sources(root, record)
    for entry in record['files']:
        require(not safe_path(root, entry['target']).exists(),
                f"目标已存在，保留源：{entry['target']}")
    for entry in record['files']:
        verify_sources(root, record)
        original, _ = read_regular(root, entry['backup'])
        exclusive_write(root, entry['target'],
                        relocated(root, entry['source'], entry['target'], original),
                        entry['identity']['mode'])
    links = verify_targets(root, record)
    verify_sources(root, record)
    return {'action': 'prepare', 'files': len(FILES), 'local_references': links,
            'source_preserved': True, 'targets_exclusively_saved': True}


def verify_plan_binding(root):
    data, _ = read_regular(root, PLAN)
    text = data.decode('utf-8')
    end = text.split('---', 2)
    require(len(end) == 3 and not end[0], "绑定计划缺少 frontmatter")
    header = end[1]
    require(f'plan_id: "{PLAN_ID}"' in header and '契约版本：4' in end[2],
            "非本批次契约版本 4")
    require(f'adr_file: "{FILES[0][1]}"' in header
            and f'  - "{FILES[1][1]}"' in header, "ADR 消费者未迁移")


def retire(root):
    record = load_preserved(root)
    verify_sources(root, record)
    verify_targets(root, record)
    verify_plan_binding(root)
    for entry in record['files']:
        data, info = read_regular(root, entry['source'])
        require(digest(data) == entry['sha256'] and info == entry['identity'],
                f"移除前源变化：{entry['source']}")
        verify_targets(root, record)
        verify_protected(root, record)
        safe_path(root, entry['source']).unlink()
    return audit(root)


def audit(root):
    record = load_preserved(root)
    links = verify_targets(root, record)
    verify_plan_binding(root)
    for entry in record['files']:
        require(not safe_path(root, entry['source']).exists(),
                f"源尚未移除：{entry['source']}")
    for entry in record['files'][:2]:
        data, _ = read_regular(root, entry['target'])
        require('PROPOSED' in data.decode('utf-8').splitlines()[2], "ADR 状态变化")
    return {'action': 'audit', 'files': len(FILES), 'local_references': links,
            'source_removed': True, 'preservation_verified': True,
            'protected_files': len(record['protected']), 'adr_status': 'PROPOSED',
            'cleanup_ok': True, 'boundary': '仅本批次磁盘与引用；不证明宿主或硬门禁'}


def restore(root):
    record = load_preserved(root)
    for entry in record['files']:
        source = safe_path(root, entry['source'])
        if source.exists():
            data, info = read_regular(root, entry['source'])
            require(digest(data) == entry['sha256'] and info['mode'] == entry['identity']['mode'],
                    f"拒绝覆盖恢复源的现有内容：{entry['source']}")
    for entry in record['files']:
        if not safe_path(root, entry['source']).exists():
            data, _ = read_regular(root, entry['backup'])
            exclusive_write(root, entry['source'], data, entry['identity']['mode'])
    return {'action': 'restore', 'files': len(FILES), 'targets_retained': True,
            'consumer_restore': '计划与 README 仅由原生工具恢复本轮差异；不得推进依赖'}


def verify_preserved(root):
    record = load_preserved(root)
    verify_sources(root, record)
    return {'action': 'verify-preserved', 'files': len(FILES),
            'original_bytes_and_identity_verified': True, 'source_preserved': True}


ACTIONS = {'preserve': preserve, 'verify-preserved': verify_preserved,
           'prepare': prepare, 'retire': retire, 'audit': audit, 'restore': restore}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=tuple(ACTIONS))
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args(argv)
    try:
        result = ACTIONS[args.action](args.root.absolute())
    except (BatchError, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'status': 'BLOCKED', 'action': args.action, 'error': str(exc),
                          'automatic_cleanup': False}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps({'status': 'PASS', **result}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
