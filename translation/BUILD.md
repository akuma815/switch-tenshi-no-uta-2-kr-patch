> Historical build notes. Current supported reconstruction and limits: [2026-10-16 guide](../docs/REBUILD_2026-10-16.md).

# 천사의 시 2 한글 패치 빌드 문서

`천사의 시 2: The Fallen Angel` Switch판(UE 5.4 IoStore)의 한글 패치 빌드 기준 문서다.
원본 컨테이너는 수정하지 않고, 필요한 애셋만 포함한 `_P` 패치를 원본 옆에 추가한다.

## 빌드와 산출물

```powershell
cd "G:\Downloads\Tenshi no Uta 2\translation"
powershell -ExecutionPolicy Bypass -File scripts\build_patch2.ps1
```

원본 Paks 경로는 다음 순서로 찾는다.

1. `..\RomFS\Emulator_Tenshinouta\Content\Paks`
2. `..\Emulator_Tenshinouta\Content\Paks`

산출물은 `translation\patch_P`에 생성되며, 빌드가 끝나면 아래 Eden 모드 폴더에도 자동 복사된다.

```text
H:\Eden\user\load\010047B021296000\Korean_Patch\romfs\Emulator_Tenshinouta\Content\Paks
```

| 파일 | 내용 |
| --- | --- |
| `TenshiKR2_P.pak/.ucas/.utoc` | 대사, 비주얼신, UI, 게임 선택, 매뉴얼, 카드게임, 위젯 폰트 크기 패치 |
| `TenshiKR_Font_P.pak` | Galmuri11-Condensed 및 낮은 세로 메트릭 폰트 |

## 번역 입력

번역은 `translation` 루트의 XLSX/CSV를 수정한다. `work`와 `patch_P`는 빌드 산출물이므로 직접 수정하지 않는다.

| 입력 | 용도 | 우선순위/비고 |
| --- | --- | --- |
| `천사의시2_대사_번역.xlsx` | 일반 대사 | 기본 마스터 |
| `천사의시2_크레딧_번역.xlsx` | 비주얼신/크레딧 | `백업_csv\visualscene2_paired.csv` 생성 |
| `천사의시2_UI_번역.xlsx` | UI 텍스트 | `백업_csv\ui_menu_text2_paired.csv` 생성 |
| `천사의시2_게임선택_번역.xlsx` | 게임 선택 화면 | `백업_csv\outgameinfo2_paired.csv` 생성 |
| `visualscene2_paired.csv` | 비주얼신 CSV 최신본 | 루트에 있으면 생성 CSV를 덮어쓴다 |
| `outgameinfo2_paired.csv` | 게임 선택 CSV 최신본 | 루트에 있으면 생성 CSV를 덮어쓴다 |

## 대사 줄바꿈 규칙

줄 수 제한보다 원문(`jp`)의 줄바꿈 구조가 우선이다.

- XLSX에는 실제 줄바꿈 대신 문자형 `\n`을 사용한다.
- `rewrap_ko.py`는 번역의 줄 수가 원문과 같으면 개행 위치를 그대로 보존한다.
- 줄 수가 다를 때만 원문의 줄 수와 각 줄의 상대 폭을 기준으로 한국어를 분할한다.
- 원문이 한 줄이면 자동 폭 분할을 하지 않는다.
- 원문 앞의 `\n`도 의미 있는 줄바꿈이다. 예: `\n%s(이)가 쓰러졌다!`는 선행 개행을 그대로 유지해야 한다.
- `#1`, `#5` 등의 색상 코드는 문자열과 줄 위치를 유지한다.
- 줄바꿈 수정도 `천사의시2_대사_번역.xlsx`에 직접 반영한다. 3줄 초과 자체는 오류가 아니다.

이전의 전각 폭 기준 자동 줄바꿈은 사용하지 않는다. 원문에 없는 개행이 생기면 메뉴 커서, 선택 행, 메시지 표시 위치가 어긋날 수 있다.

## 폰트와 메뉴 레이아웃

한글 폰트는 `Galmuri11-Condensed`를 사용한다. 빌드 시 1편 작업 폴더의 아래 소스를 복사해 세로 메트릭을 보정하고 legacy pak으로 다시 만든다.

```text
..\..\Tenshi no Uta\translation\fontsrc_condensed
```

원문 폰트의 행 높이 `1.00em`에 맞춰 폰트별 하강 비율을 적용한다. `k8x12.ufont`는 `--factor 1.00 --desc-factor 0.166667`, `BIZUDGothic-Regular.ufont`는 `--factor 1.00 --desc-factor 0.12`를 사용한다. 이 보정은 한글의 줄 높이와 기준선을 원문에 맞춰 메뉴 선택 위치와 여러 줄 문장의 누적 오차를 줄인다.

