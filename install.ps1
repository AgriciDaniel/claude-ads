#Requires -Version 5.1
<#
.SYNOPSIS
    Claude Ads Installer for Windows (multi-host).
.DESCRIPTION
    Installs the Claude Ads skill, sub-skills, agents, and reference files
    for Claude Code (default) or any of the supported experimental host CLIs.

    Targets:
      claude     Claude Code (verified)
      codex      OpenAI Codex CLI (experimental)
      cursor     Cursor IDE (experimental)
      windsurf   Windsurf IDE (experimental)
      gemini     Gemini CLI (experimental)
      goose      Goose CLI (experimental)
.PARAMETER Target
    Which host CLI to install for. Default: claude.
.PARAMETER SkillDir
    Override the target's default skill install root.
.PARAMETER AgentDir
    Override the target's default agent install root.
.EXAMPLE
    .\install.ps1
.EXAMPLE
    .\install.ps1 -Target codex
.EXAMPLE
    .\install.ps1 -SkillDir C:\Custom\Skills
.NOTES
    Prefer a host-native plugin install or a signed release archive after
    verifying its SHA-256 checksum. Never pipe remote content to PowerShell.
#>

param(
    [ValidateSet('claude','codex','cursor','windsurf','gemini','goose')]
    [string]$Target = 'claude',
    [string]$SkillDir = '',
    [string]$AgentDir = '',
    [ValidateSet('auto','local','git')]
    [string]$Source = 'auto',
    [string]$RepoDir = '',
    [switch]$NoDeps
)

$ErrorActionPreference = "Stop"

function Get-ClaudeAdsUserHome {
    if (-not [string]::IsNullOrWhiteSpace($env:USERPROFILE)) { return $env:USERPROFILE }
    if (-not [string]::IsNullOrWhiteSpace($HOME)) { return $HOME }
    $ProfileHome = [Environment]::GetFolderPath([Environment+SpecialFolder]::UserProfile)
    if (-not [string]::IsNullOrWhiteSpace($ProfileHome)) { return $ProfileHome }
    throw "Cannot determine the current user's home directory."
}

function Resolve-TargetPaths {
    param([string]$T)
    $UserHome = Get-ClaudeAdsUserHome
    switch ($T) {
        'claude' {
            return @{
                SkillBase = Join-Path $UserHome ".claude\skills"
                AgentDir  = Join-Path $UserHome ".claude\agents"
                AllowPip  = $true
                Label     = "Claude Code"
            }
        }
        'codex' {
            return @{
                SkillBase = Join-Path $UserHome ".codex\skills"
                AgentDir  = Join-Path $UserHome ".codex\agents"
                AllowPip  = $true
                Label     = "OpenAI Codex CLI"
            }
        }
        'cursor' {
            return @{
                SkillBase = Join-Path $UserHome ".cursor\extensions\claude-ads\skills"
                AgentDir  = Join-Path $UserHome ".cursor\extensions\claude-ads\agents"
                AllowPip  = $false
                Label     = "Cursor IDE"
            }
        }
        'windsurf' {
            return @{
                SkillBase = Join-Path $UserHome ".windsurf\skills"
                AgentDir  = Join-Path $UserHome ".windsurf\agents"
                AllowPip  = $false
                Label     = "Windsurf IDE"
            }
        }
        'gemini' {
            return @{
                SkillBase = Join-Path $UserHome ".gemini\extensions\claude-ads\skills"
                AgentDir  = Join-Path $UserHome ".gemini\extensions\claude-ads\agents"
                AllowPip  = $false
                Label     = "Gemini CLI"
            }
        }
        'goose' {
            return @{
                SkillBase = Join-Path $UserHome ".config\goose\skills"
                AgentDir  = Join-Path $UserHome ".config\goose\agents"
                AllowPip  = $false
                Label     = "Goose CLI"
            }
        }
        default {
            throw "Unknown target: $T"
        }
    }
}

function Test-InstallPath {
    param([string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path)) { return $false }
    if ($Path -match '[\;\&\|\$\(\)\<\>\`]') { return $false }
    if ($Path -match '\.\.') { return $false }
    if ($Path -match '^[-]') { return $false }
    if ($Path -match '^(\\\\|//)') { return $false }   # UNC paths
    return $true
}

