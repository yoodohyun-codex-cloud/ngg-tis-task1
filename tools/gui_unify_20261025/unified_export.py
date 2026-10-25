"""Pure hierarchy-preserving Windows exporter for the offline unified TIS GUI.

No filesystem/network work occurs on import. The owner passes readback-verified
immutable publications. HTML relative paths remain valid after download.
"""
from __future__ import annotations
import hashlib,json,re
from pathlib import PurePosixPath
REPO='yoodohyun-codex-cloud/ngg-tis-task1'
PREFIX='layer-unified-20261025'
DOC_PREFIX='docs/TASK1_UNIFIED_GUI_20261025/'
SOURCE_PREFIX='tools/gui_unify_20261025/'
MAX_BYTES=64*1024**2


def _path(value):
    if not isinstance(value,str)or not value or value.startswith('/')or str(PurePosixPath(value))!=value:
        raise ValueError('Canonical relative path required')
    for part in value.split('/'):
        if not part or part in('.','..')or part[-1]in(' ','.')or any(ord(c)<32 or c in '\\:\"<>|?*'for c in part):
            raise ValueError('Unsafe Windows path component')
        if re.match(r'(?i)^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)',part):
            raise ValueError('Reserved Windows device name')
    return value


def _local_path(path):
    # Crucial: no flattening or basename shortening for GUI documents/assets.
    # index.html -> views/*.html and every other relative reference keep their
    # exact positions. Collisions are rejected rather than silently renamed.
    if path.startswith(DOC_PREFIX):
        suffix=path[len(DOC_PREFIX):]
        _path(suffix)
        return PREFIX+'/gui/'+suffix
    if path.startswith(SOURCE_PREFIX):
        suffix=path[len(SOURCE_PREFIX):]
        _path(suffix)
        return PREFIX+'/source/'+suffix
    name=path.rsplit('/',1)[-1]
    if len(name)>40:name=name[:25]+'-'+hashlib.sha256(path.encode()).hexdigest()[:8]+name[-7:]
    return PREFIX+'/metadata/'+hashlib.sha256(path.encode()).hexdigest()[:8]+'-'+name


def validate_entries(entries):
    if not isinstance(entries,list)or not entries:raise ValueError('Nonempty immutable GUI export required')
    seen={}
    for row in entries:
        if not isinstance(row,dict)or row.get('group')!='GUI':raise ValueError('GUI publication group required')
        _path(row['path']);local=_path(row['local_path'])
        if not local.startswith(PREFIX+'/')or len(local)>100:raise ValueError('Short namespaced local output required')
        if not re.fullmatch('[0-9a-f]{40}',row['commit'])or not re.fullmatch('[0-9a-f]{64}',row['SHA256']):raise ValueError('Immutable commit/SHA256 required')
        if type(row['bytes'])is not int or not 0<=row['bytes']<=MAX_BYTES:raise ValueError('Bounded exact file bytes required')
        key=local.casefold()
        if key in seen:raise ValueError('Case-insensitive output collision; no GUI path may be renamed')
        seen[key]=True
        if row['path'].startswith(DOC_PREFIX)and local!=PREFIX+'/gui/'+row['path'][len(DOC_PREFIX):]:
            raise ValueError('GUI relative hierarchy must remain identical')
    if PREFIX+'/gui/index.html'not in {x['local_path']for x in entries}:raise ValueError('Unified GUI entrypoint missing')
    return entries


def build_entries(publications):
    rows=[];identities={}
    for group,publication in publications:
        if group!='GUI'or not isinstance(publication,dict)or publication.get('status')!='published_readback_verified':raise ValueError('Fully readback-verified GUI publication required')
        commit=publication.get('commit','');files=publication.get('files')
        if not re.fullmatch('[0-9a-f]{40}',commit)or not isinstance(files,dict)or not files:raise ValueError('Immutable complete publication manifest required')
        for path,item in files.items():
            _path(path)
            if not isinstance(item,dict)or item.get('readback_passed')is not True:raise ValueError('Every exported file must have full prior readback')
            identity=(group,commit,path);signature=(item.get('SHA256'),item.get('bytes'))
            if identity in identities:
                if identities[identity]!=signature:raise ValueError('Conflicting same-object metadata')
                continue
            identities[identity]=signature
            rows.append(dict(group='GUI',path=path,commit=commit,SHA256=item['SHA256'],bytes=item['bytes'],local_path=_local_path(path)))
    rows.sort(key=lambda x:(x['local_path'].casefold(),x['commit'],x['path']))
    return validate_entries(rows)


