#Requires -Version 5.1
<#
Interactive BMAD deployment menu. Local suite first; otherwise download GitHub main.zip.
No MCP or IDE settings are changed. Back up before replacing files; no automatic rollback.
The script block keeps variables and preferences local when invoked through irm | iex.
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [ValidateSet('Menu', 'Install', 'Uninstall', 'Status', 'Check', 'Exit')]
    [string]$Action = 'Menu',
    [string]$SourcePath
)

# Bind named script arguments before forwarding them to the isolated execution scope.
& {
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [ValidateSet('Menu', 'Install', 'Uninstall', 'Status', 'Check', 'Exit')]
    [string]$Action = 'Menu',
    [string]$SourcePath
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Assert-LocalPath([string]$Path) {
    $full = [IO.Path]::GetFullPath($Path)
    if ($full -notmatch '^[A-Za-z]:\\' -or $full.Substring(3).Contains(':')) {
        throw "Expected a local drive path: $Path"
    }
    for ($current = $full; $current; $current = [IO.Path]::GetDirectoryName($current)) {
        if (Test-Path -LiteralPath $current) {
            $item = Get-Item -LiteralPath $current -Force
            if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
                throw "Linked paths are not supported: $current"
            }
            if ($current -ne $full -and -not $item.PSIsContainer) {
                throw "Parent is not a directory: $current"
            }
        }
    }
    return $full
}

function Convert-Markdown([string]$Text, [string]$Name) {
    $Text = $Text.Replace('](../bmad/', '](../bmad-solo/')
    if ($Name -eq 'rules\bmad-router.md') {
        $Text = $Text.Replace('](bmad-suite-v4/rules/bmad-constitution.md',
            '](../bmad-solo/resources/bmad-constitution.md')
        $Text = $Text.Replace('](bmad-suite-v4/skills/ana-solo/', '](../skills/ana-solo/')
        $Text = $Text.Replace('](bmad-suite-v4/skills/bmad/', '](../skills/bmad-solo/')
    }
    if ($Name -eq 'skills\bmad-solo\SKILL.md') {
        $Text = $Text.Replace('`timeout 15s git --no-pager status --short < /dev/null`',
            '`git --no-pager status --short` (use a verified Windows timeout and closed stdin)')
        $Text = $Text.Replace('- **输入封闭**：附加 `< /dev/null`，仅选用当前命令实际支持的非交互参数。',
            '- **输入封闭**：使用当前平台的标准输入关闭能力；Windows 不使用 `/dev/null`，仅选用命令支持的非交互参数。')
    }
    if ($Name -eq 'bmad-solo\resources\bmad-constitution.md') {
        $start = $Text.IndexOf('## 8.5 ')
        $end = $Text.IndexOf('## 9. ', [Math]::Max(0, $start))
        if ($start -lt 0 -or $end -le $start) { throw 'Missing terminal discipline section.' }
        $windows = @'
## 8.5 Windows terminal execution discipline

- Execute commands only in an authorized engineering stage; analysis stays read-only.
- Run serially and wait for actual exit results; do not leave unmanaged processes.
- Use verified process-level timeouts: inspection 15s, verification 30s, builds 600s.
- Close redirected stdin; do not assume GNU timeout or /dev/null exists on Windows.
- Confirm process cleanup after timeout; missing results are not success.
- Use native file tools for edits. POSIX examples apply only to their original environment.
- This installer does not supply project command wrappers or additional dependencies.
- Stop the affected execution if a verified timeout/non-interactive entry is unavailable.

'@
        $Text = $Text.Substring(0, $start) + $windows + "`r`n" + $Text.Substring($end)
    }
    return $Text
}

