# Analisis Keterlambatan Pengiriman pada E-Commerce Olist

Proyek ini menganalisis keterkaitan antara ketepatan waktu pengiriman dan penilaian pelanggan pada platform e-commerce Olist di Brasil. Berdasarkan hasil analisis, pesanan yang diterima setelah melewati estimasi waktu pengiriman memperoleh rata-rata skor ulasan sebesar 2,57, sedangkan pesanan yang sampai tepat waktu memperoleh rata-rata 4,29.

![Dashboard](images/dashboard.png)

## Tujuan Analisis

Analisis ini dilakukan untuk menjawab beberapa pertanyaan berikut:

1. Berapa proporsi pesanan yang mengalami keterlambatan, dan bagaimana perubahannya setiap bulan?

2. Negara bagian mana yang memiliki tingkat keterlambatan pengiriman tertinggi?

3. Seberapa besar perbedaan skor ulasan pelanggan antara pesanan yang terlambat dan yang tepat waktu?

4. Kategori produk dan penjual mana yang memiliki tingkat keterlambatan paling tinggi?

5. Apakah terdapat keterkaitan antara biaya pengiriman dan keterlambatan pesanan?

## Data yang Digunakan

Penelitian ini menggunakan Brazilian E-Commerce Public Dataset by Olist yang tersedia melalui Kaggle. Dataset tersebut terdiri atas sembilan tabel dengan jumlah data sekitar 99 ribu pesanan. Karena ukuran datanya cukup besar, file mentah tidak disertakan dalam repositori. Untuk menjalankan proyek ini, unduh dataset dari Kaggle dan simpan sembilan file CSV ke dalam direktori data/raw/.

Analisis difokuskan pada pesanan dengan status delivered dan memiliki informasi tanggal penerimaan. Setelah proses penyaringan, terdapat 96.470 pesanan yang dapat digunakan. Pesanan dengan status lain, seperti canceled, shipped, dan unavailable, dikeluarkan karena tidak memenuhi kriteria bahwa barang telah diterima pelanggan. Selain itu, delapan pesanan berstatus delivered tanpa tanggal penerimaan juga tidak disertakan.

Pemeriksaan kualitas data menemukan dua kondisi yang perlu ditangani. Sebanyak 547 pesanan memiliki lebih dari satu ulasan. Untuk mencegah penggandaan baris ketika menggabungkan tabel, hanya ulasan terbaru yang digunakan. Sementara itu, 768 pesanan tidak memiliki ulasan pelanggan. Data tersebut tetap digunakan untuk menganalisis keterlambatan pengiriman, tetapi dikecualikan dari analisis skor ulasan.

Dalam proyek ini, pesanan dikategorikan terlambat apabila tanggal penerimaannya melewati tanggal estimasi pengiriman yang ditetapkan oleh Olist.

## Metode dan Perangkat Analisis

Proses pengolahan data dan penyusunan query dilakukan menggunakan SQL dengan SQLite. Teknik yang digunakan meliputi pembuatan view, penggabungan beberapa tabel melalui JOIN, Common Table Expression (CTE), serta window function. Selanjutnya, Python dengan pustaka pandas, scipy, dan matplotlib digunakan untuk pengujian statistik, pembuatan visualisasi, serta pengembangan dashboard.

Skor ulasan pelanggan memiliki rentang 1–5 dan bersifat ordinal. Oleh karena itu, perbandingan skor antara kelompok pesanan terlambat dan tepat waktu dilakukan menggunakan uji Mann–Whitney U. Hubungan antara jumlah hari keterlambatan dan skor ulasan dianalisis menggunakan korelasi Spearman. Pendekatan ini dipilih karena lebih sesuai dengan karakteristik data dibandingkan penggunaan uji-t sebagai metode utama.

Untuk mengurangi risiko kesimpulan yang terlalu ekstrem akibat jumlah observasi yang terbatas, analisis juga menerapkan batas minimum jumlah pesanan. Negara bagian dan kategori produk dengan kurang dari 100 pesanan, serta penjual dengan kurang dari 50 pesanan, tidak dimasukkan dalam perbandingan yang bersangkutan.

## Hasil Analisis

Dari total 96.470 pesanan yang dianalisis, sebanyak 7.826 pesanan atau 8,11% mengalami keterlambatan pengiriman.

