-- Uji dugaan: apakah order lintas negara bagian lebih sering telat?
-- Untuk order dengan beberapa seller, dipakai seller dengan seller_id terkecil (penyederhanaan).
SELECT CASE WHEN s.seller_state = c.customer_state
            THEN 'Satu negara bagian' ELSE 'Beda negara bagian' END AS rute,
       COUNT(*) AS n,
       ROUND(100.0 * SUM(CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date
                              THEN 1 ELSE 0 END) / COUNT(*), 2) AS pct_telat
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
JOIN (SELECT order_id, MIN(seller_id) AS seller_id FROM order_items GROUP BY order_id) oi
  ON o.order_id = oi.order_id
JOIN sellers s ON oi.seller_id = s.seller_id
WHERE o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL
GROUP BY rute;
