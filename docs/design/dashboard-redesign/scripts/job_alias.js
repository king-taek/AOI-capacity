/* JOB_ALIAS — 화면 표기명 21개.
 * 데이터 스크립트가 아니라 AOI-Dashboard.dc.html 의 로직 클래스 맨 위에 있습니다.
 * (aoi-data.json 에는 실제 Job 이름만 들어가고, 표기명은 화면에서만 씌웁니다)
 * 아래는 AOI-Dashboard.dc.html 488~509행을 그대로 옮긴 것입니다.
 *
 * 왼쪽 = 병합 그룹의 대표 이름(가장 많이 쓰인 실제 Job 이름)
 * 오른쪽 = 화면에 보일 이름
 * 여기 없는 Job 은 실제 이름을 고정폭 글꼴로 그대로 보여 줍니다.
 */
const JOB_ALIAS={
  "R_TB500_LIVE_PI3":"TB500 PI3",
  "R_TB500_LIVE_PI2":"TB500 PI2",
  "R_TB500_LIVE_PI4":"TB500 PI4",
  "R_ TB500 LIVE_0860154PD_BS UBM":"TB500 BS UBM",
  "R_TB500 LIVE_FS":"TB500 FS",
  "TB500_RDL4 - Multi":"TB500 RDL4",
  "R_TB500 LIVE_0860154PD_R-ETCH":"TB500 R-ETCH",
  "TB500_RDL3 - Multi":"TB500 RDL3",
  "TB500_RDL2 - Multi":"TB500 RDL2",
  "R_Kendall A0_PI4":"Kendall PI4",
  "R_Kendall A0_PI3":"Kendall PI3",
  "R_TB500 TOP D-DIE_0860312PD":"TB500 TOP D-DIE",
  "TB500_RDL1 - Multi":"TB500 RDL1",
  "TB500_RDL3 - Multi - Swelling":"TB500 RDL3 Swelling",
  "TB500_RDL4 - Multi - Swelling":"TB500 RDL4 Swelling",
  "R_TB500_LIVE_PI3 - Enhanced":"TB500 PI3 Enhanced",
  "R_KENDALL_A0_PI5":"Kendall PI5",
  "R_KENDALL_A0_FS":"Kendall FS",
  "R_KENDALL_A0_PI2":"Kendall PI2",
  "2D@RE-KENDALL A0 TOP DIE_0859659PD-0B":"Kendall TOP DIE",
  "R_MSFT_Kendall_0859275PD_BS-CAMTEK":"Kendall BS"};

if (typeof module !== 'undefined') module.exports = { JOB_ALIAS };
