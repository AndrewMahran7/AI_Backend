#Requires -Version 5.1
<#
.SYNOPSIS
    Automated Dentrix agent setup for dental office Windows PCs.

.DESCRIPTION
    This script performs a complete setup of the Dentrix data-extraction agent:
      1. Verifies Python 3.11+ is installed
      2. Creates a virtual environment (if missing)
      3. Installs pip dependencies
      4. Launches the interactive .env generator (if .env missing)
      5. Tests the ODBC connection to Dentrix
      6. Tests HTTPS connectivity to the backend
      7. Prints a PASS / FAIL summary

    Designed for field technicians — fails gracefully with clear messages.

.NOTES
    Run from the ai_backend directory:
        .\scripts\setup_dentrix.ps1
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

# ── Paths ─────────────────────────────────────────────────────────────────
$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectDir = Split-Path -Parent $ScriptDir
$VenvDir    = Join-Path $ProjectDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$VenvPip    = Join-Path $VenvDir "Scripts\pip.exe"
$ReqFile    = Join-Path $ProjectDir "requirements.txt"
$EnvFile    = Join-Path $ProjectDir ".env"
$EnvExample = Join-Path $ProjectDir ".env.dentrix.example"
$SetupEnv   = Join-Path $ScriptDir "setup_env.ps1"
$TestScript = Join-Path $ScriptDir "test_dentrix_connection.py"

# ── Helpers ───────────────────────────────────────────────────────────────
$passed = 0
$failed = 0

function Write-Step {
    param([string]$Number, [string]$Label)
    Write-Host ""
    Write-Host "  [$Number] $Label" -ForegroundColor Cyan
    Write-Host "  $('-' * 50)"
}

function Write-Pass {
    param([string]$Message)
    $script:passed++
    Write-Host "       PASS  $Message" -ForegroundColor Green
}

function Write-Fail {
    param([string]$Message)
    $script:failed++
    Write-Host "       FAIL  $Message" -ForegroundColor Red
}

function Write-Info {
    param([string]$Message)
    Write-Host "       INFO  $Message" -ForegroundColor Yellow
}

# ══════════════════════════════════════════════════════════════════════════
Write-Host ""
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host "   Dentrix Agent Setup" -ForegroundColor Cyan
Write-Host "  ============================================" -ForegroundColor Cyan

# ── Step 1: Check Python ─────────────────────────────────────────────────
Write-Step "1/6" "Checking Python installation"

$pythonCmd = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($ver -match "Python (\d+)\.(\d+)") {
            $major = [int]$Matches[1]
            $minor = [int]$Matches[2]
            if ($major -ge 3 -and $minor -ge 11) {
                $pythonCmd = $cmd
                break
            }
        }
    } catch {
        # Command not found, try next
    }
}

if ($pythonCmd) {
    $pyVer = & $pythonCmd --version 2>&1
    Write-Pass "$pyVer"
} else {
    Write-Fail "Python 3.11+ not found. Install from https://python.org/downloads/"
    Write-Host ""
    Write-Host "  Setup cannot continue without Python 3.11+." -ForegroundColor Red
    Write-Host "  Download: https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

# ── Step 2: Virtual environment ──────────────────────────────────────────
Write-Step "2/6" "Setting up virtual environment"

if (Test-Path $VenvPython) {
    Write-Pass "Virtual environment exists at .venv/"
} else {
    Write-Info "Creating virtual environment..."
    & $pythonCmd -m venv $VenvDir 2>&1 | Out-Null
    if (Test-Path $VenvPython) {
        Write-Pass "Virtual environment created at .venv/"
    } else {
        Write-Fail "Failed to create virtual environment"
        Write-Host "       Try manually: $pythonCmd -m venv .venv" -ForegroundColor Yellow
    }
}

# ── Step 3: Install dependencies ─────────────────────────────────────────
Write-Step "3/6" "Installing Python dependencies"

if (Test-Path $VenvPip) {
    Write-Info "Running pip install -r requirements.txt ..."
    $pipOutput = & $VenvPip install -r $ReqFile 2>&1
    $pipExit = $LASTEXITCODE

    # Check for pyodbc specifically
    $pyodbcCheck = & $VenvPython -c "import pyodbc; print(pyodbc.version)" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Pass "Dependencies installed (pyodbc $pyodbcCheck)"
    } else {
        Write-Fail "pyodbc import failed — ODBC driver may be missing"
        Write-Info "Install ODBC Driver 17: https://aka.ms/downloadmsodbcsql"
    }
} else {
    Write-Fail "pip not found in .venv — venv creation may have failed"
}

