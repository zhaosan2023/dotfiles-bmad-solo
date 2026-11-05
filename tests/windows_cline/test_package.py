"""Windows 载荷与安装器契约回归；不启动真实宿主。"""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('win10_package', ROOT / 'scripts/build-win10-cline-package.py')
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)


class PackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = package.snapshot_source(ROOT / 'bmad-suite-v4')
        cls.version, cls.files = package.make_payload(ROOT / 'bmad-suite-v4', cls.sources)

    def sandbox(self):
        temporary = tempfile.TemporaryDirectory(prefix='sandbox-win10-', dir=Path(__file__).parent)
        self.addCleanup(temporary.cleanup)
        return Path(temporary.name)

    def test_complete_runtime_set_and_preserved_scripts(self):
        expected = {'rules/bmad-router.md', 'bmad-solo/resources/bmad-constitution.md'}
        for name, data in self.sources.items():
            if not name.startswith('skills/') or name == package.INSTALL_ONLY:
                continue
            _, directory, resource = name.split('/', 2)
            target = f'skills/{package.NAMES[directory]}/{resource}'
            expected.add(target)
            if not name.endswith('.md'):
                self.assertEqual(self.files[target], data)
        self.assertEqual(set(self.files), expected)
        self.assertNotIn('skills/bmad-solo/scripts/validate-solo-package.py', self.files)
        self.assertFalse(any('.gemini' in name or '.roo' in name for name in self.files))

    def test_source_unchanged_and_links_closed(self):
        before = dict(self.sources)
        package.make_payload(ROOT / 'bmad-suite-v4', self.sources)
        self.assertEqual(self.sources, before)
        self.assertGreater(package.validate_payload(self.files), 0)
        router = self.files['rules/bmad-router.md'].decode()
        self.assertIn('../bmad-solo/resources/bmad-constitution.md:6', router)
        self.assertIn('(docs/project-context.md:1)', router)
        self.assertNotIn('.gemini', router)
        self.assertNotIn('timeout 15s', self.files['skills/bmad-solo/SKILL.md'].decode())

    def test_missing_resource_and_bad_reference_rejected(self):
        for target in ('skills/ana-solo/SKILL.md', 'skills/bmad-solo/references/templates/task-unit.template.md'):
            files = dict(self.files)
            del files[target]
            with self.subTest(target=target), self.assertRaises((package.PackageError, KeyError)):
                package.validate_payload(files)
        for link in ('../../escape.md', '../bmad-solo/SKILL.md:999999'):
            files = dict(self.files)
            files['skills/ana-solo/SKILL.md'] += f'\n[X]({link})\n'.encode()
            with self.subTest(link=link), self.assertRaises(package.PackageError):
                package.validate_payload(files)

    def test_reserved_names_traversal_and_collisions(self):
        for name in ('../x', '/x', 'x/../y', 'x\\y', 'a:b', 'CON.md', 'a/NUL', 'x.', 'x ', 'x//y'):
            with self.subTest(name=name), self.assertRaises(package.PackageError):
                package.safe_name(name)
        files = dict(self.files)
        files['RULES/BMAD-ROUTER.MD'] = b'collision'
        with self.assertRaises(package.PackageError):
            package.validate_payload(files)

    def test_legacy_source_and_anchor_drift_rejected(self):
        for version in (b'v4.2\n', b'v4.03\n', b'v4.3', b'v4.3.1\n'):
            with self.subTest(version=version), self.assertRaises(package.PackageError):
                package.make_payload(ROOT / 'bmad-suite-v4', {**self.sources, 'VERSION': version})
        sources = dict(self.sources)
        del sources['skills/bmad/SKILL.md']
        with self.assertRaises(package.PackageError):
            package.make_payload(ROOT / 'bmad-suite-v4', sources)
        with self.assertRaises(package.PackageError):
            package.adapt_text('skills/bmad/SKILL.md', 'changed')


    def test_legacy_zip_builder_refuses_lightweight_installer_without_output(self):
        # 用户已将安装契约改为本地套件复制，不再生成绑定安装器。
        # 保留旧载荷检查；旧打包入口必须明确拒绝，不能输出不兼容安装包。
        output = self.sandbox() / 'legacy-package'
        with self.assertRaisesRegex(package.PackageError, '旧冻结 ZIP 构建入口'):
            package.build(output, development=True)
        self.assertFalse(output.exists())
        script = (ROOT / 'install-win10.ps1').read_bytes()
        self.assertFalse(script.startswith(b'\xef\xbb\xbf'))
        self.assertTrue(script.decode('utf-8').startswith('#Requires -Version 5.1\n'))
        self.assertNotIn(b'@@WIN10_RELEASE_BINDING@@', script)

    def test_uncommitted_source_cannot_be_release(self):
        with patch.object(package, 'git', side_effect=[b'a' * 40, b'']):
            with self.assertRaises(package.PackageError):
                package.build(self.sandbox() / 'release')

    def test_hardlink_and_symlink_source_rejected(self):
        root = self.sandbox()
        original = root / 'original'
        original.write_bytes(b'test')
        hard = root / 'hard'
        os.link(original, hard)
        with self.assertRaises(package.PackageError):
            package.snapshot_source(root)
        hard.unlink()
        if os.name != 'nt':
            (root / 'link').symlink_to(original)
            with self.assertRaises(package.PackageError):
                package.snapshot_source(root)


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(PackageTests)
    count = suite.countTestCases()
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if count >= 8 and result.wasSuccessful() and not result.skipped else 1)
