#Requires -Version 5.1
<#
.SYNOPSIS
    Simple wrapper to run a Dentrix sync.

.DESCRIPTION
    Activates the Python venv and runs sync_dentrix.py with the given
    object type and limit.  Designed for field technicians who just need
    a one-liner.

.PARAMETER ObjectType
    What to sync: patients, appointments, providers, or all.

.PARAMETER Limit
    Maximum number of records to fetch (default 100).

.PARAMETER Since
    Optional ISO-8601 timestamp for incremental sync.

.PARAMETER DryRun
    Fetch and normalize records but do NOT post to the backend.

.EXAMPLE
    .\scripts\run_dentrix_sync.ps1 patients 100
    .\scripts\run_dentrix_sync.ps1 all 50
    .\scripts\run_dentrix_sync.ps1 patients 10 -DryRun
    .\scripts\run_dentrix_sync.ps1 appointments 200 -Since 2025-06-01T00:00:00
#>

param(
    [Parameter(Position = 0)]
    [ValidateSet("patients", "appointments", "providers", "all")]
    [string]$ObjectType = "patients",

    [Parameter(Position = 1)]
    [int]$Limit = 100,

    [string]$Since,

    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Resolve paths ─────────────────────────────────────────────────────────
$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectDir = Split-Path -Parent $ScriptDir
$VenvPython = Join-Path $ProjectDir ".venv\Scripts\python.exe"
$SyncScript = Join-Path $ScriptDir "sync_dentrix.py"
$EnvFile    = Join-Path $ProjectDir ".env"

# ── Pre-flight checks ────────────────────────────────────────────────────
if (-not (Test-Path $VenvPython)) {
    Write-Host ""
    Write-Host "  ERROR: Virtual environment not found at .venv\" -ForegroundColor Red
    Write-Host "  Run setup first:  .\scripts\setup_dentrix.ps1" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

if (-not (Test-Path $SyncScript)) {
    Write-Host ""
    Write-Host "  ERROR: sync_dentrix.py not found at scripts\" -ForegroundColor Red
    Write-Host "  Make sure you're running from the ai_backend directory." -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

if (-not (Test-Path $EnvFile)) {
    Write-Host ""
    Write-Host "  ERROR: .env file not found." -ForegroundColor Red
    Write-Host "  Run:  .\scripts\setup_env.ps1" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

# ── Build command ─────────────────────────────────────────────────────────
$args_list = @($SyncScript, "--object", $ObjectType, "--limit", $Limit)

if ($Since) {
    $args_list += @("--since", $Since)
}

if ($DryRun) {
    $args_list += "--dry-run"
}

# ── Run ───────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "  Dentrix Sync" -ForegroundColor Cyan
Write-Host "  ─────────────────────────────────────" -ForegroundColor Cyan
Write-Host "  Object : $ObjectType" -ForegroundColor White
Write-Host "  Limit  : $Limit" -ForegroundColor White
if ($Since)  { Write-Host "  Since  : $Since" -ForegroundColor White }
if ($DryRun) { Write-Host "  Mode   : DRY RUN (no POST)" -ForegroundColor Yellow }
Write-Host "  ─────────────────────────────────────" -ForegroundColor Cyan
Write-Host ""

Push-Location $ProjectDir
try {
    & $VenvPython @args_list
    $exitCode = $LASTEXITCODE
} finally {
    Pop-Location
}

if ($exitCode -eq 0) {
    Write-Host ""
    Write-Host "  Sync completed successfully." -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "  Sync finished with errors (exit code $exitCode)." -ForegroundColor Red
    Write-Host "  Check dentrix_sync.log for details." -ForegroundColor Yellow
    Write-Host ""
}

exit $exitCode
