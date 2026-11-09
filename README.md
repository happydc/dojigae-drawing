# 각궁도지개 제작도면 생성기

각궁을 해궁하거나 얹을 때 모양을 잡아 주는 **도지개**의 제작도면을 만드는 윈도우 프로그램입니다.
치수를 입력하면 굴곡 등급별(중곡 / 중곡~심곡 / 심곡) 도면을 만듭니다.

- **PDF**: A3, 정면도 1:1 — 배율 100%로 출력하면 그대로 형판으로 쓸 수 있습니다.
- **DXF**: 1:1 — CAD, 레이저 커팅, CNC용
- **STL (보기용 `_model`)**: 목재 + 가죽, 끈구멍·매듭 보어 포함
- **STL (3D 프린트용 `_print`)**: 목재 본체만, 판재면을 바닥에 눕힌 자세. 베드보다 길면 꺾임점에서 2분할한 `_print_A/B`와 Ø5 맞춤 핀 구멍(깊이 12)도 함께 출력
- **3D 뷰어(HTML)**: 브라우저로 열어 회전·확대해 볼 수 있음 (인터넷 연결 필요)

## 웹 버전 (설치 없이 실행)

https://happydc.github.io/dojigae-drawing/ — 브라우저에서 바로 실행합니다. 윈도우·맥·휴대폰 모두 됩니다. 처음 한 번은 20~30초 걸립니다.

## 내려받기

[Releases](../../releases)에서 `GakgungDojigae.exe`를 받아 실행하면 됩니다. 설치는 필요 없습니다.
최신 빌드는 [Actions](../../actions) → 최근 실행 → Artifacts에서도 받을 수 있습니다.

> 처음 실행할 때 Windows SmartScreen 경고가 뜨면 **추가 정보 → 실행**을 누르세요(서명되지 않은 프로그램이라 뜨는 경고입니다).

## 도면 내용

| 항목 | 기본값 |
|---|---|
| 전체 길이 / 너비(판재 두께) | 360 / 30 mm |
| 왼쪽 끝 → 꺾임점 | 167 mm (조정 가능) |
| 끝단 높이 / 꺾임부 높이 | 22 / 40 mm |
| 오목면 쪽(가죽 반대쪽) 모서리 | R = T × 0.45 (T30 → R13.5) |
| 볼록면(활 접촉면) | 폭 전체 완만한 C자 홈, 중앙 깊이 2 mm, 스웨이드 가죽 t2. 끝부분은 역굴곡 없이 직선 연장 |
| 끈구멍 | 오목면 Ø7 관통 + 가죽쪽 매듭 보어 Ø12×8 (매듭을 가죽 속에 숨김) |
| 끈 감기 턱 | 양끝 오목면 h2.5, 끝에서 8 mm |
| 굴곡 등급 | 1형 중곡(×0.75), 2형 중곡~심곡(×1.0), 3형 심곡(×1.3) |

실물이나 형판과 대조한 뒤 **곡선 보정계수**나 등급 배율로 맞추세요.

## 직접 빌드 (선택)

Python 3.10 이상이 설치된 윈도우에서 `build.bat`를 실행하면 `dist\GakgungDojigae.exe`가 만들어집니다.

```
py -m pip install -r requirements.txt
py dojigae_gui.py        # GUI 실행
py dojigae_core.py       # 기본값으로 output 폴더에 도면 생성
```

## 파일

- `dojigae_gui.py` — 입력 화면
- `dojigae_preview.py` — 입력 화면 오른쪽 미리보기(항목에 마우스를 올리면 해당 치수 강조)
- `dojigae_core.py` — 형상 계산, PDF·DXF 생성
- `dojigae_3d.py` — 단면 스윕 3D 메시, 구멍 불리언(manifold3d), STL 저장
- `dojigae_viewer.py` — three.js 3D 뷰어 HTML 생성
- `web/` — 웹 버전(Pyodide). 3D 프린트용 구멍·2분할은 브라우저에서 manifold-3d로 처리
- `.github/workflows/pages.yml` — main에 올리면 웹 버전을 GitHub Pages에 배포
- `.github/workflows/build-windows.yml` — main 브랜치에 올리면 exe를 자동 빌드하고, `v*` 태그를 달면 Release에 올림
