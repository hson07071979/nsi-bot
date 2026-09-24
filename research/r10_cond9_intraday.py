# -*- coding: utf-8 -*-
"""R10 — Is Condition 9 (OrdImb) observable DURING the session? (measured 24/09/2026)
Inputs: probe logs in OBS dir (FireAnt HistoricalQuotes/Markets/Quotes, Vietstock
gettradingresult for the whole live universe, CafeF, hnx.vn). Output:
evidence/audit_cond9_intraday.json and audit_summary.json['cond9_obs'/'cond9_intraday']."""
import json, os, sys, csv, subprocess, datetime as dt
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT)
OBS = sys.argv[1] if len(sys.argv) > 1 else '/home/claude/obs'
DAY = '2026-09-24'
L = lambda f: [json.loads(l) for l in open(os.path.join(OBS, f)) if l.strip()]
fa = [r for r in L('ordimb_obs.jsonl') if r['at'].startswith(DAY)]
ms = [r for r in L('multisource_obs.jsonl') if r['at'].startswith(DAY)]
vs = [r for r in L('vs_obs.jsonl') if r['at'].startswith(DAY)]
EX = {r['symbol']: r['exchange'] for r in csv.DictReader(open('data/by_exchange.csv'))}
rows = []
for r in fa:
    rows.append(dict(at=r['at'][11:16], source='FireAnt HistoricalQuotes', expected=r['expected'], received=r['received'],
                     has_BuyQuantity=r['has_BuyQuantity'], has_BuyCount=r['has_BuyCount'], has_SellCount=r['has_SellCount'],
                     ordimb_avail=r['ordimb_avail'], ordimb_cov=r['ordimb_cov']))
for r in ms:
    q = r['src'].get('fireant_quotes') or {}
    if 'received' in q:
        rows.append(dict(at=r['at'][11:16], source='FireAnt Markets/Quotes', expected=120, received=q['received'],
                         has_BuyQuantity=None, has_BuyCount=sum(1 for v in (q.get('ref_counts') or {}).values() if v and v[0]),
                         has_SellCount=None, ordimb_avail=q['ordimb'], ordimb_cov=round(q['ordimb'] / 120, 3)))
for r in ms:
    v = r['src'].get('vietstock') or {}
    if 'HPG' in v:
        hose = [k for k in v if EX.get(k) == 'HSX']; hnx = [k for k in v if EX.get(k) != 'HSX']
        rows.append(dict(at=r['at'][11:16], source='Vietstock mẫu (HPG FPT SSI | SHS PVS)', expected=len(v), received=len(v),
                         has_BuyQuantity=None, has_BuyCount=sum(1 for k in v if v[k].get('oi')), has_SellCount=None,
                         ordimb_avail=sum(1 for k in v if v[k].get('oi')), ordimb_cov=round(sum(1 for k in v if v[k].get('oi')) / len(v), 3),
                         by_board={'HSX': '%d/%d' % (sum(1 for k in hose if v[k].get('oi')), len(hose)),
                                   'HNX': '%d/%d' % (sum(1 for k in hnx if v[k].get('oi')), len(hnx))},
                         sample={k: v[k].get('oi') for k in v}))
for r in vs:
    by = r['vietstock_by_board']; n = sum(b['n'] for b in by.values()); oi = sum(b['ordimb'] for b in by.values())
    rows.append(dict(at=r['at'][11:16], source='Vietstock gettradingresult', expected=n, received=sum(b['row'] for b in by.values()),
                     has_BuyQuantity=None, has_BuyCount=oi, has_SellCount=oi, ordimb_avail=oi, ordimb_cov=round(oi / n, 3),
                     by_board={k: '%d/%d' % (v['ordimb'], v['n']) for k, v in by.items()},
                     cafef_hose=sum(1 for x in (r.get('cafef') or {}).values() if x), hnx_vn=sum(1 for x in (r.get('hnx') or {}).values() if x)))
rows = [x for x in rows if x['at'] >= '09:00']
rows.sort(key=lambda x: (x['at'], x['source']))
# engine entries by (current) board
D = json.load(open('data/site_data2.json'))
seen, board = set(), {}
for t in D['prod']['trades']:
    k = (t['sym'], t['entry'])
    if k not in seen:
        seen.add(k); b = EX.get(t['sym'], '?'); board[b] = board.get(b, 0) + 1
def first(pred, src):
    for x in rows:
        if x['source'] == src and pred(x): return x['at']
first_hose_counts = None
for r in vs:
    if r['vietstock_by_board'].get('HSX', {}).get('ordimb'): first_hose_counts = r['at'][11:16]; break
