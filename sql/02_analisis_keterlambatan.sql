-- Analisis keterlambatan pengiriman Olist.
-- Aturan pembersihan:
--   * hanya order 'delivered' dengan tanggal tiba terisi (96.470 order)
--   * order dengan review ganda: ambil review terbaru
-- Ambang minimum sampel: negara bagian/kategori >= 100 order, seller >= 50 order.

DROP VIEW IF EXISTS v_review_per_order;
DROP VIEW IF EXISTS v_delivered;

CREATE VIEW v_review_per_order AS
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

CREATE VIEW v_delivered AS
SELECT o.order_id,
       o.customer_id,
       o.order_purchase_timestamp,
       o.order_delivered_customer_date,
       o.order_estimated_delivery_date,
       CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date
            THEN 1 ELSE 0 END AS is_late,
       julianday(o.order_delivered_customer_date)
         - julianday(o.order_estimated_delivery_date) AS days_late
FROM orders o
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL;

-- 1. KPI utama
SELECT COUNT(*) AS n,
       SUM(is_late) AS telat,
       ROUND(100.0 * SUM(is_late) / COUNT(*), 2) AS pct_telat
FROM v_delivered;

-- 2. Telat per negara bagian
SELECT c.customer_state,
       COUNT(*) AS total_order,
       SUM(d.is_late) AS telat,
       ROUND(100.0 * SUM(d.is_late) / COUNT(*), 2) AS pct_telat
FROM v_delivered d
JOIN customers c ON d.customer_id = c.customer_id
GROUP BY c.customer_state
HAVING COUNT(*) >= 100
ORDER BY pct_telat DESC;

-- 3. Tren bulanan
SELECT strftime('%Y-%m', order_purchase_timestamp) AS bulan,
       COUNT(*) AS total_order,
       ROUND(100.0 * SUM(is_late) / COUNT(*), 2) AS pct_telat
FROM v_delivered
GROUP BY bulan
HAVING COUNT(*) >= 100
ORDER BY bulan;

-- 4. Review: telat vs tepat waktu
SELECT d.is_late,
       COUNT(*) AS n_order,
       ROUND(AVG(r.review_score), 2) AS rata_review
FROM v_delivered d
JOIN v_review_per_order r ON d.order_id = r.order_id
GROUP BY d.is_late;

-- 5. Review per tingkat keterlambatan
SELECT CASE WHEN d.days_late <= 0 THEN '1. Tepat waktu'
            WHEN d.days_late <= 3 THEN '2. Telat 0-3 hari'
            WHEN d.days_late <= 7 THEN '3. Telat 3-7 hari'
            ELSE '4. Telat > 7 hari' END AS kelompok,
       COUNT(*) AS n_order,
       ROUND(AVG(r.review_score), 2) AS rata_review
FROM v_delivered d
JOIN v_review_per_order r ON d.order_id = r.order_id
GROUP BY kelompok
ORDER BY kelompok;

-- 6. Kategori produk paling sering telat (CTE)
WITH order_kategori AS (
  SELECT DISTINCT d.order_id, d.is_late,
         COALESCE(t.product_category_name_english, p.product_category_name, 'unknown') AS kategori
  FROM v_delivered d
  JOIN order_items oi ON d.order_id = oi.order_id
  JOIN products p ON oi.product_id = p.product_id
  LEFT JOIN product_category_name_translation t
         ON p.product_category_name = t.product_category_name
)
SELECT kategori,
       COUNT(*) AS total_order,
       ROUND(100.0 * SUM(is_late) / COUNT(*), 2) AS pct_telat
FROM order_kategori
GROUP BY kategori
HAVING COUNT(*) >= 100
ORDER BY pct_telat DESC
LIMIT 15;

-- 7. Seller terburuk (CTE + window function)
WITH seller_orders AS (
  SELECT DISTINCT d.order_id, oi.seller_id, d.is_late
  FROM v_delivered d
  JOIN order_items oi ON d.order_id = oi.order_id
),
agg AS (
  SELECT seller_id,
         COUNT(*) AS total_order,
         ROUND(100.0 * SUM(is_late) / COUNT(*), 2) AS pct_telat
  FROM seller_orders
  GROUP BY seller_id
  HAVING COUNT(*) >= 50
)
SELECT RANK() OVER (ORDER BY pct_telat DESC) AS peringkat,
       seller_id, total_order, pct_telat
FROM agg
ORDER BY peringkat
LIMIT 20;

-- 8. Ongkir vs keterlambatan
WITH ongkir AS (
  SELECT order_id, SUM(freight_value) AS total_ongkir
  FROM order_items
  GROUP BY order_id
)
SELECT d.is_late,
       COUNT(*) AS n_order,
       ROUND(AVG(o.total_ongkir), 2) AS rata_ongkir
FROM v_delivered d
JOIN ongkir o ON d.order_id = o.order_id
GROUP BY d.is_late;
