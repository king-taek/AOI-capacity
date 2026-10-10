import json, re, os, sys
WORK = os.environ.get('AOI_WORK') or sys.exit('set AOI_WORK')
F = os.path.join(WORK, 'fable')
a1 = json.load(open(f'{F}/a1.json')); a2 = json.load(open(f'{F}/a2.json')); a3 = json.load(open(f'{F}/a3.json'))
g5 = a1['g5_hours_fixed']; rv = a2['review']; c6 = a2['claim6']; rp = a3['repeat3']; cr = a3['cr_refined']
ud = rv['unrev_by_defects']; nd = sum(v['n'] for k, v in ud.items() if k != '0'); un = sum(v['n'] * v['unrev_pct'] / 100 for k, v in ud.items() if k != '0')
unrev_defect_pct = round(100 * un / nd, 1)
sw = {r['dev']: r for r in a1['rdl_post_fixed'] if r['mode'] == 'multi'}
claims = [
 dict(id=1, verdict='adjust',
      number=f"G5 스캔 비중 58% → 75%(2번째 레시피 스캔을 스캔으로 셀 때) · G5 비스캔 시간 2,002h → 약 {g5['overhead_h_fixed']:,}h(로딩 {g5['load']:,}h + 레시피 전환 {g5['switch']}h + 후처리) · G5 로딩 중앙 66초 vs 구형 15~17초(같은 설정)",
      how="웨이퍼 한 장의 시간을 세 토막으로 나눕니다. 로딩 = WaferInfo 의 시작 시각부터 ScanLog 의 스캔 시작까지, 스캔 = ScanLog 의 Duration, 나머지 = 스캔 끝부터 WaferInfo 의 끝 시각까지(후처리). "
          "예: AOI-23 GDN-RDL3 의 52215757EWF2 는 23:45:32 시작 → 23:47:16 스캔 시작(로딩 104초) → Duration 566초 → 23:59:12 끝이라 '나머지' 가 150초입니다. "
          "그런데 이 150초 중 136초는 23:56:56 에 시작한 x5 레시피의 스캔입니다 — ScanLog 의 Duration 은 첫 레시피(x20)만 담고, 2번째 레시피 결과는 Recipe2 폴더에 따로 남습니다. "
          "RDL 멀티 6,234장의 94% 가 Duration ≈ x20 구간이었습니다. 그래서 2번째 레시피 구간(ExtendedScanMetaData 시각 → 끝, 후처리 20초 가정)을 스캔으로 옮기면 G5 스캔 비중은 58% 가 아니라 75% 이고, 구형 세대와의 차이(78~82%)도 크게 줄어듭니다. 로딩 66초 vs 15~17초는 그대로 맞습니다.",
      caveat="2번째 레시피의 순수 스캔 시간은 ScanLog 에 없어 구간 길이에서 후처리 20초를 뺀 추정값입니다(PI 는 1·2차 레시피 경계가 겹쳐 10~40초 오차).",
      fix="스캔 비중 58%→75%, 비스캔 시간 2,002h→약 1,180h 로 고침. 로딩 65~66초 주장은 유지."),
 dict(id=2, verdict='wrong',
      number=f"RDL 멀티의 '후처리 110~160초' = x5 스캔 55초 + 레시피 전환 {min(r['switch'] for r in sw.values())}~{max(r['switch'] for r in sw.values())}초(장비마다 다름) + 진짜 후처리 24~66초 · 단일은 11~28초",
      how="ScanLog 의 Duration 은 첫 레시피(x20)만 셉니다. 그래서 '스캔 끝 이후' 로 잡힌 시간에 x5 레시피의 스캔이 통째로 들어갔습니다. x5 만 단독으로 돈 104장의 Duration 중앙값이 55초이니 그것이 x5 순수 스캔 시간입니다. "
          f"예: AOI-24 멀티 '후처리' 149초 = 전환(x20 끝→x5 시작) 58초 + x5 스캔 55초 + 남은 후처리 약 24초(x5 구간 79초 − 55초). AOI-19 는 전환이 14초라 같은 계산이 119 = 14 + 55 + 48 입니다. "
          "즉 멀티가 단일보다 장당 100~150초 더 드는 것은 사실이지만 그 대부분은 2번째 스캔과 레시피 전환이고 '후처리가 10배' 는 아닙니다.",
      caveat="레시피 전환 시간은 CleanReferenceEvery=Wafer 설정이면 100초 넘게 늘어납니다(AOI-25 113초·AOI-23 108초, 같은 장비 CR=Lot 은 5·23초).",
      fix="'멀티 후처리 110~160초 vs 단일 11~28초' 를 '멀티는 x5 스캔 55초 + 전환 14~63초가 더 든다(장비별 전환 차이 4배)' 로 바꿈."),
 dict(id=3, verdict='adjust',
      number=f"542h → 같은 장비·같은 Job 짝 비교 {cr['clean_h']}h({cr['clean_wafers']:,}장 확인) → CR=Wafer 전체 {cr['cr_wafer_wafers_total']:,}장으로 환산 약 {cr['extrapolated_clean_h']}h · 장당 세대별 +25~66초",
      how="기존 계산은 '가족×세대' 묶음 안에서 CR=Wafer 와 CR=Lot 의 로딩 중앙값 차이를 썼는데, '기타' 묶음에는 서로 다른 Job·장비가 섞여 있어 Job 자체가 느린 것까지 CR 탓이 됩니다. "
          "대신 같은 장비에서 같은 Job 을 두 설정으로 모두 돈 경우만 골라(112쌍) 로딩 중앙값 차이 × 장수를 더했습니다. 스캔 시간까지 20% 넘게 바뀐 쌍(레시피가 함께 바뀐 것, 예: AOI-25 RDL2 장당 +1,008초)은 뺐습니다. "
          "예: AOI-5 의 'ASTB500-SP822' Job 은 CR=Wafer 618장이 로딩 142초, CR=Lot 570장이 16초 → 장당 +126초, 21.6h. 세대별 장당 추가분 중앙: EagleT +66초, EagleTP +45초, EAGLE +32초, G5 +25초(G5 는 원래 로딩이 길어 상대적으로 작음).",
      caveat="확인된 193h 는 CR=Wafer 장의 45% 에 대한 값이고 425h 는 그 비율을 나머지에 그대로 적용한 환산입니다.",
      fix="542h → '확인 193h · 환산 약 425h' 두 숫자로. AOI-25 RDL2 의 100h 는 CR 만의 효과가 아니라 10/4 레시피 변경과 겹치므로 따로 적음(새 분석 3)."),
 dict(id=4, verdict='adjust',
      number=f"재스캔 {rp['total']:,}장·{rp['hours']:,}h 중 진짜 재검사 {rp['buckets']['진짜 재검사']['n']:,}장(23%)·{rp['buckets']['진짜 재검사']['h']}h, 다른 검사 단계·레시피 {rp['buckets']['다른 검사(재검사 아님)']['n']:,}장(66%)·{rp['buckets']['다른 검사(재검사 아님)']['h']}h, 테스트·모니터 웨이퍼 {rp['buckets']['테스트·모니터']['n']:,}장(12%)·{rp['buckets']['테스트·모니터']['h']}h",
      how="같은 Job 에서 같은 Wafer ID(영숫자 6자 이상)가 두 번 이상 보이면 두 번째부터를 셉니다. 기존의 '같은 장비·다른 Lot 이름' 3,711장(548h)을 한 장씩 다시 봤습니다: ① 두 번의 레시피가 다르면 다른 검사(863장), ② Job 이 'No Pattern' 이거나 Lot 이름에 TEST 가 있으면 테스트·모니터 웨이퍼(1,829장 — 예: 'No Pattern' Job 의 웨이퍼 24 는 30일 동안 다섯 번 Lot 이름을 바꿔 돌았음), "
          "③ 20장 이상이 통째로 다른 이름으로 다시 돌면 Lot 재검사(1,394장 — 예: JJ_BU Job '0909-XKS' 25장이 9/9 전부 Pass 뒤 9/15 'XKS-161' 로 다시), ④ 일부 장만 다시(1,089장). "
          "결과: '다른 Lot 이름' 5,217장의 48% 만 진짜 재검사입니다. RE 표기 재실행 1,479장은 첫 검사가 Pass 였던 것이 94% 라 진짜 재검사입니다.",
      caveat="Lot 통째 재검사가 '이름을 잘못 넣어 다시' 인지 '품질 재검사' 인지는 로그로 구분할 수 없고, TEST 판정은 Lot 이름 토큰 기준입니다.",
      fix="'같은 장비·다른 Lot 3,711장은 재스캔' → 그중 절반만 재검사. 재스캔 총량은 그대로 두고 '진짜 재검사 4,010장·452h' 를 머리글로."),
 dict(id=5, verdict='ok',
      number=f"평균 가동 62%(장비별 첫~마지막 배치 기간 기준) · 공통 창(9/9 0시~10/10 04:28, 748h) 기준 {a2['busy']['mean_fixed']}% · 배치 사이 빈 시간 {a2['busy']['idle_gap_h']:,}h 중 2시간 미만 {a2['busy']['idle_lt2h_pct']}% · 창 앞뒤 빈 시간 {a2['busy']['head_tail_h']}h 는 별도",
      how="Report 의 Batch Start~End 를 장비마다 시간축에 놓고 겹치는 것은 합칩니다. 합친 구간이 '배치가 걸려 있던 시간', 그 사이가 빈 시간입니다. "
          f"예: 30대 × 748h = {a2['busy']['total_h']:,}h 중 배치 구간 {a2['busy']['busy_h']:,}h 라 60%. 빈 시간 8,273h 를 길이별로 나누면 30분 미만 1,642h, 30분~2시간 2,855h(둘이 54%), 2~8시간 1,933h, 8시간 이상 1,843h.",
      caveat="'배치 구간' 은 Lot 이 걸려 있던 시간이라 안의 로딩·전환까지 포함합니다(스캔 가동률이 아님). AOI-20 만 두 기준 차이가 10%p(77.9 vs 67.6 — 9/9 이후 며칠 기록 없음).",
      fix="숫자 유지. 분모가 '장비별 첫~마지막 배치' 임을 적고, 공통 창 기준 60% 를 함께."),
 dict(id=6, verdict='adjust',
      number=f"Lot 의 {c6['pct']}%({c6['lots_multi']:,}/{c6['lots']:,})는 Report 2장 이상 · Report 행 {c6['rows']:,} 중 INI 없는 행 {c6['rows_without_ini']:,}({c6['pct_asis']}%) = 스캔됐는데 INI 가 없는 {c6['scanned_but_no_ini']:,}({c6['pct_overwritten']}%) + 애초에 스캔되지 않은(중단) {c6['never_scanned_rows']:,}({c6['pct_never']}%)",
      how="Report 요약의 'Wafers Scanned' 와 그 Report 의 Batch 창 안에 든 WaferInfo 개수를 비교했습니다. 행 수 − Wafers Scanned 는 스캔 전에 중단된 행이고, Wafers Scanned − 창 안 INI 수가 '스캔은 됐는데 INI 가 없는' 행(나중 실행이 덮어썼거나 기록 안 됨)입니다. "
          "예: 4F-AOI-02 DPV Lot 의 첫 Report 는 8행·Wafers Scanned 0(중단) → INI 가 없는 이유는 덮어쓰기가 아니라 스캔을 안 한 것. 두 번째 Report 8행은 8장 모두 INI 가 있습니다.",
      caveat="'스캔됐는데 INI 없음' 안에는 덮어쓰기 외에 INI 기록 실패도 섞여 있을 수 있습니다.",
      fix="'10.4% 가 나중 실행에 덮어써짐' → '6.1% 덮어쓰기(또는 미기록) + 5.7% 스캔 안 됨' 으로 나눔. 23% 는 유지."),
 dict(id=7, verdict='adjust',
      number=f"검토 리드타임 중앙 3.8h(최근 3일 제외해도 3.8h) · 미검토 {rv['unrev_pct_asis']}% → 최근 3일 빼도 {rv['unrev_pct_excl3d']}% · 결함 0 인 {ud['0']['n']:,}장은 100% 미검토 · 결함 있는 wafer 중 미검토 {unrev_defect_pct}%, 결함 100개 이상은 {ud['100+']['unrev_pct']}% · G5 TB500 가족별 중앙 7~25h(RDL2 153h)",
      how="각 wafer 의 끝 시각부터 ScanLog 의 VerifyDate 까지를 셉니다. 최근 wafer 는 검토할 시간이 모자랐을 수 있어 마지막 3일(10/7 04:28 이후)에 끝난 wafer 를 빼고 다시 셌는데 미검토 비율이 30.6→30.1% 로 거의 같습니다 — 시간 부족이 원인이 아닙니다. "
          f"대신 결함 수로 나누면 결함 0 인 wafer 는 전부 미검토(검토할 것이 없음), 1~9개 13%, 10~99개 14.5%, 100개 이상은 {ud['100+']['unrev_pct']}% 가 미검토입니다. 3일 넘게 지난 wafer 중 24시간 안에 검토된 비율은 {rv['done24_pct']}%, 72시간 안은 {rv['done72_pct']}% — 그 뒤로는 거의 늘지 않습니다.",
      caveat="VerifyDate 가 없는 것이 '검토 안 함' 인지 '자동 Pass' 인지는 로그로 구분하지 못합니다(결함 0 은 자동으로 보임).",
      fix="'31% 미검토' → '결함 있는 wafer 기준 18%, 결함 100개 이상은 45%' 로. 우측 절단은 영향 없음을 명시."),
 dict(id=8, verdict='ok',
      number="AOI-17 Enhanced 스캔 703~827초(PI4 Enh 10/8 1,062초) vs 다른 장비 203~305초 · 두 레시피 구간이 모두 2.5배(1차 437~561 vs 160~325초, 2차 381 vs 117~171초) · 다이 수 같음(30) · 같은 AOI-17 의 일반 PI2/3/4 는 241~259초로 정상",
      how="같은 Job 을 돈 장비끼리 ScanLog Duration 중앙값을 비교하고, ExtendedScanMetaData 의 레시피 시작 시각으로 PI_Bubble 구간과 PI 구간을 따로 봤습니다. AOI-17 은 두 구간이 다 느리고 스캔한 다이 수는 똑같으며, 같은 장비에서 돈 일반 PI Job 은 다른 장비와 같습니다. "
          "즉 장비가 느린 것이 아니라 AOI-17 에 들어 있는 Enhanced Job 사본의 설정 문제입니다. 파라미터 파일 비교에서 AOI-17 만 다른 값이 93개(초점 오프셋 Zwafer 약 −20 vs 0, GMF 정렬 설정, 검출 기준 28개)이지만 단일 원인은 로그로 짚지 못했습니다.",
      caveat="AOI-17 Enhanced 는 10/5~10/10 닷새·243장의 기록이라 표본이 작습니다.",
      fix="없음. '장비 문제' 로 읽히지 않게 'AOI-17 의 Enhanced Job 사본 설정' 이라고 적을 것."),
]
# ---- new analyses
n1 = a3['n1_summary']; p25 = a3['n1_p25']
dev1 = sorted(a3['n1_dev'], key=lambda x: -x['recover_h'])
new = [
 dict(id='changeover', title='Lot 교체 공백: 같은 Job 11분, 다른 Job 26분', headline=f"2시간 미만 공백 {n1['short_h']:,}h 중 되찾을 수 있는 {a3['n1_recover_at_median_h']:,}~{a3['n1_recover_total_h']:,}h",
      how=f"장비마다 배치가 끝나고 다음 배치가 시작될 때까지의 공백(2시간 미만 {n1['short']:,}건, 합 {n1['short_h']:,}h)을 앞뒤 Job 이 같은지로 나눴습니다. 같은 Job 이 이어질 때 중앙 {n1['same_job']['med']}분, 다른 Job 으로 바뀔 때 {n1['diff_job']['med']}분, 앞 배치에 Error 가 있었을 때 {n1['after_error']['med']}분. "
          f"모든 공백을 그 유형의 전사 중앙값(같은 Job {round(n1['same_job']['med'])}분·다른 Job {round(n1['diff_job']['med'])}분)까지만 줄이면 {a3['n1_recover_at_median_h']:,}h, 상위 25% 장비 수준({p25['same']}·{p25['diff']}분)까지 줄이면 {a3['n1_recover_total_h']:,}h 가 돌아옵니다. "
          f"예: AOI-15 는 같은 Job 사이 공백이 중앙 {dev1[0]['same_med']}분(518건)으로 전사의 3배 — 이 한 대에서 {dev1[0]['recover_h']}h.",
      data=dict(by_type=dict(same=dict(med=n1['same_job']['med'], p25=n1['same_job']['p25'], p75=n1['same_job']['p75'], n=n1['same_job']['n'], h=n1['same_job_h']),
                             diff=dict(med=n1['diff_job']['med'], p25=n1['diff_job']['p25'], p75=n1['diff_job']['p75'], n=n1['diff_job']['n'], h=n1['diff_job_h']),
                             after_error=dict(med=n1['after_error']['med'], p25=n1['after_error']['p25'], p75=n1['after_error']['p75'], n=n1['after_error']['n'], h=n1['after_error_h'])),
                hist_h=a3['n1_gap_hist_h'], hist_n=a3['n1_gap_hist'], recover=dict(at_median=a3['n1_recover_at_median_h'], at_p25=a3['n1_recover_total_h']),
                by_dev=[dict(dev=x['dev'], gen=x['gen'], same=x['same_med'], diff=x['diff_med'], n=x['n'], recover_h=x['recover_h']) for x in a3['n1_dev']]),
      takeaway="공백은 길이가 아니라 횟수가 문제입니다 — 5~30분짜리 6,460건이 1,540h. 같은 Job 이 이어지는데도 11분이 비는 것은 카세트 교체·Lot 입력 대기이고, AOI-15 처럼 한 대가 30분씩 비는 곳부터 보면 됩니다."),
]
n2 = a3['n2']; m2 = a3['n2_medians']
f4 = [x for x in n2 if x['dev'].startswith('4F-AOI-0') and x['gen'] == 'EagleG5']; g2 = [x for x in n2 if x['gen'] == 'EagleG5' and not x['dev'].startswith('4F')]
absorb = sum((m2['busy'] - x['busy_pct']) / 100 * 24 * x['wph'] for x in f4)
new.append(dict(id='capacity', title='장비별 처리 속도 × 바쁨: 느려서 모자란가, 비어서 모자란가', headline=f"2층 G5 {len(g2)}대 {min(x['wph'] for x in g2)}~{max(x['wph'] for x in g2)}장/h·{min(x['busy_pct'] for x in g2):.0f}~{max(x['busy_pct'] for x in g2):.0f}% 바쁨, 4층 G5 3대 {min(x['busy_pct'] for x in f4):.0f}~{max(x['busy_pct'] for x in f4):.0f}% 비어 있음",
      how=f"장비마다 '배치가 걸려 있던 시간' 비율(바쁨)과 그 시간 동안 처리한 wafer 수(장/h)를 함께 봤습니다. 전사 중앙값은 {m2['wph']}장/h·{m2['busy']}% 입니다. 이 둘로 네 칸을 만들면 '느림·바쁨' 칸에 2층 G5 9대와 AOI-11 이 들어가고, '느림·한가' 칸에 4층 G5 3대가 들어갑니다. "
          f"4층 G5 는 같은 TB500 PI Enhanced Job 을 203초에 돌리는데(2층 237~827초) 바쁨이 {min(x['busy_pct'] for x in f4):.0f}~{max(x['busy_pct'] for x in f4):.0f}% 뿐입니다. 4층 3대를 전사 중앙 {m2['busy']}% 까지만 채우면 하루 약 {absorb:.0f}장을 더 받을 수 있습니다(지금 속도 기준). "
          "'빠름·한가' 칸(AOI-3·9·15·16 등 구형 10대, 36~56%)은 설정이 아니라 물량 배정 문제입니다.",
      data=dict(medians=m2, quad=a3['n2_quad'], absorb_per_day=round(absorb), dev=[dict(dev=x['dev'], gen=x['gen'], busy=x['busy_pct'], wph=x['wph'], wpd=x['wpd'], wt=x['wt_med']) for x in n2]),
      takeaway="2층 G5 는 설정(멀티 레시피·긴 TB500 스캔)으로 느려서 꽉 차 있고, 4층 G5 는 빨라도 물량이 없어 비어 있습니다. TB500 PI·Enhanced Lot 을 4층으로 돌리는 것이 설정을 손대는 것보다 먼저입니다."))
