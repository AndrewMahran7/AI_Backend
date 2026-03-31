#Requires -Version 5.1
<#
.SYNOPSIS
    Interactive .env file generator for the Dentrix agent.

.DESCRIPTION
    Walks the technician through each required setting with prompts,
    defaults, and validation.  Produces a ready-to-use .env file.

    If a .env file already exists, offers to back it up before overwriting.

.NOTES
    Run from the ai_backend directory:
        .\scripts\setup_env.ps1
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

# ── Paths ─────────────────────────────────────────────────────────────────
$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectDir = Split-Path -Parent $ScriptDir
$EnvFile    = Join-Path $ProjectDir ".env"

# ── Helpers ───────────────────────────────────────────────────────────────
function Prompt-Value {
    param(
        [string]$Label,
        [string]$Default = "",
        [switch]$Required,
        [switch]$Secret
    )

    $prompt = "  $Label"
    if ($Default) { $prompt += " [$Default]" }
    $prompt += ": "

    while ($true) {
        if ($Secret) {
            $secStr = Read-Host -Prompt $prompt -AsSecureString
            $value = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
                [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secStr)
            )
        } else {
            $value = Read-Host -Prompt $prompt
        }

        if ([string]::IsNullOrWhiteSpace($value)) {
            if ($Default) { return $Default }
            if ($Required) {
                Write-Host "       This field is required." -ForegroundColor Red
                continue
            }
            return ""
        }
        return $value.Trim()
    }
}

function Prompt-Choice {
    param(
        [string]$Label,
        [string[]]$Options,
        [int]$Default = 0
    )

    Write-Host ""
    Write-Host "  $Label" -ForegroundColor Cyan
    for ($i = 0; $i -lt $Options.Length; $i++) {
        $marker = if ($i -eq $Default) { "*" } else { " " }
        Write-Host "    $marker $($i + 1)) $($Options[$i])"
    }

    $choice = Read-Host -Prompt "  Choose [default: $($Default + 1)]"
    if ([string]::IsNullOrWhiteSpace($choice)) { return $Default }

    $idx = [int]$choice - 1
    if ($idx -ge 0 -and $idx -lt $Options.Length) { return $idx }
    return $Default
}

# ══════════════════════════════════════════════════════════════════════════
Write-Host ""
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host "   Dentrix Agent — Environment Setup" -ForegroundColor Cyan
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  This wizard will create your .env configuration file." -ForegroundColor White
Write-Host "  Press Enter to accept the [default] value shown in brackets." -ForegroundColor Gray
Write-Host ""

# ── Backup existing .env ─────────────────────────────────────────────────
if (Test-Path $EnvFile) {
    Write-Host "  WARNING: .env file already exists." -ForegroundColor Yellow
    $overwrite = Read-Host -Prompt "  Overwrite? A backup will be saved. [y/N]"
    if ($overwrite -notmatch "^[yY]") {
        Write-Host "  Aborted. Existing .env unchanged." -ForegroundColor Yellow
        exit 0
    }
    $backupName = ".env.backup.$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    $backupPath = Join-Path $ProjectDir $backupName
    Copy-Item $EnvFile $backupPath
    Write-Host "  Backed up to $backupName" -ForegroundColor Green
    Write-Host ""
}

