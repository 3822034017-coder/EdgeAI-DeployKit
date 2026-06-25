param(
  [switch]$NoStart
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ((Split-Path -Leaf $ScriptDir) -ieq "scripts") {
  $Root = Split-Path -Parent $ScriptDir
} else {
  $Root = $ScriptDir
}

function Test-SupportedPython {
  $candidates = @()
  if (Get-Command py -ErrorAction SilentlyContinue) {
    $pyList = & py -0p 2>$null
    foreach ($line in $pyList) {
      if ($line -match "^\s+-V:[^\s]+\s+(.+?python\.exe)\s*$") {
        $candidates += $Matches[1]
      }
    }
  }
  if (Get-Command python -ErrorAction SilentlyContinue) {
    $candidates += "python"
  }
  foreach ($candidate in ($candidates | Select-Object -Unique)) {
    $version = & $candidate -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $version) {
      continue
    }
    $parts = [string]$version -split "\."
    if ([int]$parts[0] -eq 3 -and [int]$parts[1] -ge 9 -and [int]$parts[1] -le 13) {
      Write-Host "[EdgeAI] Python ready: $candidate $version"
      return $true
    }
  }
  return $false
}

function Install-PythonWithWinget {
  if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    return $false
  }
  Write-Host "[EdgeAI] Installing Python 3.12 with winget..."
  winget install -e --id Python.Python.3.12 --scope user --accept-source-agreements --accept-package-agreements
  if ($LASTEXITCODE -ne 0) {
    return $false
  }
  return $true
}

Set-Location $Root

if (-not (Test-SupportedPython)) {
  if (-not (Install-PythonWithWinget) -or -not (Test-SupportedPython)) {
    Write-Host ""
    Write-Host "[EdgeAI] Python is still missing."
    Write-Host "Please install Python 3.10/3.11/3.12 manually and enable Add python.exe to PATH:"
    Write-Host "https://www.python.org/downloads/windows/"
    Start-Process "https://www.python.org/downloads/windows/" | Out-Null
    exit 1
  }
}

Write-Host "[EdgeAI] Runtime bootstrap finished."

if (-not $NoStart) {
  & (Join-Path $Root "start-windows.bat")
}
