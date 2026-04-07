import redis
from db import get_postgres_connection
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

def set_user(user_id, name, email):
    user_key = f"user:{user_id}"
    r.hset(user_key, mapping={"name": name, "email": email})

def get_user(user_id):
    user_key = f"user:{user_id}"
    user_data = r.hgetall(user_key)
    if user_data:
        return user_data
    return None

def set_user_postgres(user_id, name, email):
    conn = get_postgres_connection()
    with conn.cursor() as cur:
        cur.execute("INSERT INTO users (id, name, email) VALUES (%s, %s, %s) ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, email = EXCLUDED.email;", (user_id, name, email))
    conn.commit()
    conn.close()

def get_user_postgres(user_id):
    conn = get_postgres_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT id, name, email FROM users WHERE id = %s;", (user_id,))
        result = cur.fetchone()  
    conn.close()                  
    return result                
