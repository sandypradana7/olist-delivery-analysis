"""
Analisis keterlambatan pengiriman Olist -> statistik, grafik, dan dashboard.

Cara pakai (dari folder olist-delivery-analysis):
    pip install pandas matplotlib scipy
    python run_analysis.py

Hasil:
    images/*.png               grafik untuk README
    results/*.csv              tabel hasil tiap pertanyaan bisnis
    results/ringkasan.md       angka-angka kunci untuk README
    dashboard/index.html       dashboard interaktif (buka dengan browser)
"""
import json
import sqlite3
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from scipy import stats

BASE = Path(__file__).resolve().parent
DB = BASE / "olist.db"
IMG = BASE / "images"
RES = BASE / "results"
DASH = BASE / "dashboard"
for p in (IMG, RES, DASH):
    p.mkdir(exist_ok=True)

MIN_ORDER_STATE = 100     # ambang minimum order agar persentase tidak menyesatkan
MIN_ORDER_KATEGORI = 100
MIN_ORDER_SELLER = 50
MIN_ORDER_BULAN = 100

if not DB.exists():
    raise SystemExit(f"olist.db tidak ditemukan di {DB}. Jalankan load_data.py dulu.")

conn = sqlite3.connect(DB)

# ---------------------------------------------------------------- 1. VIEW BERSIH
conn.executescript("""
DROP VIEW IF EXISTS temp.v_review_per_order;
DROP VIEW IF EXISTS temp.v_delivered;

CREATE TEMP VIEW v_review_per_order AS
SELECT order_id, review_score
FROM (
  SELECT order_id, review_score,
         ROW_NUMBER() OVER (
           PARTITION BY order_id
           ORDER BY review_answer_timestamp DESC, review_id DESC
         ) AS rn
  FROM order_reviews
)
WHERE rn = 1;

CREATE TEMP VIEW v_delivered AS
SELECT o.order_id, o.customer_id, o.order_purchase_timestamp,
       o.order_delivered_customer_date, o.order_estimated_delivery_date,
       CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date
            THEN 1 ELSE 0 END AS is_late,
       julianday(o.order_delivered_customer_date)
         - julianday(o.order_estimated_delivery_date) AS days_late
FROM orders o
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL;
""")


def q(sql, params=()):
    return pd.read_sql_query(sql, conn, params=params)


# ---------------------------------------------------------------- 2. QUERY ANALISIS
kpi = q("""
SELECT COUNT(*) AS n, SUM(is_late) AS telat,
       ROUND(100.0 * SUM(is_late) / COUNT(*), 2) AS pct_telat
FROM v_delivered
""").iloc[0]

state = q("""
SELECT c.customer_state AS state, COUNT(*) AS total_order, SUM(d.is_late) AS telat,
       ROUND(100.0 * SUM(d.is_late) / COUNT(*), 2) AS pct_telat
FROM v_delivered d JOIN customers c ON d.customer_id = c.customer_id
GROUP BY c.customer_state
HAVING COUNT(*) >= ?
ORDER BY pct_telat DESC
""", (MIN_ORDER_STATE,))

bulanan = q("""
SELECT strftime('%Y-%m', order_purchase_timestamp) AS bulan,
       COUNT(*) AS total_order, SUM(is_late) AS telat,
       ROUND(100.0 * SUM(is_late) / COUNT(*), 2) AS pct_telat
FROM v_delivered
GROUP BY bulan HAVING COUNT(*) >= ?
ORDER BY bulan
""", (MIN_ORDER_BULAN,))

review_telat = q("""
SELECT d.is_late, COUNT(*) AS n_order, ROUND(AVG(r.review_score), 2) AS rata_review
FROM v_delivered d JOIN v_review_per_order r ON d.order_id = r.order_id
GROUP BY d.is_late
""")