function Get-NormalizedInstallRoot([string]$Path) {
    $FullPath = [IO.Path]::GetFullPath($Path)
    $PathRoot = [IO.Path]::GetPathRoot($FullPath)
    $Comparison = if ([Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT) {
        [StringComparison]::OrdinalIgnoreCase
    } else {
        [StringComparison]::Ordinal
    }
    if ($FullPath.Equals($PathRoot, $Comparison)) { return $FullPath }
    $Separators = [char[]]@([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar)
    return $FullPath.TrimEnd($Separators)
}

function Get-CompatibleRelativePath([string]$BasePath, [string]$ChildPath) {
    $Separators = [char[]]@([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar)
    $Boundary = [string][IO.Path]::DirectorySeparatorChar
    $Comparison = if ([Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT) {
        [StringComparison]::OrdinalIgnoreCase
    } else {
        [StringComparison]::Ordinal
    }
    $Base = [IO.Path]::GetFullPath($BasePath).TrimEnd($Separators) + $Boundary
    $Child = [IO.Path]::GetFullPath($ChildPath)
    if (-not $Child.StartsWith($Base, $Comparison)) {
        throw "Source path is outside its declared base: $ChildPath"
    }
    return $Child.Substring($Base.Length)
}

function Main {
    $paths = Resolve-TargetPaths -T $Target
    $SkillBase = $paths.SkillBase
    $AgentDirResolved = $paths.AgentDir
    $AllowPip = $paths.AllowPip
    $HostLabel = $paths.Label

    if ($SkillDir) {
        if (-not (Test-InstallPath -Path $SkillDir)) {
            Write-Host "X Invalid -SkillDir: contains forbidden characters or traversal" -ForegroundColor Red
            exit 1
        }
        $SkillBase = $SkillDir
    }
    if ($AgentDir) {
        if (-not (Test-InstallPath -Path $AgentDir)) {
            Write-Host "X Invalid -AgentDir: contains forbidden characters or traversal" -ForegroundColor Red
            exit 1
        }
        $AgentDirResolved = $AgentDir
    }

    # Normalize the configured roots before deriving any destination.  The
    # installer records and compares only these absolute lexical forms; any
    # existing reparse point in their ancestry is rejected below.
    $Separators = [char[]]@([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar)
    $Boundary = [string][IO.Path]::DirectorySeparatorChar
    $PathComparison = if ([Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT) {
        [StringComparison]::OrdinalIgnoreCase
    } else {
        [StringComparison]::Ordinal
    }
    $SkillBase = Get-NormalizedInstallRoot $SkillBase
    $AgentDirResolved = Get-NormalizedInstallRoot $AgentDirResolved
    $SkillRootPrefix = if ($SkillBase.EndsWith($Boundary, $PathComparison)) { $SkillBase } else { $SkillBase + $Boundary }
    $AgentRootPrefix = if ($AgentDirResolved.EndsWith($Boundary, $PathComparison)) { $AgentDirResolved } else { $AgentDirResolved + $Boundary }
    if ($SkillBase.Equals($AgentDirResolved, $PathComparison) -or
        $SkillBase.StartsWith($AgentRootPrefix, $PathComparison) -or
        $AgentDirResolved.StartsWith($SkillRootPrefix, $PathComparison)) {
        throw "Skill and agent install roots must not overlap: $SkillBase ; $AgentDirResolved"
    }
    $SkillDirResolved = [IO.Path]::GetFullPath((Join-Path $SkillBase "ads"))
    $BashManifestPath = [IO.Path]::GetFullPath((Join-Path $SkillBase ".claude-ads-$Target.manifest"))
    $ManifestPath = [IO.Path]::GetFullPath((Join-Path $SkillBase ".claude-ads-$Target.manifest.json"))
    $RepoUrl = "https://github.com/AgriciDaniel/claude-ads"
    $StringComparer = if ($PathComparison -eq [StringComparison]::OrdinalIgnoreCase) {
        [StringComparer]::OrdinalIgnoreCase
    } else {
        [StringComparer]::Ordinal
    }

    # Bash and PowerShell use different ownership-manifest contracts. Never
    # let one installer infer overwrite authority from the other contract.
    $BashManifestItem = Get-Item -LiteralPath $BashManifestPath -Force -ErrorAction SilentlyContinue
    if ($null -ne $BashManifestItem) {
        throw "Bash ownership manifest detected: $BashManifestPath. Continue with install.sh, or uninstall with uninstall.sh before switching installers."
    }

    function Get-RootPrefix([string]$Root) {
        if ($Root.EndsWith($Boundary, $PathComparison)) { return $Root }
        return $Root + $Boundary
    }

    function Test-PathWithinConfiguredRoots([string]$Path) {
        $FullPath = [IO.Path]::GetFullPath($Path)
        foreach ($Root in @($SkillBase, $AgentDirResolved)) {
            if ($FullPath.Equals($Root, $PathComparison) -or
                $FullPath.StartsWith((Get-RootPrefix $Root), $PathComparison)) {
                return $true
            }
        }
        return $false
    }

    function Assert-ConfiguredDestination([string]$Path) {
        $FullPath = [IO.Path]::GetFullPath($Path)
        if (-not (Test-PathWithinConfiguredRoots $FullPath)) {
            throw "Install destination escapes configured roots: $Path"
        }
        return $FullPath
    }

    function Get-ContainingConfiguredRoot([string]$Path) {
        $FullPath = Assert-ConfiguredDestination $Path
        $Candidates = @(@($SkillBase, $AgentDirResolved) | Where-Object {
            $FullPath.Equals($_, $PathComparison) -or
            $FullPath.StartsWith((Get-RootPrefix $_), $PathComparison)
        } | Sort-Object Length -Descending)
        if ($Candidates.Count -eq 0) { throw "Install destination escapes configured roots: $Path" }
        return [string]$Candidates[0]
    }

    function Assert-CurrentUserOwnedFile([string]$Path) {
        if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) { return }
        $Identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
        $Sections = [System.Security.AccessControl.AccessControlSections]::Owner
        if ($PSVersionTable.PSEdition -eq 'Core') {
            $FileInfo = [System.IO.FileInfo]::new($Path)
            $FileSecurity = [System.IO.FileSystemAclExtensions]::GetAccessControl($FileInfo, $Sections)
        } else {
            $FileSecurity = [System.IO.File]::GetAccessControl($Path, $Sections)
        }
        $OwnerSid = $FileSecurity.GetOwner([System.Security.Principal.SecurityIdentifier])
        $CallerSids = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
        if ($null -ne $Identity.User) { [void]$CallerSids.Add($Identity.User.Value) }
        foreach ($Group in @($Identity.Groups)) { [void]$CallerSids.Add($Group.Value) }
        if ($null -eq $OwnerSid -or -not $CallerSids.Contains($OwnerSid.Value)) {
            throw "Ownership authority is not owned by the current Windows identity: $Path"
        }
    }

    function Assert-NoReparseChain([string]$Path, [string]$StopAt = '') {
        $FullPath = [IO.Path]::GetFullPath($Path)
        $StopPath = if ($StopAt) { [IO.Path]::GetFullPath($StopAt) } else { '' }
        $Current = $FullPath
        while ($true) {
            $Item = Get-Item -LiteralPath $Current -Force -ErrorAction SilentlyContinue
            if ($null -ne $Item) {
                if (($Item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                    throw "Refusing reparse-point install path: $Current"
                }
                if (-not $Current.Equals($FullPath, $PathComparison) -and -not $Item.PSIsContainer) {
                    throw "Install path parent is not a directory: $Current"
                }
            }
            if ($StopPath -and $Current.Equals($StopPath, $PathComparison)) { break }
            $Parent = [IO.Path]::GetDirectoryName($Current)
            if ([string]::IsNullOrEmpty($Parent) -or $Parent.Equals($Current, $PathComparison)) { break }
            $Current = $Parent
        }
        return $FullPath
    }

    function Assert-SafeRecursiveTree([string]$Path) {
        $Root = Get-ContainingConfiguredRoot $Path
        [void](Assert-NoReparseChain $Path $Root)
        $Item = Get-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
        if ($null -eq $Item) { return }
        if (-not $Item.PSIsContainer) { throw "Managed recursive path is not a directory: $Path" }
        $Pending = [System.Collections.Generic.Stack[string]]::new()
        $Pending.Push([IO.Path]::GetFullPath($Path))
        while ($Pending.Count -gt 0) {
            $Directory = $Pending.Pop()
            [void](Assert-NoReparseChain $Directory $Root)
            foreach ($Child in @(Get-ChildItem -LiteralPath $Directory -Force)) {
                if (($Child.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                    throw "Refusing reparse point inside managed recursive directory: $($Child.FullName)"
                }
                if ($Child.PSIsContainer) { $Pending.Push($Child.FullName) }
            }
        }
    }

    function Assert-SafeConfiguredRoot([string]$Root) {
        $FullRoot = Assert-NoReparseChain $Root
        $Item = Get-Item -LiteralPath $FullRoot -Force -ErrorAction SilentlyContinue
        if ($null -ne $Item -and -not $Item.PSIsContainer) {
            throw "Configured install root is not a directory: $FullRoot"
        }
        return $FullRoot
    }

    function Read-ValidPriorManifest {
        $PriorFiles = [System.Collections.Generic.HashSet[string]]::new($StringComparer)
        $PriorDirectories = [System.Collections.Generic.HashSet[string]]::new($StringComparer)
        $PriorRecursiveDirs = [System.Collections.Generic.HashSet[string]]::new($StringComparer)
        $ManifestItem = Get-Item -LiteralPath $ManifestPath -Force -ErrorAction SilentlyContinue
        if ($null -eq $ManifestItem) {
            return @{
                Files = $PriorFiles
                Directories = $PriorDirectories
                RecursiveDirectories = $PriorRecursiveDirs
            }
        }
        if ($ManifestItem.PSIsContainer -or
            (($ManifestItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)) {
            throw "Invalid ownership manifest path: $ManifestPath"
        }
        Assert-CurrentUserOwnedFile $ManifestPath
        try {
            $PriorManifest = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json
        } catch {
            throw "Invalid ownership manifest: $ManifestPath"
        }
        $ExpectedProperties = @('version','target','files','directories','recursive_directories')
        $ActualProperties = @($PriorManifest.PSObject.Properties.Name)
        $VersionType = if ($null -eq $PriorManifest.version) { $null } else { $PriorManifest.version.GetType() }
        if (@(Compare-Object $ExpectedProperties $ActualProperties).Count -ne 0 -or
            $VersionType -notin @([int], [long]) -or $PriorManifest.version -ne 1 -or
            -not ($PriorManifest.target -is [string]) -or $PriorManifest.target -cne $Target) {
            throw "Invalid or mismatched ownership manifest: $ManifestPath"
        }
        $AllPriorPaths = [System.Collections.Generic.HashSet[string]]::new($StringComparer)
        foreach ($PropertyName in @('files','directories','recursive_directories')) {
            if (-not ($PriorManifest.$PropertyName -is [System.Array])) {
                throw "Ownership manifest property must be an array: $PropertyName"
            }
            foreach ($OwnedPath in @($PriorManifest.$PropertyName)) {
                if (-not ($OwnedPath -is [string]) -or [string]::IsNullOrWhiteSpace($OwnedPath)) {
                    throw "Invalid ownership-manifest entry in ${PropertyName}: $ManifestPath"
                }
                $Canonical = Assert-ConfiguredDestination $OwnedPath
                if (-not $OwnedPath.Equals($Canonical, $PathComparison)) {
                    throw "Non-canonical ownership-manifest path: $OwnedPath"
                }
                if ($Canonical.Equals($SkillBase, $PathComparison) -or
                    $Canonical.Equals($AgentDirResolved, $PathComparison)) {
                    throw "Ownership manifest cannot own a configured root: $Canonical"
                }
                if (-not $AllPriorPaths.Add($Canonical)) {
                    throw "Duplicate ownership-manifest path: $Canonical"
                }
                [void](Assert-NoReparseChain $Canonical (Get-ContainingConfiguredRoot $Canonical))
                $OwnedItem = Get-Item -LiteralPath $Canonical -Force -ErrorAction SilentlyContinue
                if ($null -ne $OwnedItem) {
                    if ($PropertyName -eq 'files' -and $OwnedItem.PSIsContainer) {
                        throw "Owned file entry is a directory: $Canonical"
                    }
                    if ($PropertyName -ne 'files' -and -not $OwnedItem.PSIsContainer) {
                        throw "Owned directory entry is not a directory: $Canonical"
                    }
                }
                if ($PropertyName -eq 'files') {
                    if (-not $PriorFiles.Add($Canonical)) {
                        throw "Duplicate ownership-manifest file: $Canonical"
                    }
                } elseif ($PropertyName -eq 'directories') {
                    if (-not $PriorDirectories.Add($Canonical)) {
                        throw "Duplicate ownership-manifest directory: $Canonical"
                    }
                } elseif ($PropertyName -eq 'recursive_directories') {
                    if (-not $PriorRecursiveDirs.Add($Canonical)) {
                        throw "Duplicate recursive ownership-manifest directory: $Canonical"
                    }
                }
            }
        }
        foreach ($RecursivePath in $PriorRecursiveDirs) { Assert-SafeRecursiveTree $RecursivePath }
        return @{
            Files = $PriorFiles
            Directories = $PriorDirectories
            RecursiveDirectories = $PriorRecursiveDirs
        }
    }

    Write-Host "=================================="
    Write-Host "   Claude Ads - Installer"
    Write-Host "   Target: $HostLabel"
    Write-Host "=================================="
    Write-Host ""

    # Prefer the current release/checkout when this script ships with the
    # distribution. Standalone installers use the operator's authenticated Git.
    $SourceDir = $null
    if ($RepoDir) { $Source = 'local' }
    if ($Source -eq 'auto') {
        if ((Test-Path (Join-Path $PSScriptRoot "ads\SKILL.md")) -and (Test-Path (Join-Path $PSScriptRoot "skills"))) {
            $Source = 'local'
            $SourceDir = $PSScriptRoot
        } else {
            $Source = 'git'
        }
    }
    if ($Source -eq 'local') {
        $SourceDir = if ($RepoDir) { $RepoDir } else { $PSScriptRoot }
        if (-not (Test-InstallPath -Path $SourceDir)) { throw "Invalid local repository path" }
        $SourceDir = (Resolve-Path $SourceDir).Path
        if (-not (Test-Path (Join-Path $SourceDir "ads\SKILL.md"))) {
            throw "Local source is not a Claude Ads distribution: $SourceDir"
        }
    } elseif (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        Write-Host "X Git is required for -Source git." -ForegroundColor Red
        exit 1
    }
    $ManagedPython = $null
    $PythonTarget = $null
    if ($AllowPip -and -not $NoDeps) {
        $ManagedPython = Get-Command python -ErrorAction SilentlyContinue
        if (-not $ManagedPython) {
            throw "python not found. Re-run with -NoDeps to install without Python helpers."
        }
        $PythonTarget = & $ManagedPython.Source -c "import platform,sys; print('|'.join((sys.implementation.name, f'{sys.version_info.major}.{sys.version_info.minor}', platform.system().lower(), platform.machine().lower())))"
        if ($PythonTarget -notin @("cpython|3.11|windows|amd64", "cpython|3.12|windows|amd64")) {
            throw "No verified dependency lock target for $PythonTarget. Re-run with -NoDeps; moving-range fallback is disabled."
        }
        $DependencyTargetId = if ($PythonTarget -eq "cpython|3.11|windows|amd64") { "runtime-windows-cp311" } else { "runtime-windows-cp312" }
    }
    Write-Host "OK Distribution source: $Source" -ForegroundColor Green

    # Clone to temp directory
    $TempDir = $null

    try {
        if ($Source -eq 'git') {
            $TempDir = Join-Path $env:TEMP "claude-ads-install-$(Get-Random)"
            Write-Host "Downloading Claude Ads with authenticated Git..."
            $ErrorActionPreference = "Continue"
            git clone --depth 1 $RepoUrl "$TempDir\claude-ads" 2>&1 | Out-Null
            $ErrorActionPreference = "Stop"
            if ($LASTEXITCODE -ne 0) { throw "Git clone failed" }
            $SourceDir = "$TempDir\claude-ads"
        }

        # Build the complete destination plan without touching either configured
        # root.  This lets any collision fail before the first install mutation.
        $FilePlan = [System.Collections.Generic.List[object]]::new()
        $PlannedFiles = [System.Collections.Generic.HashSet[string]]::new($StringComparer)
        $PlannedDirs = [System.Collections.Generic.List[string]]::new()
        $PlannedDirSet = [System.Collections.Generic.HashSet[string]]::new($StringComparer)
        $RecursiveDirs = [System.Collections.Generic.List[string]]::new()

        function Add-PlannedDirectory([string]$Destination) {
            $Canonical = Assert-ConfiguredDestination $Destination
            $Current = $Canonical
            while (-not ($Current.Equals($SkillBase, $PathComparison) -or
                $Current.Equals($AgentDirResolved, $PathComparison))) {
                if ($PlannedDirSet.Add($Current)) { [void]$PlannedDirs.Add($Current) }
                $Parent = [IO.Path]::GetDirectoryName($Current)
                if ([string]::IsNullOrEmpty($Parent) -or $Parent.Equals($Current, $PathComparison)) {
                    throw "Install directory escapes configured roots: $Destination"
                }
                $Current = $Parent
            }
            return $Canonical
        }

        function Add-PlannedFile([string]$SourcePath, [string]$Destination) {
            $Canonical = Assert-ConfiguredDestination $Destination
            if (-not $PlannedFiles.Add($Canonical)) {
                throw "Duplicate planned install file: $Canonical"
            }
            [void](Add-PlannedDirectory ([IO.Path]::GetDirectoryName($Canonical)))
            [void]$FilePlan.Add([pscustomobject]@{
                Source = [IO.Path]::GetFullPath($SourcePath)
                Destination = $Canonical
            })
        }

        [void](Add-PlannedDirectory $SkillDirResolved)
        $ReferencesDir = Add-PlannedDirectory (Join-Path $SkillDirResolved "references")
        Add-PlannedFile (Join-Path $SourceDir "ads\SKILL.md") (Join-Path $SkillDirResolved "SKILL.md")
        Get-ChildItem (Join-Path $SourceDir "ads\references\*.md") -File | Sort-Object Name | ForEach-Object {
            Add-PlannedFile $_.FullName (Join-Path $ReferencesDir $_.Name)
        }

        $InterfaceSource = Join-Path $SourceDir "ads\agents"
        if (Test-Path -LiteralPath $InterfaceSource -PathType Container) {
            $InterfaceDir = Add-PlannedDirectory (Join-Path $SkillDirResolved "agents")
            Get-ChildItem (Join-Path $InterfaceSource "*.yaml") -File | Sort-Object Name | ForEach-Object {
                Add-PlannedFile $_.FullName (Join-Path $InterfaceDir $_.Name)
            }
        }

        Get-ChildItem (Join-Path $SourceDir "skills") -Directory | Sort-Object Name | ForEach-Object {
            $TargetDir = Add-PlannedDirectory (Join-Path $SkillBase $_.Name)
            Add-PlannedFile (Join-Path $_.FullName "SKILL.md") (Join-Path $TargetDir "SKILL.md")
            $AssetsDir = Join-Path $_.FullName "assets"
            if (Test-Path -LiteralPath $AssetsDir -PathType Container) {
                $TargetAssets = Add-PlannedDirectory (Join-Path $TargetDir "assets")
                Get-ChildItem (Join-Path $AssetsDir "*.md") -File | Sort-Object Name | ForEach-Object {
                    Add-PlannedFile $_.FullName (Join-Path $TargetAssets $_.Name)
                }
            }
        }

        Get-ChildItem (Join-Path $SourceDir "agents\*.md") -File | Sort-Object Name | ForEach-Object {
            Add-PlannedFile $_.FullName (Join-Path $AgentDirResolved $_.Name)
        }

        $ScriptsSource = Join-Path $SourceDir "scripts"
        $ScriptsDir = Join-Path $SkillDirResolved "scripts"
        if (Test-Path -LiteralPath $ScriptsSource -PathType Container) {
            $ScriptsDir = Add-PlannedDirectory $ScriptsDir
            Get-ChildItem (Join-Path $ScriptsSource "*.py") -File | Sort-Object Name | ForEach-Object {
                Add-PlannedFile $_.FullName (Join-Path $ScriptsDir $_.Name)
            }
            Add-PlannedFile (Join-Path $SourceDir "requirements.txt") (Join-Path $SkillDirResolved "requirements.txt")
            Add-PlannedFile (Join-Path $SourceDir "requirements.lock") (Join-Path $SkillDirResolved "requirements.lock")
            $CoreSource = Join-Path $SourceDir "claude_ads_core"
            $CoreDir = Add-PlannedDirectory (Join-Path $ScriptsDir "claude_ads_core")
            Get-ChildItem $CoreSource -File -Recurse | Where-Object {
                $_.Extension -in @(".py", ".json") -and $_.FullName -notmatch "[\\/]__pycache__[\\/]"
            } | Sort-Object FullName | ForEach-Object {
                $Relative = Get-CompatibleRelativePath $CoreSource $_.FullName
                Add-PlannedFile $_.FullName (Join-Path $CoreDir $Relative)
            }
        }

        $VenvDir = Assert-ConfiguredDestination (Join-Path $SkillDirResolved ".venv")
        $ReceiptPath = Assert-ConfiguredDestination (Join-Path $SkillDirResolved "managed-runtime-receipt.json")
        if ($AllowPip -and -not $NoDeps) {
            [void]$RecursiveDirs.Add($VenvDir)
            if (-not $PlannedFiles.Add($ReceiptPath)) {
                throw "Duplicate planned install file: $ReceiptPath"
            }
        }

        # Validate the previous ownership state, then preflight every root,
        # directory, file, receipt, and managed environment before mutation.
        # On Windows the local manifest must belong to the caller's user SID or
        # one of its token-group owner principals. A process with that same
        # principal can still alter it; a local manifest cannot defend against
        # that without a separately privileged or external trust root.
        $Prior = Read-ValidPriorManifest
        $PriorFiles = $Prior.Files
        $PriorDirectories = $Prior.Directories
        $PriorRecursiveDirs = $Prior.RecursiveDirectories
        [void](Assert-SafeConfiguredRoot $SkillBase)
        [void](Assert-SafeConfiguredRoot $AgentDirResolved)
        foreach ($Directory in $PlannedDirs) {
            [void](Assert-NoReparseChain $Directory (Get-ContainingConfiguredRoot $Directory))
            $DirectoryItem = Get-Item -LiteralPath $Directory -Force -ErrorAction SilentlyContinue
            if ($null -ne $DirectoryItem -and -not $DirectoryItem.PSIsContainer) {
                throw "Install directory destination is not a directory: $Directory"
            }
        }
        foreach ($Destination in $PlannedFiles) {
            $ContainingRoot = Get-ContainingConfiguredRoot $Destination
            [void](Assert-NoReparseChain $Destination $ContainingRoot)
            $DestinationItem = Get-Item -LiteralPath $Destination -Force -ErrorAction SilentlyContinue
            if ($null -ne $DestinationItem) {
                if ($DestinationItem.PSIsContainer -or -not $PriorFiles.Contains($Destination)) {
                    throw "Refusing to overwrite unowned file: $Destination"
                }
            }
        }
        if ($AllowPip -and -not $NoDeps) {
            Assert-SafeRecursiveTree $VenvDir
            $VenvItem = Get-Item -LiteralPath $VenvDir -Force -ErrorAction SilentlyContinue
            if ($null -ne $VenvItem -and
                (-not $VenvItem.PSIsContainer -or -not $PriorRecursiveDirs.Contains($VenvDir))) {
                throw "Refusing to reuse unowned managed environment: $VenvDir"
            }
        }

        # All conflict checks passed.  Recheck each destination immediately
        # before copying so a concurrent replacement cannot bypass the guard.
        New-Item -ItemType Directory -Path $SkillBase -Force | Out-Null
        New-Item -ItemType Directory -Path $AgentDirResolved -Force | Out-Null
        $OwnedPlannedDirs = [System.Collections.Generic.HashSet[string]]::new($StringComparer)
        foreach ($Directory in @($PlannedDirs | Sort-Object Length)) {
            [void](Assert-NoReparseChain $Directory)
            $DirectoryItem = Get-Item -LiteralPath $Directory -Force -ErrorAction SilentlyContinue
            if ($null -eq $DirectoryItem) {
                New-Item -ItemType Directory -Path $Directory | Out-Null
                [void]$OwnedPlannedDirs.Add($Directory)
            } elseif ($PriorDirectories.Contains($Directory)) {
                [void]$OwnedPlannedDirs.Add($Directory)
            }
        }
        Write-Host "Installing guarded skill, sub-skill, agent, and runtime files..."
        foreach ($PlannedFile in $FilePlan) {
            [void](Assert-NoReparseChain $PlannedFile.Destination)
            $DestinationItem = Get-Item -LiteralPath $PlannedFile.Destination -Force -ErrorAction SilentlyContinue
            if ($null -ne $DestinationItem -and
                ($DestinationItem.PSIsContainer -or -not $PriorFiles.Contains($PlannedFile.Destination))) {
                throw "Refusing to overwrite unowned file: $($PlannedFile.Destination)"
            }
            Copy-Item -LiteralPath $PlannedFile.Source -Destination $PlannedFile.Destination -Force
        }

        # Commit exact canonical ownership before dependency installation so a
        # later pip failure remains recoverable with uninstall.  Preserve safe
        # prior entries that disappeared from this distribution (and a managed
        # runtime during -NoDeps) so an upgrade never strands owned artifacts.
        $ManifestFiles = [System.Collections.Generic.HashSet[string]]::new($StringComparer)
        [void]$ManifestFiles.UnionWith($PriorFiles)
        [void]$ManifestFiles.UnionWith($PlannedFiles)
        $ManifestDirectories = [System.Collections.Generic.HashSet[string]]::new($StringComparer)
        [void]$ManifestDirectories.UnionWith($PriorDirectories)
        [void]$ManifestDirectories.UnionWith($OwnedPlannedDirs)
        $ManifestRecursiveDirs = [System.Collections.Generic.HashSet[string]]::new($StringComparer)
        [void]$ManifestRecursiveDirs.UnionWith($PriorRecursiveDirs)
        [void]$ManifestRecursiveDirs.UnionWith($RecursiveDirs)
        $Manifest = @{
            version = 1
            target = $Target
            files = @($ManifestFiles | Sort-Object)
            directories = @($ManifestDirectories | Sort-Object)
            recursive_directories = @($ManifestRecursiveDirs | Sort-Object)
        }
        $ManifestTemp = Join-Path $SkillBase (".claude-ads-manifest-" + [IO.Path]::GetRandomFileName())
        $Manifest | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $ManifestTemp -Encoding UTF8
        Move-Item -LiteralPath $ManifestTemp -Destination $ManifestPath -Force
        Assert-CurrentUserOwnedFile $ManifestPath
        Write-Host "OK Ownership manifest: $ManifestPath" -ForegroundColor Green

        Write-Host ""
        if ($AllowPip -and -not $NoDeps) {
            Remove-Item -LiteralPath $ReceiptPath -Force -ErrorAction SilentlyContinue
            Write-Host "Installing exact hashed Python dependencies into a managed virtual environment..."
            $ErrorActionPreference = "Continue"
            if ($ManagedPython) {
                Assert-SafeRecursiveTree $VenvDir
                & $ManagedPython.Source -m venv $VenvDir
                if ($LASTEXITCODE -eq 0) {
                    & "$VenvDir\Scripts\python.exe" -m pip install -q --ignore-installed --report "$VenvDir\install-report.json" --require-hashes --only-binary=:all: -r "$SkillDirResolved\requirements.lock"
                }
                if ($LASTEXITCODE -eq 0) {
                    $SitePackages = & "$VenvDir\Scripts\python.exe" -c "import sysconfig; print(sysconfig.get_paths()['purelib'])"
                    $ScriptsDir | Set-Content -Path (Join-Path $SitePackages "claude-ads-core.pth") -Encoding UTF8
                    & "$VenvDir\Scripts\python.exe" -m pip check
                }
                if ($LASTEXITCODE -eq 0) {
                    & "$VenvDir\Scripts\python.exe" "$ScriptsDir\write_install_receipt.py" --inventory "$SourceDir\control-plane\manifests\dependency-inventory.json" --lock "$SkillDirResolved\requirements.lock" --evidence "$SourceDir\control-plane\dependency-evidence\$DependencyTargetId.json" --pip-report "$VenvDir\install-report.json" --target-id $DependencyTargetId --output "$SkillDirResolved\managed-runtime-receipt.json"
                }
            }
            if ($ManagedPython -and $LASTEXITCODE -eq 0) {
                Write-Host "  OK Exact locked Python dependencies installed in $VenvDir" -ForegroundColor Green
            } else {
                $CleanupRefused = $null
                try {
                    Assert-SafeRecursiveTree $VenvDir
                    Remove-Item -LiteralPath $VenvDir -Recurse -Force -ErrorAction SilentlyContinue
                } catch {
                    $CleanupRefused = $_.Exception.Message
                }
                Remove-Item -LiteralPath $ReceiptPath -Force -ErrorAction SilentlyContinue
                if ($CleanupRefused) {
                    throw "Exact hashed dependency installation failed; unsafe managed environment cleanup was refused: $CleanupRefused"
                }
                throw "Exact hashed dependency installation failed; no moving-range fallback was attempted."
            }
            $ErrorActionPreference = "Stop"
        } elseif ($NoDeps) {
            Write-Host "i  Skipping Python dependencies (-NoDeps)." -ForegroundColor Yellow
        } else {
            Write-Host "i  Skipping Python dependencies - $HostLabel host runtime may not execute Python skills directly." -ForegroundColor Yellow
            Write-Host "   Python helpers require the packaged exact-hash lock on a supported CPython wheel target."
        }

        Write-Host ""
        Write-Host "i  Image generation requires an explicitly configured eligible provider/model"
        Write-Host "   with capability evidence; Claude Ads does not probe or recommend a default."

        Write-Host ""
        Write-Host "Claude Ads installed successfully for $HostLabel!" -ForegroundColor Green
        Write-Host ""
        Write-Host "  Installed to:"
        Write-Host "    Skills: $SkillBase"
        Write-Host "    Agents: $AgentDirResolved"
        Write-Host ""
        Write-Host "  Bundled:"
        $SubSkillCount = @(Get-ChildItem "$SourceDir\skills" -Directory | Where-Object { Test-Path (Join-Path $_.FullName "SKILL.md") }).Count
        $AgentCount = @(Get-ChildItem "$SourceDir\agents\*.md" -File).Count
        $ReferenceCount = @(Get-ChildItem "$SourceDir\ads\references\*.md" -File).Count
        Write-Host "    - 1 main skill (ads orchestrator)"
        Write-Host "    - $SubSkillCount sub-skills (platform + lifecycle + functional + creative)"
        Write-Host "    - $AgentCount agents"
        Write-Host "    - $ReferenceCount reference files"
        Write-Host "    - 12 industry templates"
        Write-Host ""
        Write-Host "Usage:"
        Write-Host "  1. Start your host CLI"
        Write-Host "  2. Run commands:       /ads audit"
        Write-Host "                         /ads plan saas"
        Write-Host "                         /ads google"
        Write-Host ""
        Write-Host "To uninstall: .\uninstall.ps1 -Target $Target"
    }
    finally {
        # Cleanup temp directory
        if ($TempDir -and (Test-Path $TempDir)) {
            Remove-Item -Path $TempDir -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}

Main
