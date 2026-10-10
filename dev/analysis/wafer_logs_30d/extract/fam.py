import re
def family(job):
    j=job.strip(); u=j.upper()
    if u.startswith('TEST'): return None
    m=re.search(r'TB500[_ ]?RDL\s*(\d)',u)
    if m: return f"TB500 RDL{m.group(1)}"+(" Swelling" if 'SWELLING' in u else "")
    m=re.search(r'KENDALL[_ ]A0[_ ]PI(\d)',u)
    if m: return f"Kendall PI{m.group(1)}"
    m=re.search(r'TB500_LIVE_PI(\d)',u)
    if m: return f"TB500 PI{m.group(1)}"+(" Enhanced" if 'ENHANCED' in u else "")
    return None
CATS=['검출 기준','광학','얼라인·포커스 설정','자동화·레시피 동작','분류','티칭 결과']
def category(key):
    f=key.split('[')[0].lower()
    if f in ('rtp.txt','globalrtp.ini','defectsclustering.ini'): return '검출 기준'
    if f.startswith('zones') or re.match(r'recipe\d-zones',f): return '검출 기준(Zone 원본)'
    if 'activescenariooptics' in f or f=='equipmentinfo.ini': return '광학(장비 고유)'
    if 'opticpreset' in f or f=='zoomlevels.ini': return '광학'
    if f.startswith('traindata') or f=='uniquearea.ini': return '티칭 결과'
    if f in('alignrtp.ini','params_alignrtp.ini','wafertype.ini') or f.startswith('focusmapping'): return '얼라인·포커스 설정'
    if f=='recipe.ini': return '자동화·레시피 동작'
    if 'classification' in f or f=='manreclassify.ini' or f=='equipmentclassifications.ini': return '분류'
    if f in('params_systeminfo.ini','machinestage2tablematrix.ini'): return '장비 보정'
    return '제품·기하·기타'