kelompok = q("""
SELECT CASE WHEN d.days_late <= 0 THEN '1. Tepat waktu'
            WHEN d.days_late <= 3 THEN '2. Telat 0-3 hari'
            WHEN d.days_late <= 7 THEN '3. Telat 3-7 hari'
            ELSE '4. Telat >7 hari' END AS kelompok,
       COUNT(*) AS n_order, ROUND(AVG(r.review_score), 2) AS rata_review
FROM v_delivered d JOIN v_review_per_order r ON d.order_id = r.order_id
GROUP BY kelompok ORDER BY kelompok
""")

kategori = q("""
WITH ok AS (
  SELECT DISTINCT d.order_id, d.is_late,
         COALESCE(t.product_category_name_english, p.product_category_name, 'unknown') AS kategori
  FROM v_delivered d
  JOIN order_items oi ON d.order_id = oi.order_id
  JOIN products p ON oi.product_id = p.product_id
  LEFT JOIN product_category_name_translation t
         ON p.product_category_name = t.product_category_name
)
SELECT kategori, COUNT(*) AS total_order,
       ROUND(100.0 * SUM(is_late) / COUNT(*), 2) AS pct_telat
FROM ok GROUP BY kategori HAVING COUNT(*) >= ?
ORDER BY pct_telat DESC
""", (MIN_ORDER_KATEGORI,))

seller = q("""
WITH so AS (
  SELECT DISTINCT d.order_id, oi.seller_id, d.is_late
  FROM v_delivered d JOIN order_items oi ON d.order_id = oi.order_id
),
agg AS (
  SELECT seller_id, COUNT(*) AS total_order,
         ROUND(100.0 * SUM(is_late) / COUNT(*), 2) AS pct_telat
  FROM so GROUP BY seller_id HAVING COUNT(*) >= ?
)
SELECT RANK() OVER (ORDER BY pct_telat DESC) AS peringkat, seller_id, total_order, pct_telat
FROM agg ORDER BY peringkat LIMIT 20
""", (MIN_ORDER_SELLER,))

# data tingkat order untuk uji statistik
orders_df = q("""
WITH ongkir AS (SELECT order_id, SUM(freight_value) AS ongkir FROM order_items GROUP BY order_id)
SELECT d.order_id, d.is_late, d.days_late, r.review_score, o.ongkir
FROM v_delivered d
LEFT JOIN v_review_per_order r ON d.order_id = r.order_id
LEFT JOIN ongkir o ON d.order_id = o.order_id
""")

# tabel fakta teragregasi untuk dashboard (state x bulan x kelompok telat)
facts = q("""
SELECT c.customer_state AS state,
       strftime('%Y-%m', d.order_purchase_timestamp) AS bulan,
       CASE WHEN d.days_late <= 0 THEN 0 WHEN d.days_late <= 3 THEN 1
            WHEN d.days_late <= 7 THEN 2 ELSE 3 END AS kelompok,
       COUNT(*) AS orders,
       COALESCE(SUM(r.review_score), 0) AS review_sum,
       COUNT(r.review_score) AS review_n
FROM v_delivered d
JOIN customers c ON d.customer_id = c.customer_id
LEFT JOIN v_review_per_order r ON d.order_id = r.order_id
GROUP BY 1, 2, 3
""")
bulan_valid = set(bulanan["bulan"])
facts = facts[facts["bulan"].isin(bulan_valid)]

# ---------------------------------------------------------------- 3. UJI STATISTIK
rv = orders_df.dropna(subset=["review_score"])
late_sc = rv.loc[rv.is_late == 1, "review_score"]
ontime_sc = rv.loc[rv.is_late == 0, "review_score"]

mw = stats.mannwhitneyu(late_sc, ontime_sc, alternative="two-sided")
cles_late_higher = mw.statistic / (len(late_sc) * len(ontime_sc))  # P(telat > tepat), ties = 0.5
p_ontime_higher = 1 - cles_late_higher

sp_all = stats.spearmanr(rv["days_late"], rv["review_score"])
late_only = rv[rv.is_late == 1]
sp_late = stats.spearmanr(late_only["days_late"], late_only["review_score"])

