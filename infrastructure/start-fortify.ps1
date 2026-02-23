# ============================================================
# Project Fortify - Single Terminal Launcher
# Place this file in: infrastructure/
# Usage: .\start-fortify.ps1
# Stop:  Ctrl+C  (cleans up all background jobs automatically)
# ============================================================

$ErrorActionPreference = "Stop"

# --- Force UTF-8 for Python processes (fixes emoji/unicode on Windows) ---
$env:PYTHONUTF8 = "1"

# --- Resolve paths ------------------------------------------
$infraRoot   = $PSScriptRoot                              # .../project-fortify/infrastructure
$projectRoot = (Resolve-Path "$PSScriptRoot\..").Path     # .../project-fortify

# --- Colour helpers -----------------------------------------
function Write-Label($label, $msg, $color) {
    Write-Host "[$label] " -ForegroundColor $color -NoNewline
    Write-Host $msg
}

function Info($msg)    { Write-Label "FORTIFY" $msg Cyan    }
function Success($msg) { Write-Label "FORTIFY" $msg Green   }
function Err($msg)     { Write-Label "FORTIFY" $msg Red     }

# --- Cleanup on exit ----------------------------------------
$script:jobs = @()

function Stop-AllJobs {
    Info "Shutting down all services..."
    foreach ($job in $script:jobs) {
        if ($job.State -eq "Running") {
            Stop-Job $job | Out-Null
            Remove-Job $job | Out-Null
        }
    }
    Info "Stopping Docker services..."
    Set-Location $infraRoot
    docker-compose down | Out-Null
    Success "All services stopped. Goodbye!"
}

# Trap Ctrl+C and any script exit
trap {
    Stop-AllJobs
    break
}

# --- Step 1: Start Docker services --------------------------
Info "Starting Docker services (postgres + redis)..."
Set-Location $infraRoot
docker-compose up -d postgres redis

Info "Waiting for postgres and redis to be healthy..."
$timeout = 60
$elapsed = 0
while ($elapsed -lt $timeout) {
    $pgHealth    = (docker inspect --format="{{.State.Health.Status}}" fortify-postgres 2>$null)
    $redisHealth = (docker inspect --format="{{.State.Health.Status}}" fortify-redis    2>$null)

    if ($pgHealth -eq "healthy" -and $redisHealth -eq "healthy") {
        Success "postgres and redis are healthy!"
        break
    }

    Start-Sleep -Seconds 2
    $elapsed += 2
    Info "  Still waiting... ($elapsed`s elapsed)"
}

if ($elapsed -ge $timeout) {
    Err "Timed out waiting for Docker services. Run 'docker-compose logs' to debug."
    exit 1
}

# --- Step 2: Start API --------------------------------------
$apiJob = Start-Job -Name "API" -ScriptBlock {
    param($root)
    Set-Location "$root\api"
    & ".\venv\Scripts\Activate.ps1"
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload 2>&1
} -ArgumentList $projectRoot

$script:jobs += $apiJob
Write-Label "API" "Started  ->  http://localhost:8000/docs" Magenta

Start-Sleep -Seconds 3   # give the API a moment before the simulator connects

# --- Step 3: Start Metrics Simulator ------------------------
$simJob = Start-Job -Name "SIM" -ScriptBlock {
    param($root)
    Set-Location $root
    & ".\api\venv\Scripts\Activate.ps1"
    python -u data/generators/metrics_simulator.py 2>&1
} -ArgumentList $projectRoot

$script:jobs += $simJob
Write-Label "SIM" "Started  (metrics simulator running)" Yellow

# --- Step 4: Start Dashboard --------------------------------
$dashJob = Start-Job -Name "DASH" -ScriptBlock {
    param($root)
    Set-Location "$root\frontend\dashboard"
    & ".\venv\Scripts\Activate.ps1"
    streamlit run app.py 2>&1
} -ArgumentList $projectRoot

$script:jobs += $dashJob
Write-Label "DASH" "Started  ->  http://localhost:8501" Blue

# --- Step 5: Stream logs from all jobs ----------------------
Success "All services running! Streaming logs below (Ctrl+C to stop everything)"
Write-Host ""

$labelColors = @{
    "API"  = "Magenta"
    "SIM"  = "Yellow"
    "DASH" = "Blue"
}

while ($true) {
    foreach ($job in $script:jobs) {
        $output = Receive-Job $job -ErrorAction SilentlyContinue
        if ($output) {
            $color = $labelColors[$job.Name]
            if (-not $color) { $color = "White" }
            foreach ($line in $output) {
                Write-Label $job.Name $line $color
            }
        }

        # Warn if a job died unexpectedly
        if ($job.State -eq "Failed" -or $job.State -eq "Stopped") {
            Err "$($job.Name) stopped unexpectedly! Check the output above."
        }
    }

    Start-Sleep -Milliseconds 500
}