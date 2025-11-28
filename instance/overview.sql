-- System Overview
SELECT 
    (SELECT COUNT(*) FROM user) as total_users,
    (SELECT COUNT(*) FROM item) as total_items,
    (SELECT COUNT(*) FROM item WHERE type = 'lost') as lost_items,
    (SELECT COUNT(*) FROM item WHERE type = 'found') as found_items,
    (SELECT COUNT(*) FROM notification) as total_notifications,
    (SELECT COUNT(*) FROM notification WHERE is_seen = 0) as unread_notifications;