Terdapat perbedaan rata-rata skor ulasan yang cukup besar antara kedua kelompok. Pesanan yang tiba tepat waktu memperoleh rata-rata skor 4,29, sedangkan pesanan yang terlambat memperoleh rata-rata 2,57. Proporsi ulasan bintang satu mencapai 6,6% pada pesanan tepat waktu dan meningkat menjadi 46,2% pada pesanan terlambat. Hasil uji Mann–Whitney U menunjukkan nilai p kurang dari 0,001. Berdasarkan ukuran perbandingan probabilistik yang digunakan, kemungkinan sebuah pesanan tepat waktu memperoleh skor lebih tinggi daripada sebuah pesanan terlambat yang dipilih secara acak adalah sekitar 77,7%.

Analisis khusus terhadap pesanan terlambat juga menunjukkan hubungan negatif antara durasi keterlambatan dan skor ulasan. Nilai korelasi Spearman sebesar −0,52 mengindikasikan bahwa semakin lama keterlambatan, skor ulasan cenderung semakin rendah.

Berdasarkan wilayah, negara bagian dengan persentase keterlambatan tertinggi adalah AL sebesar 23,93%, MA sebesar 19,67%, dan PI sebesar 15,97%. Tingkat keterlambatan di AL hampir tiga kali lipat dibandingkan rata-rata nasional.

Perbedaan antar kategori produk relatif tidak sebesar perbedaan antarwilayah. Tiga kategori dengan persentase keterlambatan tertinggi adalah audio sebesar 12,93%, fashion_underwear_beach sebesar 12,82%, dan books_technical sebesar 10,94%. Angka tersebut setara dengan sekitar 1,3 hingga 1,6 kali rata-rata nasional.

Dari sisi biaya pengiriman, median biaya pada pesanan terlambat adalah 18,05 real Brasil, sedangkan pada pesanan tepat waktu sebesar 17,07 real Brasil. Perbedaan tersebut signifikan secara statistik dengan nilai p kurang dari 0,001. Namun, karena selisih median hanya sekitar satu real, hasil ini belum cukup untuk menyimpulkan bahwa biaya pengiriman merupakan penyebab keterlambatan.

## Rekomendasi

- Evaluasi pengiriman di wilayah prioritas. Negara bagian AL, MA, dan PI perlu mendapatkan perhatian lebih lanjut. Jika jarak pengiriman terbukti berperan, estimasi waktu pengiriman ke wilayah tersebut dapat    disesuaikan agar lebih realistis.

- Perkuat komunikasi kepada pelanggan. Notifikasi dapat diberikan ketika pesanan melewati estimasi waktu pengiriman, mengingat durasi keterlambatan berkaitan dengan penurunan skor ulasan.

- Lakukan evaluasi terhadap penjual. Penjual dengan frekuensi keterlambatan tinggi dapat ditinjau lebih lanjut menggunakan daftar yang tersedia pada results/seller_terburuk.csv.

## Keterbatasan Analisis

Temuan dalam proyek ini menunjukkan hubungan antarvariabel, bukan bukti bahwa keterlambatan secara langsung menyebabkan rendahnya skor ulasan. Penilaian pelanggan juga dapat dipengaruhi oleh faktor lain, termasuk kualitas produk.

Dugaan bahwa jarak antara penjual dan pelanggan menjadi penyebab tingginya keterlambatan di AL, MA, dan PI belum diuji secara langsung dalam analisis ini.

Selain itu, pesanan tanpa ulasan tidak dilibatkan dalam perhitungan skor pelanggan. Karena pelanggan yang memberikan ulasan mungkin memiliki pengalaman yang sangat memuaskan atau mengecewakan, hasil analisis skor dapat mengandung bias akibat karakteristik responden yang memberikan ulasan.

## Cara Menjalankan Proyek

```
pip install pandas matplotlib scipy
python load_data.py      # muat 9 CSV di data/raw ke olist.db
python run_analysis.py   # hasil ke images/, results/, dashboard/
```

## Isi repo

```
sql/             query analisis
images/          grafik
results/         tabel hasil dan ringkasan
dashboard/       dashboard interaktif
load_data.py     memuat CSV ke SQLite
run_analysis.py  analisis, grafik, dashboard
```