# ── Step 4: Environment file ─────────────────────────────────────────────
Write-Step "4/6" "Checking environment configuration"

if (Test-Path $EnvFile) {
    Write-Pass ".env file exists"
    # Sanity check: make sure DENTRIX_BACKEND_URL is set
    $backendLine = Select-String -Path $EnvFile -Pattern "^DENTRIX_BACKEND_URL=.+" -Quiet
    if ($backendLine) {
        Write-Pass "DENTRIX_BACKEND_URL is configured"
    } else {
        Write-Fail "DENTRIX_BACKEND_URL is empty or missing in .env"
        Write-Info "Edit .env and set DENTRIX_BACKEND_URL=https://your-backend.example.com"
    }
} else {
    Write-Info ".env file not found — launching interactive setup..."
    if (Test-Path $SetupEnv) {
        & powershell.exe -ExecutionPolicy Bypass -File $SetupEnv
        if (Test-Path $EnvFile) {
            Write-Pass ".env file created"
        } else {
            Write-Fail ".env file was not created"
            Write-Info "You can create it manually: copy .env.dentrix.example .env"
        }
    } else {
        Write-Fail "setup_env.ps1 not found"
        if (Test-Path $EnvExample) {
            Copy-Item $EnvExample $EnvFile
            Write-Info "Copied .env.dentrix.example to .env — edit it with your values"
        } else {
            Write-Fail "No .env template found either"
        }
    }
}

# ── Step 5: Test ODBC connection ─────────────────────────────────────────
Write-Step "5/6" "Testing Dentrix ODBC connection"

if (Test-Path $EnvFile) {
    if (Test-Path $TestScript) {
        $testOutput = & $VenvPython $TestScript 2>&1 | Out-String
        Write-Host $testOutput
        if ($testOutput -match "ALL CHECKS PASSED") {
            Write-Pass "All connection tests passed"
        } else {
            Write-Fail "One or more connection tests failed (see output above)"
        }
    } else {
        Write-Info "test_dentrix_connection.py not found — skipping automated test"
        Write-Info "Run manually: python scripts\sync_dentrix.py --test-connection"
        $script:passed++
    }
} else {
    Write-Fail ".env not configured — cannot test connections"
}

# ── Step 6: Check ODBC drivers ──────────────────────────────────────────
Write-Step "6/6" "Checking installed ODBC drivers"

$driverOutput = & $VenvPython -c "import pyodbc; [print(f'       {d}') for d in pyodbc.drivers()]" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Pass "Installed ODBC drivers:"
    Write-Host $driverOutput
} else {
    Write-Info "Could not list ODBC drivers (pyodbc may not be installed)"
}

# ── Summary ──────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host "   Setup Summary" -ForegroundColor Cyan
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host ""

if ($failed -eq 0) {
    Write-Host "   ALL STEPS PASSED" -ForegroundColor Green
    Write-Host ""
    Write-Host "   Next steps:" -ForegroundColor Cyan
    Write-Host "     1. Run a small test sync:" -ForegroundColor White
    Write-Host "        .\scripts\run_dentrix_sync.ps1 patients 5" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "     2. Verify records in the backend" -ForegroundColor White
    Write-Host ""
    Write-Host "     3. Run a full sync when ready:" -ForegroundColor White
    Write-Host "        .\scripts\run_dentrix_sync.ps1 all 500" -ForegroundColor Yellow
    Write-Host ""
} else {
    Write-Host "   $failed step(s) FAILED — review the output above" -ForegroundColor Red
    Write-Host "   $passed step(s) passed" -ForegroundColor Green
    Write-Host ""
    Write-Host "   Fix the issues and re-run this script." -ForegroundColor Yellow
    Write-Host ""
}