def manifest_document(entries):
    validate_entries(entries)
    return dict(schema='task1-unified-gui-hierarchical-export-v1',repository=REPO,destination_prefix=PREFIX,
        files=[dict(x)for x in entries],total_bytes=sum(x['bytes']for x in entries),groups=['GUI'],
        entry_point=PREFIX+'/gui/index.html',GUI_relative_hierarchy_preserved=True,GUI_paths_flattened=False,
        optional_archives=[x['local_path']for x in entries if x['path'].lower().endswith('.zip')],archives_automatically_extracted=False,
        exporter_source_module='unified_export.py',exporter_source_verification='Parent owns source hash pinning and immutable full publication readback',
        Windows_saved=False,OneDrive_sync_verified=False,cloud_originals_deleted=False,storage_capacity_guard_enabled=False)


def render(entries):
    validate_entries(entries)
    encoded=json.dumps(entries,ensure_ascii=True,separators=(',',':'))
    return SCRIPT.replace('__MANIFEST__',encoded).replace('__REPOSITORY__',REPO)


def powershell_document(entries):return render(entries)


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
$receipt=[ordered]@{schema='task1-unified-gui-windows-export-v1';status='started';started_utc=[DateTime]::UtcNow.ToString('o');destination=$rootPath;Windows_files_SHA256_verified=$false;OneDrive_sync_verified=$false;cloud_originals_deleted=$false;files=$records;error=$null}
function Test-ExpectedFile([string]$Path,$Spec){
 if(!(Test-Path -LiteralPath $Path -PathType Leaf)){return $false}
 $file=Get-Item -LiteralPath $Path
 if($file.Length -ne [long]$Spec.bytes){throw('Existing size differs; preserved: '+$Path)}
 if((Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $Spec.SHA256){throw('Existing SHA256 differs; preserved: '+$Path)}
 return $true
}
try{
 [IO.Directory]::CreateDirectory($rootPath)|Out-Null
 $lockStream=[IO.File]::Open([IO.Path]::Combine($rootPath,'.tis-unified-gui-export.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
 $pending=New-Object System.Collections.Generic.List[object]
 $seen=New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
 [long]$requiredBytes=1048576
 foreach($spec in $files){
  if($spec.commit -notmatch '^[0-9a-f]{40}$' -or $spec.SHA256 -notmatch '^[0-9a-f]{64}$' -or [long]$spec.bytes -lt 0 -or [long]$spec.bytes -gt 67108864){throw 'Invalid immutable file manifest.'}
  $relative=[string]$spec.local_path
  if(!$relative.StartsWith('layer-unified-20261025/') -or $relative.Length -gt 100 -or !($seen.Add($relative))){throw 'Invalid or colliding compact destination.'}
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
  $staging=[IO.Path]::Combine($rootPath,'layer-unified-20261025','._partial')
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
   $receiptPath=[IO.Path]::Combine($rootPath,('tis-unified-gui-export-'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfff')+'-'+[Guid]::NewGuid().ToString('N').Substring(0,8)+'.json'))
   $bytes=[Text.Encoding]::UTF8.GetBytes(($receipt|ConvertTo-Json -Depth 10))
   $stream=[IO.File]::Open($receiptPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
   try{$stream.Write($bytes,0,$bytes.Length)}finally{$stream.Dispose()}
   Write-Host('Receipt: '+$receiptPath)
  }finally{$lockStream.Dispose()}
 }
}
'''