fr = orders_df.dropna(subset=["ongkir"])
mw_fr = stats.mannwhitneyu(
    fr.loc[fr.is_late == 1, "ongkir"], fr.loc[fr.is_late == 0, "ongkir"], alternative="two-sided"
)
med_fr_late = fr.loc[fr.is_late == 1, "ongkir"].median()
med_fr_ontime = fr.loc[fr.is_late == 0, "ongkir"].median()

rata_telat = late_sc.mean()
rata_tepat = ontime_sc.mean()
selisih = rata_tepat - rata_telat
pct_review_1_telat = 100 * (late_sc == 1).mean()
pct_review_1_tepat = 100 * (ontime_sc == 1).mean()

# ---------------------------------------------------------------- 4. EXPORT CSV
state.to_csv(RES / "telat_per_state.csv", index=False)
bulanan.to_csv(RES / "tren_bulanan.csv", index=False)
review_telat.to_csv(RES / "review_telat_vs_tepat.csv", index=False)
kelompok.to_csv(RES / "review_per_kelompok.csv", index=False)
kategori.to_csv(RES / "telat_per_kategori.csv", index=False)
seller.to_csv(RES / "seller_terburuk.csv", index=False)

# ---------------------------------------------------------------- 5. GRAFIK PNG
plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False})
MERAH, BIRU, ABU = "#d1495b", "#2e6f95", "#9aa5b1"

# 5a. telat per negara bagian
top = state.head(10).iloc[::-1]
fig, ax = plt.subplots(figsize=(8, 5))
ax.barh(top["state"], top["pct_telat"], color=MERAH)
ax.axvline(kpi.pct_telat, color=ABU, ls="--")
ax.text(kpi.pct_telat, -0.9, f" rata-rata nasional {kpi.pct_telat:.1f}%", color="#555", fontsize=8, va="top")
for y, v in enumerate(top["pct_telat"]):
    ax.text(v + 0.2, y, f"{v:.1f}%", va="center", fontsize=8)
ax.set_title(f"{state.iloc[0]['state']} punya persentase telat tertinggi: {state.iloc[0]['pct_telat']:.1f}%", loc="left")
ax.set_xlabel("% order telat dari estimasi")
fig.tight_layout(); fig.savefig(IMG / "01_telat_per_state.png"); plt.close(fig)

# 5b. tren bulanan
fig, ax = plt.subplots(figsize=(9, 4.5))
ax.plot(bulanan["bulan"], bulanan["pct_telat"], color=BIRU, marker="o", ms=3)
ax.set_title("Persentase order telat per bulan pembelian", loc="left")
ax.set_ylabel("% telat")
ax.set_xticks(range(0, len(bulanan), 2))
ax.set_xticklabels(bulanan["bulan"].iloc[::2], rotation=60, ha="right", fontsize=8)
fig.tight_layout(); fig.savefig(IMG / "02_tren_bulanan.png"); plt.close(fig)

# 5c. review per kelompok keterlambatan
fig, ax = plt.subplots(figsize=(7, 4.5))
warna = [BIRU, "#e0a458", "#e07a5f", MERAH]
ax.bar(kelompok["kelompok"].str[3:], kelompok["rata_review"], color=warna)
for i, v in enumerate(kelompok["rata_review"]):
    ax.text(i, v + 0.05, f"{v:.2f}", ha="center", fontsize=9)
ax.set_ylim(0, 5)
ax.set_title(f"Order telat menurunkan skor review sekitar {selisih:.1f} poin", loc="left")
ax.set_ylabel("Rata-rata skor review (1-5)")
plt.setp(ax.get_xticklabels(), rotation=15)
fig.tight_layout(); fig.savefig(IMG / "03_review_per_kelompok.png"); plt.close(fig)

