# Phase 0 probe runner: executes the planned probe set once, sequentially,
# capturing raw stdout JSON to probe/out/. Loads QLOO_API_KEY from ../.env.
# Usage: powershell -File probe\run-probes.ps1
# Quota hygiene: ~13 calls total, 2s spacing. Do not loop.
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

$probes = @(
    @{ file = "find_tags.jazz";              op = "find_tags";             input = '{"query":"jazz"}' },
    @{ file = "find_tags.natural_wine";      op = "find_tags";             input = '{"query":"natural wine"}' },
    @{ file = "find_tags.tacos";             op = "find_tags";             input = '{"query":"tacos"}' },
    @{ file = "find_tags.listening_bar";     op = "find_tags";             input = '{"query":"listening bar"}' },
    @{ file = "find_tags.empty_case";        op = "find_tags";             input = '{"query":"quantum flux dining"}' },
    @{ file = "describe.franklin_barbecue";  op = "describe";              input = '{"entity":"Franklin Barbecue"}' },
    @{ file = "entity_tags.franklin_barbecue"; op = "entity_tags";         input = '{"entities":["Franklin Barbecue"],"limit":15}' },
    @{ file = "recommend.jazz_brooklyn";     op = "recommend";             input = '{"target_type":"artist","signal_tags":["urn:tag:genre:music:jazz"],"signal_location":"Brooklyn, New York","demographic":"millennials","limit":5}' },
    @{ file = "rank.coffee_brands";          op = "rank";                  input = '{"options":["Blue Bottle Coffee","Stumptown Coffee Roasters","Intelligentsia Coffee"],"option_type":"brand","signal_location":"Brooklyn, New York","demographic":"millennials"}' },
    @{ file = "where_popular.franklin_austin"; op = "where_popular";       input = '{"entity":"Franklin Barbecue","entity_type":"place","within":"Austin, Texas"}' },
    @{ file = "compare_audiences.two_music"; op = "compare_audiences";     input = '{"group_a":["Daft Punk"],"group_b":["Miles Davis"]}' },
    @{ file = "audience_demographics.franklin"; op = "audience_demographics"; input = '{"entity":"Franklin Barbecue","entity_type":"place"}' },
    @{ file = "trends.franklin_12mo";        op = "trends";                input = '{"entities":["Franklin Barbecue"],"entity_type":"place","start_date":"2025-10-01","end_date":"2026-10-01"}' }
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
