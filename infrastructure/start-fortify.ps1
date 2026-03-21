# ============================================================================
# Project Fortify – Launcher with Pre‑Cleanup
# Place this file in: infrastructure/
# Usage: .\start-fortify.ps1
# Stop:  Ctrl+C  (kills everything, even orphaned processes)
# ============================================================================

$ErrorActionPreference = "Stop"

# -------------------------------
# Force UTF-8 everywhere
# -------------------------------
chcp 65001 > $null
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::UTF8
$PSDefaultParameterValues['*:Encoding'] = 'utf8'
$env:PYTHONUTF8 = "1"

# -------------------------------
# Paths
# -------------------------------
$infraRoot   = $PSScriptRoot
$projectRoot = (Resolve-Path "$PSScriptRoot\..").Path

# -------------------------------
# Coloured output helpers
# -------------------------------
function Write-Label($label, $msg, $color) {
    $timestamp = Get-Date -Format "HH:mm:ss"
    Write-Host "[$timestamp][$label] " -ForegroundColor $color -NoNewline
    Write-Host $msg
}
function Info($msg)    { Write-Label "FORTIFY" $msg Cyan    }
function Success($msg) { Write-Label "FORTIFY" $msg Green   }
function Err($msg)     { Write-Label "FORTIFY" $msg Red     }

# -------------------------------
# Global flag and process list
# -------------------------------
$script:stopping  = $false
$script:processes = @()   # each: [PSCustomObject]@{Name=; Process=; OutEvent=; ErrEvent=}

# -------------------------------
# Recursively kill a process and its children
# -------------------------------
function Stop-ProcessTree($processId) {
    if ($processId -le 0) { return }
    try {
        # Kill children first (using WMI for reliability)
        Get-WmiObject Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.ParentProcessId -eq $processId } | ForEach-Object {
            Stop-ProcessTree $_.ProcessId
        }
        $proc = Get-Process -Id $processId -ErrorAction SilentlyContinue
        if ($proc) { $proc.Kill() }
    } catch {}
}

# -------------------------------
# Kill any leftover processes from previous runs (but NOT Docker)
# -------------------------------
function Stop-LeftoverProcesses {
    Info "Checking for leftover processes from previous runs..."
    $projectPathEscaped = [regex]::Escape($projectRoot)
    $processes = Get-WmiObject Win32_Process -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -and $_.CommandLine -match $projectPathEscaped
    }
    foreach ($proc in $processes) {
        Write-Label "CLEANUP" "Killing leftover process PID $($proc.ProcessId) ($($proc.Name))" Yellow
        Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

# -------------------------------
# Cleanup function – kills all tracked processes and stops Docker
# -------------------------------
function Stop-AllServices {
    if ($script:stopping) { return }  # avoid double execution
    $script:stopping = $true

    Info "Shutting down all services..."

    foreach ($entry in $script:processes) {
        $p = $entry.Process
        if ($p -and !$p.HasExited) {
            Write-Label $entry.Name "Stopping (PID $($p.Id))..." Yellow
            # Unregister events first
            if ($entry.OutEvent) {
                Unregister-Event -SourceIdentifier $entry.OutEvent.Name -Force -ErrorAction SilentlyContinue
                Remove-Job -Job $entry.OutEvent -Force -ErrorAction SilentlyContinue
            }
            if ($entry.ErrEvent) {
                Unregister-Event -SourceIdentifier $entry.ErrEvent.Name -Force -ErrorAction SilentlyContinue
                Remove-Job -Job $entry.ErrEvent -Force -ErrorAction SilentlyContinue
            }
            # Try graceful shutdown, then force kill tree
            $p.CloseMainWindow() | Out-Null
            Start-Sleep -Milliseconds 500
            if (!$p.HasExited) { Stop-ProcessTree $p.Id }
        }
    }

    Info "Stopping Docker services..."
    Set-Location $infraRoot
    docker-compose down 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Label "FORTIFY" "Warning: docker-compose down returned exit code $LASTEXITCODE" Yellow
    }

    Success "All services stopped. Goodbye!"
}

# -------------------------------
# .NET Ctrl+C handler – sets the stopping flag
# -------------------------------
$consoleHandler = [System.ConsoleCancelEventHandler]{
    Write-Host "`nCtrl+C pressed. Stopping everything..." -ForegroundColor Yellow
    $script:stopping = $true
    $args[1].Cancel = $true   # prevent default termination (we handle cleanup)
}
[Console]::add_CancelKeyPress($consoleHandler)

