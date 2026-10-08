"""多环境目标与显式覆盖契约；仅使用项目内隔离目标。"""
import unittest

import yaml

import test_asset_safety_shell as fixtures


class GitOpsTargets(unittest.TestCase):
    setUp = fixtures.ShellEntrySafety.setUp
    run_shell = fixtures.ShellEntrySafety.run_shell
    tree = fixtures.ShellEntrySafety.tree

    CANDIDATES = (
        '.antigravity-ide-server/data/User/globalStorage/'
        'rooveterinaryinc.roo-cline/settings/custom_modes.yaml',
        '.vscode-server/data/User/globalStorage/'
        'rooveterinaryinc.roo-cline/settings/custom_modes.yaml',
        '.config/Code/User/globalStorage/'
        'rooveterinaryinc.roo-cline/settings/custom_modes.yaml',
    )

    def test_all_three_existing_candidates_preserve_personal_modes(self):
        for relative in self.CANDIDATES:
            path = self.target / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(
                b'theme: dark\ncustomModes: [{slug: personal, name: Personal}]\n'
            )
        result = self.run_shell()
        self.assertEqual(result.returncode, 0, result.stderr)
        for relative in self.CANDIDATES:
            with self.subTest(target=relative):
                data = yaml.safe_load((self.target / relative).read_bytes())
                self.assertEqual(data['theme'], 'dark')
                slugs = {mode['slug'] for mode in data['customModes']}
                self.assertTrue({'personal', 'ana-architect', 'bmad-engineer'} <= slugs)
                self.assertIn(relative.rsplit('/', 1)[0], result.stdout)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_explicit_target_overrides_discovery(self):
        relative = "custom profile with 'quote'/settings/custom_modes.yaml"
        selected = self.target / relative
        selected.parent.mkdir(parents=True)
        selected.write_bytes(b'customModes: [{slug: personal, name: Personal}]\n')
        # 未选中的自动候选损坏也不应被读取或覆盖。
        self.mode.write_bytes(b'customModes: [')
        before_unselected = self.mode.read_bytes()
        result = self.run_shell('--mode-target', relative)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.mode.read_bytes(), before_unselected)
        data = yaml.safe_load(selected.read_bytes())
        self.assertTrue(
            {'personal', 'ana-architect', 'bmad-engineer'}
            <= {mode['slug'] for mode in data['customModes']}
        )
        self.assertEqual(list(self.home.iterdir()), [])

    def test_explicit_target_dry_run_creates_no_directories(self):
        relative = 'new-profile/settings/custom_modes.yaml'
        before = self.tree()
        result = self.run_shell('--dry-run', '--mode-target', relative)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.tree(), before)
        self.assertFalse((self.target / 'new-profile').exists())
        self.assertEqual(list(self.home.iterdir()), [])

    def test_one_corrupt_candidate_blocks_all_target_writes(self):
        other = self.target / self.CANDIDATES[0]
        other.parent.mkdir(parents=True)
        other.write_bytes(b'customModes: [')
        before = self.tree()
        result = self.run_shell()
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertEqual(self.tree(), before)
        self.assertEqual(list(self.home.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
