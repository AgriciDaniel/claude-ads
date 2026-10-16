#Requires -Version 5.1
<#
.SYNOPSIS
    Claude Ads Uninstaller for Windows (multi-host).
.DESCRIPTION
    Removes only paths listed in install.ps1's ownership manifest. Unrelated
    ads-* skills and agents are never discovered or deleted by namespace.
.PARAMETER Target
    Which host CLI to uninstall from. Default: claude.
#>

param(
    [ValidateSet('claude','codex','cursor','windsurf','gemini','goose')]
    [string]$Target = 'claude',
    [string]$SkillDir = '',
    [string]$AgentDir = ''
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
        'claude'   { return @{ SkillBase = Join-Path $UserHome ".claude\skills";                                AgentDir = Join-Path $UserHome ".claude\agents" } }
        'codex'    { return @{ SkillBase = Join-Path $UserHome ".codex\skills";                                 AgentDir = Join-Path $UserHome ".codex\agents" } }
        'cursor'   { return @{ SkillBase = Join-Path $UserHome ".cursor\extensions\claude-ads\skills";          AgentDir = Join-Path $UserHome ".cursor\extensions\claude-ads\agents" } }
        'windsurf' { return @{ SkillBase = Join-Path $UserHome ".windsurf\skills";                              AgentDir = Join-Path $UserHome ".windsurf\agents" } }
        'gemini'   { return @{ SkillBase = Join-Path $UserHome ".gemini\extensions\claude-ads\skills";          AgentDir = Join-Path $UserHome ".gemini\extensions\claude-ads\agents" } }
        'goose'    { return @{ SkillBase = Join-Path $UserHome ".config\goose\skills";                          AgentDir = Join-Path $UserHome ".config\goose\agents" } }
        default    { throw "Unknown target: $T" }
    }
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

