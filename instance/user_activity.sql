SELECT 
    u.username,
    COUNT(i.id) as total_items,
    SUM(CASE WHEN i.type = 'lost' THEN 1 ELSE 0 END) as lost_items,
    SUM(CASE WHEN i.type = 'found' THEN 1 ELSE 0 END) as found_items
FROM user u
LEFT JOIN item i ON u.id = i.user_id
GROUP BY u.username;