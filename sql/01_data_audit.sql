-- Audit kualitas data Olist. Jalankan sebelum analisis.
-- Hasil: 99.441 order unik; 96.478 delivered; 8 delivered tanpa tanggal tiba;
-- 547 order dengan review ganda; 768 order tanpa review; 0 tanggal janggal.

-- 1. Apakah order_id unik?
SELECT COUNT(*) AS total_baris, COUNT(DISTINCT order_id) AS order_unik FROM orders;

-- 2. Ringkasan masalah data dan sebaran status
SELECT 'status_' || order_status AS cek, COUNT(*) AS n
FROM orders GROUP BY order_status
UNION ALL
SELECT 'delivered_tanpa_tanggal', COUNT(*)
FROM orders
WHERE order_status = 'delivered' AND order_delivered_customer_date IS NULL
UNION ALL
SELECT 'order_review_ganda', COUNT(*)
FROM (SELECT order_id FROM order_reviews GROUP BY order_id HAVING COUNT(*) > 1)
UNION ALL
SELECT 'order_tanpa_review', COUNT(*)
FROM orders o
WHERE NOT EXISTS (SELECT 1 FROM order_reviews r WHERE r.order_id = o.order_id)
UNION ALL
SELECT 'tanggal_janggal', COUNT(*)
FROM orders
WHERE order_delivered_customer_date < order_purchase_timestamp;