현재 적용되는 크기 패치는 다음과 같다.

| 대상 | 값 | 목적 |
| --- | --- | --- |
| `DT_RichTextFormat` | `27 -> 20` (6개) | 태그가 있는 대사/메뉴 텍스트 |
| `WBP_LocalizeText` offset `890` | `27 -> 20` | 태그 없는 기본 텍스트도 같은 크기로 통일 |
| `WBP_InGame_Menu` | `16 -> 14` (5개) | 게임 내 메뉴 항목 크기 조정 |
| `WBP_ContentItem` | `18 -> 15` (2개) | 게임 선택 화면 상세 설명이 버튼 영역을 침범하지 않도록 조정 |

`WBP_InGame_Menu`의 `36` 값은 폰트 크기가 아니라 레이아웃 값이다. 변경하면 메뉴 배치가 틀어지므로 수정하지 않는다.

## 빌드 파이프라인

`scripts\build_patch2.ps1`은 다음 순서로 동작한다.

1. `work` 초기화
2. 번역 XLSX를 CSV로 변환
3. 루트의 `visualscene2_paired.csv`, `outgameinfo2_paired.csv`가 있으면 생성 CSV를 덮어씀
4. 원본에서 `Localization`, `Data/DT`, 필요한 위젯을 `retoc to-legacy`로 추출
5. 문자열 offset 지도 생성 및 원문 줄 구조 정렬
6. 일반 대사, 비주얼신, UI, 게임 선택 교체 계획 생성
7. UTF-16LE FString 교체 및 `uasset` SerialSize 갱신
8. RichText, 기본 텍스트, 인게임 메뉴, 게임 선택 위젯의 폰트 크기 패치
9. `INCLUDE_MANUAL=1`이면 매뉴얼 이미지 주입
10. 카드게임 번역 PNG 29개 생성 및 원본 Texture2D에 주입
11. `cutscene_translate`의 번역 MP4를 원본과 같은 `Ogix/Movie/Game2` UFS 경로에 포함
12. `retoc to-zen`으로 `TenshiKR2_P.*` 생성
13. 낮은 세로 메트릭 폰트 pak 생성
14. `patch_P`와 Eden 모드 폴더에 배포

## 매뉴얼 이미지

매뉴얼 텍스처는 색상 이상 가능성이 있어 기본 검수 빌드에서 주입하지 않는다.

`Manual2_*.png`를 포함해야 할 때만 환경 변수를 지정한다.

```powershell
$env:INCLUDE_MANUAL = "1"
powershell -ExecutionPolicy Bypass -File scripts\build_patch2.ps1
Remove-Item Env:INCLUDE_MANUAL
```

## 비주얼신과 오프닝 영상

`visualscene2_paired.csv`는 `DT_Tenshi2_VisualSceneText`에 적용된다. 빌드 로그에서 비주얼신 replacement mismatch가 `0`이면 데이터 테이블 번역은 정상 반영된 것이다.

장면 8의 offset `15259/15298` 레코드는 원본 `DT_Tenshi2_VisualSceneText.uexp`에서 `VisualSceneID`가 `19`로 잘못 지정되어 있다. 원본 타이밍은 `13.00~26.55초`이며, 바로 다음 offset `15454/15477` 레코드는 장면 8의 `27.51~29.69초` 자막이다. `build_patch2.ps1`은 문자열 교체 전에 `patch_visualscene_scene_id.py`로 앞 레코드의 장면 ID를 `19 -> 8`, 시작 시간을 `13.00 -> 22.00초`로 교정한다. 종료 시간 `26.55초`와 다음 자막의 타이밍은 유지하여 겹침을 막는다. 원본 캐시는 수정하지 않으며, 예상 offset과 바이트 문맥이 다르면 빌드를 중단한다.

원본 ROM 재검사에서 offset `597`의 성우 출연 크레딧 한 쌍이 추가로 발견되었다. 영어 행이 전각 공백으로 시작하는 UTF-16 문자열이라 기존 페어링 코드가 누락한 경우였다. 이 행은 `visualscene2_paired.csv`와 `천사의시2_크레딧_번역.xlsx`에 추가되어 있으며, 현재 `ko`는 번역 대기 상태다. 페어링 로직은 전각 공백을 일본어 판별 근거로 쓰지 않도록 수정했다.

게임 오프닝의 `Game2Opening.mp4`에 구워진 영어 자막은 이 CSV로 바뀌지 않는다. 번역한 영상은 `cutscene_translate`에 원본과 같은 파일명으로 두면 빌드 시 `Emulator_Tenshinouta/Content/Ogix/Movie/Game2` 경로의 UFS 파일로 포함된다. MP4 헤더와 파일명 화이트리스트를 검사하고, pak 생성 후 각 파일의 SHA-256을 다시 대조한다.

