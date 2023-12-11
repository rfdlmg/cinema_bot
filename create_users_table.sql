CREATE TABLE IF NOT EXISTS users (
    id serial PRIMARY KEY,
    user_id BIGINT UNIQUE,
    count_of_subscription INT DEFAULT 0,
    subscribe TIMESTAMP,
    is_attempt_spent BOOL DEFAULT FALSE
);
