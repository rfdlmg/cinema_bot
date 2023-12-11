INSERT INTO users (user_id)
VALUES (%s)
ON CONFLICT (user_id) DO UPDATE
SET user_id = EXCLUDED.user_id
RETURNING user_id;
