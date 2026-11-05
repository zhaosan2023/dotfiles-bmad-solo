#Requires -Version 5.1
# Native Windows regression. Optional HTTP read; never install or remove files.
[CmdletBinding()]
param([string]$Uri)

& {
    Set-StrictMode -Version Latest
    $ErrorActionPreference = 'Stop'
    if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT -or
        $PSVersionTable.PSVersion.Major -ne 5 -or $PSVersionTable.PSVersion.Minor -ne 1) {
        throw 'Run this regression in Windows PowerShell 5.1.'
    }
    $installer = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\install-win10.ps1'))
    $bytes = [IO.File]::ReadAllBytes($installer)
    if ($bytes.Length -lt 3 -or
        ($bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF)) {
        throw 'Installer must be nonempty UTF-8 without BOM.'
    }
    $utf8 = New-Object System.Text.UTF8Encoding($false, $true)
    $diskText = $utf8.GetString($bytes)
    $httpText = $diskText
    if ($Uri) {
        $httpText = irm -Uri $Uri -TimeoutSec 15 -ErrorAction Stop
    }
    if ($httpText -isnot [string] -or $httpText.Length -eq 0 -or $httpText[0] -eq [char]0xFEFF) {
        throw 'Transport text must be a nonempty string without a leading U+FEFF.'
    }
    if ($httpText -cne $diskText) { throw 'Transport text differs from the checked-out candidate.' }
    $tokens = $null
    $errors = $null
    [System.Management.Automation.Language.Parser]::ParseInput($httpText, [ref]$tokens, [ref]$errors) | Out-Null
    if ($errors.Count -gt 0) { throw ($errors | Out-String) }

    # Explicit UTF-8 decoding also avoids PS 5.1's default ANSI disk decoding.
    & ([scriptblock]::Create($diskText)) -Action Exit -WhatIf
    $observed = New-Object 'System.Collections.Generic.List[string]'
    $errorCount = $Error.Count
    & {
        function Read-Host {
            param([string]$Prompt)
            $observed.Add('READ:' + $Prompt)
            return '0'
        }
        function Write-Host {
            param([object]$Object)
            $observed.Add([string]$Object)
        }
        # Feed original transport text directly into the real Invoke-Expression alias.
        $httpText | iex
    }
    if ($Error.Count -ne $errorCount) { throw 'Direct iex added an error record.' }
    foreach ($label in @('[1]', '[2]', '[3]', '[0]')) {
        if (@($observed | Where-Object { $_.StartsWith($label) }).Count -ne 1) {
            throw "Expected exactly one menu item: $label"
        }
    }
    if (@($observed | Where-Object { $_.StartsWith('READ:') }).Count -ne 1) {
        throw 'Expected exactly one menu read with Exit selected.'
    }
    Write-Output 'PASS: UTF-8 no BOM; unmodified transport parsed; named Exit and direct iex menu Exit executed without errors.'
}