first_fa = first(lambda x: x['ordimb_avail'] > 0, 'FireAnt HistoricalQuotes')
pre = [x for x in rows if x['at'] < '14:45']
# EOD check: Vietstock intraday HNX/UPCoM vs the engine's definition (FireAnt EOD == hnx.vn)
fa_eod = [r for r in fa if r['ordimb_avail'] >= 100]
eod = None
if fa_eod and vs:
    fo = fa_eod[-1]['ordimb']; v0 = vs[0]['vietstock']; vN = vs[-1]['vietstock']
    hn = [s for s, x in v0.items() if x and x[5] and EX.get(s) != 'HSX']
    hose = [s for s, x in vN.items() if x and x[5] and EX.get(s) == 'HSX' and fo.get(s)]
    eod = dict(fireant_eod_at=fa_eod[-1]['at'][11:16], vietstock_eod_at=vs[-1]['at'][11:16],
               hnx_upcom={s: dict(vietstock_1506=v0[s][5], vietstock_eod=vN[s][5], fireant_eod=fo.get(s),
                                  hnx_vn=(vs[-1].get('hnx') or {}).get(s)) for s in hn},
               hnx_upcom_max_abs_diff_vs_engine=round(max(abs(v0[s][5] - fo[s]) for s in hn if fo.get(s)), 4),
               hnx_upcom_n_diff_gt_0_01=sum(1 for s in hn if fo.get(s) and abs(v0[s][5] - fo[s]) > 0.01),
               hose_vietstock_eod_vs_fireant_max_abs_diff=round(max(abs(vN[s][5] - fo[s]) for s in hose), 4),
               hose_n=len(hose))
res = dict(
    meta=dict(git_sha=subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip(),
              data_asof=D.get('asof'), prod_config_hash=D.get('prod_config_hash'),
              generated=dt.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'), experiment_version='audit-2026-09-23/r10',
              status='CURRENT', session=DAY),
    question='Có quan sát được OrdImb (BuyCount/SellCount) của phiên TRƯỚC 14:45 để báo MUA trong phiên không?',
    rows=rows,
    engine_entries_by_board=board,
    first_hose_counts_vietstock=first_hose_counts, first_ordimb_fireant=first_fa, eod_check=eod,
    findings=[
        'HOSE (106/120 mã của vũ trụ, %d/%d deal của bộ máy): trong phiên KHÔNG nguồn miễn phí nào có số LỆNH đặt '
        '(BuyCount/SellCount = 0 ở FireAnt HistoricalQuotes, FireAnt Markets/Quotes, Vietstock, CafeF); chỉ có khối lượng đặt '
        '(BuyQuantity/SellQuantity). OrdImb cần cả số lệnh nên KHÔNG tính được trước khi đóng cửa.' % (board.get('HSX', 0), sum(board.values())),
        'HNX + UPCoM (14/120 mã, %d deal): Vietstock gettradingresult có đủ 4 trường trong phiên (09:25 → 14:46), '
        'OrdImb thay đổi theo thời gian thực; FireAnt không có. NHƯNG so với số cuối ngày của bộ máy (FireAnt = hnx.vn) '
        'thì số Vietstock cho HNX/UPCoM KHÁC định nghĩa (13/14 mã lệch > 0,01, lệch tối đa %s) → KHÔNG dùng được cho Điều kiện 9.'
        % (board.get('HNX', 0) + board.get('UPCOM', 0), (eod or {}).get('hnx_upcom_max_abs_diff_vs_engine')),
        'Sau phiên: số lệnh HOSE chưa có lúc 15:45; có đủ 106/106 ở Vietstock và 120/120 ở FireAnt lúc 20:26 '
        '(23/09: FireAnt đủ lúc 18:02). Vietstock HOSE khớp FireAnt tuyệt đối (lệch tối đa %s).' % (eod or {}).get('hose_vietstock_eod_vs_fireant_max_abs_diff'),
        'Proxy thay thế (Simplize active ratio, KL mua/bán chủ động, KL đặt không có số lệnh) đã bị loại trước đó: tương quan hạng ≤ 0,36 với OrdImb.',
    ],
    decision='Giữ nguyên luật: live_scan chỉ báo SAP_DU/WAITING_FOR_FLOW_CONFIRMATION cho mã HOSE khi thiếu số lệnh, '
             'KHÔNG bao giờ MUA khi thiếu Điều kiện 9. Lệnh vào theo bộ máy (giá đóng cửa phiên tín hiệu) được xác nhận sau phiên '
             'khi nguồn EOD có số lệnh. Không đổi chiến lược.',
)
os.makedirs('evidence', exist_ok=True)
json.dump(res, open('evidence/audit_cond9_intraday.json', 'w'), ensure_ascii=False, indent=1)
S = json.load(open('evidence/audit_summary.json'))
S['cond9_obs'] = [dict(at=x['at'] + ' · ' + x['source'].split()[0] + (' ' + x['source'].split()[1] if x['source'].startswith('FireAnt') else ''),
                       received=x['received'], expected=x['expected'], has_BuyCount=x['has_BuyCount'], has_SellCount=x['has_SellCount'],
                       ordimb_avail=x['ordimb_avail'], ordimb_cov=x['ordimb_cov']) for x in rows if x['source'] != 'FireAnt Markets/Quotes']
S['cond9_intraday'] = dict(findings=res['findings'], decision=res['decision'], engine_entries_by_board=board,
                           first_hose_counts_vietstock=first_hose_counts, first_ordimb_fireant=first_fa, eod_check=eod)
json.dump(S, open('evidence/audit_summary.json', 'w'), ensure_ascii=False, indent=1)
print(json.dumps(dict(board=board, first_hose=first_hose_counts, first_fa=first_fa, n=len(rows), pre1445_any=sum(x['ordimb_avail'] for x in pre)), ensure_ascii=False))
