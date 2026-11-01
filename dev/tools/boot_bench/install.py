"""variants/ 의 조각을 이어 template.html 의 <script id="boot"> 를 바꾼다(11/1 D105: _shell(layoutSpec 뺌) + _text + _bars + bars_b).
사용: python3 dev/tools/boot_bench/install.py [변형=bars_b]  — 바꾼 뒤 dev/tests 의 boot 가드를 돌린다."""
import sys
from pathlib import Path
S = Path(__file__).resolve().parent; ROOT = S.parents[2]; B = S/"variants"
HEAD = '''/* ============================================================================
   시작 화면(11/1, D105 — 현택 결정 T2-B '장비 목록'): 가동률 화면의 줄 7개(장비 이름 자리 · 숫자 블록 · 24시간 트랙)가 깔리고,
   트랙 안의 바쁜 구간이 자라서 'AOI' 를 쓴다(5×7 비트맵, 쉬는 시간은 회색 트랙). 값이 오기 전엔 회청색, 로딩이 끝나면 범례 색(Scan 파랑 · Rescan 연파랑 · Test 보라 · Error 빨강).
   · 이 스크립트는 큰 데이터(#embedded)보다 앞에 있어서 파일을 읽는 동안부터 돈다. 움직임은 전부 CSS 키프레임 · WAAPI(transform · opacity 만) 라
     합성 스레드에서 돈다 — 프레임마다 도는 JS 가 0 이어서 JSON 해석 · 모델 계산이 메인 스레드를 막아도 끊기지 않는다(옛 D104 입자 장면은 Worker 캔버스였는데도
     입자 16,000개 · dpr 2 · 걷힘 blur 때문에 현장에서 끊겼다 — dev/tools/boot_bench 계측, docs/proposals/boot_lag_2026-10-31).
   · 페이지를 연 때부터 4초(MIN) 안에는 걷히지 않는다. 로딩이 4초를 넘으면 구간이 읽는 순서로 차례로 밝아졌다 돌아오며(점등 — 회청색 겹의 opacity 만, 현택 11/1 "'지금' 선은 구리다")
     기다린다. 로딩이 끝나면(AOI_BOOT.done) 제 색으로 앉고 0.4초 뒤 덮개가 opacity 만으로 0.6초에 걷힌다(blur · scale 없음). 신호가 없으면 4초 + 2.5초 뒤 그냥 연다.
   · 바깥 요청 0건(글꼴은 시스템) · 덮개는 클릭을 막지 않는다(pointer-events:none) · 움직임 줄이기면 완성 상태로 바로 · LOT 배포판(data-boot="lot")도 같은 장면.
   · 변형 · 계측 도구는 dev/tools/boot_bench — 이 코드는 install.py 가 variants/_shell + _text + _bars + bars_b 를 이은 것(여기서 직접 고치지 말고 variants 를 고친 뒤 다시 잇는다).
   ============================================================================ */
'''
def assemble(variant="bars_b"):
    shell = (B/"_shell.js").read_text(encoding="utf-8")
    a = shell.index("/* 창 크기에 맞춘 고정 대시보드 모양"); b = shell.index("function bootShell(o){")
    shell = shell[:a] + shell[b:]            # layoutSpec 은 입자 · CSS 스켈레톤 변형만 쓴다
    shell = shell.replace("/* 공통 껍데기 — 덮개 · 단계 글자(DOM, 합성 스레드 애니메이션) · AOI_BOOT API · 4초 최소 · 걷힘(opacity 만). 장면은 make() 가 만든다. */",
                          "/* 껍데기 — 덮개 · 단계 글자(DOM, 합성 스레드 애니메이션) · AOI_BOOT API · 4초 최소 · 걷힘(opacity 만). 장면은 아래 bootShell({make}) 이 만든다. */")
    parts = [shell, (B/"_text.js").read_text(encoding="utf-8"), (B/"_bars.js").read_text(encoding="utf-8"), (B/f"{variant}.js").read_text(encoding="utf-8")]
    return HEAD + '(function(){\n"use strict";\n' + "\n".join(parts) + "\n})();"
def install(variant="bars_b"):
    tpl = ROOT/"aoi_capacity/ui/assets/template.html"; s = tpl.read_text(encoding="utf-8")
    a = s.index('<script id="boot">') + len('<script id="boot">'); b = s.index("</script>", a)
    s = s[:a] + "\n" + assemble(variant) + "\n" + s[b:]
    tpl.write_text(s, encoding="utf-8"); return tpl
if __name__ == "__main__":
    print(install(sys.argv[1] if len(sys.argv) > 1 else "bars_b"))
