# 현장 수집 결과 보관

앱이 실제 NAS 를 읽어 만든 결과 HTML 을 그대로 둔다. **개발·검증용**이고 배포본에는 들어가지 않는다
(`updater._UPDATE_SKIP_TOP` 이 `dev/` 를 통째로 건너뛴다).

## 왜 두는가

- 화면(`template.html`)을 고칠 때 **NAS 없이도 진짜 데이터로 확인**할 수 있다. 가짜 데이터로는
  드러나지 않는 것들(배치 중단이 파란 막대에 묻히는 문제, 빈 job 때문에 INI 를 못 찾는 문제,
  같은 Lot 안 7~8분 공백)이 전부 여기서 나왔다.
- 행을 꺼내는 법 — HTML 한 장에 데이터가 박혀 있다. 문자열 풀은 `pooled` 열만 펴면 된다:

```python
import json
from pathlib import Path

text = Path("dev/samples/AOI_capacity_2026-09-16_3일치.html").read_text(encoding="utf-8")
d = json.loads(text.split('id="embedded">')[1].split("</script>")[0])
pool, pooled, cols = d.get("pool"), set(d.get("pooled") or []), d["cols"]
rows = [dict(zip(cols, [pool[v] if c in pooled else v for c, v in zip(cols, r)])) for r in d["rows"]]
meta = d["meta"]
```

- 화면만 다시 그려 보려면 그 `rows` 를 `collect.write_html` 에 그대로 넘기면 된다(NAS 접근 없음).

## 파일

| 파일 | 언제 | 무엇 |
|---|---|---|
| `AOI_capacity_2026-09-16_3일치.html` | 2026-09-16 21:01 수집 | 첫 현장 수집. 9/13~9/16 · 25대 · 15,626행 · 수집 28.6분 |
| `AOI_capacity_2026-09-17_30대.html` | 2026-09-17 08:38 수집 | 30대 전부(4층 포함). 9/13~9/17 · 18,719행 · 수집 5.1분(목록 197초·읽기 108초). sha256 `58b70556…`. 9/17 인계 프롬프트가 분석한 그 첨부 |

`AOI_capacity_2026-09-16_3일치.html` 에 대해 알아 둘 것:

- **4층 5대가 빠져 있다.** 당시 `devices.csv` 의 `4층 / I:\ / *` 행이 자동 탐색이라 범위 제한 중
  통째로 건너뛰었다(`acaa6ce` 에서 고침). `meta.devices` 에 `4층`이 `scope: "out"` 으로 남아 있다.
- **AOI-10 의 9/15 가동률(24.1%)은 실제보다 낮다.** `R_TB500 TOP D-DIE_0860312PD` 배치들의 job 을
  못 읽어 INI 경로가 어긋났고, 그래서 8.8시간이 '미가동' 으로 잡혔다(`acaa6ce` 에서 고침).
- `norm_status`·`scan_type` 은 **그때 규칙으로 계산된 값**이다. 지금 규칙으로 보려면 다시 계산한다:
  `r["norm_status"] = collect.norm_status(r["status"])`, `r["scan_type"] = collect.scan_type(r["lot"])`.
