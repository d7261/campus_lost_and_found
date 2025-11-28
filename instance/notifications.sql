SELECT u.username, n.message, n.is_seen, n.created_at
FROM notification n 
JOIN user u ON n.user_id = u.id
ORDER BY n.created_at DESC;
