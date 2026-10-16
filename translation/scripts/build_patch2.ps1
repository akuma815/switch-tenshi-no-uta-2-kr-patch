param([string]$SourcePaks = '', [string]$RetocPath = '', [string]$RepakPath = '', [switch]$CurrentTranslations)
# ============================================================
# 천사의 시 2편 (The Fallen Angel) 한글 패치 원클릭 빌드 스크립트
# 실행: powershell -ExecutionPolicy Bypass -File scripts\build_patch2.ps1
# (작업 기준 폴더 = 이 스크립트의 상위 폴더 = translation)
# ============================================================
$ErrorActionPreference = "Stop"
if (-not $CurrentTranslations) { $env:INCLUDE_MANUAL = '1' }
$root = Split-Path $PSScriptRoot            # translation 폴더
$scripts = $PSScriptRoot
$gameRoot = Split-Path $root                # 게임 루트 폴더
$gamesRoot = Split-Path $gameRoot            # Games 폴더
$projectRoot = Split-Path $gamesRoot         # Korean Traslate Project 폴더

function Find-FirstExistingPath([string[]]$candidates) {
    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return (Resolve-Path $candidate).Path
        }
    }
    return $null
}

# 프로젝트를 옮겨도 translation/tools, 게임 루트/tools, 공용 Tools 순으로 찾는다.
$retoc = Find-FirstExistingPath @(
    (Join-Path $root "tools\retoc.exe"),
    (Join-Path $gameRoot "tools\retoc.exe"),
    (Join-Path $projectRoot "Tools\retoc.exe")
)
$repak = Find-FirstExistingPath @(
    (Join-Path $root "tools\repak.exe"),
    (Join-Path $gameRoot "tools\repak.exe"),
    (Join-Path $projectRoot "Tools\repak.exe")
)
if ($RepakPath) { $repak = (Resolve-Path -LiteralPath $RepakPath).Path }
if (-not $repak) { throw "repak.exe를 찾을 수 없습니다. translation/tools, 게임 루트/tools 또는 공용 Tools 폴더를 확인하세요." }

$paksCandidates = @(
    (Join-Path $gameRoot "RomFS\Emulator_Tenshinouta\Content\Paks"),
    (Join-Path $gameRoot "Emulator_Tenshinouta\Content\Paks"),
    (Join-Path $root "..\RomFS\Emulator_Tenshinouta\Content\Paks"),
    (Join-Path $root "..\Emulator_Tenshinouta\Content\Paks")
)
$paksDir = $null
foreach ($cand in $paksCandidates) {
    if (Test-Path $cand) {
        $paksDir = (Resolve-Path $cand).Path
        break
    }
}
$retoc = (Resolve-Path -LiteralPath $RetocPath).Path
$repak = (Resolve-Path -LiteralPath $RepakPath).Path
$paksDir = (Resolve-Path -LiteralPath $SourcePaks).Path
$work = Join-Path $root "work"
$srcDir = Join-Path $work "src"             # 원본 legacy 추출본
$patchDir = Join-Path $work "patch_src"     # 패치 적용본 (to-zen 입력)
$outDir = Join-Path $work "out"             # 빌드 결과
$backup = Join-Path $work "csv"
$sourceCache = Join-Path $root "source_cache"
$manualCache = Join-Path $root "manual_source_cache"

function Step($msg) { Write-Host "`n=== $msg ===" -ForegroundColor Cyan }

function Copy-WithRetry([string]$source, [string]$destination, [int]$attempts = 10) {
    # An emulator may hold an unchanged pak open. Avoid replacing an identical
    # destination so a harmless file lock does not abort the whole deployment.
    if (Test-Path $destination) {
        $sourceHash = (Get-FileHash $source -Algorithm SHA256).Hash
        $destinationHash = (Get-FileHash $destination -Algorithm SHA256).Hash
        if ($sourceHash -eq $destinationHash) {
            Write-Host "  동일 파일, Eden 복사 생략: $(Split-Path $source -Leaf)"
            return
        }
    }
    for ($attempt = 1; $attempt -le $attempts; $attempt++) {
        try {
            Copy-Item $source $destination -Force -ErrorAction Stop
            return
        } catch [System.IO.IOException] {
            if ($attempt -eq $attempts) { throw }
            Write-Host "  파일 사용 중, Eden 배포 재시도 ($attempt/$attempts): $(Split-Path $source -Leaf)"
            Start-Sleep -Seconds 1
        }
    }
}

