# Analisis Keterlambatan Pengiriman dan Kepuasan Pelanggan (Olist)

Order yang telat dari estimasi dapat review rata-rata **2,57**, sedangkan yang tepat waktu **4,29**. Di projek ini saya cari tahu seberapa sering order telat, di mana masalahnya paling parah, dan seberapa besar efeknya ke review pelanggan.

![Dashboard](images/dashboard.png)

Dashboard interaktif: **[isi link GitHub Pages di sini]**

## Pertanyaan bisnis

Bayangkan saya analis di marketplace, dan manajemen minta tahu kenapa review jelek.

1. Berapa persen order yang telat, dan bagaimana tren per bulan?
2. Negara bagian mana yang paling sering telat?
3. Seberapa besar telat menurunkan skor review?
4. Kategori produk dan seller mana yang banyak telat?
5. Apakah ongkir berhubungan dengan telat?
6. Dari semua itu, mana yang paling layak ditindaklanjuti?

## Data

Brazilian E-Commerce Public Dataset by Olist (Kaggle), 9 tabel, sekitar 99 ribu order.

Yang saya analisis hanya order berstatus `delivered` dengan tanggal tiba terisi: **96.470 order**. Sisanya (canceled, shipped, unavailable, dan lain-lain) saya keluarkan karena belum atau tidak sampai ke pelanggan. 8 order delivered tanpa tanggal tiba juga dibuang.

Dua hal yang saya tangani saat pembersihan:
- 547 order punya lebih dari satu review. Saya ambil review terbaru per order, supaya hasil JOIN tidak menggandakan baris.
- 768 order tidak punya review. Mereka tetap ikut analisis keterlambatan, tapi tidak ikut analisis skor.

"Telat" artinya tanggal tiba lebih lambat dari tanggal estimasi yang diberikan Olist.

## Cara menjalankan ulang

```
pip install pandas matplotlib scipy
python load_data.py      # muat 9 CSV di data/raw ke olist.db
python run_analysis.py   # hasil ke images/, results/, dashboard/
```

## Metode

- **SQL (SQLite):** view bersih, JOIN banyak tabel, CTE, dan window function (`ROW_NUMBER` untuk review terbaru, `RANK` untuk seller).
- **Python (pandas, scipy):** uji statistik dan grafik.
- **Mann-Whitney U** untuk membandingkan skor review order telat vs tepat waktu. Skor review itu ordinal (1-5), jadi saya tidak pakai t-test.
- **Korelasi Spearman** antara jumlah hari telat dan skor review, karena alasan yang sama.
- Negara bagian dengan kurang dari 100 order, kategori kurang dari 100 order, dan seller kurang dari 50 order saya keluarkan. Sampel kecil bikin persentase ekstrem yang cuma kebetulan.

## Temuan

**Telat itu jarang, tapi dampaknya besar.** 7.826 dari 96.470 order telat (8,11%). Review rata-rata order tepat waktu 4,29 vs telat 2,57, selisih 1,73 poin. Review bintang 1 muncul di 6,6% order tepat waktu, tapi di 46,2% order telat.

**Efeknya bukan cuma signifikan secara statistik, tapi juga besar.** Mann-Whitney U menghasilkan p < 0,001, dan peluang review order tepat waktu lebih tinggi daripada review order telat adalah 77,7% (50% berarti tidak ada beda).

**Makin telat, makin jelek.** Di antara order yang telat saja, korelasi Spearman antara hari telat dan skor review adalah -0,52. Pelanggan bukan cuma marah karena telat, tapi makin marah kalau telatnya lama.

**Masalahnya terkonsentrasi di wilayah tertentu.** Tiga negara bagian teratas: AL (23,93%), MA (19,67%), PI (15,97%). AL hampir tiga kali rata-rata nasional.

**Kategori dan ongkir bukan penyebab utama.** Kategori tertinggi adalah audio (12,93%), fashion_underwear_beach (12,82%), dan books_technical (10,94%), selisihnya dari rata-rata nasional tidak besar. Median ongkir order telat 18,05 vs 17,07 tepat waktu. Selisih sekitar 1 real itu cuma terdeteksi signifikan karena sampelnya hampir 100 ribu, jadi secara praktis kecil.

## Rekomendasi

1. **Fokus perbaikan di AL, MA, dan PI.** Ini tempat keterlambatan paling parah. Kalau penyebabnya jarak dari seller, opsi yang masuk akal adalah menaikkan estimasi pengiriman untuk wilayah itu supaya janji ke pelanggan lebih realistis, atau mendorong seller yang lebih dekat.
2. **Kirim notifikasi proaktif begitu order lewat estimasi.** Karena makin lama telat makin jelek review-nya, komunikasi cepat dan kompensasi kecil pada order yang sudah telat berpotensi menahan penurunan review.
3. **Pantau seller yang rutin telat.** Daftar seller dengan persentase telat tertinggi ada di `results/seller_terburuk.csv`.

## Keterbatasan

- Ini hubungan, bukan bukti sebab-akibat. Review rendah bisa juga datang dari kualitas produk, bukan cuma telat.
- "Telat" diukur terhadap estimasi buatan Olist. Kalau estimasi untuk satu wilayah memang dibuat lebih ketat, persentase telatnya jadi kelihatan lebih tinggi.
- Saya belum menguji apakah jarak seller ke pelanggan penjelasan utama di AL, MA, dan PI. Itu masih dugaan.
- Order tanpa review tidak ikut analisis skor. Orang yang menulis review cenderung yang puas sekali atau kecewa sekali.

## Struktur repo

```
data/raw/        CSV asli (tidak di-commit)
sql/             query analisis
images/          grafik
results/         tabel hasil dan ringkasan
dashboard/       dashboard interaktif
load_data.py     memuat CSV ke SQLite
run_analysis.py  analisis, grafik, dashboard
```
