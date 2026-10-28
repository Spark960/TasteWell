# Restart the Tastewell backend on :8000 - kills the existing listener
# FIRST (a plain re-launch dies with bind-error 10048 and leaves the old
# process serving a stale code/key - the silent-restart trap), starts the
# new one, and asserts the new PID actually owns the port.
param([int]$Port = 8000)
$repo = Split-Path -Parent $PSScriptRoot
$logDir = Join-Path $env:TEMP "opencode"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$errLog = Join-Path $logDir "uvicorn.err.log"

$conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($conn) {
    $conn | Select-Object -Unique OwningProcess | ForEach-Object {
        Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
        Write-Output "killed old pid $($_.OwningProcess)"
    }
    Start-Sleep -Milliseconds 800
}

# Parse repo .env into this shell in the SAME process that launches uvicorn.
$lines = Get-Content (Join-Path $repo ".env")
foreach ($l in $lines) {
    if ($l -match '^([A-Z0-9_]+)=(.*)$') {
        [Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
    }
}
# Provider/model: .env wins; these defaults keep the historical Groq setup.
if (-not $env:LLM_PROVIDER) { $env:LLM_PROVIDER = "groq" }
if (-not $env:LLM_MODEL) { $env:LLM_MODEL = "openai/gpt-oss-120b" }
if (-not $env:QLOO_BIN) {
    $installedQloo = Join-Path ([Environment]::GetFolderPath("ApplicationData")) "npm\qloo.cmd"
    if (Test-Path -LiteralPath $installedQloo) { $env:QLOO_BIN = $installedQloo }
}

$localPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (Test-Path -LiteralPath $localPython) {
    $pythonExe = $localPython
    $pythonArgs = @("-m", "uvicorn", "app.main:app", "--port", "$Port")
} else {
    $pythonExe = "py"
    $pythonArgs = @("-3.12", "-m", "uvicorn", "app.main:app", "--port", "$Port")
}

$proc = Start-Process $pythonExe -ArgumentList $pythonArgs `
    -WorkingDirectory (Join-Path $repo "backend") -WindowStyle Hidden `
    -RedirectStandardError $errLog -PassThru
Start-Sleep -Seconds 5

$bound = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique
# NB: py.exe (the launcher = $proc.Id) spawns python3.12.exe as a child with
# a DIFFERENT pid, so compare port owner == $proc.Id is always false. Assert
# the real thing instead: the fresh log belongs to this launch and reports a
# successful bind.
Start-Sleep -Milliseconds 500
$log = (Get-Content $errLog -ErrorAction SilentlyContinue) -join "`n"
if ($bound -and $log -match "Uvicorn running on") {
    Write-Output "backend listening on :$Port - owner pid(s) $($bound -join ',') (launcher $($proc.Id), log: $errLog)"
} else {
    Write-Output "WARNING: :$Port owner pid(s) $($bound -join ','), launcher $($proc.Id) did not come up - see $errLog"
}
