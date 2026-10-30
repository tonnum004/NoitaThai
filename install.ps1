# Noita Thai translation installer: copies the mod into <Noita>\mods\thai,
# enables it and switches the game language to Thai. Run via install.bat.
param(
    [string]$NoitaPath,  # skip auto-detect (also used for testing)
    [string]$SaveDir = "$env:USERPROFILE\AppData\LocalLow\Nolla_Games_Noita",
    [switch]$Quiet       # print instead of message boxes (for testing)
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms

function Say($text, $icon = 'Information') {
    if ($Quiet) { Write-Output "[$icon] $text"; return }
    [void][System.Windows.Forms.MessageBox]::Show($text, 'Noita ภาษาไทย', 'OK', $icon)
}

function Find-Noita {
    $steam = (Get-ItemProperty 'HKCU:\Software\Valve\Steam' -ErrorAction SilentlyContinue).SteamPath
    if (-not $steam) { return $null }
    $libs = @($steam)
    $vdf = Join-Path $steam 'steamapps\libraryfolders.vdf'
    if (Test-Path $vdf) {
        $libs += Select-String -Path $vdf -Pattern '"path"\s+"([^"]+)"' |
            ForEach-Object { $_.Matches[0].Groups[1].Value -replace '\\\\', '\' }
    }
    foreach ($lib in $libs) {
        $p = Join-Path $lib 'steamapps\common\Noita'
        if (Test-Path (Join-Path $p 'noita.exe')) { return $p }
    }
    return $null
}

try {
    if (Get-Process noita, noita_dev -ErrorAction SilentlyContinue) {
        Say 'กรุณาปิดเกม Noita ก่อน แล้วรันตัวติดตั้งอีกครั้ง' 'Warning'
        exit 1
    }

    if (-not $NoitaPath) { $NoitaPath = Find-Noita }
    if (-not $NoitaPath) {
        $dlg = New-Object System.Windows.Forms.FolderBrowserDialog
        $dlg.Description = 'หาโฟลเดอร์เกม Noita ไม่เจอ กรุณาเลือกโฟลเดอร์ที่มีไฟล์ noita.exe'
        if ($dlg.ShowDialog() -ne 'OK') { exit 1 }
        $NoitaPath = $dlg.SelectedPath
    }
    if (-not (Test-Path (Join-Path $NoitaPath 'noita.exe'))) {
        Say "ไม่พบ noita.exe ใน:`n$NoitaPath" 'Error'
        exit 1
    }

    # 1) copy mod files (the game's xml files expect the folder name "thai")
    $src = $PSScriptRoot
    $dst = Join-Path $NoitaPath 'mods\thai'
    if ((Resolve-Path $src).Path -ne [IO.Path]::GetFullPath($dst)) {
        New-Item -ItemType Directory -Force -Path (Join-Path $dst 'fonts') | Out-Null
        foreach ($f in 'mod.xml', 'translation.xml', 'translation.csv', 'README_THAI.txt') {
            Copy-Item (Join-Path $src $f) $dst -Force
        }
        Copy-Item (Join-Path $src 'fonts\*') (Join-Path $dst 'fonts') -Force
        Copy-Item (Join-Path $src 'fonts_src\OFL.txt') $dst -Force  # font license must ship with the font
    }

    # 2) enable the mod and set the language (backups next to each file)
    $notes = @()
    $modCfg = Join-Path $SaveDir 'save00\mod_config.xml'
    $entry = '  <Mod enabled="1" name="thai" settings_fold_open="0" workshop_item_id="0" >' + "`r`n  </Mod>`r`n"
    if (Test-Path $modCfg) {
        Copy-Item $modCfg "$modCfg.bak-thai" -Force
        $x = [IO.File]::ReadAllText($modCfg)
        if ($x -match '<Mod [^>]*name="thai"') {
            $x = $x -replace '<Mod enabled="0"( name="thai")', '<Mod enabled="1"$1'
        } else {
            # the game writes "\r\r\n" line ends, so match any run of CR/LF
            $x = $x -replace '<Mods>[\r\n]*', "<Mods>`r`n$entry"
        }
        if ($x -notmatch '<Mod enabled="1" name="thai"') { throw "could not enable the mod in $modCfg" }
        [IO.File]::WriteAllText($modCfg, $x)
    } else {
        New-Item -ItemType Directory -Force -Path (Split-Path $modCfg) | Out-Null
        [IO.File]::WriteAllText($modCfg, "<Mods>`r`n$entry</Mods>`r`n")
    }

    $cfg = Join-Path $SaveDir 'save_shared\config.xml'
    if (Test-Path $cfg) {
        Copy-Item $cfg "$cfg.bak-thai" -Force
        $x = [IO.File]::ReadAllText($cfg)
        if ($x -match 'language="[^"]*"') {
            [IO.File]::WriteAllText($cfg, ($x -replace 'language="[^"]*"', 'language="th"'))
        } else { $notes += 'เลือกภาษาเองที่ Options > Language > ภาษาไทย' }
    } else { $notes += 'เปิดเกมแล้วเลือกภาษาที่ Options > Language > ภาษาไทย' }

    Say ("ติดตั้งเสร็จแล้ว เปิดเกมได้เลย`n`n" + ($notes -join "`n")).Trim()
} catch {
    Say "ติดตั้งไม่สำเร็จ:`n$($_.Exception.Message)" 'Error'
    exit 1
}