# 5d. kategori paling sering telat
tk = kategori.head(10).iloc[::-1]
fig, ax = plt.subplots(figsize=(8, 5))
ax.barh(tk["kategori"], tk["pct_telat"], color=MERAH)
ax.axvline(kpi.pct_telat, color=ABU, ls="--")
ax.set_title("10 kategori produk dengan persentase telat tertinggi", loc="left")
ax.set_xlabel("% order telat")
fig.tight_layout(); fig.savefig(IMG / "04_telat_per_kategori.png"); plt.close(fig)

# ---------------------------------------------------------------- 6. RINGKASAN
def fmt_p(p):
    return "< 0,001" if p < 0.001 else f"{p:.3f}".replace(".", ",")

ringkasan = f"""# Ringkasan hasil analisis

## Basis data
- Order dianalisis (status delivered + tanggal tiba terisi): **{int(kpi.n):,}**
- Order telat dari estimasi: **{int(kpi.telat):,} ({kpi.pct_telat:.2f}%)**
- Order dengan review dianalisis: {len(rv):,} (satu review terbaru per order)

## Temuan utama
1. Rata-rata review order **tepat waktu {rata_tepat:.2f}** vs **telat {rata_telat:.2f}**, selisih {selisih:.2f} poin.
2. Review bintang 1: {pct_review_1_tepat:.1f}% pada order tepat waktu vs {pct_review_1_telat:.1f}% pada order telat.
3. Negara bagian telat tertinggi: {', '.join(state.head(3)['state'] + ' (' + state.head(3)['pct_telat'].astype(str) + '%)')}.
4. Kategori telat tertinggi: {', '.join(kategori.head(3)['kategori'] + ' (' + kategori.head(3)['pct_telat'].astype(str) + '%)')}.

## Uji statistik
- Mann-Whitney U, skor review telat vs tepat waktu: p = {fmt_p(mw.pvalue)}.
  Peluang review order tepat waktu lebih tinggi dari order telat = {100*p_ontime_higher:.1f}% (efek ukuran; 50% berarti tidak ada beda).
- Spearman, hari keterlambatan vs skor review (semua order): rho = {sp_all.statistic:.3f}, p = {fmt_p(sp_all.pvalue)}.
- Spearman, hanya order telat: rho = {sp_late.statistic:.3f}, p = {fmt_p(sp_late.pvalue)}.
- Ongkir (Mann-Whitney U): median telat {med_fr_late:.2f} vs tepat waktu {med_fr_ontime:.2f}, p = {fmt_p(mw_fr.pvalue)}.

## Catatan interpretasi (tulis di README)
- Ini hubungan, bukan bukti sebab-akibat: review rendah bisa juga dipengaruhi kualitas produk.
- Dengan puluhan ribu order, p-value hampir selalu kecil. Lihat ukuran efek, jangan hanya p-value.
- Negara bagian < {MIN_ORDER_STATE} order, kategori < {MIN_ORDER_KATEGORI}, seller < {MIN_ORDER_SELLER} dikeluarkan agar persentase tidak ekstrem karena sampel kecil.
- Order tanpa review tidak ikut analisis skor, tetapi tetap ikut analisis keterlambatan.
"""
(RES / "ringkasan.md").write_text(ringkasan, encoding="utf-8")

# ---------------------------------------------------------------- 7. DASHBOARD HTML
payload = {
    "kpi": {"n": int(kpi.n), "telat": int(kpi.telat), "pct": float(kpi.pct_telat)},
    "state": state.to_dict(orient="records"),
    "kategori": kategori.head(10).to_dict(orient="records"),
    "facts": facts.to_dict(orient="records"),
    "stat": {
        "rata_tepat": round(float(rata_tepat), 2),
        "rata_telat": round(float(rata_telat), 2),
        "p_mw": fmt_p(mw.pvalue),
        "efek": round(100 * float(p_ontime_higher), 1),
        "rho": round(float(sp_all.statistic), 3),
    },
    "min_state": MIN_ORDER_STATE,
}