# -------------------------------
# Function: Start a service, capture output, store process
# -------------------------------
function Start-Service($name, $command, $workDir, $color) {
    Info "Starting $name ..."

    $fullCommand = "cd '$workDir'; if (Test-Path '.\venv\Scripts\Activate.ps1') { & '.\venv\Scripts\Activate.ps1' }; $command"

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = "powershell.exe"
    $psi.Arguments = "-NoLogo -NoProfile -Command `"$fullCommand`""
    $psi.WorkingDirectory = $workDir
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true

    $p = [System.Diagnostics.Process]::Start($psi)

    # Output event – using $Event (capital E) for correct automatic variable
    $outEvent = Register-ObjectEvent -InputObject $p -EventName 'OutputDataReceived' -Action {
        $line = $EventArgs.Data
        if ($null -ne $line) {
            $timestamp = Get-Date -Format "HH:mm:ss"
            $msgData = $Event.MessageData   # this is the hashtable passed below
            Write-Host "[$timestamp][$($msgData.Name)] " -ForegroundColor $msgData.Color -NoNewline
            Write-Host $line
        }
    } -MessageData @{Name = $name; Color = $color}

    # Error event – simpler: just pass the name
    $errEvent = Register-ObjectEvent -InputObject $p -EventName 'ErrorDataReceived' -Action {
        $line = $EventArgs.Data
        if ($null -ne $line) {
            $timestamp = Get-Date -Format "HH:mm:ss"
            Write-Host "[$timestamp][$Event.MessageData] " -ForegroundColor Red -NoNewline
            Write-Host $line
        }
    } -MessageData $name

    $p.BeginOutputReadLine()
    $p.BeginErrorReadLine()

    $script:processes += [PSCustomObject]@{
        Name     = $name
        Process  = $p
        OutEvent = $outEvent
        ErrEvent = $errEvent
    }

    Write-Label $name "Started (PID $($p.Id))" $color
}

# -------------------------------
# MAIN SCRIPT with try/finally
# -------------------------------
try {
    # --- Pre‑cleanup: kill any leftover processes from previous runs (Docker untouched) ---
    Stop-LeftoverProcesses

    # --- Start Docker ---
    Info "Starting Docker services (postgres + redis)..."
    Set-Location $infraRoot

    # Run docker-compose up, capture exit code without triggering PowerShell error
    $originalErrorAction = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    docker-compose up -d postgres redis 2>&1 | Out-Null
    $exitCode = $LASTEXITCODE
    $ErrorActionPreference = $originalErrorAction

    if ($exitCode -ne 0) {
        Err "Docker Compose failed with exit code $exitCode. Please ensure Docker is running and try again."
        exit 1
    }

    # Wait for both to be healthy
    Info "Waiting for postgres and redis to be healthy..."
    $timeout = 60
    $elapsed = 0
    while ($elapsed -lt $timeout -and !$script:stopping) {
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

    # --- Start API ---
    Start-Service -name "API" `
                  -command "uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload" `
                  -workDir "$projectRoot\api" `
                  -color "Magenta"

    # Give API plenty of time to fully initialise
    $apiWarmup = 10
    for ($i = 1; $i -le $apiWarmup; $i++) {
        if ($script:stopping) { break }
        Info "  Waiting for API to warm up... ($i/$apiWarmup)"
        Start-Sleep -Seconds 1
    }

    # --- Start Simulator ---
    Start-Service -name "SIM" `
                  -command "api\venv\Scripts\python.exe -u data/generators/metrics_simulator.py" `
                  -workDir $projectRoot `
                  -color "Yellow"

    # --- Start Dashboard ---
    Start-Service -name "DASH" `
                  -command "streamlit run app.py" `
                  -workDir "$projectRoot\frontend\dashboard" `
                  -color "Blue"

    Success "All services running! Press Ctrl+C to stop everything."
    Write-Host ""

    # --- Main monitoring loop ---
    while (!$script:stopping) {
        foreach ($entry in $script:processes) {
            $p = $entry.Process
            if ($p.HasExited) {
                Write-Label $entry.Name "Process exited unexpectedly (code $($p.ExitCode))!" Red
            }
        }
        Start-Sleep -Seconds 2
    }
}
finally {
    # This runs on normal exit OR when Ctrl+C breaks the loop
    Stop-AllServices
}