function Get-InstallFiles([string]$Source) {
    $entries = @(
        @{ From = 'cline\templates\bmad-router.md'; To = 'rules\bmad-router.md' },
        @{ From = 'rules\bmad-constitution.md'; To = 'bmad-solo\resources\bmad-constitution.md' }
    )
    foreach ($skill in @('ana-solo', 'bmad')) {
        $directory = Assert-LocalPath (Join-Path $Source "skills\$skill")
        if (-not (Test-Path -LiteralPath (Join-Path $directory 'SKILL.md') -PathType Leaf)) {
            throw "Missing skill entry: $directory"
        }
        $destination = $skill
        if ($skill -eq 'bmad') { $destination = 'bmad-solo' }
        foreach ($file in Get-ChildItem -LiteralPath $directory -Recurse -Force) {
            Assert-LocalPath $file.FullName | Out-Null
            if ($file.PSIsContainer) { continue }
            $relative = $file.FullName.Substring($directory.Length + 1)
            $entries += @{ From = "skills\$skill\$relative"; To = "skills\$destination\$relative" }
        }
    }
    foreach ($entry in $entries) {
        $path = Assert-LocalPath (Join-Path $Source $entry.From)
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Missing source file: $path" }
        $text = $null
        if ([IO.Path]::GetExtension($path) -eq '.md') {
            $text = Convert-Markdown ([IO.File]::ReadAllText($path)) $entry.To
        }
        [pscustomobject]@{ Source = $path; Relative = $entry.To; Text = $text }
    }
}