HTML = r"""<!doctype html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Dashboard Keterlambatan Pengiriman Olist</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
:root{--bg:#f5f7fa;--card:#fff;--tx:#1f2933;--mut:#6b7785;--bd:#e3e8ee;--red:#d1495b;--blue:#2e6f95;--amb:#e0a458}
@media (prefers-color-scheme:dark){:root{--bg:#12161b;--card:#1b2128;--tx:#e6eaee;--mut:#97a3b0;--bd:#2a323b}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--tx);font:15px/1.5 system-ui,Segoe UI,Roboto,sans-serif}
.wrap{max-width:1150px;margin:0 auto;padding:20px 16px 40px}
h1{font-size:22px;margin:0 0 4px}
.sub{color:var(--mut);margin:0 0 16px}
.bar{display:flex;gap:10px;align-items:center;margin-bottom:16px;flex-wrap:wrap}
select{padding:7px 10px;border-radius:8px;border:1px solid var(--bd);background:var(--card);color:var(--tx);font:inherit}
.grid{display:grid;gap:14px}
.kpis{grid-template-columns:repeat(4,1fr)}
.two{grid-template-columns:1fr 1fr;margin-top:14px}
.card{background:var(--card);border:1px solid var(--bd);border-radius:12px;padding:14px 16px}
.kpi .l{color:var(--mut);font-size:13px}
.kpi .v{font-size:28px;font-weight:650;margin-top:2px}
.card h2{font-size:15px;margin:0 0 10px}
.box{position:relative;height:300px}
.note{color:var(--mut);font-size:13px;margin-top:8px}
ul{margin:6px 0 0;padding-left:18px}
@media(max-width:800px){.kpis{grid-template-columns:1fr 1fr}.two{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="wrap">
  <h1>Keterlambatan Pengiriman &amp; Kepuasan Pelanggan</h1>
  <p class="sub">Olist Brazilian E-Commerce. Hanya order berstatus delivered dengan tanggal tiba terisi.</p>

  <div class="bar">
    <label for="f">Negara bagian:</label>
    <select id="f"></select>
  </div>

  <div class="grid kpis">
    <div class="card kpi"><div class="l">Total order</div><div class="v" id="k1"></div></div>
    <div class="card kpi"><div class="l">Order telat</div><div class="v" id="k2"></div></div>
    <div class="card kpi"><div class="l">% telat</div><div class="v" id="k3"></div></div>
    <div class="card kpi"><div class="l">Rata-rata review</div><div class="v" id="k4"></div></div>
  </div>

  <div class="grid two">
    <div class="card"><h2>Tren % telat per bulan pembelian</h2><div class="box"><canvas id="c1"></canvas></div></div>
    <div class="card"><h2>Skor review menurut tingkat keterlambatan</h2><div class="box"><canvas id="c2"></canvas></div></div>
  </div>
  <div class="grid two">
    <div class="card"><h2>% telat per negara bagian (10 tertinggi)</h2><div class="box"><canvas id="c3"></canvas></div>
      <div class="note" id="n3"></div></div>
    <div class="card"><h2>10 kategori produk paling sering telat</h2><div class="box"><canvas id="c4"></canvas></div></div>
  </div>

  <div class="card" style="margin-top:14px">
    <h2>Temuan statistik</h2>
    <ul id="stat"></ul>
    <div class="note">Hubungan, bukan bukti sebab-akibat. Grafik negara bagian dan kategori tidak mengikuti filter.</div>
  </div>
</div>

<script>
const D = __DATA__;
const nf = new Intl.NumberFormat('id-ID');
const GR = ['Tepat waktu','Telat 0-3 hari','Telat 3-7 hari','Telat >7 hari'];
const COL = ['#2e6f95','#e0a458','#e07a5f','#d1495b'];
const sel = document.getElementById('f');
sel.innerHTML = '<option value="ALL">Semua</option>' +
  [...new Set(D.facts.map(r=>r.state))].sort().map(s=>`<option>${s}</option>`).join('');

const lineC = new Chart(c1, {type:'line', data:{labels:[],datasets:[{data:[],borderColor:'#2e6f95',tension:.25,pointRadius:2}]},
  options:{maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{y:{beginAtZero:true,title:{display:true,text:'% telat'}}}}});
const revC = new Chart(c2, {type:'bar', data:{labels:GR,datasets:[{data:[],backgroundColor:COL}]},
  options:{maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{y:{min:0,max:5,title:{display:true,text:'Rata-rata skor (1-5)'}}}}});
const topState = D.state.slice(0,10);
const stC = new Chart(c3, {type:'bar', data:{labels:topState.map(r=>r.state),datasets:[{data:topState.map(r=>r.pct_telat),backgroundColor:topState.map(()=>'#d1495b')}]},
  options:{indexAxis:'y',maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{title:{display:true,text:'% telat'}}}}});
new Chart(c4, {type:'bar', data:{labels:D.kategori.map(r=>r.kategori),datasets:[{data:D.kategori.map(r=>r.pct_telat),backgroundColor:'#d1495b'}]},
  options:{indexAxis:'y',maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{title:{display:true,text:'% telat'}}}}});
document.getElementById('n3').textContent = 'Hanya negara bagian dengan minimal ' + D.min_state + ' order.';

document.getElementById('stat').innerHTML = [
  `Rata-rata review order tepat waktu <b>${D.stat.rata_tepat}</b> vs telat <b>${D.stat.rata_telat}</b>.`,
  `Mann-Whitney U: p = ${D.stat.p_mw}. Peluang review order tepat waktu lebih tinggi daripada order telat: ${D.stat.efek}%.`,
  `Spearman hari telat vs skor review: rho = ${D.stat.rho}.`
].map(t=>`<li>${t}</li>`).join('');

function update(){
  const s = sel.value;
  const rows = D.facts.filter(r => s==='ALL' || r.state===s);
  let n=0, late=0, rs=0, rn=0;
  const byB = [0,0,0,0].map(()=>({rs:0,rn:0}));
  const byM = {};
  rows.forEach(r=>{
    n+=r.orders; if(r.kelompok>0) late+=r.orders;
    rs+=r.review_sum; rn+=r.review_n;
    byB[r.kelompok].rs+=r.review_sum; byB[r.kelompok].rn+=r.review_n;
    byM[r.bulan] = byM[r.bulan] || {o:0,l:0};
    byM[r.bulan].o += r.orders; if(r.kelompok>0) byM[r.bulan].l += r.orders;
  });
  k1.textContent = nf.format(n);
  k2.textContent = nf.format(late);
  k3.textContent = n ? (100*late/n).toFixed(2).replace('.',',')+'%' : '-';
  k4.textContent = rn ? (rs/rn).toFixed(2).replace('.',',') : '-';
  const months = Object.keys(byM).sort();
  lineC.data.labels = months;
  lineC.data.datasets[0].data = months.map(m=>+(100*byM[m].l/byM[m].o).toFixed(2));
  revC.data.datasets[0].data = byB.map(b=>b.rn>=20 ? +(b.rs/b.rn).toFixed(2) : null);
  lineC.update(); revC.update();
}
sel.addEventListener('change', update);
update();
</script>
</body>
</html>
"""

(DASH / "index.html").write_text(
    HTML.replace("__DATA__", json.dumps(payload, ensure_ascii=False)), encoding="utf-8"
)

conn.close()
print("Selesai.")
print(f"  Order dianalisis : {int(kpi.n):,} | telat {kpi.pct_telat}%")
print(f"  Review tepat/telat: {rata_tepat:.2f} vs {rata_telat:.2f} | MWU p = {fmt_p(mw.pvalue)}")
print("  Grafik   : images/")
print("  Tabel    : results/")
print("  Dashboard: dashboard/index.html (klik dua kali untuk membuka)")