function Main {
    $paths = Resolve-TargetPaths -T $Target
    $Separators = [char[]]@([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar)
    $Boundary = [string][IO.Path]::DirectorySeparatorChar
    $PathComparison = if ([Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT) {
        [StringComparison]::OrdinalIgnoreCase
    } else {
        [StringComparison]::Ordinal
    }
    $StringComparer = if ($PathComparison -eq [StringComparison]::OrdinalIgnoreCase) {
        [StringComparer]::OrdinalIgnoreCase
    } else {
        [StringComparer]::Ordinal
    }
    $SkillBase = if ($SkillDir) { $SkillDir } else { $paths.SkillBase }
    $AgentDirResolved = if ($AgentDir) { $AgentDir } else { $paths.AgentDir }
    $SkillBase = Get-NormalizedInstallRoot $SkillBase
    $AgentDirResolved = Get-NormalizedInstallRoot $AgentDirResolved

    function Get-RootPrefix([string]$Root) {
        if ($Root.EndsWith($Boundary, $PathComparison)) { return $Root }
        return $Root + $Boundary
    }

    $SkillRootPrefix = Get-RootPrefix $SkillBase
    $AgentRootPrefix = Get-RootPrefix $AgentDirResolved
    if ($SkillBase.Equals($AgentDirResolved, $PathComparison) -or
        $SkillBase.StartsWith($AgentRootPrefix, $PathComparison) -or
        $AgentDirResolved.StartsWith($SkillRootPrefix, $PathComparison)) {
        throw "Skill and agent install roots must not overlap: $SkillBase ; $AgentDirResolved"
    }
    $ManifestPath = [IO.Path]::GetFullPath((Join-Path $SkillBase ".claude-ads-$Target.manifest.json"))

    function Get-ContainingRoot([string]$Path) {
        $FullPath = [IO.Path]::GetFullPath($Path)
        if ($FullPath.StartsWith($SkillRootPrefix, $PathComparison)) { return $SkillBase }
        if ($FullPath.StartsWith($AgentRootPrefix, $PathComparison)) { return $AgentDirResolved }
        throw "Unsafe ownership-manifest path: $Path"
    }

    function Assert-CanonicalOwnedPath([string]$Path) {
        if ([string]::IsNullOrWhiteSpace($Path)) { throw "Invalid empty ownership-manifest path" }
        $FullPath = [IO.Path]::GetFullPath($Path)
        if (-not $Path.Equals($FullPath, $PathComparison)) {
            throw "Non-canonical ownership-manifest path: $Path"
        }
        try { $null = Get-ContainingRoot $FullPath } catch {
            throw "Unsafe ownership-manifest path: $Path"
        }
        return $FullPath
    }

    function Assert-NoReparseChain([string]$Path, [string]$StopAt = '') {
        $FullPath = [IO.Path]::GetFullPath($Path)
        $StopPath = if ($StopAt) { [IO.Path]::GetFullPath($StopAt) } else { '' }
        $Current = $FullPath
        while ($true) {
            $Item = Get-Item -LiteralPath $Current -Force -ErrorAction SilentlyContinue
            if ($null -ne $Item) {
                if (($Item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                    throw "Refusing reparse-point uninstall path: $Current"
                }
                if (-not $Current.Equals($FullPath, $PathComparison) -and -not $Item.PSIsContainer) {
                    throw "Uninstall path parent is not a directory: $Current"
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
        $Root = Get-ContainingRoot $Path
        [void](Assert-NoReparseChain $Path $Root)
        $Item = Get-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
        if ($null -eq $Item) { return }
        if (-not $Item.PSIsContainer) { throw "Recursive ownership entry is not a directory: $Path" }
        $Pending = [System.Collections.Generic.Stack[string]]::new()
        $Pending.Push([IO.Path]::GetFullPath($Path))
        while ($Pending.Count -gt 0) {
            $Directory = $Pending.Pop()
            [void](Assert-NoReparseChain $Directory $Root)
            foreach ($Child in @(Get-ChildItem -LiteralPath $Directory -Force)) {
                if (($Child.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                    throw "Refusing reparse point inside recursive ownership directory: $($Child.FullName)"
                }
                if ($Child.PSIsContainer) { $Pending.Push($Child.FullName) }
            }
        }
    }

    function Assert-ExactBytecodeDirectory([string]$Path) {
        $Canonical = Assert-CanonicalOwnedPath $Path
        $Allowed = @(
            [IO.Path]::GetFullPath((Join-Path $SkillBase "ads\scripts\claude_ads_core\__pycache__")),
            [IO.Path]::GetFullPath((Join-Path $SkillBase "ads\scripts\claude_ads_core\adapters\__pycache__"))
        )
        if (@($Allowed | Where-Object { $_.Equals($Canonical, $PathComparison) }).Count -ne 1) {
            throw "Unsafe bytecode ownership root: $Path"
        }
        return $Canonical
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
            throw "Ownership manifest is not owned by the current Windows principal: $Path"
        }
    }

    [void](Assert-NoReparseChain $SkillBase)
    [void](Assert-NoReparseChain $AgentDirResolved)
    [void](Assert-NoReparseChain $ManifestPath $SkillBase)
    $ManifestItem = Get-Item -LiteralPath $ManifestPath -Force -ErrorAction SilentlyContinue
    if ($null -eq $ManifestItem -or $ManifestItem.PSIsContainer -or
        (($ManifestItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)) {
        throw "Ownership manifest not found or unsafe: $ManifestPath. Refusing namespace-based deletion."
    }
    Assert-CurrentUserOwnedFile $ManifestPath
    try { $Manifest = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json } catch {
        throw "Invalid ownership manifest: $ManifestPath"
    }
    $LegacyExpectedProperties = @('version','target','files','directories','recursive_directories')
    $CurrentExpectedProperties = @($LegacyExpectedProperties + 'bytecode_directories')
    $ActualProperties = @($Manifest.PSObject.Properties.Name)
    $HasLegacyShape = @(Compare-Object $LegacyExpectedProperties $ActualProperties).Count -eq 0
    $HasCurrentShape = @(Compare-Object $CurrentExpectedProperties $ActualProperties).Count -eq 0
    $VersionType = if ($null -eq $Manifest.version) { $null } else { $Manifest.version.GetType() }
    if ((-not $HasLegacyShape -and -not $HasCurrentShape) -or
        $VersionType -notin @([int], [long]) -or $Manifest.version -ne 1 -or
        -not ($Manifest.target -is [string]) -or $Manifest.target -cne $Target) {
        throw "Invalid or mismatched ownership manifest: $ManifestPath"
    }

    $AllPaths = [System.Collections.Generic.HashSet[string]]::new($StringComparer)
    $Validated = @{}
    $OwnershipProperties = @('files','directories','recursive_directories')
    if ($HasCurrentShape) { $OwnershipProperties += 'bytecode_directories' }
    foreach ($PropertyName in $OwnershipProperties) {
        if (-not ($Manifest.$PropertyName -is [System.Array])) {
            throw "Ownership manifest property must be an array: $PropertyName"
        }
        $Paths = [System.Collections.Generic.List[string]]::new()
        foreach ($OwnedPath in @($Manifest.$PropertyName)) {
            if (-not ($OwnedPath -is [string])) {
                throw "Invalid ownership-manifest entry in ${PropertyName}: $ManifestPath"
            }
            $FullPath = Assert-CanonicalOwnedPath $OwnedPath
            if ($PropertyName -eq 'bytecode_directories') {
                $FullPath = Assert-ExactBytecodeDirectory $FullPath
            }
            if (-not $AllPaths.Add($FullPath)) { throw "Duplicate ownership-manifest path: $FullPath" }
            [void](Assert-NoReparseChain $FullPath (Get-ContainingRoot $FullPath))
            $Item = Get-Item -LiteralPath $FullPath -Force -ErrorAction SilentlyContinue
            if ($null -ne $Item) {
                if ($PropertyName -eq 'files' -and $Item.PSIsContainer) {
                    throw "Owned file entry is a directory: $FullPath"
                }
                if ($PropertyName -ne 'files' -and -not $Item.PSIsContainer) {
                    throw "Owned directory entry is not a directory: $FullPath"
                }
            }
            [void]$Paths.Add($FullPath)
        }
        $Validated[$PropertyName] = $Paths
    }
    foreach ($RecursivePath in $Validated.recursive_directories) { Assert-SafeRecursiveTree $RecursivePath }
    if (-not $HasCurrentShape) { $Validated.bytecode_directories = @() }
    foreach ($BytecodePath in $Validated.bytecode_directories) {
        $Parent = [IO.Path]::GetDirectoryName($BytecodePath)
        $OwnedModules = @($Validated.files | Where-Object {
            ([IO.Path]::GetDirectoryName($_)).Equals($Parent, $PathComparison) -and
            [IO.Path]::GetExtension($_) -ceq '.py'
        })
        if ($OwnedModules.Count -eq 0) {
            throw "Bytecode ownership root has no owned Python modules: $BytecodePath"
        }
    }

    Write-Host "Uninstalling Claude Ads from $SkillBase and $AgentDirResolved..."

    foreach ($FullPath in $Validated.files) {
        [void](Assert-NoReparseChain $FullPath (Get-ContainingRoot $FullPath))
        $Item = Get-Item -LiteralPath $FullPath -Force -ErrorAction SilentlyContinue
        if ($null -ne $Item) {
            if ($Item.PSIsContainer -or (($Item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)) {
                throw "Owned file changed type before deletion: $FullPath"
            }
            Remove-Item -LiteralPath $FullPath -Force
        }
    }

    foreach ($BytecodePath in $Validated.bytecode_directories) {
        [void](Assert-NoReparseChain $BytecodePath (Get-ContainingRoot $BytecodePath))
        $BytecodeItem = Get-Item -LiteralPath $BytecodePath -Force -ErrorAction SilentlyContinue
        if ($null -eq $BytecodeItem) { continue }
        if (-not $BytecodeItem.PSIsContainer -or
            (($BytecodeItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)) {
            throw "Bytecode directory changed type before cleanup: $BytecodePath"
        }
        $Parent = [IO.Path]::GetDirectoryName($BytecodePath)
        foreach ($OwnedSource in $Validated.files) {
            if (-not ([IO.Path]::GetDirectoryName($OwnedSource)).Equals($Parent, $PathComparison) -or
                [IO.Path]::GetExtension($OwnedSource) -cne '.py') {
                continue
            }
            $Module = [regex]::Escape([IO.Path]::GetFileNameWithoutExtension($OwnedSource))
            $Pattern = "^${Module}\.cpython-(?:311|312)(?:\.opt-[0-9])?\.pyc$"
            foreach ($Cached in @(Get-ChildItem -LiteralPath $BytecodePath -File -Force -ErrorAction SilentlyContinue)) {
                if ($Cached.Name -notmatch $Pattern -or
                    (($Cached.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)) {
                    continue
                }
                Remove-Item -LiteralPath $Cached.FullName -Force
            }
        }
        if (@(Get-ChildItem -LiteralPath $BytecodePath -Force -ErrorAction SilentlyContinue).Count -eq 0) {
            Remove-Item -LiteralPath $BytecodePath -Force -Confirm:$false
        }
    }

    foreach ($FullPath in $Validated.recursive_directories) {
        Assert-SafeRecursiveTree $FullPath
        $Item = Get-Item -LiteralPath $FullPath -Force -ErrorAction SilentlyContinue
        if ($null -ne $Item) { Remove-Item -LiteralPath $FullPath -Recurse -Force }
    }

    foreach ($FullPath in @($Validated.directories | Sort-Object Length -Descending)) {
        [void](Assert-NoReparseChain $FullPath (Get-ContainingRoot $FullPath))
        $Item = Get-Item -LiteralPath $FullPath -Force -ErrorAction SilentlyContinue
        if ($null -ne $Item) {
            if (-not $Item.PSIsContainer -or (($Item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)) {
                throw "Owned directory changed type before deletion: $FullPath"
            }
            $Children = @(Get-ChildItem -LiteralPath $FullPath -Force -ErrorAction SilentlyContinue)
            if ($Children.Count -eq 0) {
                Remove-Item -LiteralPath $FullPath -Force -Confirm:$false
            }
        }
    }

    [void](Assert-NoReparseChain $ManifestPath $SkillBase)
    $ManifestItem = Get-Item -LiteralPath $ManifestPath -Force -ErrorAction SilentlyContinue
    if ($null -eq $ManifestItem -or $ManifestItem.PSIsContainer -or
        (($ManifestItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)) {
        throw "Ownership manifest changed before deletion: $ManifestPath"
    }
    Remove-Item -LiteralPath $ManifestPath -Force

    Write-Host "[OK] Claude Ads uninstalled." -ForegroundColor Green
}

Main
