# 천사의 시 한글 패치 빌드 문서

`천사의 시`(Switch판, UE 5.4 IoStore 컨테이너) 한글 패치의 빌드 절차와 구조를 정리한 문서다.
2026-07-05 기준의 스크립트 실체와 일치하도록 전면 재정리했다.

## 1. 개요

- 원본 pak 위치: `..\RomFS\Emulator_Tenshinouta\Content\Paks` (원본은 절대 수정하지 않는다)
- 빌드 실행:

```powershell
cd "G:\Downloads\Tenshi no Uta"
powershell -ExecutionPolicy Bypass -File translation\scripts\build_patch.ps1
```

- 최종 산출물 (`translation\patch_P`):

| 파일 | 내용 |
| --- | --- |
| `TenshiKR_P.pak/.ucas/.utoc` | 대사, 비주얼신, UI, 선택 화면, 매뉴얼 이미지, 폰트 크기 설정 (zen 컨테이너) |
| `TenshiKR_Font_P.pak` | 한글 폰트 + 낮춘 세로 메트릭 (legacy pak, 매 빌드 재생성) |

- `H:\` 드라이브가 있으면 `H:\Eden\user\load\010096F021294000\Korean_Patch\romfs\Emulator_Tenshinouta\Content\Paks`로 산출물 4개를 자동 복사한다.
- 수동 적용 시: 에뮬레이터 모드 폴더의 `<모드명>\romfs\Emulator_Tenshinouta\Content\Paks\`에 4개 파일을 복사한다. 원본 pak은 그대로 둔다.

## 2. 번역 원본 파일 (빌드 입력)

`translation` 루트의 다음 파일이 항상 최신본이며 빌드 기준이다.

| 파일 | 용도 | 비고 |
| --- | --- | --- |
| `천사의시_대사_번역.xlsx` | 일반 대사 | 항상 사용 |
| `천사의시_3줄초과_수정필요.xlsx` | 대사 보정본 | 같은 offset이 있으면 대사 번역본보다 우선 적용 |
| `visualscene_paired.xlsx` | 비주얼신 자막 | 루트에 없으면 `백업_csv\visualscene_paired.csv` 폴백 |
| `ui_menu_text_paired.xlsx` | UI/메뉴/크레딧 | 루트에 없으면 `백업_csv\ui_menu_text_paired.csv` 폴백 |
| `outgameinfo_paired.csv` | 게임 선택 화면 | 루트 csv → 루트 xlsx → `백업_csv` 순 |
| `매뉴얼_번역\Manual1_*.png` | 매뉴얼 이미지 | 있을 때만 주입 |

`검수_필요_목록.csv`는 번역 품질 검수용 리포트(포맷 코드 불일치·기계 음차·행 어긋남 의심 369행)로, 빌드 입력이 아니다.

## 3. 빌드 파이프라인

`scripts\build_patch.ps1`의 처리 순서:

1. `translation\work` 초기화 (매 빌드 삭제 후 재생성되는 임시 폴더)
2. XLSX → CSV 변환, 3줄초과 수정본을 offset 기준으로 병합
3. 원본 pak에서 대상 애셋을 `retoc to-legacy`로 추출
4. `uexp` 문자열 스캔으로 offset 지도 생성
5. 한국어 자동 줄바꿈 (`rewrap_ko.py`, 아래 규칙 참조)
6. 대사/비주얼신/UI/선택 화면 교체 계획(JSON) 생성
7. `uexp` 문자열을 UTF-16LE FString으로 교체, `uasset` SerialSize 갱신
8. 비주얼신: 원본 타이밍을 유지한 채 한국어 전체 삽입
9. 폰트 크기 패치 (아래 "크기 조절 지점" 참조)
10. 매뉴얼 PNG를 Texture2D에 주입 (있을 때만)
11. `retoc to-zen`으로 `TenshiKR_P.*` 생성, `patch_P`로 복사
12. 폰트 세로 메트릭을 낮춘 사본으로 `TenshiKR_Font_P.pak` 재생성 (`repak pack --version V11 -p 1253859140`)
13. Eden 모드 폴더로 자동 복사 (H:\ 존재 시)

## 4. 텍스트 줄바꿈 규칙

- **원문(jp)의 줄바꿈 구조를 그대로 따른다.** 번역 시트의 ko가 원문과 같은 위치에 줄바꿈을 갖고 있고, `rewrap_ko.py`는 이 줄바꿈을 보존한다. 메뉴/선택지(줄 단위 커서), 전각 공백 정렬(비석·중앙 정렬 문구)이 여기에 의존한다.
- 전각 32자(`WRAP_WIDTH`)를 넘는 줄만 단어 단위로 추가 분할한다.
- `PRESERVE_LAYOUT_OFFSETS`(현재 3844 = 전투 커맨드 3줄 메뉴)는 어떤 경우에도 재랩핑하지 않는다.
- 3줄 초과 행은 빌드 로그의 `entries exceeding 3 lines`로 집계된다(번역 갱신에 따라 변동, 최근 19). 화면에서 잘리면 `천사의시_3줄초과_수정필요.xlsx`에서 다듬는다.

## 5. 폰트 크기·간격 조절 지점 (실기 검증 완료)

모든 조절 지점은 `build_patch.ps1` 안에 있으며, 값 하나만 바꿔 리빌드하면 된다.

| 대상 | 실제 결정 지점 | 현재 값 | 바꾸는 곳 |
| --- | --- | --- | --- |
| 대화창(메시지 윈도우) 기본 크기 | `WBP_LocalizeText` 우버그래프 바이트코드 `EX_FloatConst`(uexp 890) | 27 → 22 | `patch_floats_at_offsets.py` 인자 `"890:27:22"` |
| 대사 태그(`<red>` 등) 스타일 크기 | `DT_RichTextFormat` 6행 | 27 → 22 | `patch_richtext_font_size.py` 인자 (대화창 크기와 일치시킬 것) |
| 비주얼신 자막 크기 | `WBP_VisualSceneText` RichTextBlock의 `DefaultTextStyleOverride`에 `FSlateFontInfo.Size` **주입** | 16.5 (체감 22, 체감치 × 0.75) | `inject_visualscene_fontsize.py` 마지막 인자 |
| 줄 간격(전체) | 폰트 파일의 hhea/OS2 세로 메트릭 | k8x12: `--factor 1.00 --desc-factor 0.166667`, BIZ: `--factor 1.00 --desc-factor 0.12` | 원문 행 높이 1.00em 및 폰트별 기준선에 맞춤 |

배경 설명:

- 대화창 기본 폰트는 블루프린트가 `MakeStruct SlateFontInfo`로 직접 생성하며 크기가 바이트코드 상수 27.0에 하드코딩되어 있다. `DT_RichTextFormat`은 태그 스타일 전용이라 기본 크기에 반영되지 않는다.
- 비주얼신 자막은 원본에 Size가 직렬화되어 있지 않아(엔진 기본 크기로 렌더) 어떤 기존 값을 바꿔도 무효였다. `inject_visualscene_fontsize.py`가 unversioned fragment 헤더(0x0302→0x0502)를 수정해 Size 필드 4바이트를 삽입하고 uasset export map(SerialSize/SerialOffset)을 보정한다.
- 줄 간격은 위젯의 `LineHeightPercentage`(uexp 4908, 1.3)를 바꿔도 실기에 반영되지 않았고, 폰트 세로 메트릭으로만 조절된다.

## 6. 건드리면 안 되는 것 (프리징·오패치 원인)

- **`WBP_VisualSceneText`에 전역 float 치환(`patch_richtext_font_size.py`) 금지.** 32.0f 매치는 폰트 크기가 아니라 `BPTYPE_Normal` 문자열의 길이 필드에 걸친 우연한 바이트 패턴이며, 치환하면 문자열 길이가 깨져 인게임 진입 시 프리징된다. (`WBP_LocalizeText`의 마지막 32.0f 매치도 동일한 가짜 패턴)
- `WBP_EnglishSubtitles`의 40.0 6개는 폰트가 아니라 버튼 아이콘(40x40)·밴드(200x40) 이미지 크기다.
- `DT_LocalizeTextStyle`의 22.0은 비주얼신 자막에 반영되지 않고(원복됨), 32.0들은 Slate 브러시 ImageSize 기본값이다.
- `WBP_LocalizeText` 영역 export들의 float 쌍(MessageWindow 192x64, 전체 화면 256x184 등)은 에뮬레이트 화면 좌표계의 영역 크기이고, `SetDefaultSize/SetDotByDot/SetFullSize`의 960/768/1280x720은 화면 표시 모드 크기다.
- **원본에 없던 텍스처 애셋을 패치 컨테이너에 새로 추가하지 말 것.** `message_button1/2`(대화창 페이징 커서 텍스처)를 추출·투명화해 주입했더니 컨테이너 마운트(LayeredFS)는 되지만 부팅 중 크래시로 게임이 실행되지 않았다(2026-07-05, 원복). 정확한 메커니즘은 미확정이나, 매뉴얼 이미지처럼 원본에 이미 존재하는 텍스처를 덮어쓰는 것과 달리 위험하다. 관련 스크립트 `hide_paging_cursor.py`는 남아 있으나 빌드에서 호출하지 않는다(비활성).
- 새 float 값을 패치할 때는 전역 패턴 치환 대신 `patch_floats_at_offsets.py`(오프셋 지정 + 기존 값 검증)를 쓴다.

### 대화창 페이징 커서(삼각형) 숨김 — 실패 기록

대화창 진행 시 텍스트에 겹쳐 나오는 삼각형(▼)은 `WBP_Paging`이 `message_button1/2`(8x8 DXT5 삼각형 텍스처)를 그린 것이며, 위치는 네이티브 코드가 고정해 위젯 측 조정이 불가능하다. 두 제거 시도 모두 실패해 **현재는 커서를 그대로 둔다.**

- `WBP_Paging`의 Image_button 브러시 `ImageSize`(8x8)를 0으로 치환: 실기에서 커서 크기 불변(실제 렌더 크기는 브러시가 아니라 슬롯/네이티브 코드가 결정) → 무효.
- `message_button` 텍스처를 완전 투명 DXT5로 주입: 위 "건드리면 안 되는 것" 참조, 게임 크래시 → 원복.

## 7. 비주얼신 자막 싱크와 번역

- `DT_Tenshi_VisualSceneText`의 원본 큐 타이밍을 유지한 채 한국어 전체를 삽입하고 SerialSize를 갱신한다. (고정 슬롯 방식은 짧은 슬롯에서 한글이 잘려 폐기)
- 번역 쌍 생성(`build_replacements.py` visualscene 모드)은 offset 기준 매칭이다. 영문에 전각 공백이 섞인 utf16 문자열(엔딩 크레딧)과 분할된 고아 문자열도 쌍으로 잡는다.

## 8. 빌드 로그 체크리스트

- `merged from over3 file: N` — 3줄초과 수정본 병합 건수
- `OK: ... DT_Tenshi_VisualSceneText (full Korean, original timing)`
- `regen rows: 384, csv rows: 382, mismatches: 0` — 비주얼신 (384-382=2는 미번역 (c)TELENET 표기, 정상)
- `OK: ... DT_RichTextFormat (font size 22 ...)` / `OK: ... WBP_LocalizeText (대화창 크기 22)`
- `injected FSlateFontInfo.Size = 16.5`
- `injected: 40/40` — 매뉴얼 이미지
- 일반 대사의 `mismatches`(최근 약 83~85)는 원본 스캔과 대사표의 기지(旣知) 불일치로, 치명 오류가 아니다. 번역 갱신에 따라 소폭 변동한다.
- `patch_P`의 파일 시간이 최신인지 확인

## 9. 주요 스크립트

| 스크립트 | 역할 |
| --- | --- |
| `build_patch.ps1` | 전체 빌드 실행 (원클릭) |
| `xlsx_to_csv.py` | 대사 XLSX 변환 + 3줄초과 수정본 병합 |
| `xlsx2csv_any.py` | UI/비주얼신 등 일반 XLSX 변환 |
| `extract_strings.py` | `uexp` 문자열 offset 스캔 |
| `rewrap_ko.py` | 줄바꿈 보존 + 폭 초과 줄 분할 |
| `build_replacements.py` | 대사/비주얼신 교체 계획 생성 |
| `build_ui_replacements.py` | UI 교체 계획 생성 |
| `build_st_replacements.py` | 선택 화면 교체 계획 생성 |
| `apply_replacements.py` | `uexp` 문자열을 UTF-16LE FString으로 교체 |
| `patch_serialsize_binary.py` | `uasset` SerialSize 갱신 |
| `patch_visualscene_timing_scale.py` | 비주얼신 타이밍 조절용 보조 도구 (현재 빌드에서는 사용하지 않음) |
| `patch_richtext_font_size.py` | DT 테이블의 폰트 크기 float 전역 치환 (개수 검증) |
| `patch_floats_at_offsets.py` | 지정 오프셋 float 제자리 치환 (기존 값 검증) |
| `inject_visualscene_fontsize.py` | 비주얼신 RichTextBlock에 Size 필드 주입 |
| `patch_font_vertical_metrics.py` | `.ufont`(TTF) 세로 메트릭 조정 |
| `inject_manual_png.py` / `export_manual_png.py` | 매뉴얼 이미지 주입/추출 |
| `hide_paging_cursor.py` | 페이징 커서 텍스처 투명화 (게임 크래시로 **빌드에서 비활성**, 섹션 6 참조) |

## 10. 도구와 의존성

- Python 3 + `pip install openpyxl pillow texture2ddecoder quicktex`
- `tools\retoc.exe` — UE 5.4 IoStore 추출(to-legacy)·재생성(to-zen)
- `tools\repak.exe` — 폰트용 legacy pak 생성 (V11, path-hash-seed `1253859140`)

폰트 소스는 `fontsrc_condensed` (k8x12.ufont = Galmuri11-Condensed, BIZUDGothic-Regular.ufont = 한글 폰트)이며, 빌드 시 `work\fontsrc_lowmetrics`에 메트릭 조정 사본을 만들어 pak을 생성한다. 폰트 파일은 원본과 같은 내부 경로·파일명이어야 한다.

## 11. 작업 원칙

- 원본 pak은 수정·교체하지 않는다. 패치는 원본 옆에 추가하는 방식이다.
- 번역은 루트의 xlsx/csv를 수정하고, 산출물은 항상 스크립트로 재생성한다.
- `translation\work`는 임시 폴더다. 수동 편집 금지.
- 폰트 크기·메트릭·타이밍은 모두 `build_patch.ps1`에서 자동 적용되므로 수동 패치하지 않는다.
- 새 크기/간격 문제를 조사할 때는 색상 프로브(직렬화된 색상 값을 바꿔 실기 반영 여부 확인) 방식으로 해당 직렬화 데이터가 실제 사용되는지 먼저 검증한다.

## 12. 페이지 진행 커서 숨김

페이지 진행 커서는 정식 빌드에서 숨긴다.

```powershell
cd "G:\Downloads\Tenshi no Uta"
powershell -ExecutionPolicy Bypass -File translation\scripts\build_patch.ps1
```

- `message_button1/2` 텍스처를 추가하거나 교체하지 않는다. 이 방식은 부팅 크래시 이력이 있어 금지한다.
- 원본 `WBP_Paging`만 패치하며, `SetVisibility(Visible)` 두 호출의 ESlateVisibility 값을 `Hidden`으로 바꾼다.
- 파일 크기, SerialSize, 애셋 목록은 바뀌지 않는다.