## 주요 패치 대상

| 애셋 | 내용 |
| --- | --- |
| `Localization\TextData\tenshi2_text_en` | 본편 대사 |
| `Localization\TextData\DT_Tenshi2_VisualSceneText` | 비주얼신/크레딧 |
| `Localization\DataTable_Game1\ST_OutGameInfo_Game1` | 게임 선택 화면 |
| `L10N\en\Ogix\Data\DT\Game_2\DT_Game2_GameInfo` | 2편 타이틀/설명문 |
| `L10N\en\Ogix\Data\DT\Game_1\DT_Game1_HomeMenuSelectInfo` | 홈 메뉴 버튼 |
| `Ogix\Data\DT\Common\DT_RichTextFormat` | 태그 텍스트 폰트 크기 |
| `Ogix\WBP\Common\InGame\Localize\WBP_LocalizeText` | 기본 텍스트 폰트 크기 |
| `Ogix\WBP\Common\InGame\WBP_InGame_Menu` | 인게임 메뉴 폰트 크기 |
| `Ogix\WBP\Game_Collection\00_GameSelect\WBP_ContentItem` | 게임 선택 상세 설명 폰트 크기 |

## 검증 기준

최근 빌드의 정상 기준은 다음과 같다. 번역량에 따라 숫자는 달라질 수 있다.

- `master rows: 5213`
- `rows with ko: 5177, source-layout fixes: ...`
- `entries exceeding 3 lines`은 원문 구조상 남아도 정상
- 일반 대사에서 영어 슬롯이 없는 일본어 조각 11건은 매칭 대상에서 제외한다.
- 일본어 슬롯 자체가 영어이고 시트의 `en`과 동일한 공용 문자열은 해당 슬롯을 직접 교체한다. 현재 offset `518891` 한 건이다.
- offset `1236328`의 `한 달 후`는 같은 위치에 이어지는 `로스코몬 마을`과 겹치지 않도록 빌드 시 해당 문자열에만 종료 제어 `\c`를 덧붙인다.
- 비주얼신 `mismatches: 0`
- 비주얼신은 `regen rows: 285, csv rows: 285`가 현재 기준
- UI `mismatches: 0`
- 게임 선택 `mismatched: 0`
- `OK: WBP_LocalizeText (default font size 20)`
- `OK: TenshiKR_Font_P.pak (low vertical metrics)`
- `patch_P`와 Eden 폴더의 파일 시간이 최신

## 주의 사항

- 원본 `Emulator_Tenshinouta-Switch.pak/.ucas/.utoc`를 교체하거나 전체 컨테이너를 재조립하지 않는다.
- `work`는 매 빌드 때 삭제된다.
- 새 float를 찾을 때 전역 치환을 사용하지 않는다. 검증된 값 개수 또는 정확한 byte offset을 사용한다.
- `WBP_VisualSceneText`의 `32.0f`를 전역 치환하면 `BPTYPE_Normal` 문자열 길이 필드가 손상되어 프리징될 수 있다.
- `WBP_InGame_Menu`의 레이아웃 값 `36`을 폰트 크기로 오인해 변경하지 않는다.
- 번역 변경은 XLSX/루트 CSV에만 하고, `백업_csv`와 `work`의 변경은 다음 빌드에서 사라진다.

## 도구와 스크립트

필수 도구는 Python 3, `tools\retoc.exe`, `tools\repak.exe`다. Python 의존성은 다음과 같다.

```powershell
pip install openpyxl pillow texture2ddecoder quicktex
```

| 스크립트 | 역할 |
| --- | --- |
| `build_patch2.ps1` | 전체 빌드 및 Eden 배포 |
| `xlsx2_to_csv.py` | XLSX 변환 및 보정본 병합 |
| `rewrap_ko.py` | 원문 줄 구조 정렬 및 문자형 `\n` 정규화 |
| `extract_strings.py` | `uexp` 문자열 offset 스캔 |
| `build_replacements.py` | 대사/비주얼신 교체 계획 생성 |
| `build_ui_replacements2.py` | UI 교체 계획 생성 |
| `build_st_replacements.py` | 게임 선택 교체 계획 생성 |
| `apply_replacements.py` | FString 교체 |
| `patch_serialsize_binary.py` | `uasset` SerialSize 갱신 |
| `patch_richtext_font_size.py` | 검증된 개수의 float 크기 치환 |
| `patch_floats_at_offsets.py` | 정확한 offset의 float 치환 |
| `inject_manual_png.py` | 선택적 매뉴얼 이미지 주입 |
| `translate_card_game_png.py` | 카드게임 한글 PNG 생성 |
| `inject_card_game_png.py` | 카드게임 PNG를 원본 Texture2D에 주입 |
