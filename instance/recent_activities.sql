SELECT 
    u.username,
    i.title as activity,
    i.type as item_type, 
    i.status as item_status,
    i.created_at as activity_date,
    'item' as activity_type
FROM item i
JOIN user u ON i.user_id = u.id
UNION ALL
SELECT 
    u.username,
    n.message as activity,
    'notification' as item_type,
    CASE WHEN n.is_seen THEN 'read' ELSE 'unread' END as item_status,
    n.created_at as activity_date,
    'notification' as activity_type
FROM notification n
JOIN user u ON n.user_id = u.id
ORDER BY activity_date DESC
LIMIT 10;