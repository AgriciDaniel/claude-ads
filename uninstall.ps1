#Requires -Version 5.1
<#
.SYNOPSIS
    Claude AI Ads Uninstaller for Windows
.DESCRIPTION
    Removes the Claude AI Ads skill, sub-skills, agents, and reference files
    from Claude Code on Windows systems.
#>

$ErrorActionPreference = "Stop"

function Main {
    Write-Host "→ Uninstalling Claude AI Ads..."

    $ClaudeDir = Join-Path $env:USERPROFILE ".claude"

    # Remove main skill (orchestrator + references)
    $MainSkill = Join-Path $ClaudeDir "skills\ads"
    if (Test-Path $MainSkill) {
        Remove-Item -Path $MainSkill -Recurse -Force
    }

    # Remove sub-skills
    $SubSkills = @(
        "ads-audit", "ads-google", "ads-meta", "ads-youtube",
        "ads-linkedin", "ads-tiktok", "ads-microsoft", "ads-creative",
        "ads-landing", "ads-budget", "ads-plan", "ads-competitor"
    )
    foreach ($skill in $SubSkills) {
        $SkillPath = Join-Path $ClaudeDir "skills\$skill"
        if (Test-Path $SkillPath) {
            Remove-Item -Path $SkillPath -Recurse -Force
        }
    }

    # Remove agents
    $Agents = @(
        "audit-google", "audit-meta", "audit-creative",
        "audit-tracking", "audit-budget", "audit-compliance"
    )
    foreach ($agent in $Agents) {
        $AgentPath = Join-Path $ClaudeDir "agents\$agent.md"
        if (Test-Path $AgentPath) {
            Remove-Item -Path $AgentPath -Force
        }
    }

    Write-Host "✓ Claude AI Ads uninstalled." -ForegroundColor Green
}

Main
