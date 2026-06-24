param()

$ErrorActionPreference = "SilentlyContinue"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ((Split-Path -Leaf $ScriptDir) -ieq "scripts") {
  $Root = Split-Path -Parent $ScriptDir
} else {
  $Root = $ScriptDir
}

$PidDir = Join-Path $Root "outputs\pids"

function Stop-PidFile([string]$Name) {
  $path = Join-Path $PidDir $Name
  if (Test-Path $path) {
    $pidValue = Get-Content $path -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($pidValue) {
      Stop-Process -Id ([int]$pidValue) -Force -ErrorAction SilentlyContinue
    }
    Remove-Item $path -Force -ErrorAction SilentlyContinue
  }
}

function Stop-PortOwner([string]$PortFile) {
  $path = Join-Path $PidDir $PortFile
  if (Test-Path $path) {
    $port = Get-Content $path -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($port -and (Get-Command Get-NetTCPConnection -ErrorAction SilentlyContinue)) {
      Get-NetTCPConnection -LocalPort ([int]$port) -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique |
        ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
    }
    Remove-Item $path -Force -ErrorAction SilentlyContinue
  }
}

Stop-PidFile "webui.pid"
Stop-PidFile "api.pid"
Stop-PortOwner "webui.port"
Stop-PortOwner "api.port"

Write-Host "[EdgeAI] stopped"

