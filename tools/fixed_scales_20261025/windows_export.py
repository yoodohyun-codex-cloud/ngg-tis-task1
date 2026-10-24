"""Build an immutable public-result downloader; never access Windows on import."""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import PurePosixPath

REPO = 'yoodohyun-codex-cloud/ngg-tis-task1'


def validate_entries(entries):
    seen = set()
    for item in entries:
        path = item['path']
        parts = path.split('/')
        if not (isinstance(path, str) and path and not path.startswith('/') and
                all(p and p not in ('.', '..') and not any(c in p for c in '\\:<>|?*\x00') and
                    not p.endswith((' ', '.')) and not re.match(r'(?i)^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)', p)
                    for p in parts) and str(PurePosixPath(path)) == path):
            raise ValueError('Unsafe Windows relative result path')
        if not re.fullmatch('[0-9a-f]{40}', item['commit']) or not re.fullmatch('[0-9a-f]{64}', item['SHA256']):
            raise ValueError('Immutable commit and SHA256 required')
        if type(item['bytes']) is not int or item['bytes'] < 0 or item['bytes'] > 64*1024**2:
            raise ValueError('Bounded exact file size required')
        # Commit prefix isolates old versus new immutable snapshots.
        target = item['commit'][:8]+'/'+path
        if target.casefold() in seen:
            raise ValueError('Case-insensitive Windows output collision')
        seen.add(target.casefold())
    if not entries:
        raise ValueError('An empty export is not completed storage')
    return entries


def render(entries):
    entries = validate_entries(entries)
    manifest = json.dumps(entries, ensure_ascii=True, separators=(',', ':'))
    # ASCII source works in both Windows PowerShell5.1 and PowerShell7.
    # User-specific destination is supplied locally, never embedded publicly.
    return SCRIPT.replace('__MANIFEST__', manifest).replace('__REPOSITORY__', REPO)


SCRIPT = r'''#requires -Version 5.1
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$Destination)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$manifestJson = @'
__MANIFEST__
'@
$files = @($manifestJson | ConvertFrom-Json)
$repository = '__REPOSITORY__'
if ($Destination -notmatch '^[A-Za-z]:[\\/]') { throw 'An absolute Windows drive path is required.' }
$rootPath = [IO.Path]::GetFullPath($Destination).TrimEnd([char[]]@('\','/'))
$lockStream = $null
$records = New-Object System.Collections.Generic.List[object]
$receipt = [ordered]@{schema='task1-windows-export-receipt-v1';status='started';started_utc=[DateTime]::UtcNow.ToString('o');destination=$rootPath;Windows_files_SHA256_verified=$false;OneDrive_sync_verified=$false;cloud_originals_deleted=$false;files=$records;error=$null}
function Test-ExpectedFile([string]$Path, $Spec) {
    if (!(Test-Path -LiteralPath $Path -PathType Leaf)) { return $false }
    $file = Get-Item -LiteralPath $Path
    if ($file.Length -ne [long]$Spec.bytes) { throw ('Existing file size differs; preserved: '+$Path) }
    if ((Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $Spec.SHA256) { throw ('Existing file hash differs; preserved: '+$Path) }
    return $true
}
try {
    [IO.Directory]::CreateDirectory($rootPath) | Out-Null
    $lockStream = [IO.File]::Open([IO.Path]::Combine($rootPath,'.tis-export.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
    $pending = New-Object System.Collections.Generic.List[object]
    [long]$requiredBytes = 1048576
    foreach ($spec in $files) {
        if ($spec.commit -notmatch '^[0-9a-f]{40}$' -or $spec.SHA256 -notmatch '^[0-9a-f]{64}$' -or [long]$spec.bytes -lt 0 -or [long]$spec.bytes -gt 67108864) { throw 'Invalid immutable manifest.' }
        $relative = $spec.commit.Substring(0,8)+'/'+$spec.path
        foreach ($segment in ($relative -split '/')) {
            if (!$segment -or $segment -in @('.','..') -or $segment -match '[\\:<>|?*\x00]' -or $segment -match '[ .]$' -or $segment -match '^(?i:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)') { throw 'Unsafe manifest path.' }
        }
        $local = [IO.Path]::GetFullPath([IO.Path]::Combine($rootPath,($relative -replace '/','\')))
        if (!$local.StartsWith($rootPath+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Output escaped destination.' }
        if ($local.Length -ge 248) { throw ('Path too long for conservative Windows compatibility: '+$local) }
        if (Test-ExpectedFile $local $spec) {
            $records.Add([ordered]@{relative=$relative;status='reused_SHA256_verified';SHA256=$spec.SHA256;bytes=[long]$spec.bytes})
        } else {
            if (Test-Path -LiteralPath $local) { throw ('Destination is not a file; preserved: '+$local) }
            $pending.Add([pscustomobject]@{spec=$spec;relative=$relative;local=$local})
            $requiredBytes += [long]$spec.bytes
        }
    }
    $drive = New-Object IO.DriveInfo ([IO.Path]::GetPathRoot($rootPath))
    if ($drive.AvailableFreeSpace -lt $requiredBytes) { throw 'Insufficient local drive space; no results deleted.' }
    $receipt['required_local_free_bytes'] = $requiredBytes
    foreach ($item in $pending) {
        $spec = $item.spec
        $staging = [IO.Path]::Combine($rootPath,$spec.commit.Substring(0,8),'._partial')
        [IO.Directory]::CreateDirectory($staging) | Out-Null
        $partial = [IO.Path]::Combine($staging,([Guid]::NewGuid().ToString('N')+'.part'))
        $urlPath = (($spec.path -split '/') | ForEach-Object { [Uri]::EscapeDataString($_) }) -join '/'
        $url = 'https://raw.githubusercontent.com/'+$repository+'/'+$spec.commit+'/'+$urlPath
        $record = [ordered]@{relative=$item.relative;status='downloading';SHA256=$spec.SHA256;bytes=[long]$spec.bytes;partial=$partial}
        $records.Add($record)
        Write-Host ('Downloading '+$item.relative)
        Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $partial -TimeoutSec 120
        if (!(Test-ExpectedFile $partial $spec)) { throw 'Downloaded file is absent.' }
        [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($item.local)) | Out-Null
        [IO.File]::Move($partial,$item.local)
        if (!(Test-ExpectedFile $item.local $spec)) { throw 'Final file verification failed.' }
        $record['status'] = 'downloaded_SHA256_verified'
    }
    $receipt.status = 'Windows_files_verified_OneDrive_sync_unverified'
    $receipt.Windows_files_SHA256_verified = $true
    Write-Host 'All requested files saved and SHA256 verified. OneDrive synchronization is NOT verified.'
} catch {
    $receipt.status = 'failed_preserved'
    $receipt.error = $_.Exception.Message
    Write-Host ('Stopped; originals and partial downloads preserved: '+$receipt.error)
    throw
} finally {
    $receipt['finished_utc'] = [DateTime]::UtcNow.ToString('o')
    if ($null -ne $lockStream) {
        try {
            $receiptPath = [IO.Path]::Combine($rootPath,('tis-export-receipt-'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfff')+'-'+[Guid]::NewGuid().ToString('N').Substring(0,8)+'.json'))
            $bytes = [Text.Encoding]::UTF8.GetBytes(($receipt | ConvertTo-Json -Depth 10))
            $stream = [IO.File]::Open($receiptPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
            try { $stream.Write($bytes,0,$bytes.Length) } finally { $stream.Dispose() }
            Write-Host ('Receipt: '+$receiptPath)
        } finally { $lockStream.Dispose() }
    }
}
'''
