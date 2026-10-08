"""只读构建部署来源清单；返回快照，由现有受管事务统一提交。"""
from __future__ import annotations

import io
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile

from asset_safety import AssetError, Snapshot, checked_path, snapshot
from managed_files import ownership_record, validate_relative_path
from managed_modes import mode_digest
from asset_safety import parse_modes


MANIFEST_TARGET = '.gemini/config/plugins/bmad-suite/.manifest.json'


def git(repo, *arguments):
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith('GIT_')}
    environment.update(GIT_TERMINAL_PROMPT='0', GIT_OPTIONAL_LOCKS='0')
    try:
        result = subprocess.run(
            ['git', '--no-pager', '-C', str(repo), *arguments],
            env=environment, stdin=subprocess.DEVNULL,
            capture_output=True, timeout=15,
        )
    except subprocess.TimeoutExpired as exc:
        raise AssetError('来源核验 Git 命令超时') from exc
    if result.returncode:
        raise AssetError('来源核验失败：' + result.stderr.decode(
            'utf-8', errors='replace').strip())
    return result.stdout


def committed_files(repo, commit, relative):
    """比较实际分发字节和 Git 提交，不仅依赖工作树状态提示。"""
    content = git(repo, 'archive', '--format=tar', commit, '--', relative)
    result = {}
    prefix = relative + '/'
    try:
        with tarfile.open(fileobj=io.BytesIO(content), mode='r:') as archive:
            for member in archive:
                name = member.name.rstrip('/') if member.isdir() else member.name
                validate_relative_path(name)
                if member.isdir():
                    continue
                if not name.startswith(prefix) or not member.isfile():
                    raise AssetError('提交归档包含范围外路径、链接或特殊文件')
                key = name[len(prefix):]
                validate_relative_path(key)
                if key in result:
                    raise AssetError('提交归档包含重复路径')
                stream = archive.extractfile(member)
                if stream is None:
                    raise AssetError('无法读取提交归档成员')
                with stream:
                    result[key] = Snapshot(stream.read(), member.mode)
    except tarfile.TarError as exc:
        raise AssetError('无法解析来源提交归档') from exc
    return result


def build_manifest(source, sources, files, modes, *, repository=None):
    source = checked_path(source)
    metadata = {
        'schema_version': 1,
        'source_directory': str(source),
        'source_repository': None,
        'source_commit': None,
        'source_dirty': None,
        'source_kind': 'unversioned',
        'source_dirty_scope': 'distributed_suite',
    }
    if repository is not None:
        repo = checked_path(repository)
        actual_root = checked_path(Path(git(
            repo, 'rev-parse', '--show-toplevel'
        ).decode('utf-8').strip()))
        if actual_root != repo:
            raise AssetError('来源仓库参数必须指向实际仓库根目录')
        metadata['source_repository'] = str(repo)
        cache_root = repo / '.versions'
        if source.is_relative_to(cache_root):
            relative_parts = source.relative_to(cache_root).parts
            if (len(relative_parts) != 2 or relative_parts[1] != 'bmad-suite-v4'
                    or not re.fullmatch(r'commit-([0-9a-f]{40}|[0-9a-f]{64})',
                                        relative_parts[0])):
                raise AssetError('来源缓存路径不符合提交绑定契约')
            commit = relative_parts[0][len('commit-'):]
            marker = snapshot(source.parent / 'commit.txt')
            if marker != Snapshot((commit + '\n').encode('ascii'), 0o600):
                raise AssetError('来源缓存提交标识缺失或不匹配')
            expected = committed_files(repo, commit, 'bmad-suite-v4')
            if expected != sources:
                raise AssetError('来源缓存内容或权限与提交不符')
            metadata.update(source_commit=commit, source_dirty=False,
                            source_kind='commit_cache')
        else:
            if source == repo or not source.is_relative_to(repo):
                raise AssetError('工作树套件源必须位于指定仓库内')
            relative = source.relative_to(repo).as_posix()
            validate_relative_path(relative)
            commit = git(repo, 'rev-parse', '--verify', 'HEAD^{commit}').decode('ascii').strip()
            if not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', commit):
                raise AssetError('非法来源提交标识')
            expected = committed_files(repo, commit, relative)
            # Git 只跟踪可执行位；源完整权限另外记录于清单摘要中。
            dirty = set(expected) != set(sources) or any(
                sources[name].content != value.content
                or (sources[name].mode & 0o111) != (value.mode & 0o111)
                for name, value in expected.items() if name in sources
            )
            if git(repo, 'rev-parse', '--verify', 'HEAD^{commit}').decode('ascii').strip() != commit:
                raise AssetError('来源核验期间 HEAD 发生变化')
            metadata.update(source_commit=commit, source_dirty=dirty,
                            source_kind='worktree')
    metadata['source_files'] = {
        name: ownership_record(value) for name, value in sorted(sources.items())
    }
    metadata['managed_files'] = {
        name: ownership_record(value) for name, value in sorted(files.items())
    }
    metadata['managed_modes'] = {
        target: {mode['slug']: mode_digest(mode)
                 for mode in parse_modes(content)['customModes']}
        for target, content in sorted(modes.items())
    }
    # 不写时间戳，保持相同输入幂等；实际逐目标结果由事务日志记录。
    metadata['result_evidence'] = 'ownership.json and transaction logs in .bmad-solo-deployment'
    content = (json.dumps(metadata, ensure_ascii=False, sort_keys=True, indent=2)
               + '\n').encode('utf-8')
    return Snapshot(content, 0o600)
