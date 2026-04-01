from main import (
    clean_db,
    setup_all,
    write_user_single,
    write_user_sharded,
    read_user_single,
    read_user_sharded,
    get_shard_number,
    NUM_SHARDS,
)
import time
import threading
import random

# ─────────────────────────────────────────────
# Scenarios: (num_reads, num_writes)
# ─────────────────────────────────────────────

scenarios = [
    (100, 100),   # equal reads and writes
    (500, 100),   # read heavy
    (100, 500),   # write heavy
]


# ─────────────────────────────────────────────
# Single Shard Benchmark
# ─────────────────────────────────────────────

def single_shard_writes(num_writes):
    for i in range(num_writes):
        write_user_single(i, f"User {i}", f"user{i}@example.com")


def single_shard_reads(num_reads, max_id):
    for _ in range(num_reads):
        uid = random.randint(0, max_id - 1)
        read_user_single(uid)


def benchmark_single_shard(num_reads, num_writes):
    clean_db()

    start = time.time()

    write_thread = threading.Thread(target=single_shard_writes, args=(num_writes,))
    read_thread = threading.Thread(target=single_shard_reads, args=(num_reads, max(num_writes, 1)))

    write_thread.start()
    read_thread.start()

    write_thread.join()
    read_thread.join()

    return time.time() - start


# ─────────────────────────────────────────────
# Sharded Benchmark
# ─────────────────────────────────────────────

def sharded_writes(num_writes):
    for i in range(num_writes):
        write_user_sharded(i, f"User {i}", f"user{i}@example.com")


def sharded_reads(num_reads, max_id):
    for _ in range(num_reads):
        uid = random.randint(0, max_id - 1)
        read_user_sharded(uid)


def benchmark_sharded(num_reads, num_writes):
    clean_db()

    start = time.time()

    write_thread = threading.Thread(target=sharded_writes, args=(num_writes,))
    read_thread = threading.Thread(target=sharded_reads, args=(num_reads, max(num_writes, 1)))

    write_thread.start()
    read_thread.start()

    write_thread.join()
    read_thread.join()

    return time.time() - start


# ─────────────────────────────────────────────
# Run All Benchmarks
# ─────────────────────────────────────────────

if __name__ == "__main__":
    # Ensure tables exist on all databases
    setup_all()

    print("=" * 55)
    print("  SHARDING BENCHMARK — Single Shard vs 3 Shards")
    print("=" * 55)

    for num_reads, num_writes in scenarios:
        print(f"\n📊 Scenario: {num_reads} reads, {num_writes} writes")
        print("-" * 45)

        single_time = benchmark_single_shard(num_reads, num_writes)
        sharded_time = benchmark_sharded(num_reads, num_writes)

        print(f"  Single Shard : {single_time:.4f}s")
        print(f"  Sharded (x3) : {sharded_time:.4f}s")

        diff = single_time - sharded_time
        if diff > 0:
            print(f"  ✅ Sharded faster by {abs(diff):.4f}s ({abs(diff)/single_time*100:.1f}%)")
        else:
            print(f"  ⚠️  Single faster by {abs(diff):.4f}s ({abs(diff)/sharded_time*100:.1f}%)")

        # Show data distribution across shards
        print(f"\n  Shard distribution for {num_writes} users:")
        counts = [0] * NUM_SHARDS
        for uid in range(num_writes):
            counts[get_shard_number(uid)] += 1
        for s in range(NUM_SHARDS):
            bar = "█" * (counts[s] // 20)
            print(f"    shard_{s}: {counts[s]:>5} users  {bar}")

        print("-" * 45)
