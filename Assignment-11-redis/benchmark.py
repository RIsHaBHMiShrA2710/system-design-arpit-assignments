import time
from main import set_user, get_user, set_user_postgres, get_user_postgres
import redis

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# ─────────────────────────────────────────────
# Cleanup
# ─────────────────────────────────────────────

def clean_db():
    # Clear Redis
    r.flushdb()

    # Clear PostgreSQL
    from db import get_postgres_connection
    conn = get_postgres_connection()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM users;")
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
# Benchmarks
# ─────────────────────────────────────────────

def benchmark_writes(n):
    clean_db()

    # Redis writes
    start = time.perf_counter()
    for i in range(n):
        set_user(i, f"User {i}", f"user{i}@example.com")
    redis_time = time.perf_counter() - start

    clean_db()

    # PostgreSQL writes
    start = time.perf_counter()
    for i in range(n):
        set_user_postgres(i, f"User {i}", f"user{i}@example.com")
    postgres_time = time.perf_counter() - start

    return redis_time, postgres_time


def benchmark_reads(n):
    clean_db()

    # Seed data first
    for i in range(n):
        set_user(i, f"User {i}", f"user{i}@example.com")
        set_user_postgres(i, f"User {i}", f"user{i}@example.com")

    # Redis reads
    start = time.perf_counter()
    for i in range(n):
        get_user(i)
    redis_time = time.perf_counter() - start

    # PostgreSQL reads
    start = time.perf_counter()
    for i in range(n):
        get_user_postgres(i)
    postgres_time = time.perf_counter() - start

    return redis_time, postgres_time


def benchmark_mixed(n):
    clean_db()

    # Redis mixed
    start = time.perf_counter()
    for i in range(n):
        set_user(i, f"User {i}", f"user{i}@example.com")
    for i in range(n):
        get_user(i)
    redis_time = time.perf_counter() - start

    clean_db()

    # PostgreSQL mixed
    start = time.perf_counter()
    for i in range(n):
        set_user_postgres(i, f"User {i}", f"user{i}@example.com")
    for i in range(n):
        get_user_postgres(i)
    postgres_time = time.perf_counter() - start

    return redis_time, postgres_time


# ─────────────────────────────────────────────
# Helper — print comparison
# ─────────────────────────────────────────────

def print_result(label, redis_time, postgres_time):
    diff = postgres_time - redis_time
    faster = "Redis faster" if diff > 0 else "PostgreSQL faster"
    pct = abs(diff) / max(postgres_time, redis_time) * 100
    print(f"  {label}:")
    print(f"    Redis      : {redis_time:.4f}s")
    print(f"    PostgreSQL : {postgres_time:.4f}s")
    print(f"    {faster} by {abs(diff):.4f}s ({pct:.1f}%)")


# ─────────────────────────────────────────────
# Scenarios
# ─────────────────────────────────────────────

scenarios = [100, 200, 500]

if __name__ == "__main__":
    for n in scenarios:
        print(f"\n{'='*55}")
        print(f"📊 Scenario: {n} users")
        print(f"{'='*55}")
        print_result("Writes", *benchmark_writes(n))
        print_result("Reads ", *benchmark_reads(n))
        print_result("Mixed ", *benchmark_mixed(n))
        print(f"{'─'*55}")