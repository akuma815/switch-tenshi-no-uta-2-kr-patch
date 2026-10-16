# ============================================================
# 천사의 시 한글 패치 원클릭 빌드 스크립트
# 실행: powershell -ExecutionPolicy Bypass -File scripts\build_patch.ps1
# (작업 기준 폴더 = 이 스크립트의 상위 폴더 = translation)
# ============================================================
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot            # translation 폴더
$scripts = $PSScriptRoot
$retoc = Join-Path $root "tools\retoc.exe"
$paksCandidates = @(
    "..\RomFS\Emulator_Tenshinouta\Content\Paks",
    "..\Emulator_Tenshinouta\Content\Paks"
)
$paksDir = $null
foreach ($cand in $paksCandidates) {
    $path = Join-Path $root $cand
    if (Test-Path $path) {
        $paksDir = (Resolve-Path $path).Path
        break
    }
}
if (-not $paksDir) { throw "원본 Paks 경로를 찾을 수 없습니다. expected one of: $($paksCandidates -join ', ')" }
$work = Join-Path $root "work"
$srcDir = Join-Path $work "src"             # 원본 legacy 추출본
$patchDir = Join-Path $work "patch_src"     # 패치 적용본 (to-zen 입력)
$outDir = Join-Path $work "out"             # 빌드 결과
$backup = Join-Path $root "백업_csv"

function Step($msg) { Write-Host "`n=== $msg ===" -ForegroundColor Cyan }

# ------------------------------------------------------------
Step "0. 작업 폴더 초기화"
if (Test-Path $work) { Remove-Item -Recurse -Force $work }
New-Item -ItemType Directory -Force -Path $srcDir, $patchDir, $outDir | Out-Null

# ------------------------------------------------------------
Step "1. XLSX -> CSV (3줄초과 수정본 자동 병합)"
python (Join-Path $scripts "xlsx_to_csv.py") $root (Join-Path $work "tenshi_master.csv")
if ($LASTEXITCODE -ne 0) { throw "xlsx_to_csv 실패" }

# ------------------------------------------------------------
Step "2. 원본 pak에서 대상 애셋 추출 (retoc to-legacy)"
& $retoc to-legacy -f "Localization" --version UE5_4 $paksDir $srcDir | Out-Null
& $retoc to-legacy -f "Data/DT" --version UE5_4 $paksDir $srcDir | Out-Null
$content = Join-Path $srcDir "Emulator_Tenshinouta\Content"
if (-not (Test-Path "$content\Localization\TextData\tenshi_text_en.uexp")) { throw "원본 추출 실패" }

# ------------------------------------------------------------
Step "3. 원본 문자열 스캔 (offset 지도 생성)"
python (Join-Path $scripts "extract_strings.py") "$content\Localization\TextData\tenshi_text_en.uexp" (Join-Path $work "tenshi_strings.json") (Join-Path $work "tenshi_strings.csv")
python (Join-Path $scripts "extract_strings.py") "$content\Localization\TextData\DT_Tenshi_VisualSceneText.uexp" (Join-Path $work "vs_strings.json") (Join-Path $work "vs_strings.csv")

# ------------------------------------------------------------
Step "4. 한국어 자동 줄바꿈 (전각 23자, 문자형 \n 정규화)"
python (Join-Path $scripts "rewrap_ko.py") (Join-Path $work "tenshi_master.csv") (Join-Path $work "tenshi_wrapped.csv")

# ------------------------------------------------------------
Step "5. 교체 계획(replacements) 생성"
python (Join-Path $scripts "build_replacements.py") tenshi (Join-Path $work "tenshi_strings.json") (Join-Path $work "tenshi_wrapped.csv") (Join-Path $work "repl_tenshi.json")
python (Join-Path $scripts "build_replacements.py") visualscene (Join-Path $work "vs_strings.json") (Join-Path $backup "visualscene_paired.csv") (Join-Path $work "repl_vs.json")
python (Join-Path $scripts "build_ui_replacements.py") $srcDir (Join-Path $backup "ui_menu_text_paired.csv") (Join-Path $work "repl_ui.json")
python (Join-Path $scripts "build_st_replacements.py") "$content\Localization\DataTable_Game1\ST_OutGameInfo_Game1.uexp" (Join-Path $backup "outgameinfo_paired.csv") (Join-Path $work "repl_st.json")

