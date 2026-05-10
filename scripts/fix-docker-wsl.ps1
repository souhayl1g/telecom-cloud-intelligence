#Requires -RunAsAdministrator

<#
.SYNOPSIS
    Fixes Docker Desktop WSL integration with Ubuntu-22.04 and cleans junk containers/images.
.DESCRIPTION
    1. Fully stops Docker Desktop and WSL
    2. Updates WSL kernel (permanent stability fix)
    3. Restarts Docker Desktop cleanly
    4. Waits for full health
    5. Removes old Signoz/junky containers and images
    6. Prunes dangling resources but preserves project volumes by default
    7. Shows next steps for your NeXoligence stack
.PARAMETER PurgeVolumes
    If set, also deletes ALL unused Docker volumes (including postgres/minio data).
#>

param(
    [switch]$PurgeVolumes
)

$ErrorActionPreference = "Continue"
$Host.UI.RawUI.BackgroundColor = "Black"

function Write-Header($text) {
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host " $text" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
}

function Write-Step($num, $total, $text) {
    Write-Host "`n[$num/$total] $text" -ForegroundColor Yellow
}

Write-Header "Docker Desktop WSL Fix + Cleanup Tool"
Write-Host "Project: Telecom NeXoligence" -ForegroundColor Gray
Write-Host "Distro : Ubuntu-22.04`n" -ForegroundColor Gray

# -- Phase 1: Fix WSL Integration --
Write-Step 1 7 "Stopping Docker Desktop..."
$dd = Get-Process "Docker Desktop" -ErrorAction SilentlyContinue
if ($dd) {
    $dd | Stop-Process -Force
    Write-Host "  Docker Desktop stopped." -ForegroundColor Green
} else {
    Write-Host "  Docker Desktop was not running." -ForegroundColor Gray
}
# Kill any orphaned com.docker.* processes
Get-Process | Where-Object { $_.Name -like "com.docker*" } | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3

Write-Step 2 7 "Shutting down WSL..."
wsl --shutdown
Start-Sleep -Seconds 10
Write-Host "  WSL shut down." -ForegroundColor Green

Write-Step 3 7 "Updating WSL kernel (permanent stability fix)..."
wsl --update
Start-Sleep -Seconds 5
Write-Host "  WSL updated." -ForegroundColor Green

Write-Step 4 7 "Starting Docker Desktop..."
$dockerExe = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
if (Test-Path $dockerExe) {
    Start-Process $dockerExe
} else {
    Write-Error "Docker Desktop not found at $dockerExe"
    exit 1
}
Start-Sleep -Seconds 10

Write-Step 5 7 "Waiting for Docker to be healthy..."
$maxWait = 150
$elapsed = 0
$ready = $false
while ($elapsed -lt $maxWait -and -not $ready) {
    Start-Sleep -Seconds 5
    $elapsed += 5
    try {
        $out = docker version 2>$null
        if ($LASTEXITCODE -eq 0 -and $out -match "Server:") {
            $ready = $true
            Write-Host "  Docker is healthy! (${elapsed}s)" -ForegroundColor Green
        }
    } catch {
        Write-Host "  Still waiting... (${elapsed}s)" -ForegroundColor DarkGray
    }
}
if (-not $ready) {
    Write-Error "`nDocker Desktop failed to become healthy within ${maxWait}s.`n"
    Write-Host "Hard-reset option (run in Admin PowerShell):" -ForegroundColor Red
    Write-Host "  wsl --unregister docker-desktop" -ForegroundColor Yellow
    Write-Host "Then restart Docker Desktop (it will recreate the distro).`n" -ForegroundColor Yellow
    exit 1
}

# -- Phase 2: Docker Cleanup --
Write-Step 6 7 "Cleaning up junk containers & images..."

# Stop everything first
$running = docker ps -q 2>$null
if ($running) {
    Write-Host "  Stopping running containers..."
    docker stop $running | Out-Null
}

# Remove ALL containers (including old Signoz, ClickHouse, etc.)
$all = docker ps -aq 2>$null
if ($all) {
    Write-Host "  Removing all containers ($($all.Count) found)..."
    docker rm $all | Out-Null
}

# Remove old Signoz / ClickHouse / legacy observability images
Write-Host "  Scanning for old Signoz/ClickHouse/legacy images..."
$images = docker images --format "{{.Repository}}:{{.Tag}}|{{.ID}}" 2>$null
$junkPatterns = @("signoz", "clickhouse", "query-service", "flattables", "alertmanager", "zookeeper", "otel-collector" )
$removed = 0
foreach ($line in $images) {
    $parts = $line -split '\|'
    $repo = $parts[0]
    $id   = $parts[1]
    foreach ($p in $junkPatterns) {
        if ($repo -match $p) {
            Write-Host "    Removing: $repo" -ForegroundColor DarkGray
            docker rmi -f $id 2>$null | Out-Null
            $removed++
            break
        }
    }
}
Write-Host "  Removed $removed junk images." -ForegroundColor Green

# Remove dangling images, unused networks, build cache
Write-Host "  Pruning dangling images, networks, build cache..."
docker image prune -f | Out-Null
docker network prune -f | Out-Null
docker builder prune -f | Out-Null

# Volumes
if ($PurgeVolumes) {
    Write-Host "  !!! DELETING ALL UNUSED VOLUMES (postgres/minio data will be lost) !!!" -ForegroundColor Red
    docker volume prune -f | Out-Null
} else {
    Write-Host "  Preserving volumes (postgres, minio, grafana, etc.)." -ForegroundColor Green
    Write-Host "  Use -PurgeVolumes if you want a full wipe including data." -ForegroundColor DarkGray
}

Write-Step 7 7 "Verifying project image list..."
$needed = @(
    "postgres:16",
    "minio/minio",
    "netdata/netdata",
    "prom/prometheus",
    "grafana/grafana",
    "jaegertracing/jaeger",
    "otel/opentelemetry-collector-contrib"
)
foreach ($img in $needed) {
    $has = docker images --format "{{.Repository}}:{{.Tag}}" | Select-String "^$([regex]::Escape($img))"
    if (-not $has) {
        Write-Host "  [MISSING] $img -- will pull on next compose up" -ForegroundColor Yellow
    } else {
        Write-Host "  [OK] $img" -ForegroundColor Green
    }
}

Write-Header "DONE! Docker is fixed and cleaned up."
Write-Host "`nNext steps (run inside WSL Ubuntu-22.04):" -ForegroundColor Cyan
Write-Host "  cd ~/projects/telecom-cloud-intelligence" -ForegroundColor White
Write-Host "  docker compose up -d" -ForegroundColor White
Write-Host "`nTo avoid this issue in the future:" -ForegroundColor Cyan
Write-Host "  1. Keep Docker Desktop auto-updates enabled." -ForegroundColor Gray
Write-Host "  2. Don't force-shutdown Windows while containers are running." -ForegroundColor Gray
Write-Host "  3. If this happens again, just re-run this script." -ForegroundColor Gray
