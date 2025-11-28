-- Run this daily to see what's happening
SELECT 
    date(created_at) as activity_date,
    COUNT(*) as new_items,
    SUM(CASE WHEN type = 'lost' THEN 1 ELSE 0 END) as lost_items,
    SUM(CASE WHEN type = 'found' THEN 1 ELSE 0 END) as found_items
FROM item
WHERE date(created_at) = date('now')
GROUP BY date(created_at);