# ------------------------------------------------------------
Step "6. 바이너리 패치 적용 (uexp 문자열 교체 + uasset SerialSize 갱신)"
# 대상 파일별 원본 SerialSize / SerialOffset (변하지 않는 상수)
$targets = @(
    @{ rel = "Localization\TextData\tenshi_text_en";                          repl = "repl_tenshi.json"; filter = $null;                                                        ss = 1389054; so = 100708 },
    @{ rel = "Localization\TextData\DT_Tenshi_VisualSceneText";               repl = "repl_vs.json";     filter = $null;                                                        ss = 29496;   so = 3635 },
    @{ rel = "Localization\DataTable_Game1\ST_OutGameInfo_Game1";             repl = "repl_st.json";     filter = $null;                                                        ss = 2803;    so = 703 },
    @{ rel = "L10N\en\Ogix\Data\DT\Common\DT_BootView";                       repl = "repl_ui.json";     filter = "L10N/en/Ogix/Data/DT/Common/DT_BootView.uexp";               ss = 335;     so = 1290 },
    @{ rel = "L10N\en\Ogix\Data\DT\Game_1\DT_Game1_GameInfo";                 repl = "repl_ui.json";     filter = "L10N/en/Ogix/Data/DT/Game_1/DT_Game1_GameInfo.uexp";         ss = 454;     so = 1074 },
    @{ rel = "L10N\en\Ogix\Data\DT\Game_1\DT_Game1_HomeMenuSelectInfo";       repl = "repl_ui.json";     filter = "L10N/en/Ogix/Data/DT/Game_1/DT_Game1_HomeMenuSelectInfo.uexp"; ss = 296;   so = 1217 },
    @{ rel = "L10N\en\Ogix\Data\DT\Game_1\DT_Game1_SoundInfo";                repl = "repl_ui.json";     filter = "L10N/en/Ogix/Data/DT/Game_1/DT_Game1_SoundInfo.uexp";        ss = 1588;    so = 4125 },
    @{ rel = "L10N\en\Ogix\Data\DT\Game_1\DT_Game1_VisualInfo";               repl = "repl_ui.json";     filter = "L10N/en/Ogix/Data/DT/Game_1/DT_Game1_VisualInfo.uexp";       ss = 254;     so = 3068 },
    @{ rel = "Ogix\Data\DT\Common\DT_BootView";                               repl = "repl_ui.json";     filter = "Ogix/Data/DT/Common/DT_BootView.uexp";                       ss = 335;     so = 1274 }
)
foreach ($t in $targets) {
    $srcUexp = Join-Path $content "$($t.rel).uexp"
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
# to-zen에 필요한 스크립트 오브젝트 복사
Copy-Item (Join-Path $srcDir "scriptobjects.bin") $patchDir -Force

# ------------------------------------------------------------
Step "6.5 매뉴얼 이미지 주입 (매뉴얼_번역\*.png 있을 때만)"
$manualPng = Join-Path $root "매뉴얼_번역"
if ((Test-Path $manualPng) -and (Get-ChildItem $manualPng -Filter "Manual1_*.png" -ErrorAction SilentlyContinue)) {
    $manualSrc = Join-Path $work "manual_src"
    New-Item -ItemType Directory -Force -Path $manualSrc | Out-Null
    & $retoc to-legacy -f "ManualBook" --version UE5_4 $paksDir $manualSrc | Out-Null
    python (Join-Path $scripts "inject_manual_png.py") $manualSrc $manualPng $patchDir
    if ($LASTEXITCODE -ne 0) { throw "매뉴얼 주입 실패" }
} else {
    Write-Host "  (매뉴얼 PNG 없음 - 건너뜀)"
}

# ------------------------------------------------------------
Step "7. Zen 컨테이너 빌드 (retoc to-zen)"
& $retoc to-zen --version UE5_4 $patchDir (Join-Path $outDir "TenshiKR_P.utoc") | Out-Null
if (-not (Test-Path (Join-Path $outDir "TenshiKR_P.ucas"))) { throw "to-zen 실패" }

# ------------------------------------------------------------
Step "8. patch_P 폴더로 배포"
$deploy = Join-Path $root "patch_P"
New-Item -ItemType Directory -Force -Path $deploy | Out-Null
Copy-Item (Join-Path $outDir "TenshiKR_P.pak") $deploy -Force
Copy-Item (Join-Path $outDir "TenshiKR_P.ucas") $deploy -Force
Copy-Item (Join-Path $outDir "TenshiKR_P.utoc") $deploy -Force
Get-ChildItem $deploy | Format-Table Name, Length, LastWriteTime -AutoSize

Write-Host "`n빌드 완료. patch_P 폴더의 파일들을 에뮬레이터 모드 폴더에 복사하세요." -ForegroundColor Green
