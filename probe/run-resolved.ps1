# Phase 0 probe runner, stage 2: disambiguated UUID inputs + true empty case.
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $root ".env"
$env:QLOO_BASE_URL = "https://hackathon.api.qloo.com"
$env:QLOO_TRUSTED_BASE_URL = "https://hackathon.api.qloo.com"
$line = (Get-Content $envFile) -match '^QLOO_API_KEY=' | Select-Object -First 1
$env:QLOO_API_KEY = $line.Substring('QLOO_API_KEY='.Length).Trim()

$outDir = Join-Path $PSScriptRoot "out"
$inDir = Join-Path $PSScriptRoot "inputs"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
New-Item -ItemType Directory -Force -Path $inDir | Out-Null

$franklin = "CE9EE2BD-D7AE-4349-B627-3D051D98AE77"   # Franklin Barbecue, Austin TX place
$daftpunk = "012EF80C-B187-4ECB-9C3D-9CA5228B503C"   # Daft Punk artist
$miles    = "578CFC26-B696-449A-9655-3FB270DDA725"   # Miles Davis artist

$probes = @(
    @{ file = "describe.franklin_uuid";           op = "describe";               input = ('{"entity":"' + $franklin + '"}') },
    @{ file = "entity_tags.franklin_uuid";        op = "entity_tags";            input = ('{"entities":["' + $franklin + '"],"limit":15}') },
    @{ file = "where_popular.franklin_uuid";      op = "where_popular";          input = ('{"entity":"' + $franklin + '","within":"Austin, Texas","limit":10}') },
    @{ file = "compare_audiences.uuid";           op = "compare_audiences";      input = ('{"group_a":["' + $daftpunk + '"],"group_b":["' + $miles + '"],"limit":10}') },
    @{ file = "audience_demographics.franklin_uuid"; op = "audience_demographics"; input = ('{"entity":"' + $franklin + '","limit":10}') },
    @{ file = "trends.franklin_uuid";             op = "trends";                 input = ('{"entities":["' + $franklin + '"],"entity_type":"place","start_date":"2025-10-01","end_date":"2026-10-01"}') },
    @{ file = "find_tags.empty_semantic_false";   op = "find_tags";              input = '{"query":"quantum flux dining","semantic":false}' }
)

$summary = @()
foreach ($p in $probes) {
    $inPath = Join-Path $inDir ("{0}.json" -f $p.file)
    Set-Content -Path $inPath -Value $p.input -Encoding ascii
    $path = Join-Path $outDir ("{0}.json" -f $p.file)
    Write-Host ("-> {0}  ({1})" -f $p.file, $p.op)
    qloo exec $p.op --input-file $inPath > $path 2>&1
    $raw = Get-Content $path -Raw
    try {
        $json = $raw | ConvertFrom-Json
        $status = if ($json.status) { $json.status } elseif ($json.error) { "error/$($json.error.code)" } else { "UNPARSEABLE" }
        $count = if ($json.result_count -ne $null) { $json.result_count } else { "-" }
        $summary += [pscustomobject]@{ file = $p.file; status = $status; result_count = $count }
    } catch {
        $summary += [pscustomobject]@{ file = $p.file; status = "UNPARSEABLE"; result_count = "-" }
    }
    Start-Sleep -Seconds 2
}
$summary | Format-Table -AutoSize
