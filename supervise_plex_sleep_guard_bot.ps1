param(
    [Parameter(Mandatory = $true)]
    [string] $ProjectDir
)

$ErrorActionPreference = 'Stop'
$ProjectDir = [System.IO.Path]::GetFullPath($ProjectDir)
$RunDir = Join-Path $ProjectDir 'run'
$PythonExe = $env:PLEX_SLEEP_GUARD_PYTHON_EXE
if (-not $PythonExe) {
    $PythonExe = Join-Path $ProjectDir '.venv\Scripts\python.exe'
}
$LockPath = Join-Path $RunDir 'supervisor.lock'
$PidPath = Join-Path $RunDir 'supervisor.pid'
$StopPath = Join-Path $RunDir 'stop.request'
$RestartPath = Join-Path $RunDir 'restart.request'

if (-not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) {
    exit 2
}

New-Item -ItemType Directory -Path $RunDir -Force | Out-Null
try {
    # FileShare.None acts as a process-lifetime lock and becomes available on exit.
    $Lock = [System.IO.File]::Open(
        $LockPath,
        [System.IO.FileMode]::OpenOrCreate,
        [System.IO.FileAccess]::ReadWrite,
        [System.IO.FileShare]::None
    )
} catch [System.IO.IOException] {
    # Another supervisor owns the lock. It will observe restart.request.
    exit 0
}

try {
    [System.IO.File]::WriteAllText($PidPath, [string] $PID)
    Remove-Item -LiteralPath $StopPath, $RestartPath -Force -ErrorAction SilentlyContinue
    $env:PLEX_SLEEP_GUARD_SUPERVISED = '1'
    $SourceDir = Join-Path $ProjectDir 'src'

    while ($true) {
        $Child = Start-Process `
            -FilePath $PythonExe `
            -ArgumentList @('-m', 'plex_sleep_guard_bot') `
            -WorkingDirectory $SourceDir `
            -WindowStyle Hidden `
            -PassThru

        $RequestedAction = $null
        while (-not $Child.HasExited) {
            if (Test-Path -LiteralPath $StopPath) {
                $RequestedAction = 'stop'
                break
            }
            if (Test-Path -LiteralPath $RestartPath) {
                $RequestedAction = 'restart'
                break
            }
            Start-Sleep -Seconds 1
            $Child.Refresh()
        }

        if ($RequestedAction) {
            $Deadline = [DateTime]::UtcNow.AddSeconds(25)
            while (-not $Child.HasExited -and [DateTime]::UtcNow -lt $Deadline) {
                Start-Sleep -Milliseconds 250
                $Child.Refresh()
            }
            if (-not $Child.HasExited) {
                # A wedged process must not leave the supervisor or its request behind.
                Stop-Process -Id $Child.Id -Force -ErrorAction SilentlyContinue
                $Child.WaitForExit()
            }
        }

        if ((Test-Path -LiteralPath $StopPath) -or $RequestedAction -eq 'stop') {
            Remove-Item -LiteralPath $StopPath, $RestartPath -Force -ErrorAction SilentlyContinue
            break
        }
        if ((Test-Path -LiteralPath $RestartPath) -or $RequestedAction -eq 'restart') {
            Remove-Item -LiteralPath $RestartPath -Force -ErrorAction SilentlyContinue
            Start-Sleep -Milliseconds 500
            continue
        }

        # Restart after an unexpected bot exit, including a clean but unsolicited exit.
        Start-Sleep -Seconds 5
    }
} finally {
    Remove-Item -LiteralPath $PidPath -Force -ErrorAction SilentlyContinue
    if ($Lock) {
        $Lock.Dispose()
    }
}
