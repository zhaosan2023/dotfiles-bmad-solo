"""轻量安装器源码回归；不解析或执行 PowerShell，不模拟文件安装。"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]


class InstallerContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = (ROOT / 'install-win10.ps1').read_bytes()
        cls.text = cls.raw.decode('utf-8-sig')
        cls.status = cls.text.split("    if ($Action -in @('Status', 'Check')) {", 1)[1].split(
            "    if ((Test-Path", 1)[0]
        cls.uninstall = cls.text.split("    if ($Action -eq 'Uninstall') {", 1)[1].split(
            '    $source = $null', 1)[0]
        cls.install = cls.text.split('    $source = $null', 1)[1].split('} catch {', 1)[0]
        cls.cleanup = cls.text.split('} finally {', 1)[1]

    def test_ps51_encoding_and_no_external_installer_dependencies(self):
        self.assertTrue(self.raw.startswith(b'\xef\xbb\xbf'))
        self.assertTrue(self.text.startswith('#Requires -Version 5.1\n'))
        for obsolete in ('Add-Type', 'Get-FileHash', 'SHA256', 'Invoke-Transaction',
                         'ReleaseBinding', 'Read-Package', 'Invoke-WebRequest'):
            self.assertNotIn(obsolete, self.text)

    def test_menu_defaults_and_single_read_without_session_exit(self):
        self.assertIn("[string]$Action = 'Menu'", self.text)
        for label in ('[1] 一键安装 (Install)', '[2] 完美卸载 (Uninstall)',
                      '[3] 健康检查 (Status/Check)', '[0] 退出 (Exit)'):
            self.assertIn(label, self.text)
        menu = self.text.split("    if ($Action -eq 'Menu') {", 1)[1].split(
            '    $targetRoot =', 1)[0]
        self.assertEqual(menu.count('Read-Host'), 1)
        self.assertIn("if ([string]::IsNullOrWhiteSpace($choice)) { $choice = '1' }", menu)
        for number, action in (('1', 'Install'), ('2', 'Uninstall'), ('3', 'Status')):
            self.assertIn("'" + number + "' { $Action = '" + action + "' }", menu)
        self.assertIn("'0' { return }", menu)
        self.assertIn('default { throw', menu)
        self.assertNotRegex(self.text, r'(?m)^\s*(?:while\s*\(|do\s*\{|exit\b)')
        self.assertTrue(self.text.rstrip().endswith('} @PSBoundParameters'))
        self.assertNotIn('} @args', self.text)
        self.assertIn("else { $localSource = Join-Path (Get-Location).Path 'bmad-suite-v4' }", self.install)

    def test_native_remote_bootstrap_and_owned_finally_cleanup(self):
        remote = self.install.split('    if (-not $source) {', 1)[1]
        self.assertIn('Assert-LocalPath $env:TEMP', remote)
        self.assertIn("'bmad-win10-' + [Guid]::NewGuid().ToString('N')", remote)
        self.assertIn("$archive = Join-Path $tempRoot 'main.zip'", remote)
        self.assertIn('https://github.com/zhaosan2023/dotfiles-bmad-solo/archive/refs/heads/main.zip', remote)
        self.assertIn('-OutFile $archive -TimeoutSec 60 -ErrorAction Stop', remote)
        self.assertIn('Expand-Archive -LiteralPath $archive -DestinationPath $expanded -ErrorAction Stop', remote)
        self.assertIn("'dotfiles-bmad-solo-main\\bmad-suite-v4'", remote)
        self.assertLess(remote.index('Invoke-RestMethod'), remote.index('Expand-Archive'))
        self.assertLess(remote.index('Expand-Archive'), remote.index('Get-ValidatedInstallFiles'))
        self.assertIn('$tempRoot = (New-Item -ItemType Directory -Path $candidate -ErrorAction Stop).FullName', remote)
        self.assertIn('Temporary and target directories must not overlap.', remote)
        self.assertIn('if ($tempRoot -and (Test-Path -LiteralPath $tempRoot))', self.cleanup)
        self.assertLess(self.cleanup.index('Assert-RemovalTree $tempRoot'),
                        self.cleanup.index('Remove-Item -LiteralPath $tempRoot -Recurse -Force'))
        self.assertIn('[Net.ServicePointManager]::SecurityProtocol = $originalTls', self.cleanup)
        self.assertNotRegex(self.cleanup, r'Remove-Item[^\n]*\$env:TEMP')
        explicit = self.install.split("if ($PSBoundParameters.ContainsKey('SourcePath')) {", 1)[1].split(
            '} else {', 1)[0]
        self.assertIn('Get-ValidatedInstallFiles $source $targetRoot', explicit)
        self.assertNotIn('Invoke-RestMethod', explicit)

    def test_local_source_and_userprofile_target(self):
        self.assertIn("(Join-Path $PSScriptRoot 'bmad-suite-v4')", self.text)
        self.assertIn("(Join-Path $env:USERPROFILE '.cline')", self.text)
        self.assertIn('Source and target directories must not overlap.', self.text)
        self.assertIn('Missing suite directory:', self.text)
        self.assertIn('ReparsePoint', self.text)

    def test_full_skill_file_copy_and_name_mapping(self):
        self.assertIn("foreach ($skill in @('ana-solo', 'bmad'))", self.text)
        self.assertIn("if ($skill -eq 'bmad') { $destination = 'bmad-solo' }", self.text)
        self.assertIn('Get-ChildItem -LiteralPath $directory -Recurse -Force', self.text)
        self.assertIn('Copy-Item -LiteralPath $file.Source -Destination $target -Force', self.text)
        self.assertNotIn('validate-solo-package.py', self.text)
        for skill, identity in (('ana-solo', 'ana-solo'), ('bmad', 'bmad-solo')):
            entry = ROOT / 'bmad-suite-v4' / 'skills' / skill / 'SKILL.md'
            self.assertIn('name: ' + identity, entry.read_text(encoding='utf-8'))
            self.assertTrue((entry.parent / 'references').is_dir())
        self.assertTrue((ROOT / 'bmad-suite-v4/skills/bmad/scripts').is_dir())

    def test_whatif_returns_before_all_writes_and_backup_precedes_install(self):
        approval = self.install.index('if (-not $PSCmdlet.ShouldProcess(')
        backup = self.install.index('foreach ($file in $existing)')
        install = self.install.index('foreach ($file in $files)', backup)
        self.assertIn('return', self.install[approval:backup])
        for operation in ('New-Item', 'Invoke-RestMethod', 'Expand-Archive',
                          '[IO.Directory]::CreateDirectory', 'Copy-Item', '[IO.File]::WriteAllText'):
            self.assertLess(approval, self.install.index(operation))
        self.assertLess(backup, install)
        self.assertIn('Copy-Item -LiteralPath (Join-Path $targetRoot $file.Relative) -Destination $backup',
                      self.install[backup:install])
        self.assertIn('no automatic rollback was attempted', self.text)
        self.assertIn('[CmdletBinding(SupportsShouldProcess = $true)]', self.text)

    def test_managed_deployment_and_readonly_collisions_refused(self):
        self.assertIn("if ((Test-Path -LiteralPath (Join-Path $env:USERPROFILE '.bmad-solo-deployment')) -or", self.text)
        self.assertIn("(Test-Path -LiteralPath (Join-Path $targetRoot 'bmad-solo\\state\\ownership.json')))", self.text)
        self.assertIn('Target is a directory or read-only file:', self.text)
        # Installation remains non-destructive; deletion belongs only to uninstall/owned TEMP cleanup.
        self.assertNotRegex(self.install, r'(?:Remove-Item|\[IO\.File\]::Delete)')
        validation = self.text.split('function Get-ValidatedInstallFiles', 1)[1].split(
            'function Assert-RemovalTree', 1)[0]
        self.assertNotRegex(validation, r'(?:Remove-Item|\[IO\.File\]::Delete)')
        guard = self.text.index("    if ((Test-Path -LiteralPath (Join-Path $env:USERPROFILE '.bmad-solo-deployment'))")
        self.assertLess(guard, self.text.index("    if ($Action -eq 'Uninstall') {"))

    def test_uninstall_scope_preflight_and_whatif_before_deletion(self):
        targets = self.uninstall.split('$targets = @(', 1)[1].split(')', 1)[0]
        self.assertEqual(re.findall(r"'([^']+)'", targets), [
            'rules\\bmad-router.md', 'bmad-solo\\resources\\bmad-constitution.md',
            'skills\\ana-solo', 'skills\\bmad-solo'])
        approval = self.uninstall.index('if (-not $PSCmdlet.ShouldProcess(')
        deletion = self.uninstall.index('Remove-Item -LiteralPath $path -Recurse -Force')
        prompt = self.uninstall.index('Read-Host')
        self.assertLess(self.uninstall.index('Assert-RemovalTree (Join-Path $targetRoot $relative)'), approval)
        self.assertLess(approval, deletion)
        self.assertLess(deletion, prompt)
        self.assertIn('return', self.uninstall[approval:deletion])
        preflight = self.text.split('function Assert-RemovalTree', 1)[1].split(
            'function Remove-EmptyDirectory', 1)[0]
        self.assertLess(preflight.index('Assert-LocalPath $Path'), preflight.index('Get-ChildItem'))
        self.assertIn('Assert-RemovalTree $child.FullName', preflight)

    def test_backups_prompt_defaults_to_retention_and_empty_parent_only(self):
        self.assertIn("$backups = Assert-LocalPath (Join-Path $targetRoot 'bmad-solo\\backups')", self.uninstall)
        self.assertIn('if (Test-Path -LiteralPath $backups -PathType Container)', self.uninstall)
        self.assertIn('BMAD 规则与技能已全部卸载！是否连同历史备份目录一并彻底删除？[Y/N] (默认 N): ', self.uninstall)
        self.assertIn("if ($answer -ieq 'Y')", self.uninstall)
        self.assertEqual(self.uninstall.count('Remove-Item -LiteralPath $backups'), 1)
        delete = self.uninstall.index('Remove-Item -LiteralPath $backups -Recurse -Force')
        self.assertLess(self.uninstall.index("if ($answer -ieq 'Y')"), delete)
        self.assertLess(self.uninstall.index('Assert-RemovalTree $backups'), delete)
        self.assertIn('else { Write-Host "历史备份保留于：$backups" }', self.uninstall)
        self.assertIn("Remove-EmptyDirectory (Join-Path $targetRoot 'bmad-solo')", self.uninstall)
        empty = self.text.split('function Remove-EmptyDirectory', 1)[1].split('$backupRoot = $null', 1)[0]
        self.assertIn('@(Get-ChildItem -LiteralPath $Path -Force).Count -eq 0', empty)
        self.assertNotIn('-Recurse', empty)

    def test_router_and_cross_skill_links_adapted_without_project_copy(self):
        self.assertIn('](../bmad-solo/resources/bmad-constitution.md', self.text)
        self.assertIn('](../skills/ana-solo/', self.text)
        self.assertIn('](../skills/bmad-solo/', self.text)
        self.assertIn(".Replace('](../bmad/', '](../bmad-solo/')", self.text)
        self.assertIn('File installation does not verify Cline runtime loading', self.text)
        for private in ('AGENTS.md', 'project-context.md', 'mcpServers', 'custom_modes.yaml'):
            self.assertNotRegex(self.text, r"From\s*=\s*'[^']*" + re.escape(private))

    def test_status_checks_core_files_without_mutations_or_download(self):
        for relative in ('rules\\bmad-router.md', 'bmad-solo\\resources\\bmad-constitution.md',
                         'skills\\ana-solo\\SKILL.md', 'skills\\bmad-solo\\SKILL.md'):
            self.assertIn("Relative = '" + relative + "'; Type = 'Leaf'", self.status)
        for relative in ('skills\\ana-solo', 'skills\\bmad-solo'):
            self.assertIn("Relative = '" + relative + "'; Type = 'Container'", self.status)
        self.assertIn('Test-Path -LiteralPath $path -PathType $check.Type', self.status)
        self.assertIn('Write-Host "[OK] $path"', self.status)
        self.assertIn('Write-Host "[MISSING] $path"', self.status)
        self.assertIn('return', self.status)
        self.assertNotRegex(self.status, r'Remove-Item|Copy-Item|New-Item|WriteAllText|Invoke-RestMethod|Expand-Archive|Read-Host')

    def test_windows_terminal_section_is_replaced_and_links_preserved(self):
        self.assertIn("$start = $Text.IndexOf('## 8.5 ')", self.text)
        self.assertIn("$end = $Text.IndexOf('## 9. ', [Math]::Max(0, $start))", self.text)
        self.assertIn("throw 'Missing terminal discipline section.'", self.text)
        self.assertIn('## 8.5 Windows terminal execution discipline', self.text)
        self.assertIn('inspection 15s, verification 30s, builds 600s.', self.text)
        self.assertIn('Close redirected stdin', self.text)
        self.assertIn('$Text.Substring(0, $start) + $windows + "`r`n" + $Text.Substring($end)', self.text)
        self.assertIn('New-Object System.Text.UTF8Encoding($true)', self.install)


if __name__ == '__main__':
    unittest.main(verbosity=2)
