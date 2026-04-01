import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables from the parent directory's .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

NUM_SHARDS = 3


# ─────────────────────────────────────────────
# 1. Connection Functions
# ─────────────────────────────────────────────

def get_single_shard_connection():
    """Connect to shard_0 acting as the single, un-sharded database."""
    return psycopg2.connect(
        host=os.getenv("SHARD_0_HOST"),
        port=os.getenv("SHARD_0_PORT"),
        dbname=os.getenv("SHARD_0_DB"),
        user=os.getenv("SHARD_0_USER"),
        password=os.getenv("SHARD_0_PASSWORD"),
    )


def get_shard_connection(shard_num):
    """Connect to a specific shard (0, 1, or 2)."""
    return psycopg2.connect(
        host=os.getenv(f"SHARD_{shard_num}_HOST"),
        port=os.getenv(f"SHARD_{shard_num}_PORT"),
        dbname=os.getenv(f"SHARD_{shard_num}_DB"),
        user=os.getenv(f"SHARD_{shard_num}_USER"),
        password=os.getenv(f"SHARD_{shard_num}_PASSWORD"),
    )


# ─────────────────────────────────────────────
# 2. The Router — Heart of Sharding
# ─────────────────────────────────────────────

def get_shard_number(id, num_shards=NUM_SHARDS):
    """
    Determine which shard a id belongs to using modulo hashing.

    Example:
        id=7,  num_shards=3  →  7 % 3 = 1  → shard_1
        id=12, num_shards=3  →  12 % 3 = 0  → shard_0
    """
    return id % num_shards


# ─────────────────────────────────────────────
# 3. Table Setup (helper)
# ─────────────────────────────────────────────

def create_users_table(conn):
    """Create the users table if it doesn't exist."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id  BIGINT PRIMARY KEY,
                name     VARCHAR(100),
                email    VARCHAR(255)
            );
        """)
    conn.commit()


def setup_all():
    """Create the users table on the single-shard DB and on every shard."""
    # Single-shard DB
    conn = get_single_shard_connection()
    create_users_table(conn)
    conn.close()

    # Each shard
    for shard in range(NUM_SHARDS):
        conn = get_shard_connection(shard)
        create_users_table(conn)
        conn.close()

    print("✅ All tables created successfully.")


def clean_db():
    """Truncate the users table on every shard (including shard_0 used as single DB)."""
    for shard in range(NUM_SHARDS):
        conn = get_shard_connection(shard)
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users;")
        conn.commit()
        conn.close()


# ─────────────────────────────────────────────
# 4. Write Functions
# ─────────────────────────────────────────────

def write_user_single(id, name, email):
    """Write a user to the single (un-sharded) database."""
    conn = get_single_shard_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (id, name, email) VALUES (%s, %s, %s) "
                "ON CONFLICT (id) DO NOTHING;",
                (id, name, email),
            )
        conn.commit()
    finally:
        conn.close()


def write_user_sharded(id, name, email):
    """Use the router to find the correct shard and write the user there."""
    shard = get_shard_number(id)
    conn = get_shard_connection(shard)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (id, name, email) VALUES (%s, %s, %s) "
                "ON CONFLICT (id) DO NOTHING;",
                (id, name, email),
            )
        conn.commit()
    finally:
        conn.close()


# ─────────────────────────────────────────────
# 5. Read Functions
# ─────────────────────────────────────────────

def read_user_single(id):
    """Read a user from the single (un-sharded) database."""
    conn = get_single_shard_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, email FROM users WHERE id = %s;",
                (id,),
            )
            return cur.fetchone()
    finally:
        conn.close()


def read_user_sharded(id):
    """Use the router to find the correct shard, then read the user."""
    shard = get_shard_number(id)
    conn = get_shard_connection(shard)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, email FROM users WHERE id = %s;",
                (id,),
            )
            return cur.fetchone()
    finally:
        conn.close()


# ─────────────────────────────────────────────
# 6. Demo / Quick Test
# ─────────────────────────────────────────────

if __name__ == "__main__":
    # Set up tables on all databases
    setup_all()

    # Sample users
    sample_users = [
        (1, "Alice",   "alice@example.com"),
        (2, "Bob",     "bob@example.com"),
        (3, "Charlie", "charlie@example.com"),
        (4, "Diana",   "diana@example.com"),
        (5, "Eve",     "eve@example.com"),
        (6, "Frank",   "frank@example.com"),
    ]

    # --- Write to SINGLE shard ---
    print("\n📝 Writing to single (un-sharded) DB …")
    for uid, name, email in sample_users:
        write_user_single(uid, name, email)
        print(f"   Wrote user {uid} ({name})")

    # --- Write to SHARDED DBs ---
    print("\n📝 Writing to sharded DBs …")
    for uid, name, email in sample_users:
        shard = get_shard_number(uid)
        write_user_sharded(uid, name, email)
        print(f"   Wrote user {uid} ({name}) → shard_{shard}")

    # --- Read from SINGLE shard ---
    print("\n📖 Reading from single DB …")
    for uid, _, _ in sample_users:
        row = read_user_single(uid)
        print(f"   id={uid} → {row}")

    # --- Read from SHARDED DBs ---
    print("\n📖 Reading from sharded DBs …")
    for uid, _, _ in sample_users:
        shard = get_shard_number(uid)
        row = read_user_sharded(uid)
        print(f"   id={uid} (shard_{shard}) → {row}")
