"""Pure compact-path Windows downloader for immutable human-hybrid report bundles.

No network, filesystem, authentication or numerical work occurs on import.
The caller supplies fully readback-verified publication records.
"""
from __future__ import annotations
import hashlib
import json
import re
from collections import Counter
from pathlib import PurePosixPath

REPO='yoodohyun-codex-cloud/ngg-tis-task1'
PREFIX='layer-human-20261025'
MAX_BYTES=64*1024**2


def _path(value):
    if not isinstance(value,str) or not value or value.startswith('/') or str(PurePosixPath(value))!=value:
        raise ValueError('Canonical relative path required')
    for segment in value.split('/'):
        if not segment or segment in ('.','..') or segment[-1] in (' ','.') or any(ord(c)<32 or c in '\\:"<>|?*' for c in segment):
            raise ValueError('Unsafe Windows path component')
        if re.match(r'(?i)^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)',segment):
            raise ValueError('Reserved Windows device path')
    return value


def _short_name(path):
    name=path.rsplit('/',1)[-1]
    if len(name)>48:
        name=name[:31]+'-'+hashlib.sha256(path.encode()).hexdigest()[:8]+name[-8:]
    return name


def _local_candidate(group,path):
    name=_short_name(path);parts=path.split('/')
    root=PREFIX+('/gui' if group=='GUI' else '/'+group)
    if group=='GUI':
        if path.startswith('tools/'):
            folder='source'
        elif 'evidence' in parts or 'failure-evidence' in parts:
            folder='evidence'
        else:
            return root+'/'+name
    elif 'bases' in parts:
        folder='raw'
    elif 'postprocess' in parts:
        folder='post'
    elif 'configs' in parts:
        folder='config'
    elif 'masks' in parts:
        folder='mask'
    elif 'classes' in parts:
        folder='classes'
    elif 'logs' in parts:
        folder='log'
    elif path.startswith('tools/') or 'frozen-numerical-sources' in parts:
        folder='source'
    else:
        folder='meta'
    if folder in ('source','meta','evidence'):
        name=hashlib.sha256(path.encode()).hexdigest()[:8]+'-'+name
    return root+'/'+folder+'/'+name


def validate_entries(entries):
    if not isinstance(entries,list) or not entries:
        raise ValueError('Nonempty immutable export required')
    seen=set()
    for row in entries:
        if not isinstance(row,dict) or row.get('group') not in ('HUMAN','HUMANSC4','GUI'):
            raise ValueError('Named human-reference publication group required')
        _path(row['path']);local=_path(row['local_path'])
        if not local.startswith(PREFIX+'/') or len(local)>100:
            raise ValueError('Short namespaced local output required')
        if not re.fullmatch('[0-9a-f]{40}',row['commit']) or not re.fullmatch('[0-9a-f]{64}',row['SHA256']):
            raise ValueError('Pinned commit and SHA256 required')
        if type(row['bytes'])is not int or not 0<=row['bytes']<=MAX_BYTES:
            raise ValueError('Bounded exact file size required')
        if local.casefold() in seen:
            raise ValueError('Case-insensitive compact output collision')
        seen.add(local.casefold())
    return entries


def build_entries(publications):
    """Convert [(HUMAN|HUMANSC4|GUI, publication)] into compact verified entries.

    Both colliding basenames receive a deterministic path+commit hash prefix, so
    mapping does not depend on input order. Repository paths remain unchanged
    for download URLs and audit; only local destination paths are shortened.
    """
    rows=[];sources={}
    for group,publication in publications:
        if group not in ('HUMAN','HUMANSC4','GUI') or not isinstance(publication,dict) or publication.get('status')!='published_readback_verified':
            raise ValueError('Fully verified named publication required')
        commit=publication.get('commit','')
        if not re.fullmatch('[0-9a-f]{40}',commit):
            raise ValueError('Immutable publication commit required')
        files=publication.get('files')
        if not isinstance(files,dict) or not files:
            raise ValueError('Publication file manifest required')
        for path,item in files.items():
            _path(path)
            if not isinstance(item,dict) or item.get('readback_passed')is not True:
                raise ValueError('Every exported file needs full prior readback')
            identity=(group,commit,path)
            signature=(item.get('SHA256'),item.get('bytes'))
            if identity in sources:
                if sources[identity]!=signature:
                    raise ValueError('Conflicting metadata for same immutable source')
                continue
            sources[identity]=signature
            rows.append(dict(group=group,path=path,commit=commit,SHA256=item['SHA256'],bytes=item['bytes'],local_path=_local_candidate(group,path)))
    collisions=Counter(row['local_path'].casefold() for row in rows)
    for row in rows:
        if collisions[row['local_path'].casefold()]>1:
            directory,name=row['local_path'].rsplit('/',1)
            digest=hashlib.sha256((row['commit']+'\0'+row['path']).encode()).hexdigest()[:8]
            row['local_path']=directory+'/'+digest+'-'+name
    rows.sort(key=lambda x:(x['local_path'].casefold(),x['commit'],x['path']))
    return validate_entries(rows)


