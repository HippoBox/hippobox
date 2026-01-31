param(
    [string]$Tag = "local"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot

$hatchCmd = Get-Command hatch -ErrorAction SilentlyContinue
if (-not $hatchCmd) {
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCmd) {
        throw "Python is not installed or not found in PATH."
    }
}

Push-Location "$root\\src\\backend"
try {
    if ($hatchCmd) {
        hatch build
    } else {
        python -m hatch build
    }
} finally {
    Pop-Location
}

docker build -f "$root\\docker\\Dockerfile" -t "hippobox:$Tag" "$root"
