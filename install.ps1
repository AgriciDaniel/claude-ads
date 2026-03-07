#Requires -Version 5.1
<#
.SYNOPSIS
    Claude AI Ads Installer for Windows
.DESCRIPTION
    Installs the Claude AI Ads skill, sub-skills, agents, and reference files
    for Claude Code on Windows systems.
#>

$ErrorActionPreference = "Stop"

function Main {
    $SkillDir = Join-Path $env:USERPROFILE ".claude\skills\ads"
    $AgentDir = Join-Path $env:USERPROFILE ".claude\agents"
    $RepoUrl = "https://github.com/EveryThingAi/claude-ai-ads"

    Write-Host "=================================="
    Write-Host "   Claude AI Ads - Installer"
    Write-Host "   Claude Code Paid Ads Skill"
    Write-Host "=================================="
    Write-Host ""

    # Check prerequisites
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        Write-Host "X Git is required but not installed." -ForegroundColor Red
        exit 1
    }
    Write-Host "OK Git detected" -ForegroundColor Green

    # Create directories
    New-Item -ItemType Directory -Path (Join-Path $SkillDir "references") -Force | Out-Null
    New-Item -ItemType Directory -Path $AgentDir -Force | Out-Null

    # Clone to temp directory
    $TempDir = Join-Path $env:TEMP "claude-ai-ads-install-$(Get-Random)"
    Write-Host "Downloading Claude AI Ads..."

    try {
        git clone --depth 1 $RepoUrl "$TempDir\claude-ai-ads" 2>$null
        if ($LASTEXITCODE -ne 0) { throw "Git clone failed" }

        # Copy main skill + references
        Write-Host "Installing skill files..."
        Copy-Item "$TempDir\claude-ai-ads\ads\SKILL.md" -Destination "$SkillDir\SKILL.md" -Force
        Copy-Item "$TempDir\claude-ai-ads\ads\references\*.md" -Destination "$SkillDir\references\" -Force

        # Copy sub-skills
        Write-Host "Installing sub-skills..."
        Get-ChildItem "$TempDir\claude-ai-ads\skills" -Directory | ForEach-Object {
            $TargetDir = Join-Path $env:USERPROFILE ".claude\skills\$($_.Name)"
            New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
            Copy-Item (Join-Path $_.FullName "SKILL.md") -Destination "$TargetDir\SKILL.md" -Force

            # Copy assets (industry templates) if they exist
            $AssetsDir = Join-Path $_.FullName "assets"
            if (Test-Path $AssetsDir) {
                $TargetAssets = Join-Path $TargetDir "assets"
                New-Item -ItemType Directory -Path $TargetAssets -Force | Out-Null
                Copy-Item "$AssetsDir\*.md" -Destination "$TargetAssets\" -Force
            }
        }

        # Copy agents
        Write-Host "Installing subagents..."
        Copy-Item "$TempDir\claude-ai-ads\agents\*.md" -Destination "$AgentDir\" -Force

        # Copy scripts (optional Python tools)
        $ScriptsSource = "$TempDir\claude-ai-ads\scripts"
        if (Test-Path $ScriptsSource) {
            Write-Host "Installing Python scripts..."
            $ScriptsDir = Join-Path $SkillDir "scripts"
            New-Item -ItemType Directory -Path $ScriptsDir -Force | Out-Null
            Copy-Item "$ScriptsSource\*.py" -Destination "$ScriptsDir\" -Force
            Copy-Item "$TempDir\claude-ai-ads\requirements.txt" -Destination "$SkillDir\requirements.txt" -Force
        }

        Write-Host ""
        Write-Host "Claude AI Ads installed successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "  Installed:"
        Write-Host "    - 1 main skill (ads orchestrator)"
        Write-Host "    - 12 sub-skills (platform + functional)"
        Write-Host "    - 6 parallel audit agents"
        Write-Host "    - 12 reference files"
        Write-Host "    - 11 industry templates"
        Write-Host ""
        Write-Host "Usage:"
        Write-Host "  1. Start Claude Code:  claude"
        Write-Host "  2. Run commands:       /ads audit"
        Write-Host "                         /ads plan saas"
        Write-Host "                         /ads google"
    }
    finally {
        # Cleanup temp directory
        if (Test-Path $TempDir) {
            Remove-Item -Path $TempDir -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}

Main
