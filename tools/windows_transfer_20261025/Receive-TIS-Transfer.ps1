[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Manifest,
    [Parameter(Mandatory = $true)][ValidatePattern('^[0-9a-fA-F]{64}$')][string]$ExpectedManifestSHA256,
    [Parameter(Mandatory = $true)][string]$Destination
)

# This receiver changes no execution policy, trust store, security setting or
# installed package. It does not extract archives or execute downloaded files.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
trap {
    [Console]::Error.WriteLine('Receiver aborted before completion. Existing artifacts and partial evidence are preserved; inspect the local state.')
    exit 1
}
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
    throw 'This receive receipt must be produced on the actual Windows receiver.'
}

function Assert-SafeRelative([string]$PathText) {
    if ([string]::IsNullOrWhiteSpace($PathText) -or $PathText.Contains('\') -or $PathText.Contains(':') -or [IO.Path]::IsPathRooted($PathText)) {
        throw 'Unsafe relative path in manifest.'
    }
    foreach ($segment in $PathText.Split('/')) {
        if ($segment -eq '' -or $segment -eq '.' -or $segment -eq '..' -or
            $segment -match '[<>"|?*\x00-\x1f]' -or $segment -match '[ .]$' -or
            $segment -match '^(?i:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)') {
            throw 'Unsafe Windows path component in manifest.'
        }
    }
}

function Assert-NoReparse([string]$FullPath) {
    $cursor = [IO.Path]::GetFullPath($FullPath)
    while (-not [string]::IsNullOrEmpty($cursor)) {
        if (Test-Path -LiteralPath $cursor) {
            $info = Get-Item -LiteralPath $cursor -Force
            if (($info.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                throw 'Receiver refuses an existing reparse point in its path.'
            }
        }
        $parent = [IO.Directory]::GetParent($cursor)
        if ($null -eq $parent) { break }
        $cursor = $parent.FullName
    }
}

function Resolve-SafeTarget([string]$Relative) {
    Assert-SafeRelative $Relative
    $target = [IO.Path]::GetFullPath((Join-Path $script:Root $Relative.Replace('/', [IO.Path]::DirectorySeparatorChar)))
    if (-not $target.StartsWith($script:RootPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Resolved destination escapes the receiver root.'
    }
    Assert-NoReparse $target
    return $target
}

$actualManifestSHA = (Get-FileHash -LiteralPath $Manifest -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualManifestSHA -ne $ExpectedManifestSHA256.ToLowerInvariant()) {
    throw 'Manifest SHA256 mismatch. No downloads started.'
}
$doc = Get-Content -LiteralPath $Manifest -Raw -Encoding UTF8 | ConvertFrom-Json
if ($doc.schema -ne 'task1-safe-windows-transfer-manifest-v1' -or
    $doc.repository -ne 'yoodohyun-codex-cloud/ngg-tis-task1' -or
    $doc.public_reference_commit -cnotmatch '^[0-9a-f]{40}$' -or
    $doc.Windows_backup_complete -ne $false) {
    throw 'Manifest identity or fixed-commit contract is invalid.'
}

$script:Root = [IO.Path]::GetFullPath($Destination)
Assert-NoReparse $script:Root
[IO.Directory]::CreateDirectory($script:Root) | Out-Null
$script:RootPrefix = $script:Root.TrimEnd('\', '/') + [IO.Path]::DirectorySeparatorChar
$identities = @{}
$downloadItems = New-Object 'System.Collections.Generic.List[object]'
$allowedSuffixes = @('', '.json', '.py', '.java', '.class', '.md', '.txt', '.log', '.csv', '.csv.gz', '.bin', '.bin.gz', '.npz', '.npy', '.f64le', '.tar.gz', '.properties', '.ps1', '.xlsx', '.html', '.png', '.svg', '.zip', '.artifact')
foreach ($item in @($doc.files) + @($doc.logical_file_aliases)) {
    $keys = @($item.PSObject.Properties.Name | Sort-Object)
    $wanted = @('SHA256', 'bytes', 'fixed_commit', 'repo_relative_path', 'safe_destination_relative_path') | Sort-Object
    if (($keys -join '|') -ne ($wanted -join '|') -or
        $item.fixed_commit -cnotmatch '^[0-9a-f]{40}$' -or
        $item.SHA256 -cnotmatch '^[0-9a-f]{64}$' -or
        $item.bytes -isnot [ValueType] -or $item.bytes -is [bool] -or
        [decimal]$item.bytes -lt 0 -or [decimal]$item.bytes -ne [decimal]([long]$item.bytes)) {
        throw 'Invalid per-file metadata.'
    }
    Assert-SafeRelative $item.repo_relative_path
    Assert-SafeRelative $item.safe_destination_relative_path
    if ($item.safe_destination_relative_path -cnotmatch ('^objects/' + $item.SHA256 + '(?:\.[A-Za-z0-9_-]+){0,3}$')) {
        throw 'Download destination is not full-SHA256 addressed.'
    }
    $suffix = $item.safe_destination_relative_path.Substring(('objects/' + $item.SHA256).Length)
    if ($suffix -cnotin $allowedSuffixes) { throw 'Unexpected destination extension.' }
    $key = $item.safe_destination_relative_path.ToLowerInvariant()
    $identity = $item.SHA256 + ':' + [string]$item.bytes
    if ($identities.ContainsKey($key)) {
        if ($identities[$key] -ne $identity) { throw 'Conflicting duplicate download destination.' }
    } else {
        $identities[$key] = $identity
        $downloadItems.Add($item)
    }
    Resolve-SafeTarget $item.safe_destination_relative_path | Out-Null
}
if ($downloadItems.Count -eq 0) { throw 'Manifest contains no downloadable files.' }

Add-Type -AssemblyName System.Net.Http
$handler = [System.Net.Http.HttpClientHandler]::new()
$handler.AllowAutoRedirect = $false
$client = [System.Net.Http.HttpClient]::new($handler)
$client.Timeout = [TimeSpan]::FromMinutes(10)
$client.DefaultRequestHeaders.UserAgent.ParseAdd('TIS-fixed-commit-receiver/1.0')
$rows = New-Object 'System.Collections.Generic.List[object]'
$started = [DateTime]::UtcNow.ToString('o')
try {
    foreach ($item in $downloadItems) {
        $relative = [string]$item.safe_destination_relative_path
        $partialRelative = $null
        $partialCreated = $false
        $status = 'not_started'
        try {
            $target = Resolve-SafeTarget $relative
            if (Test-Path -LiteralPath $target) {
                $existing = Get-Item -LiteralPath $target -Force
                if ($existing.PSIsContainer -or $existing.Length -ne [long]$item.bytes -or
                    (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant() -ne $item.SHA256) {
                    $status = 'existing_mismatch_preserved'
                    throw 'Existing target mismatch; preserved without replacement.'
                }
                $status = 'existing_file_verified'
            } else {
                $parent = [IO.Path]::GetDirectoryName($target)
                Assert-NoReparse $parent
                [IO.Directory]::CreateDirectory($parent) | Out-Null
                Assert-NoReparse $parent
                $partialRelative = $relative + '.partial.' + [Guid]::NewGuid().ToString('N')
                $partial = Resolve-SafeTarget $partialRelative
                $encodedPath = (($item.repo_relative_path.Split('/') | ForEach-Object { [Uri]::EscapeDataString($_) }) -join '/')
                $url = 'https://raw.githubusercontent.com/' + $doc.repository + '/' + $item.fixed_commit + '/' + $encodedPath
                $response = $null; $stream = $null; $body = $null
                $cancel = [Threading.CancellationTokenSource]::new()
                $cancel.CancelAfter([TimeSpan]::FromMinutes(10))
                try {
                    $response = $client.GetAsync($url, [Net.Http.HttpCompletionOption]::ResponseHeadersRead, $cancel.Token).GetAwaiter().GetResult()
                    if ([int]$response.StatusCode -ne 200) {
                        $status = 'HTTP_status_' + [string][int]$response.StatusCode
                        throw 'Expected a direct successful fixed-host response.'
                    }
                    if ($null -ne $response.Content.Headers.ContentLength -and
                        [long]$response.Content.Headers.ContentLength -ne [long]$item.bytes) {
                        $status = 'HTTP_length_mismatch'
                        throw 'Unexpected HTTP content length.'
                    }
                    $stream = [IO.FileStream]::new($partial, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
                    $partialCreated = $true
                    $body = $response.Content.ReadAsStreamAsync().GetAwaiter().GetResult()
                    $buffer = New-Object byte[] 65536
                    [long]$count = 0
                    while (($read = $body.ReadAsync($buffer, 0, $buffer.Length, $cancel.Token).GetAwaiter().GetResult()) -gt 0) {
                        $stream.Write($buffer, 0, $read); $count += $read
                        if ($count -gt [long]$item.bytes) {
                            $status = 'download_length_exceeded_partial_preserved'
                            throw 'Download exceeded its declared byte count.'
                        }
                    }
                    $stream.Flush($true)
                } finally {
                    if ($null -ne $body) { $body.Dispose() }
                    if ($null -ne $stream) { $stream.Dispose() }
                    if ($null -ne $response) { $response.Dispose() }
                    $cancel.Dispose()
                }
                $received = Get-Item -LiteralPath $partial -Force
                if ($received.Length -ne [long]$item.bytes -or
                    (Get-FileHash -LiteralPath $partial -Algorithm SHA256).Hash.ToLowerInvariant() -ne $item.SHA256) {
                    $status = 'download_integrity_failed_partial_preserved'
                    throw 'Downloaded byte count or SHA256 mismatch.'
                }
                Assert-NoReparse $parent
                # Move has no replace flag: an external racing file is preserved.
                [IO.File]::Move($partial, $target)
                $partialRelative = $null
                $status = 'downloaded_file_verified'
            }
        } catch {
            if (-not $partialCreated) { $partialRelative = $null }
            if ($status -eq 'not_started') { $status = 'receive_failed_evidence_preserved' }
            # Deliberately omit exception text: it may contain private root paths.
        }
        $rows.Add([ordered]@{ relative_destination = $relative; expected_bytes = [long]$item.bytes;
            expected_SHA256 = $item.SHA256; status = $status; preserved_partial_relative_path = $partialRelative })
        Write-Output ($relative + ': ' + $status)
    }
} finally {
    $client.Dispose(); $handler.Dispose()
}
$allVerified = @($rows | Where-Object { $_.status -notin @('downloaded_file_verified', 'existing_file_verified') }).Count -eq 0
$dependenciesComplete = @($doc.durability_gaps).Count -eq 0 -and @($doc.required_local_only_raw_arrays).Count -eq 0
$receipt = [ordered]@{ schema = 'task1-Windows-receive-receipt-v1'; started_UTC = $started;
    finished_UTC = [DateTime]::UtcNow.ToString('o'); manifest_SHA256 = $actualManifestSHA;
    public_reference_commit = $doc.public_reference_commit; all_manifest_files_verified = $allVerified;
    required_dependencies_addressed_by_manifest = $dependenciesComplete;
    Windows_backup_complete = ($allVerified -and $dependenciesComplete); OneDrive_sync_verified = $false;
    auto_extraction_performed = $false; downloaded_code_executed = $false; files = @($rows.ToArray()) }
$receiptRelative = 'receive-receipt-' + [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ') + '-' + [Guid]::NewGuid().ToString('N') + '.json'
$receiptTarget = Resolve-SafeTarget $receiptRelative
$receiptText = $receipt | ConvertTo-Json -Depth 12
$receiptStream = [IO.FileStream]::new($receiptTarget, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
try {
    $receiptBytes = ([Text.UTF8Encoding]::new($false)).GetBytes($receiptText + [Environment]::NewLine)
    $receiptStream.Write($receiptBytes, 0, $receiptBytes.Length); $receiptStream.Flush($true)
} finally { $receiptStream.Dispose() }
Write-Output ('Relative receipt: ' + $receiptRelative)
Write-Output ('All manifest files verified: ' + $allVerified)
Write-Output ('Windows backup complete for required manifest scope: ' + $receipt.Windows_backup_complete)
Write-Output 'OneDrive synchronization remains unverified.'
if (-not $allVerified -or -not $dependenciesComplete) { exit 2 }
