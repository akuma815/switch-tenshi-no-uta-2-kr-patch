# 번역 영상의 Git 보존·복원 — 2026-10-16

사용자가 알려 준 에뮬레이터 모드에서 영상 포함 빌드를 확인했다. `H:/Eden/user/load/010047B021296000/Korean_Patch/romfs/Emulator_Tenshinouta/Content/Paks/TenshiKR2_P.pak`은 169,533,722바이트, SHA-256 `7c3ff25befc093346b4cd80e7af9a5dd8ec008be6e52652d7dc2dd961284340b`이며 공개 v1.5와 같다. 이 팩에 번역 MP4 10개와 Track02.iso가 있다. Citron NEO의 같은 게임 모드는 347바이트의 빈 companion pak이므로 영상 기준본으로 사용하지 않았다. 설치 파일은 변경하지 않았다.

## 보존 방식

`assets/video_deltas/`에 원본 게임 영상이 필요한 xdelta3/VCDIFF 10개와 해시 매니페스트를 보관한다. 원본·번역 MP4 전체와 게임 ISO는 커밋하지 않는다. 각 차분은 `VCD_SOURCE`를 사용하며 호스트 경로가 들어가는 application header를 제거했다. 원본 영상, 차분, 복원 결과의 크기·SHA-256을 각각 확인한다.

Eden 모드에서 추출한 번역 영상을 기준으로 차분을 만들었고 10개 모두 실제 역적용하여 동일 바이트를 확인했다. 대상은 오프닝·엔딩·장면 01/04/05/07/08/09/10/11이다. 이전의 고정 v1.5 압축 파일 다운로드 의존성을 제거했다. 영상 복원 코드는 네트워크 요청을 하지 않는다.

이 방식은 인코딩된 번역 영상의 보존이다. 자막 편집 프로젝트와 영상 인코딩 명령을 되살리는 것은 아니며, 새로운 영상 재생/자막 시각 검수를 수행했다는 뜻도 아니다.

## 영상만 복원

Git을 복제한 뒤 지원 원본의 Paks와 외부 도구를 지정한다. 원본 추출은 [재빌드 안내](REBUILD_2026-10-16.md)를 따른다.

```powershell
python -X utf8 translation/scripts/restore_compiled_videos.py --source-paks '지원 원본 Paks의 절대 경로' --repak 'repak.exe의 절대 경로' --xdelta 'xdelta3.exe의 절대 경로'
```

기본 출력은 `translation/cutscene_translate/`, 원장은 `translation/input_cache/video_deltas/video_restoration_report.json`이다. `--output`, `--cache`로 별도 경로를 지정할 수도 있다.

## 전체 빌드

```powershell
python -m pip install -r requirements.txt
powershell -NoProfile -ExecutionPolicy Bypass -File translation/scripts/build_reproducible.ps1 -SourcePaks '지원 원본 Paks의 절대 경로' -RetocPath 'retoc.exe의 절대 경로' -RepakPath 'repak.exe의 절대 경로' -XdeltaPath 'xdelta3.exe의 절대 경로'
```

영상 10개를 원본과 Git 차분으로 먼저 복원한 뒤 기존 빌드에 포함한다. `-ReleaseArchive` 옵션과 `py7zr` 의존성은 제거했다. 최종 검증은 IoStore 자산 76개와 UFS 파일 11개를 기존 v1.5의 자산별 해시와 대조한다. 컨테이너 전체 해시 동일성과 내부 자산 동일성은 구분한다.

최신 원격 검증 결과와 소스 커밋은 [video_git_verification_2026-10-16.json](video_git_verification_2026-10-16.json)에 기록한다. 원본·개인 키셋·외부 도구와 편집 기록의 비공개 백업은 계속 필요하지만, 번역 영상 복원을 위해 예전 설치 모드나 릴리즈 압축 파일을 따로 유지할 필요는 없다. 게임 폴더 삭제는 이번 작업 범위에 포함하지 않는다.
