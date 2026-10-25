#requires -Version 5.1
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$Destination)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$manifestJson=@'
[{"group":"GUI","path":"docs/TASK1_UNIFIED_GUI_20261025/evidence/build-receipt.json","commit":"1c2abc71b0312ac79f6e1b598554b4b5577ac329","SHA256":"2f4bca3ec279d95c390aacdfa2f102291f6610e9017996bae2594a8e3a4eecb8","bytes":2879,"local_path":"layer-unified-20261025/gui/evidence/build-receipt.json"},{"group":"GUI","path":"docs/TASK1_UNIFIED_GUI_20261025/evidence/registration.json","commit":"1c2abc71b0312ac79f6e1b598554b4b5577ac329","SHA256":"04367affa8143675b177bb85878f804ea3df32a04c0abbc93c51f9c03834e055","bytes":2294,"local_path":"layer-unified-20261025/gui/evidence/registration.json"},{"group":"GUI","path":"docs/TASK1_UNIFIED_GUI_20261025/first-build-failure.json","commit":"1c2abc71b0312ac79f6e1b598554b4b5577ac329","SHA256":"66922fb6704811eda7a358ece42f04b5473c46c167bd1b7fa0b8d293af5c113c","bytes":945,"local_path":"layer-unified-20261025/gui/first-build-failure.json"},{"group":"GUI","path":"docs/TASK1_UNIFIED_GUI_20261025/index.html","commit":"1c2abc71b0312ac79f6e1b598554b4b5577ac329","SHA256":"e3b14762433b1b6a6931676468d575d3af9e8bfa81dfd2f3431bd2b38de6e5ae","bytes":20637,"local_path":"layer-unified-20261025/gui/index.html"},{"group":"GUI","path":"docs/TASK1_UNIFIED_GUI_20261025/input-sha256.json","commit":"1c2abc71b0312ac79f6e1b598554b4b5577ac329","SHA256":"4e0b1ec13bfea625c279f0ab22e04b15c3c085f6e4591d838a0199076ba90f86","bytes":1305,"local_path":"layer-unified-20261025/gui/input-sha256.json"},{"group":"GUI","path":"docs/TASK1_UNIFIED_GUI_20261025/manifest.json","commit":"1c2abc71b0312ac79f6e1b598554b4b5577ac329","SHA256":"90e598f56dde0709cd42c1f1c0943e6327b39d26e2bd9aadd5693140d684455a","bytes":13097,"local_path":"layer-unified-20261025/gui/manifest.json"},{"group":"GUI","path":"docs/TASK1_UNIFIED_GUI_20261025/preview.jpg","commit":"1c2abc71b0312ac79f6e1b598554b4b5577ac329","SHA256":"08d0cb5392ef880529f24a02bfb8103af73485be9ee17e495d261fb95bddc129","bytes":201374,"local_path":"layer-unified-20261025/gui/preview.jpg"},{"group":"GUI","path":"docs/TASK1_UNIFIED_GUI_20261025/prior-build-failures.json","commit":"1c2abc71b0312ac79f6e1b598554b4b5577ac329","SHA256":"756e260b9046d55bdc1a95b3d71fd8715732e1cabd25ab6587378a8439e15ece","bytes":2954,"local_path":"layer-unified-20261025/gui/prior-build-failures.json"},{"group":"GUI","path":"docs/TASK1_UNIFIED_GUI_20261025/probe-view-manifest.json","commit":"1c2abc71b0312ac79f6e1b598554b4b5577ac329","SHA256":"d8de97d2a117d4c270f877b03441772ac8001b6b8925cc6e217a25008526f5b0","bytes":1774,"local_path":"layer-unified-20261025/gui/probe-view-manifest.json"},{"group":"GUI","path":"docs/TASK1_UNIFIED_GUI_20261025/requested-features-audit.json","commit":"1c2abc71b0312ac79f6e1b598554b4b5577ac329","SHA256":"cf7268c85c5d5e5ec4d44dbb7ce71c08fa0395e1553e2455b68f937ca145fea1","bytes":5798,"local_path":"layer-unified-20261025/gui/requested-features-audit.json"},{"group":"GUI","path":"docs/TASK1_UNIFIED_GUI_20261025/validation.json","commit":"1c2abc71b0312ac79f6e1b598554b4b5577ac329","SHA256":"955fd8c3f2f4d7e44d2b236c1b3ff606cc6bc99b2e3098abb7deeecfbb848f1d","bytes":2038,"local_path":"layer-unified-20261025/gui/validation.json"},{"group":"GUI","path":"docs/TASK1_UNIFIED_GUI_20261025/views/human-current.html","commit":"1c2abc71b0312ac79f6e1b598554b4b5577ac329","SHA256":"9cba879d335596dc9265be594000ee3d5ef95da5489670a22059b33a0ed7c6c1","bytes":18637368,"local_path":"layer-unified-20261025/gui/views/human-current.html"},{"group":"GUI","path":"docs/TASK1_UNIFIED_GUI_20261025/views/manual-phantom.html","commit":"1c2abc71b0312ac79f6e1b598554b4b5577ac329","SHA256":"7cf7db90092f0e0b3aa2a17a67af669b477b8f6579c159bbf473042c4d20e2d7","bytes":3810551,"local_path":"layer-unified-20261025/gui/views/manual-phantom.html"},{"group":"GUI","path":"docs/TASK1_UNIFIED_GUI_20261025/views/probes.html","commit":"1c2abc71b0312ac79f6e1b598554b4b5577ac329","SHA256":"c052f8efb5b5a4a5ad0766eabef165352d4963f0cc98ba9e9cb08f5a5632c6c6","bytes":952224,"local_path":"layer-unified-20261025/gui/views/probes.html"},{"group":"GUI","path":"docs/TASK1_UNIFIED_GUI_20261025/views/sc-sensitivity.html","commit":"1c2abc71b0312ac79f6e1b598554b4b5577ac329","SHA256":"f2e83adeb061c5fd844b08451d370d0e0cc1bc59074850d457eb397e02d680ed","bytes":17627797,"local_path":"layer-unified-20261025/gui/views/sc-sensitivity.html"},{"group":"GUI","path":"docs/TASK1_UNIFIED_GUI_20261025/views/top5-phantom.html","commit":"1c2abc71b0312ac79f6e1b598554b4b5577ac329","SHA256":"218a34f5acf90fa9f9898c9554ab332bbceb28a110de0ef430ee48558a77dd7d","bytes":1937565,"local_path":"layer-unified-20261025/gui/views/top5-phantom.html"},{"group":"GUI","path":"tools/gui_unify_20261025/export_wrapper.py","commit":"1c2abc71b0312ac79f6e1b598554b4b5577ac329","SHA256":"5a78b031d69eacacb6ea4343813a7acfa764b018282abf8500912fb8ab5bbc24","bytes":583,"local_path":"layer-unified-20261025/source/export_wrapper.py"},{"group":"GUI","path":"tools/gui_unify_20261025/probe_view.py","commit":"1c2abc71b0312ac79f6e1b598554b4b5577ac329","SHA256":"eee931a0f0ceb4701855e999200e03ee38552484cc47da59547ae5400f034fe9","bytes":21807,"local_path":"layer-unified-20261025/source/probe_view.py"},{"group":"GUI","path":"tools/gui_unify_20261025/top5_ranges.py","commit":"1c2abc71b0312ac79f6e1b598554b4b5577ac329","SHA256":"280aa7756151707c5ff09a830f0ce59e337c181f0ffb9ba426bbea948ff6c1b3","bytes":12435,"local_path":"layer-unified-20261025/source/top5_ranges.py"},{"group":"GUI","path":"tools/gui_unify_20261025/unified_export.py","commit":"1c2abc71b0312ac79f6e1b598554b4b5577ac329","SHA256":"1cfced9402b3ca1705a618b949d81196fae459644e20e3731a2181e0aba52ccb","bytes":11161,"local_path":"layer-unified-20261025/source/unified_export.py"},{"group":"GUI","path":"tools/gui_unify_20261025/unify_gui.py","commit":"1c2abc71b0312ac79f6e1b598554b4b5577ac329","SHA256":"15444238d339afbd0cf8d8c421f873872f6db516f8de59f153ce7d772b0e5b60","bytes":18974,"local_path":"layer-unified-20261025/source/unify_gui.py"},{"group":"GUI","path":"tools/gui_unify_20261025/unify_run.py","commit":"1c2abc71b0312ac79f6e1b598554b4b5577ac329","SHA256":"75f2db3bc03c0c0565de16b7b2277d5a7452425b951dcab13055c561b009eb29","bytes":25933,"local_path":"layer-unified-20261025/source/unify_run.py"}]
'@
$files=@($manifestJson | ConvertFrom-Json)
$repository='yoodohyun-codex-cloud/ngg-tis-task1'
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
