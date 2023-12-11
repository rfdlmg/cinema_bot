UPDATE users
SET
    subscribe = CURRENT_TIMESTAMP,
    is_attempt_spent = TRUE
WHERE user_id = %s;