function Get-ValidatedInstallFiles([string]$Source, [string]$TargetRoot) {
    $source = Assert-LocalPath $Source
    if (-not (Test-Path -LiteralPath $source -PathType Container)) { throw "Missing suite directory: $source" }
    $source = (Get-Item -LiteralPath $source -Force).FullName.TrimEnd('\')
    if ($source -eq $TargetRoot -or $source.StartsWith($TargetRoot + '\', [StringComparison]::OrdinalIgnoreCase) -or
        $TargetRoot.StartsWith($source + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Source and target directories must not overlap.'
    }
    $files = @(Get-InstallFiles $source)
    foreach ($file in $files) {
        $target = Assert-LocalPath (Join-Path $TargetRoot $file.Relative)
        if (Test-Path -LiteralPath $target) {
            $item = Get-Item -LiteralPath $target -Force
            if ($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReadOnly)) {
                throw "Target is a directory or read-only file: $target"
            }
        }
    }
    return $files
}

function Assert-RemovalTree([string]$Path) {
    Assert-LocalPath $Path | Out-Null
    if (Test-Path -LiteralPath $Path -PathType Container) {
        foreach ($child in Get-ChildItem -LiteralPath $Path -Force) {
            Assert-RemovalTree $child.FullName
        }
    }
}

function Remove-EmptyDirectory([string]$Path) {
    Assert-LocalPath $Path | Out-Null
    if ((Test-Path -LiteralPath $Path -PathType Container) -and
        @(Get-ChildItem -LiteralPath $Path -Force).Count -eq 0) {
        Remove-Item -LiteralPath $Path -Force
    }
}

$backupRoot = $null
$tempRoot = $null
$originalTls = $null
try {
    if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) { throw 'Windows is required.' }
    if (-not $env:USERPROFILE -or -not (Test-Path -LiteralPath $env:USERPROFILE -PathType Container)) {
        throw 'USERPROFILE must point to an existing user directory.'
    }
    if ($Action -eq 'Menu') {
        Write-Host '[1] 一键安装 (Install)'
        Write-Host '[2] 完美卸载 (Uninstall)'
        Write-Host '[3] 健康检查 (Status/Check)'
        Write-Host '[0] 退出 (Exit)'
        $choice = (Read-Host '请选择操作 [0-3] (默认 1)').Trim()
        if ([string]::IsNullOrWhiteSpace($choice)) { $choice = '1' }
        switch ($choice) {
            '1' { $Action = 'Install' }
            '2' { $Action = 'Uninstall' }
            '3' { $Action = 'Status' }
            '0' { return }
            default { throw "Invalid menu selection: $choice" }
        }
    }
    if ($Action -eq 'Exit') { return }
    $targetRoot = Assert-LocalPath (Join-Path $env:USERPROFILE '.cline')
    if ($Action -in @('Status', 'Check')) {
        $checks = @(
            @{ Relative = 'rules\bmad-router.md'; Type = 'Leaf' },
            @{ Relative = 'bmad-solo\resources\bmad-constitution.md'; Type = 'Leaf' },
            @{ Relative = 'skills\ana-solo'; Type = 'Container' },
            @{ Relative = 'skills\ana-solo\SKILL.md'; Type = 'Leaf' },
            @{ Relative = 'skills\bmad-solo'; Type = 'Container' },
            @{ Relative = 'skills\bmad-solo\SKILL.md'; Type = 'Leaf' }
        )
        foreach ($check in $checks) {
            $path = Join-Path $targetRoot $check.Relative
            if (Test-Path -LiteralPath $path -PathType $check.Type) { Write-Host "[OK] $path" }
            else { Write-Host "[MISSING] $path" }
        }
        Write-Host 'File presence only; Cline runtime loading and routing are not verified.'
        return
    }
    if ((Test-Path -LiteralPath (Join-Path $env:USERPROFILE '.bmad-solo-deployment')) -or
        (Test-Path -LiteralPath (Join-Path $targetRoot 'bmad-solo\state\ownership.json'))) {
        throw 'Existing managed deployment detected. Migrate it separately; this script will not adopt it.'
    }
    if ($Action -eq 'Uninstall') {
        $targets = @(
            'rules\bmad-router.md',
            'bmad-solo\resources\bmad-constitution.md',
            'skills\ana-solo',
            'skills\bmad-solo'
        )
        foreach ($relative in $targets) {
            Assert-RemovalTree (Join-Path $targetRoot $relative)
        }
        if (-not $PSCmdlet.ShouldProcess($targetRoot, 'Uninstall BMAD rules and both complete skill directories')) {
            return
        }
        foreach ($relative in $targets) {
            $path = Join-Path $targetRoot $relative
            if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Recurse -Force }
        }
        Remove-EmptyDirectory (Join-Path $targetRoot 'bmad-solo\resources')
        $backups = Assert-LocalPath (Join-Path $targetRoot 'bmad-solo\backups')
        if (Test-Path -LiteralPath $backups -PathType Container) {
            $answer = (Read-Host 'BMAD 规则与技能已全部卸载！是否连同历史备份目录一并彻底删除？[Y/N] (默认 N): ').Trim()
            if ($answer -ieq 'Y') {
                Assert-RemovalTree $backups
                if ($PSCmdlet.ShouldProcess($backups, 'Permanently delete historical backups')) {
                    Remove-Item -LiteralPath $backups -Recurse -Force
                    Write-Host "历史备份已彻底删除：$backups"
                } else { Write-Host "历史备份保留于：$backups" }
            } else { Write-Host "历史备份保留于：$backups" }
        }
        Remove-EmptyDirectory (Join-Path $targetRoot 'bmad-solo')
        Write-Host 'BMAD 规则与技能已全部卸载；其他规则、技能及 IDE 设置未改动。'
        return
    }

    $source = $null
    $files = @()
    if ($PSBoundParameters.ContainsKey('SourcePath')) {
        if ([string]::IsNullOrWhiteSpace($SourcePath)) { throw 'SourcePath must not be empty.' }
        $source = Assert-LocalPath $SourcePath
        $files = @(Get-ValidatedInstallFiles $source $targetRoot)
    } else {
        if ($PSScriptRoot) { $localSource = (Join-Path $PSScriptRoot 'bmad-suite-v4') }
        else { $localSource = Join-Path (Get-Location).Path 'bmad-suite-v4' }
        $localSource = Assert-LocalPath $localSource
        if (Test-Path -LiteralPath $localSource) {
            $source = $localSource
            $files = @(Get-ValidatedInstallFiles $source $targetRoot)
        }
    }
    if ($source) { Write-Host "Source: $source ($($files.Count) files)" }
    else { Write-Host 'Source: GitHub main.zip (download after approval)' }
    Write-Host "Target: $targetRoot"
    if (-not $PSCmdlet.ShouldProcess($targetRoot, 'Download if needed, back up existing files and install BMAD rules and skills')) {
        return
    }
    if (-not $source) {
        if (-not $env:TEMP) { throw 'TEMP must point to an existing local directory.' }
        $temporary = Assert-LocalPath $env:TEMP
        if (-not (Test-Path -LiteralPath $temporary -PathType Container)) {
            throw 'TEMP must point to an existing local directory.'
        }
        $candidate = Assert-LocalPath (Join-Path $temporary ('bmad-win10-' + [Guid]::NewGuid().ToString('N')))
        if ($candidate -eq $targetRoot -or
            $candidate.StartsWith($targetRoot + '\', [StringComparison]::OrdinalIgnoreCase) -or
            $targetRoot.StartsWith($candidate + '\', [StringComparison]::OrdinalIgnoreCase)) {
            throw 'Temporary and target directories must not overlap.'
        }
        # Record ownership only after creating a new directory; never clean up an existing path.
        $tempRoot = (New-Item -ItemType Directory -Path $candidate -ErrorAction Stop).FullName
        $archive = Join-Path $tempRoot 'main.zip'
        $expanded = Join-Path $tempRoot 'expanded'
        $originalTls = [Net.ServicePointManager]::SecurityProtocol
        [Net.ServicePointManager]::SecurityProtocol = $originalTls -bor [Net.SecurityProtocolType]::Tls12
        Invoke-RestMethod -Uri 'https://github.com/zhaosan2023/dotfiles-bmad-solo/archive/refs/heads/main.zip' -OutFile $archive -TimeoutSec 60 -ErrorAction Stop
        Expand-Archive -LiteralPath $archive -DestinationPath $expanded -ErrorAction Stop
        $source = Join-Path $expanded 'dotfiles-bmad-solo-main\bmad-suite-v4'
        $files = @(Get-ValidatedInstallFiles $source $targetRoot)
        Write-Host "Source: $source ($($files.Count) files)"
    }
    if (-not (Test-Path -LiteralPath $targetRoot -PathType Container)) {
        Write-Host 'The .cline directory will be created; this does not install the Cline extension.'
    }
    $existing = @($files | Where-Object { Test-Path -LiteralPath (Join-Path $targetRoot $_.Relative) })
    if ($existing.Count -gt 0) {
        $stamp = (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '-' + [Guid]::NewGuid().ToString('N')
        $backupRoot = Assert-LocalPath (Join-Path $targetRoot "bmad-solo\backups\$stamp")
        Write-Host "Backup: $backupRoot"
        # Finish every backup before replacing any destination file.
        foreach ($file in $existing) {
            $backup = Join-Path $backupRoot $file.Relative
            [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($backup)) | Out-Null
            Copy-Item -LiteralPath (Join-Path $targetRoot $file.Relative) -Destination $backup
        }
    }
    $utf8Bom = New-Object System.Text.UTF8Encoding($true)
    foreach ($file in $files) {
        $target = Join-Path $targetRoot $file.Relative
        [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($target)) | Out-Null
        if ($null -ne $file.Text) { [IO.File]::WriteAllText($target, $file.Text, $utf8Bom) }
        else { Copy-Item -LiteralPath $file.Source -Destination $target -Force }
    }
    Write-Host 'BMAD files copied. Enable/check rules and both skills in Cline, then start a new task.'
    Write-Host 'MCP, AGENTS.md, IDE settings and extension activation were not changed.'
    Write-Host 'File installation does not verify Cline runtime loading or automatic mode routing.'
} catch {
    if ($backupRoot) { Write-Warning "Backups retained at: $backupRoot" }
    if ($Action -eq 'Install') {
        Write-Warning 'Installation stopped. Some files may have been copied; no automatic rollback was attempted.'
    }
    throw
} finally {
    if ($null -ne $originalTls) { [Net.ServicePointManager]::SecurityProtocol = $originalTls }
    if ($tempRoot -and (Test-Path -LiteralPath $tempRoot)) {
        Assert-RemovalTree $tempRoot
        Remove-Item -LiteralPath $tempRoot -Recurse -Force
    }
}
} @PSBoundParameters
