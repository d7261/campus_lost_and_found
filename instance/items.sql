SELECT u.username, i.title, i.type, i.status, i.created_at
FROM item i 
JOIN user u ON i.user_id = u.id
ORDER BY i.created_at DESC;