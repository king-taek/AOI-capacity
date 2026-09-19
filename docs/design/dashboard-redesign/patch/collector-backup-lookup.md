# 수집기 수정안 — Scanresult 백업 폴더 조회

## 문제

`collect.py` 는 `{장비경로}\Scanresult\{Job}\{Setup}\{Lot}\{WaferID}\WaferInfo.ini`
한 경로만 확인합니다. 그런데 현장에서는 **어느 날짜를 기준으로 그 이전 Scanresult 를
통째로 백업 폴더로 옮기고** 있어서, 옮겨진 순간부터 전부 `NOT_FOUND` 가 됩니다.

30대 조사 결과 **16대에 백업 폴더**가 있고, 거기 잠긴 Job 폴더가 **5,078개**입니다.
폴더 이름은 제각각입니다.

```
Scanresult_Back up_260918     "Back up" 사이 공백
Scanresult Backup_260707      언더바 없이 공백
Scanresult backup260904       소문자 · 붙여쓰기
Scanresult_BAKCUP_260429      BACKUP 오타
Scanresult - BACKTUP 0827     하이픈 + 오타
Scanresult - 5.9.3            백업이 아니라 버전명
Scanresult_0901               날짜만
Scanresult_Backup_268020      있을 수 없는 날짜
```

그래서 목록으로는 못 잡고 **`Scanresult` 로 시작하는지**로만 걸러야 합니다.

## 효과 (30대 실측)

- 검사한 Lot 4,107개 중 **1,840개(44.8%)** 가 백업에서 발견
- 읽을 수 있는 `WaferInfo.ini` **24,050 → 53,069개 (2.2배)**
- AOI-7 `0 → 4,465` · AOI-5 `50 → 5,229` · AOI-4 `0 → 1,165` · AOI-12 `671 → 5,644`
- 실제로 사라진 것은 2.7% 뿐

## 수정 1 — `aoi_capacity/devices.py`

```python
def cutoff_of(name, path):
    """폴더 이름의 날짜 = 그 이전 것을 담아 둔 경계. 못 읽으면 None."""
    m = re.search(r"(\d{6})(?!\d)", name)          # 260918 · 250324
    if m:
        try:
            return datetime.strptime(m.group(1), "%y%m%d")
        except ValueError:
            pass                                    # 268020 같은 잘못된 날짜
    m = re.search(r"(?<!\d)(\d{4})(?!\d)", name)    # 0901 · 0421 → 폴더 해에 맞춤
    if m:
        try:
            y = datetime.fromtimestamp(os.path.getmtime(path)).year
            return datetime.strptime(f"{y}{m.group(1)}", "%Y%m%d")
        except (ValueError, OSError):
            pass
    return None                                     # "Scanresult - 5.9.3" — 맨 뒤로

def scan_dirs_of(root, primary):
    """Scanresult 로 시작하는 폴더를 모두 후보로. 경계 날짜 이른 것부터."""
    try:
        names = [n for n in os.listdir(root)
                 if n.lower().startswith("scanresult")
                 and os.path.isdir(os.path.join(root, n))]
    except OSError:
        return [primary]
    others = sorted((n for n in names if n != primary),
                    key=lambda n: cutoff_of(n, os.path.join(root, n)) or datetime.max)
    return [primary] + others

# attach() 안, 기존 scan_dir 설정 바로 뒤
dev["scan_dirs"] = scan_dirs_of(str(dev["path"]), dev["scan_dir"])
```

## 수정 2 — `aoi_capacity/collect.py`

999행 부근:
```python
# 전
scan_root = os.path.join(d["path"], str(d.get("scan_dir") or cfg["scan_dir"]))
# 후
scan_roots = [os.path.join(d["path"], n)
              for n in (d.get("scan_dirs") or [str(d.get("scan_dir") or cfg["scan_dir"])])]
```

490행 부근:
```python
def roots_for(batch_start, scan_roots, cutoffs):
    """배치 날짜가 들어 있을 폴더부터. 경계보다 이른 배치는 그 백업에 있다."""
    dated = [(cutoffs[p], p) for p in scan_roots[1:] if cutoffs.get(p)]
    dated.sort(key=lambda x: x[0])
    for cut, p in dated:
        if batch_start < cut:
            return [p] + [q for q in scan_roots if q != p]
    return scan_roots

rel = os.path.join(rep["equipment"], rep["process_code"],
                   w["lot"], w["wafer_id"], "WaferInfo.ini")
ini_path = None
for sr in roots_for(rep["batch_start"], scan_roots, cutoffs):
    cand = os.path.join(sr, rel)
    if nas_guard.exists(cand):
        ini_path = cand
        if sr is not scan_roots[0]:
            r["data_issue"] = "백업 폴더에서 찾음: " + os.path.basename(sr)
        break
if ini_path is None:
    r["ini_match"], r["data_issue"] = "NOT_FOUND", "예상 경로에 WaferInfo.ini 없음"
```

**속도** — 백업이 날짜로 잘려 있어 배치 날짜로 폴더를 바로 고를 수 있습니다.
확인 횟수는 지금과 같은 1번이고, 골라 간 폴더에 없을 때만 나머지를 훑습니다.

**원칙 유지** — 재귀 탐색을 늘리는 게 아니라 확인할 루트만 늘립니다.
정확 경로만 확인하는 규칙과 NAS 읽기 전용 규칙은 그대로입니다.

## 같이 넣을 것

폴더는 있는데 `MoveResultFlag` 만 있고 INI 가 없으면 “파일을 못 찾음”이 아니라
**“이동만 되고 스캔 안 함”** 입니다(AOI-4 `XBL WBG\24` 에서 확인).
지금은 둘이 `NOT_FOUND` 로 섞여 품질 지표가 실제보다 나빠 보입니다.
`ini_match` 에 `MOVED_ONLY` 같은 값을 하나 더 두세요.

## 그래도 남는 것

- **4층 5대(4F-AOI-01~05)는 백업 폴더가 없습니다.** 보존 기간을 늘리거나
  매일 자동 수집(`scripts/run_collect.bat` 을 작업 스케줄러에)으로만 해결됩니다
- 실제로 삭제된 2.7% 는 Report 의 배치 시각으로 추정합니다(화면에 이미 반영)

## 검증 방법

수정 후 `python -m aoi_capacity.cli --full` 로 재수집하고, 장비별 **시각 확인 비율**을
전후 비교하세요. 현재값: AOI-4 4% · 4F-AOI-01 15% · AOI-7 43% · AOI-5 53% ·
AOI-12 61% · AOI-2 66% · (정상군) AOI-15 87% · AOI-14 86% · AOI-9 84%