# ── Connection mode ──────────────────────────────────────────────────────
$mode = Prompt-Choice `
    -Label "How do you want to connect to Dentrix?" `
    -Options @(
        "DSN-based  (you already set up an ODBC System DSN)",
        "Driver-based  (connect directly — no DSN needed)"
    ) `
    -Default 1

$DSN = ""
$Driver = ""
$Server = ""
$Database = ""

if ($mode -eq 0) {
    # DSN mode
    Write-Host ""
    Write-Host "  ── ODBC DSN Settings ──" -ForegroundColor Cyan
    $DSN = Prompt-Value -Label "ODBC DSN name" -Default "DentrixDB" -Required
} else {
    # Driver mode
    Write-Host ""
    Write-Host "  ── ODBC Driver Settings ──" -ForegroundColor Cyan
    $Driver   = Prompt-Value -Label "ODBC driver"       -Default "{SQL Server}"
    $Server   = Prompt-Value -Label "Server\Instance"   -Default "localhost\INTUIT_DG" -Required
    $Database = Prompt-Value -Label "Database name"      -Default "DentrixDB" -Required
}

# ── Authentication ───────────────────────────────────────────────────────
Write-Host ""
Write-Host "  ── Authentication ──" -ForegroundColor Cyan

$authMode = Prompt-Choice `
    -Label "Authentication method:" `
    -Options @(
        "Windows Authentication  (Trusted_Connection — no password needed)",
        "SQL Server login  (username + password)"
    ) `
    -Default 0

$Username = ""
$Password = ""

if ($authMode -eq 1) {
    $Username = Prompt-Value -Label "SQL username" -Default "sa" -Required
    $Password = Prompt-Value -Label "SQL password" -Required -Secret
}

# ── Backend settings ─────────────────────────────────────────────────────
Write-Host ""
Write-Host "  ── Backend Settings ──" -ForegroundColor Cyan

$BackendUrl = Prompt-Value -Label "Backend URL" -Default "https://your-backend.example.com" -Required
$ApiPrefix  = Prompt-Value -Label "API prefix"  -Default "/api/v1"
$ApiKey     = Prompt-Value -Label "API key (if required)" -Default ""

# ── Sync settings ────────────────────────────────────────────────────────
Write-Host ""
Write-Host "  ── Sync Settings (press Enter for defaults) ──" -ForegroundColor Cyan

$BatchSize   = Prompt-Value -Label "Batch size"       -Default "100"
$MaxRetries  = Prompt-Value -Label "Max retries"      -Default "3"
$HttpTimeout = Prompt-Value -Label "HTTP timeout (s)" -Default "60"
$LogFile     = Prompt-Value -Label "Log file"         -Default "dentrix_sync.log"

# ── Write .env ───────────────────────────────────────────────────────────
$envContent = @"
# ════════════════════════════════════════════════════════════════════════
#  Dentrix Local Agent  —  Environment Configuration
#  Generated by setup_env.ps1 on $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
# ════════════════════════════════════════════════════════════════════════

# ── Dentrix ODBC Connection ─────────────────────────────────────────────
DENTRIX_ODBC_DSN=$DSN
DENTRIX_ODBC_DRIVER=$Driver
DENTRIX_ODBC_SERVER=$Server
DENTRIX_ODBC_DATABASE=$Database
DENTRIX_ODBC_USERNAME=$Username
DENTRIX_ODBC_PASSWORD=$Password
DENTRIX_ODBC_EXTRA=
DENTRIX_ODBC_TIMEOUT=30

# ── Backend API ─────────────────────────────────────────────────────────
DENTRIX_BACKEND_URL=$BackendUrl
DENTRIX_API_PREFIX=$ApiPrefix
DENTRIX_API_KEY=$ApiKey

# ── Sync Behaviour ──────────────────────────────────────────────────────
DENTRIX_BATCH_SIZE=$BatchSize
DENTRIX_MAX_RETRIES=$MaxRetries
DENTRIX_BACKOFF_BASE=2.0
DENTRIX_HTTP_TIMEOUT=$HttpTimeout

# ── Logging ─────────────────────────────────────────────────────────────
DENTRIX_LOG_FILE=$LogFile
"@

Set-Content -Path $EnvFile -Value $envContent -Encoding UTF8

Write-Host ""
Write-Host "  ============================================" -ForegroundColor Green
Write-Host "   .env file saved successfully!" -ForegroundColor Green
Write-Host "  ============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Location: $EnvFile" -ForegroundColor White
Write-Host ""
Write-Host "  Next step: test the connection" -ForegroundColor Cyan
Write-Host "    python scripts\test_dentrix_connection.py" -ForegroundColor Yellow
Write-Host ""
