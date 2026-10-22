"""从已核验的部署快照解析套件身份；不读取来源仓库、不写入资产。"""
from __future__ import annotations

import json
from pathlib import Path

from asset_safety import AssetError
from managed_files import ownership_record
from suite_versions import SuiteSpec, suite_spec, unique_object


PLUGIN_PREFIX = '.gemini/config/plugins/bmad-suite/'
IDENTITY_FIELDS = ('suite_id', 'major_version', 'source_path')


def manifest_suite(provenance, observed, *, retired_from=None):
    """输入必须来自所有权校验及末次复核后的快照；未知旧记录返回 None。

    同账号仍能同时修改清单和文件；此处提供一致性校验，不宣称防篡改。
    observed 使用部署根目录内相对路径作为键，不重新读取磁盘。
    """
    sources = provenance.get('source_files')
    managed = provenance.get('managed_files')
    if not isinstance(sources, dict) or not isinstance(managed, dict):
        raise AssetError('部署来源文件摘要结构非法')
    # 可选身份文件仅允许两份清单同时缺省；不能把部分丢失降级为旧 V4。
    if ('suite.json' in sources) != (PLUGIN_PREFIX + 'suite.json' in managed):
        raise AssetError('部署身份文件在来源与受管清单中的存在性不一致')

    def source_object(relative):
        target = PLUGIN_PREFIX + relative
        value = observed.get(target)
        record = sources.get(relative)
        if (value is None or value.content is None or record is None
                or managed.get(target) != record
                or ownership_record(value) != record):
            raise AssetError(f'部署套件身份资产与来源摘要不一致：{relative}')
        try:
            data = json.loads(value.content, object_pairs_hook=unique_object)
        except (ValueError, UnicodeError) as exc:
            raise AssetError(f'部署套件身份资产损坏：{relative}') from exc
        if not isinstance(data, dict):
            raise AssetError(f'部署套件身份资产不是对象：{relative}')
        return data

    if retired_from not in {None, 'v5'}:
        raise AssetError('仅允许显式核验一次性 V5 退役身份')
    fields = [provenance.get(key) for key in IDENTITY_FIELDS]
    directory = provenance.get('source_directory')
    if not isinstance(directory, str) or not directory:
        raise AssetError('部署来源目录缺失或非法')
    if all(value is None for value in fields):
        # 旧 V4 清单仅在物理来源名称和已受管插件同时可核验时识别。
        # 不将泛用目录、当前 HEAD 或默认版本当作历史部署身份。
        if (Path(directory).name != 'bmad-suite-v4'
                or 'suite.json' in sources
                or provenance.get('source_kind') not in {'worktree', 'commit_cache'}):
            return None
        spec = suite_spec('v4')
    else:
        if any(value is None for value in fields):
            raise AssetError('部署套件身份字段不完整')
        if retired_from == 'v5':
            if provenance['major_version'] != 'v5':
                raise AssetError('退役迁移需要可核验的现有 V5 身份；不重放或回退')
            # 仅描述退役快照，不加入来源映射，不读取或执行 V5 代码。
            spec = SuiteSpec('v5', 'bmralph-suite-v5', 'bmralph-suite-v5')
        else:
            spec = suite_spec(provenance['major_version'])
        if (provenance['suite_id'] != spec.suite_id
                or provenance['source_path'] != spec.source_path
                or Path(directory).name != spec.source_path):
            raise AssetError('部署套件身份与固定来源映射不一致')

    if retired_from == 'v5' and 'suite.json' not in sources:
        raise AssetError('显式 V5 退役身份缺少受管 suite.json；不凭来源名称接管')
    plugin = source_object('plugin.json')
    if plugin.get('name') != 'bmad-suite':
        raise AssetError('部署插件不符合单一活动槽位契约')
    if 'suite.json' in sources:
        identity = source_object('suite.json')
        if (type(identity.get('schema_version')) is not int or identity != {
                'schema_version': 1,
                'suite_id': spec.suite_id,
                'major_version': spec.major_version,
                'source_path': spec.source_path,
        }):
            raise AssetError('部署套件身份文件与来源清单不一致')
    return spec