# ------------------------------------------------------------

function Assert-IsolatedBuildWork([string]$path) {
    $expected = [IO.Path]::GetFullPath((Join-Path $root 'work')).TrimEnd('\')
    $actual = [IO.Path]::GetFullPath($path).TrimEnd('\')
    if ($actual -cne $expected) { throw 'Build work path outside expected directory' }
    if (Test-Path -LiteralPath $path) {
        $items = @((Get-Item -LiteralPath $path -Force)) + @(Get-ChildItem -LiteralPath $path -Force -Recurse)
        if (@($items | Where-Object { ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 }).Count -ne 0) { throw 'Reparse point in build work directory' }
    }
}
Assert-IsolatedBuildWork $work
Step "0. 작업 폴더 초기화"
# 원본 Paks가 없는 이동 환경에서도 마지막 정상 추출본을 빌드 입력으로 보존한다.
if (-not (Test-Path $sourceCache) -and (Test-Path (Join-Path $work "src"))) {
    Copy-Item (Join-Path $work "src") $sourceCache -Recurse -Force
    Write-Host "  원본 추출 캐시 보존: $sourceCache"
}
if ($CurrentTranslations -and ($env:INCLUDE_MANUAL -eq "1") -and -not (Test-Path $manualCache) -and (Test-Path (Join-Path $work "manual_src"))) {
    Copy-Item (Join-Path $work "manual_src") $manualCache -Recurse -Force
    Write-Host "  매뉴얼 추출 캐시 보존: $manualCache"
}
if (Test-Path $work) { Remove-Item -Recurse -Force $work }
New-Item -ItemType Directory -Force -Path $srcDir, $patchDir, $outDir, $backup | Out-Null

# ------------------------------------------------------------
Step "1. XLSX -> CSV (대사 + 크레딧/UI/게임선택)"
python (Join-Path $scripts "xlsx2_to_csv.py") $root (Join-Path $work "tenshi_master.csv") $backup
if ($LASTEXITCODE -ne 0) { throw "xlsx2_to_csv 실패" }
foreach ($csvName in @("visualscene2_paired.csv", "outgameinfo2_paired.csv")) {
    $rootCsv = Join-Path $root $csvName
    if (Test-Path $rootCsv) {
        Copy-Item $rootCsv (Join-Path $backup $csvName) -Force
        Write-Host "  root CSV override: $csvName"
    }
}

# ------------------------------------------------------------
Step "2. 원본 pak에서 대상 애셋 추출 (retoc to-legacy)"
if ($paksDir) {
    if (-not $retoc) { throw "원본 Paks는 찾았지만 retoc.exe를 찾을 수 없습니다." }
    & $retoc to-legacy -f "Localization" --version UE5_4 $paksDir $srcDir | Out-Null
    & $retoc to-legacy -f "Data/DT" --version UE5_4 $paksDir $srcDir | Out-Null
    & $retoc to-legacy -f "WBP_ContentItem" --version UE5_4 $paksDir $srcDir | Out-Null
    & $retoc to-legacy -f "WBP_InGame_Menu" --version UE5_4 $paksDir $srcDir | Out-Null
    & $retoc to-legacy -f "WBP_LocalizeText" --version UE5_4 $paksDir $srcDir | Out-Null
} elseif (Test-Path $sourceCache) {
    Copy-Item (Join-Path $sourceCache "*") $srcDir -Recurse -Force
    Write-Host "  원본 Paks 미발견: 보존된 추출 캐시를 사용합니다."
} else {
    throw "원본 Paks 또는 source_cache를 찾을 수 없습니다. Paks 후보: $($paksCandidates -join ', ')"
}
$content = Join-Path $srcDir "Emulator_Tenshinouta\Content"
if (-not (Test-Path "$content\Localization\TextData\tenshi2_text_en.uexp")) { throw "원본 추출 실패" }

# ------------------------------------------------------------
Step "3. 원본 문자열 스캔 (offset 지도 생성)"
python (Join-Path $scripts "extract_strings.py") "$content\Localization\TextData\tenshi2_text_en.uexp" (Join-Path $work "tenshi2_strings.json") (Join-Path $work "tenshi2_strings.csv")
python (Join-Path $scripts "extract_strings.py") "$content\Localization\TextData\DT_Tenshi2_VisualSceneText.uexp" (Join-Path $work "vs2_strings.json") (Join-Path $work "vs2_strings.csv")

# ------------------------------------------------------------
Step "4. 한국어 줄바꿈 정렬 (원문 줄 구조 우선, 문자형 \n 정규화)"
python (Join-Path $scripts "rewrap_ko.py") (Join-Path $work "tenshi_master.csv") (Join-Path $work "tenshi_wrapped.csv")

# ------------------------------------------------------------
Step "5. 교체 계획(replacements) 생성"
python (Join-Path $scripts "build_replacements.py") tenshi (Join-Path $work "tenshi2_strings.json") (Join-Path $work "tenshi_wrapped.csv") (Join-Path $work "repl_tenshi.json")
python (Join-Path $scripts "build_replacements.py") visualscene (Join-Path $work "vs2_strings.json") (Join-Path $backup "visualscene2_paired.csv") (Join-Path $work "repl_vs.json")
python (Join-Path $scripts "build_ui_replacements2.py") $srcDir (Join-Path $backup "ui_menu_text2_paired.csv") (Join-Path $work "repl_ui.json")
python (Join-Path $scripts "build_st_replacements.py") "$content\Localization\DataTable_Game1\ST_OutGameInfo_Game1.uexp" (Join-Path $backup "outgameinfo2_paired.csv") (Join-Path $work "repl_st.json")

# ------------------------------------------------------------
if (-not $CurrentTranslations) {
    foreach ($plan in @('repl_tenshi.json', 'repl_vs.json', 'repl_ui.json', 'repl_st.json')) {
        Copy-Item -LiteralPath (Join-Path $root "../assets/release_plans/$plan") -Destination (Join-Path $work $plan) -Force
    }
}
Step "6. 바이너리 패치 적용 (uexp 문자열 교체 + uasset SerialSize 갱신)"
# 장면 8의 13.00~26.55초 자막 한 건은 원본 데이터에서 VisualSceneID가
# 19로 잘못 지정되어 있다. 같은 길이의 임시 사본에서 ID만 교정한 뒤
# 시작을 22.00초로 늦춰 문자열 교체에 사용한다. 종료 26.55초와 뒤따르는
# 27.51~29.69초 자막의 타이밍은 유지해 두 자막이 겹치지 않게 한다.
$visualSceneRel = "Localization\TextData\DT_Tenshi2_VisualSceneText"
$visualSceneMetadataSrc = Join-Path $work "DT_Tenshi2_VisualSceneText_scene8_fix.uexp"
python (Join-Path $scripts "patch_visualscene_scene_id.py") (Join-Path $content "$visualSceneRel.uexp") $visualSceneMetadataSrc
if ($LASTEXITCODE -ne 0) { throw "비주얼신 장면 ID 교정 실패" }

# 대상 파일별 원본 SerialSize / SerialOffset (2편 원본 기준, 불변)
$targets = @(
    @{ rel = "Localization\TextData\tenshi2_text_en";                          repl = "repl_tenshi.json"; filter = $null;                                                          ss = 1314754; so = 89756 },
    @{ rel = "Localization\TextData\DT_Tenshi2_VisualSceneText";               repl = "repl_vs.json";     filter = $null;                                                          ss = 24439;   so = 2797 },
    @{ rel = "Localization\DataTable_Game1\ST_OutGameInfo_Game1";              repl = "repl_st.json";     filter = $null;                                                          ss = 2803;    so = 703 },
    @{ rel = "L10N\en\Ogix\Data\DT\Common\DT_BootView";                        repl = "repl_ui.json";     filter = "L10N/en/Ogix/Data/DT/Common/DT_BootView.uexp";                 ss = 335;     so = 1290 },
    @{ rel = "L10N\en\Ogix\Data\DT\Game_2\DT_Game2_GameInfo";                  repl = "repl_ui.json";     filter = "L10N/en/Ogix/Data/DT/Game_2/DT_Game2_GameInfo.uexp";           ss = 1092;    so = 1074 },
    @{ rel = "L10N\en\Ogix\Data\DT\Game_1\DT_Game1_HomeMenuSelectInfo";        repl = "repl_ui.json";     filter = "L10N/en/Ogix/Data/DT/Game_1/DT_Game1_HomeMenuSelectInfo.uexp"; ss = 296;     so = 1217 },
    @{ rel = "L10N\en\Ogix\Data\DT\Game_2\DT_Game2_SoundInfo";                 repl = "repl_ui.json";     filter = "L10N/en/Ogix/Data/DT/Game_2/DT_Game2_SoundInfo.uexp";          ss = 1595;    so = 4125 },
    @{ rel = "L10N\en\Ogix\Data\DT\Game_2\DT_Game2_VisualInfo";                repl = "repl_ui.json";     filter = "L10N/en/Ogix/Data/DT/Game_2/DT_Game2_VisualInfo.uexp";         ss = 358;     so = 3983 },
    @{ rel = "L10N\en\Ogix\Data\DT\Game_1\DT_Game1_SoundInfo";                 repl = "repl_ui.json";     filter = "L10N/en/Ogix/Data/DT/Game_1/DT_Game1_SoundInfo.uexp";          ss = 1388;    so = 843 },
    @{ rel = "L10N\en\Ogix\Data\DT\Game_1\DT_Game1_VisualInfo";                repl = "repl_ui.json";     filter = "L10N/en/Ogix/Data/DT/Game_1/DT_Game1_VisualInfo.uexp";         ss = 204;     so = 902 },
    @{ rel = "Ogix\Data\DT\Common\DT_BootView";                                repl = "repl_ui.json";     filter = "Ogix/Data/DT/Common/DT_BootView.uexp";                         ss = 335;     so = 1274 }
)
foreach ($t in $targets) {
    $srcUexp = Join-Path $content "$($t.rel).uexp"
    if ($t.rel -eq $visualSceneRel) { $srcUexp = $visualSceneMetadataSrc }
    $srcUasset = Join-Path $content "$($t.rel).uasset"
    $dstUexp = Join-Path $patchDir "Emulator_Tenshinouta\Content\$($t.rel).uexp"
    $dstUasset = Join-Path $patchDir "Emulator_Tenshinouta\Content\$($t.rel).uasset"
    New-Item -ItemType Directory -Force -Path (Split-Path $dstUexp) | Out-Null

    $repl = Join-Path $work $t.repl
    if ($t.filter) {
        python (Join-Path $scripts "apply_replacements.py") $srcUexp $repl $dstUexp $t.filter
    } else {
        python (Join-Path $scripts "apply_replacements.py") $srcUexp $repl $dstUexp
    }
    if ($LASTEXITCODE -ne 0) { throw "uexp 패치 실패: $($t.rel)" }

    $newSerial = (Get-Item $dstUexp).Length - 4
    python (Join-Path $scripts "patch_serialsize_binary.py") $srcUasset $t.ss $t.so $newSerial $dstUasset
    if ($LASTEXITCODE -ne 0) { throw "SerialSize 패치 실패: $($t.rel)" }
    Write-Host "  OK: $($t.rel)"
}

$richSrc = Join-Path $content "Ogix\Data\DT\Common\DT_RichTextFormat"
$richDst = Join-Path $patchDir "Emulator_Tenshinouta\Content\Ogix\Data\DT\Common\DT_RichTextFormat"
New-Item -ItemType Directory -Force -Path (Split-Path "$richDst.uexp") | Out-Null
Copy-Item "$richSrc.uasset" "$richDst.uasset" -Force
python (Join-Path $scripts "patch_richtext_font_size.py") "$richSrc.uexp" "$richDst.uexp" 27.0 20.0 6
if ($LASTEXITCODE -ne 0) { throw "RichText font size 패치 실패" }
Write-Host "  OK: Ogix\Data\DT\Common\DT_RichTextFormat (font size 20)"

# 게임 선택 화면의 장문 설명은 전용 위젯 크기를 낮춰 버튼 영역을 침범하지 않게 한다.
$contentItemSrc = Join-Path $content "Ogix\WBP\Game_Collection\00_GameSelect\WBP_ContentItem"
$contentItemDst = Join-Path $patchDir "Emulator_Tenshinouta\Content\Ogix\WBP\Game_Collection\00_GameSelect\WBP_ContentItem"
New-Item -ItemType Directory -Force -Path (Split-Path "$contentItemDst.uexp") | Out-Null
Copy-Item "$contentItemSrc.uasset" "$contentItemDst.uasset" -Force
python (Join-Path $scripts "patch_richtext_font_size.py") "$contentItemSrc.uexp" "$contentItemDst.uexp" 18.0 15.0 2
if ($LASTEXITCODE -ne 0) { throw "게임 선택 설명문 폰트 크기 패치 실패" }
Write-Host "  OK: WBP_ContentItem (title detail font size 15)"

# 게임 내 메뉴는 별도 TextBlock 크기를 사용한다. 36은 레이아웃 수치이므로
# 건드리지 않고, 실제 글자 크기인 16을 한글 폰트에 맞춰 14로 낮춘다.
$inGameMenuSrc = Join-Path $content "Ogix\WBP\Common\InGame\WBP_InGame_Menu"
$inGameMenuDst = Join-Path $patchDir "Emulator_Tenshinouta\Content\Ogix\WBP\Common\InGame\WBP_InGame_Menu"
New-Item -ItemType Directory -Force -Path (Split-Path "$inGameMenuDst.uexp") | Out-Null
Copy-Item "$inGameMenuSrc.uasset" "$inGameMenuDst.uasset" -Force
python (Join-Path $scripts "patch_richtext_font_size.py") "$inGameMenuSrc.uexp" "$inGameMenuDst.uexp" 16.0 14.0 5
if ($LASTEXITCODE -ne 0) { throw "게임 내 메뉴 폰트 크기 패치 실패" }
python (Join-Path $scripts "patch_selected_font_size.py") "$inGameMenuDst.uexp" 14.0 16.0 "1,2,3,4"
if ($LASTEXITCODE -ne 0) { throw "전투 이름 폰트 크기 복원 실패" }
Write-Host "  OK: WBP_InGame_Menu (menu 14, party-name slots 16)"

# 기본 문자열은 RichText 태그 스타일을 거치지 않는다. WBP의 하드코딩된
# 기본 크기도 20으로 맞춰 같은 메뉴 안에서 크기가 섞이지 않게 한다.
$localizeTextSrc = Join-Path $content "Ogix\WBP\Common\InGame\Localize\WBP_LocalizeText"
$localizeTextDst = Join-Path $patchDir "Emulator_Tenshinouta\Content\Ogix\WBP\Common\InGame\Localize\WBP_LocalizeText"
New-Item -ItemType Directory -Force -Path (Split-Path "$localizeTextDst.uexp") | Out-Null
Copy-Item "$localizeTextSrc.uasset" "$localizeTextDst.uasset" -Force
python (Join-Path $scripts "patch_floats_at_offsets.py") "$localizeTextSrc.uexp" "$localizeTextDst.uexp" "890:27:20"
if ($LASTEXITCODE -ne 0) { throw "기본 메뉴 폰트 크기 패치 실패" }
Write-Host "  OK: WBP_LocalizeText (default font size 20)"

# to-zen에 필요한 스크립트 오브젝트 복사
Copy-Item (Join-Path $srcDir "scriptobjects.bin") $patchDir -Force

# ------------------------------------------------------------
if (-not $CurrentTranslations) {
    $manualAssetRoot = Join-Path $root 'manual_patch_assets'
    if (-not (Test-Path -LiteralPath $manualAssetRoot)) { throw 'Run prepare_build_inputs.py first; frozen manual assets are required' }
    foreach ($asset in (Get-ChildItem -LiteralPath $manualAssetRoot -Recurse -File)) {
        $relative = $asset.FullName.Substring($manualAssetRoot.Length + 1)
        $destination = Join-Path $patchDir $relative
        New-Item -ItemType Directory -Force -Path (Split-Path $destination) | Out-Null
        Copy-Item -LiteralPath $asset.FullName -Destination $destination -Force
    }
}
Step "6.5 매뉴얼 이미지 주입 (INCLUDE_MANUAL=1일 때만)"
$manualPng = Join-Path $root "매뉴얼_번역"
if ($CurrentTranslations -and ($env:INCLUDE_MANUAL -eq "1") -and (Test-Path $manualPng) -and (Get-ChildItem $manualPng -Filter "Manual2_*.png" -ErrorAction SilentlyContinue)) {
    $manualSrc = Join-Path $work "manual_src"
    New-Item -ItemType Directory -Force -Path $manualSrc | Out-Null
    if ($paksDir) {
        if (-not $retoc) { throw "매뉴얼 원본 추출에 필요한 retoc.exe를 찾을 수 없습니다." }
        & $retoc to-legacy -f "ManualBook" --version UE5_4 $paksDir $manualSrc | Out-Null
    } elseif (Test-Path $manualCache) {
        Copy-Item (Join-Path $manualCache "*") $manualSrc -Recurse -Force
        Write-Host "  원본 Paks 미발견: 보존된 매뉴얼 추출 캐시를 사용합니다."
    } else {
        Write-Warning "원본 Paks와 manual_source_cache가 없어 매뉴얼 주입을 건너뜁니다."
        $manualSrc = $null
    }
    if ($manualSrc) {
        python (Join-Path $scripts "inject_manual_png.py") $manualSrc $manualPng $patchDir
        if ($LASTEXITCODE -ne 0) { throw "매뉴얼 주입 실패" }
    }
} else {
    Write-Host "  (매뉴얼 주입 비활성 - 건너뜀)"
}

# ------------------------------------------------------------
Step "6.6 카드게임 이미지 생성 및 주입"
$cardRoot = Join-Path $root "card_game_extract"
$cardSource = Join-Path $cardRoot "legacy"
$cardPng = Join-Path $cardRoot "translate"
python (Join-Path $scripts "translate_card_game_png.py")
if ($LASTEXITCODE -ne 0) { throw "카드게임 번역 이미지 생성 실패" }
python (Join-Path $scripts "inject_card_game_png.py") $cardSource $cardPng $patchDir
if ($LASTEXITCODE -ne 0) { throw "카드게임 이미지 주입 실패" }

# ------------------------------------------------------------
Step "6.7 Track02 카드 한글 타일 주입"
# 검수 완료된 카드명 패치는 기본 포함한다. 문제 조사용 빌드에서만
# ENABLE_TRACK02_CARD_PATCH=0으로 명시하여 제외할 수 있다.
$enableTrack02CardPatch = $env:ENABLE_TRACK02_CARD_PATCH -ne "0"
$ufsPakRoot = Join-Path $work "ufs_pak_src"
if ($enableTrack02CardPatch) {
    $track02Source = Join-Path $cardRoot "gamepack\Emulator_Tenshinouta\Content\Ogix\GamePack\install\Tenshi2\Track02.iso"
    $track02Target = Join-Path $ufsPakRoot "Emulator_Tenshinouta\Content\Ogix\GamePack\install\Tenshi2\Track02.iso"
    $cardFontAtlas = Join-Path $cardRoot "GalmuriMono9_10x10.png"
    if (-not (Test-Path $track02Source)) { throw "Track02.iso 원본을 찾을 수 없습니다: $track02Source" }
    if (-not (Test-Path $cardFontAtlas)) { throw "카드 한글 폰트를 찾을 수 없습니다: $cardFontAtlas" }
    python (Join-Path $scripts "patch_track02_korean_cards.py") $track02Source $cardFontAtlas $track02Target
    if ($LASTEXITCODE -ne 0) { throw "Track02 카드 한글 타일 주입 실패" }
} else {
    Write-Host "  (ENABLE_TRACK02_CARD_PATCH=0 - 카드명 패치 건너뜀)"
}

# ------------------------------------------------------------
Step "6.8 번역 컷신 MP4 포함"
# 메인 메뉴의 컷신 모음은 아래 경로의 UFS MP4를 직접 재생한다.
# 번역 폴더에 존재하는 검증된 파일만 같은 상대 경로로 덮어쓴다.
$cutsceneSource = Join-Path $root "cutscene_translate"
$cutsceneNames = @(
    "Game2Ending.mp4",
    "Game2Opening.mp4",
    "Game2Scene01.mp4",
    "Game2Scene04.mp4",
    "Game2Scene05.mp4",
    "Game2Scene07.mp4",
    "Game2Scene08.mp4",
    "Game2Scene09.mp4",
    "Game2Scene10.mp4",
    "Game2Scene11.mp4"
)
$includedCutscenes = @()
if (Test-Path $cutsceneSource) {
    $unexpectedCutscenes = Get-ChildItem $cutsceneSource -File -Filter "*.mp4" |
        Where-Object { $cutsceneNames -notcontains $_.Name }
    if ($unexpectedCutscenes) {
        throw "지원하지 않는 컷신 파일명: $($unexpectedCutscenes.Name -join ', ')"
    }

    $cutsceneTargetDir = Join-Path $ufsPakRoot "Emulator_Tenshinouta\Content\Ogix\Movie\Game2"
    New-Item -ItemType Directory -Force -Path $cutsceneTargetDir | Out-Null
    foreach ($name in $cutsceneNames) {
        $sourceMovie = Join-Path $cutsceneSource $name
        if (-not (Test-Path $sourceMovie)) { continue }

        $stream = [System.IO.File]::OpenRead($sourceMovie)
        try {
            $header = New-Object byte[] 12
            $read = $stream.Read($header, 0, $header.Length)
        } finally {
            $stream.Dispose()
        }
        if ($read -ne 12 -or [System.Text.Encoding]::ASCII.GetString($header, 4, 4) -ne "ftyp") {
            throw "올바른 MP4가 아닙니다: $sourceMovie"
        }

        Copy-Item $sourceMovie (Join-Path $cutsceneTargetDir $name) -Force
        $includedCutscenes += $name
        Write-Host "  OK: $name ($((Get-Item $sourceMovie).Length) bytes)"
    }
}
if ($includedCutscenes.Count -eq 0) {
    Write-Host "  (번역 컷신 없음 - 건너뜀)"
}

# ------------------------------------------------------------
Step "7. Zen 컨테이너 빌드 (retoc to-zen)"
& $retoc to-zen --version UE5_4 $patchDir (Join-Path $outDir "TenshiKR2_P.utoc") | Out-Null
if (-not (Test-Path (Join-Path $outDir "TenshiKR2_P.ucas"))) { throw "to-zen 실패" }

# Track02.iso and MP4 movies are regular UFS files. Pack them into retoc's
# companion pak and verify every packed payload against its source hash.
if ($enableTrack02CardPatch -or $includedCutscenes.Count -gt 0) {
    $ufsPak = Join-Path $outDir "TenshiKR2_P.pak"
    & $repak pack $ufsPakRoot $ufsPak --version V11 --path-hash-seed 4090041728 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "UFS 패치 pak 생성 실패" }

    $packedHashes = @{}
    foreach ($line in (& $repak hash-list $ufsPak)) {
        if ($line -match '^([0-9a-fA-F]{64})\s+(.+)$') {
            $packedHashes[$Matches[2]] = $Matches[1].ToLowerInvariant()
        }
    }
    foreach ($file in (Get-ChildItem $ufsPakRoot -File -Recurse)) {
        $relativePath = $file.FullName.Substring($ufsPakRoot.Length + 1).Replace('\', '/')
        $expectedHash = (Get-FileHash $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        if (-not $packedHashes.ContainsKey($relativePath) -or $packedHashes[$relativePath] -ne $expectedHash) {
            throw "UFS pak 검증 실패: $relativePath"
        }
    }
    Write-Host "  OK: UFS payloads packed and verified ($($packedHashes.Count) files)"
}

# ------------------------------------------------------------
Step "8. patch_P 폴더로 배포"
$deploy = Join-Path $root "patch_P"
New-Item -ItemType Directory -Force -Path $deploy | Out-Null
Copy-Item (Join-Path $outDir "TenshiKR2_P.pak") $deploy -Force
Copy-Item (Join-Path $outDir "TenshiKR2_P.ucas") $deploy -Force
Copy-Item (Join-Path $outDir "TenshiKR2_P.utoc") $deploy -Force
Get-ChildItem $deploy | Format-Table Name, Length, LastWriteTime -AutoSize

# ------------------------------------------------------------
Step "8.5 낮은 세로 메트릭 폰트 pak 생성"
$fontSource = Find-FirstExistingPath @(
    (Join-Path $root "fontsrc_condensed"),
    (Join-Path $gamesRoot "Tenshi no Uta\translation\fontsrc_condensed")
)
$fontMetricScript = Find-FirstExistingPath @(
    (Join-Path $scripts "patch_font_vertical_metrics.py"),
    (Join-Path $gamesRoot "Tenshi no Uta\translation\scripts\patch_font_vertical_metrics.py")
)
$fontWork = Join-Path $work "fontsrc_lowmetrics"
if (-not $fontSource) { throw "Galmuri11-Condensed 폰트 소스를 찾을 수 없습니다." }
if (-not $fontMetricScript) { throw "폰트 메트릭 패치 스크립트를 찾을 수 없습니다." }
Copy-Item $fontSource $fontWork -Recurse -Force
$fontDir = Join-Path $fontWork "Emulator_Tenshinouta\Content\Ogix\Font"
python $fontMetricScript (Join-Path $fontSource "Emulator_Tenshinouta\Content\Ogix\Font\k8x12.ufont") (Join-Path $fontDir "k8x12.ufont") --factor 1.00 --desc-factor 0.166667
if ($LASTEXITCODE -ne 0) { throw "k8x12 폰트 세로 메트릭 패치 실패" }
python $fontMetricScript (Join-Path $fontSource "Emulator_Tenshinouta\Content\Ogix\Font\BIZUDGothic-Regular.ufont") (Join-Path $fontDir "BIZUDGothic-Regular.ufont") --factor 1.00 --desc-factor 0.12
if ($LASTEXITCODE -ne 0) { throw "BIZUDGothic 폰트 세로 메트릭 패치 실패" }
& $repak pack --version V11 --mount-point "../../../" --path-hash-seed 1253859140 $fontWork (Join-Path $deploy "TenshiKR_Font_P.pak") | Out-Null
if ($LASTEXITCODE -ne 0) { throw "폰트 pak 생성 실패" }
Write-Host "  OK: TenshiKR_Font_P.pak (low vertical metrics)"

# ------------------------------------------------------------
Step "9. Eden 모드 폴더로 복사"
Write-Host "Build complete. Outputs remain in translation/patch_P; no emulator deployment."