rows25 = a2['aoi25_rdl2_lots']
bef = [x for x in rows25 if x['cr'] == 'Wafer' and x['lot'] != 'TEST']; aft = [x for x in rows25 if x['cr'] == 'Lot']
import statistics as st
new.append(dict(id='cr_multi_g5', title='G5 멀티 레시피 Job 의 CleanReference=Wafer: 장당 10~18분', headline=f"AOI-25 RDL2 장당 {round(st.median([x['wt'] for x in bef])/60)}분 → {round(st.median([x['wt'] for x in aft])/60)}분(10/4 레시피 변경)",
      how=f"AOI-25 의 TB500 RDL2 Lot 을 날짜순으로 놓으면 10/4 전 {len(bef)}개 Lot(CR=Wafer)은 장당 로딩 약 {round(st.median([x['load'] for x in bef]))}초·x20 스캔 {round(st.median([x['scan'] for x in bef]))}초·장당 {round(st.median([x['wt'] for x in bef]))}초였고, 10/4 뒤 {len(aft)}개 Lot(CR=Lot)은 로딩 {round(st.median([x['load'] for x in aft]))}초·스캔 {round(st.median([x['scan'] for x in aft]))}초·장당 {round(st.median([x['wt'] for x in aft]))}초입니다. "
          "25장 Lot 하나가 14.8시간에서 5시간으로 줄었습니다. 10/8 'TEST' Lot 은 다시 CR=Wafer 로 돌아 장당 2,091초 — 설정이 같으면 같은 시간이 나옵니다. "
          "같은 일이 AOI-23 RDL3 에도 있습니다: CR=Wafer 167장은 로딩 +522초, x20→x5 전환도 108초(CR=Lot 23초). G5 멀티 Job 에서 CR=Wafer 는 레시피마다 기준 촬영을 다시 해 장당 10~18분을 쓰는데, 구형 장비의 단일 Job 에서는 같은 설정이 장당 25~66초입니다.",
      data=dict(aoi25=[dict(day=x['day'][5:], lot=x['lot'], cr=x['cr'], load=x['load'], scan=x['scan'], wt=x['wt'], n=x['n']) for x in rows25],
                switch_by_cr=[dict(dev=x['dev'], cr=x['cr'], n=x['n'], switch=x['switch']) for x in a3['n3_settings'] if x['dev'] in ('AOI-23', 'AOI-25')],
                aoi23_rdl3=next((dict(dev=x['dev'], n_w=x['n_w'], delta_load=x['delta_load'], scan_w=x['scan_w'], scan_l=x['scan_l']) for x in cr['confounded'] if x['dev'] == 'AOI-23'), None)),
      takeaway="CR=Wafer 는 구형 장비에서는 장당 1분이지만 G5 멀티 Job 에서는 장당 10~18분입니다. AOI-25 는 10/4 에 이미 바꿔 RDL2 처리량이 3배가 됐고, AOI-23 RDL3 등 남은 G5 멀티 Job 의 CR=Wafer Lot 을 먼저 확인할 가치가 있습니다(스캔 시간도 같이 바뀌어 레시피 변경과 겹침)."))
out = dict(claims=claims, new=new)
s = json.dumps(out, ensure_ascii=False, indent=1)
open(f'{F}/audit.json', 'w', encoding='utf-8').write(s)
print(len(s.encode('utf-8')), 'bytes')