def render(entries):
    validate_entries(entries)
    manifest=json.dumps(entries,ensure_ascii=True,separators=(',',':'))
    return SCRIPT.replace('__MANIFEST__',manifest).replace('__REPOSITORY__',REPO)


def manifest_document(entries):
    """Return a JSON-serializable manifest; no file access or saving is implied."""
    validate_entries(entries)
    return dict(schema='task1-human-compact-export-v1',repository=REPO,
                destination_prefix=PREFIX,files=[dict(row)for row in entries],
                total_bytes=sum(row['bytes']for row in entries),
                groups=sorted({row['group']for row in entries}),
                source_materials='declared_human_reference_hybrid_surrogates',
                Windows_saved=False,OneDrive_sync_verified=False,
                cloud_originals_deleted=False,storage_capacity_guard_enabled=False)


def powershell_document(entries):
    """Return the standalone ASCII PowerShell downloader for a generic Destination."""
    return render(entries)


SCRIPT=r'''#requires -Version 5.1
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$Destination)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$manifestJson=@'
__MANIFEST__
'@
$files=@($manifestJson | ConvertFrom-Json)
$repository='__REPOSITORY__'
if($Destination -notmatch '^[A-Za-z]:[\\/]'){throw 'An absolute Windows drive path is required.'}
$rootPath=[IO.Path]::GetFullPath($Destination)
if($rootPath.Length -gt 3){$rootPath=$rootPath.TrimEnd([char[]]@('\','/'))}
$rootPrefix=$rootPath.TrimEnd([char[]]@('\','/'))+[IO.Path]::DirectorySeparatorChar
$lockStream=$null
$records=New-Object System.Collections.Generic.List[object]
$receipt=[ordered]@{schema='task1-human-compact-windows-export-v1';status='started';started_utc=[DateTime]::UtcNow.ToString('o');destination=$rootPath;Windows_files_SHA256_verified=$false;OneDrive_sync_verified=$false;cloud_originals_deleted=$false;files=$records;error=$null}
function Test-ExpectedFile([string]$Path,$Spec){
 if(!(Test-Path -LiteralPath $Path -PathType Leaf)){return $false}
 $file=Get-Item -LiteralPath $Path
 if($file.Length -ne [long]$Spec.bytes){throw('Existing size differs; preserved: '+$Path)}
 if((Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $Spec.SHA256){throw('Existing SHA256 differs; preserved: '+$Path)}
 return $true
}
try{
 [IO.Directory]::CreateDirectory($rootPath)|Out-Null
 $lockStream=[IO.File]::Open([IO.Path]::Combine($rootPath,'.tis-human-export.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
 $pending=New-Object System.Collections.Generic.List[object]
 $seen=New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
 [long]$requiredBytes=1048576
 foreach($spec in $files){
  if($spec.commit -notmatch '^[0-9a-f]{40}$' -or $spec.SHA256 -notmatch '^[0-9a-f]{64}$' -or [long]$spec.bytes -lt 0 -or [long]$spec.bytes -gt 67108864){throw 'Invalid immutable file manifest.'}
  $relative=[string]$spec.local_path
  if(!$relative.StartsWith('layer-human-20261025/') -or $relative.Length -gt 100 -or !($seen.Add($relative))){throw 'Invalid or colliding compact destination.'}
  foreach($segment in ($relative -split '/')){
   if(!$segment -or $segment -in @('.','..') -or $segment -match '[\\:"<>|?*\x00-\x1f]' -or $segment -match '[ .]$' -or $segment -match '^(?i:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)'){throw 'Unsafe local manifest path.'}
  }
  $local=[IO.Path]::GetFullPath([IO.Path]::Combine($rootPath,($relative -replace '/','\')))
  if(!$local.StartsWith($rootPrefix,[StringComparison]::OrdinalIgnoreCase)){throw 'Output escaped destination.'}
  if($local.Length -ge 248){throw('Path too long for conservative Windows compatibility: '+$local)}
  if(Test-ExpectedFile $local $spec){$records.Add([ordered]@{relative=$relative;repository_path=$spec.path;commit=$spec.commit;status='reused_SHA256_verified';SHA256=$spec.SHA256;bytes=[long]$spec.bytes})}
  else{
   if(Test-Path -LiteralPath $local){throw('Destination is not a file; preserved: '+$local)}
   $pending.Add([pscustomobject]@{spec=$spec;relative=$relative;local=$local})
   $requiredBytes += [long]$spec.bytes
  }
 }
 $drive=New-Object IO.DriveInfo ([IO.Path]::GetPathRoot($rootPath))
 # Storage-capacity preflight is disabled by explicit user instruction. OS failures preserve partial files.
 $receipt['estimated_local_download_bytes']=$requiredBytes
 $receipt['storage_capacity_guard_enabled']=$false
 $receipt['observed_destination_free_bytes']=$drive.AvailableFreeSpace
 foreach($item in $pending){
  $spec=$item.spec
  $staging=[IO.Path]::Combine($rootPath,'layer-human-20261025','._partial')
  [IO.Directory]::CreateDirectory($staging)|Out-Null
  $partial=[IO.Path]::Combine($staging,([Guid]::NewGuid().ToString('N')+'.part'))
  if($partial.Length -ge 248){throw 'Partial path too long; no results deleted.'}
  $urlPath=(($spec.path -split '/')|ForEach-Object{[Uri]::EscapeDataString($_)}) -join '/'
  $url='https://raw.githubusercontent.com/'+$repository+'/'+$spec.commit+'/'+$urlPath
  $record=[ordered]@{relative=$item.relative;repository_path=$spec.path;commit=$spec.commit;status='downloading';SHA256=$spec.SHA256;bytes=[long]$spec.bytes;partial=$partial}
  $records.Add($record)
  Write-Host('Downloading '+$item.relative)
  Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $partial -TimeoutSec 120
  if(!(Test-ExpectedFile $partial $spec)){throw 'Downloaded file is absent.'}
  [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($item.local))|Out-Null
  [IO.File]::Move($partial,$item.local)
  if(!(Test-ExpectedFile $item.local $spec)){throw 'Final file verification failed.'}
  $record['status']='downloaded_SHA256_verified'
 }
 $receipt.status='Windows_files_verified_OneDrive_sync_unverified'
 $receipt.Windows_files_SHA256_verified=$true
 Write-Host 'All requested files saved and SHA256 verified. OneDrive synchronization is NOT verified.'
}catch{
 $receipt.status='failed_preserved';$receipt.error=$_.Exception.Message
 Write-Host('Stopped; originals and partial downloads preserved: '+$receipt.error)
 throw
}finally{
 $receipt['finished_utc']=[DateTime]::UtcNow.ToString('o')
 if($null -ne $lockStream){
  try{
   $receiptPath=[IO.Path]::Combine($rootPath,('tis-human-export-'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfff')+'-'+[Guid]::NewGuid().ToString('N').Substring(0,8)+'.json'))
   $bytes=[Text.Encoding]::UTF8.GetBytes(($receipt|ConvertTo-Json -Depth 10))
   $stream=[IO.File]::Open($receiptPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
   try{$stream.Write($bytes,0,$bytes.Length)}finally{$stream.Dispose()}
   Write-Host('Receipt: '+$receiptPath)
  }finally{$lockStream.Dispose()}
 }
}
'''
