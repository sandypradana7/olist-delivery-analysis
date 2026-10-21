# Ringkasan hasil analisis

## Basis data
- Order dianalisis (status delivered + tanggal tiba terisi): **96,470**
- Order telat dari estimasi: **7,826 (8.11%)**
- Order dengan review dianalisis: 95,824 (satu review terbaru per order)

## Temuan utama
1. Rata-rata review order **tepat waktu 4.29** vs **telat 2.57**, selisih 1.73 poin.
2. Review bintang 1: 6.6% pada order tepat waktu vs 46.2% pada order telat.
3. Negara bagian telat tertinggi: AL (23.93%), MA (19.67%), PI (15.97%).
4. Kategori telat tertinggi: audio (12.93%), fashion_underwear_beach (12.82%), books_technical (10.94%).

## Uji statistik
- Mann-Whitney U, skor review telat vs tepat waktu: p = < 0,001.
  Peluang review order tepat waktu lebih tinggi dari order telat = 77.7% (efek ukuran; 50% berarti tidak ada beda).
- Spearman, hari keterlambatan vs skor review (semua order): rho = -0.176, p = < 0,001.
- Spearman, hanya order telat: rho = -0.521, p = < 0,001.
- Ongkir (Mann-Whitney U): median telat 18.05 vs tepat waktu 17.07, p = < 0,001.

## Catatan interpretasi (tulis di README)
- Ini hubungan, bukan bukti sebab-akibat: review rendah bisa juga dipengaruhi kualitas produk.
- Dengan puluhan ribu order, p-value hampir selalu kecil. Lihat ukuran efek, jangan hanya p-value.
- Negara bagian < 100 order, kategori < 100, seller < 50 dikeluarkan agar persentase tidak ekstrem karena sampel kecil.
- Order tanpa review tidak ikut analisis skor, tetapi tetap ikut analisis keterlambatan.
