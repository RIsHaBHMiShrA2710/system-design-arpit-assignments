from main import get_primary_connection, get_replica_connection, sync_replicas, read_users_primary, read_users_replica, write_user
import time
import threading

def clean_db():
    conn_primary = get_primary_connection()
    conn_replica = get_replica_connection()
    with conn_primary.cursor() as cursor:
        cursor.execute("DELETE FROM users")
    with conn_replica.cursor() as cursor:
        cursor.execute("DELETE FROM users")
    conn_primary.commit()
    conn_replica.commit()
    conn_primary.close()
    conn_replica.close()

# --- Single DB Benchmark ---

def single_db_writes(num_writes):
    for i in range(num_writes):
        write_user(f"User {i}", f"user{i}@example.com")

def single_db_reads(num_reads):
    for i in range(num_reads):
        read_users_primary()

def benchmark_single_db(num_reads, num_writes):
    clean_db()
    start_time = time.time()

    write_thread = threading.Thread(target=single_db_writes, args=(num_writes,))
    read_thread = threading.Thread(target=single_db_reads, args=(num_reads,))

    write_thread.start()
    read_thread.start()

    write_thread.join()
    read_thread.join()

    return time.time() - start_time

# --- Replica Benchmark ---

stop_sync = threading.Event()

def background_sync():
    # simulates continuous background replication
    while not stop_sync.is_set():
        sync_replicas()
        time.sleep(0.1)  # sync every 100ms, like replication lag

def replica_writes(num_writes):
    for i in range(num_writes):
        write_user(f"User {i}", f"user{i}@example.com")

def replica_reads(num_reads):
    for i in range(num_reads):
        read_users_replica()

def benchmark_with_replica(num_reads, num_writes):
    clean_db()
    stop_sync.clear()
    start_time = time.time()

    sync_thread = threading.Thread(target=background_sync)
    write_thread = threading.Thread(target=replica_writes, args=(num_writes,))
    read_thread = threading.Thread(target=replica_reads, args=(num_reads,))

    sync_thread.start()
    write_thread.start()
    read_thread.start()

    write_thread.join()
    read_thread.join()
    stop_sync.set()   # signal sync thread to stop
    sync_thread.join()

    return time.time() - start_time

# --- Scenarios ---

scenarios = [
    (100, 1),
    (100, 5),
    (100, 10),
    (400, 1),
    (400, 5),
    (400, 10),
]

def measure_staleness(num_reads, num_writes):
    clean_db()
    staleness_log = []
    stop_sync.clear()

    def writes():
        for i in range(num_writes):
            write_user(f"User {i}", f"user{i}@example.com")

    def reads():
        for i in range(num_reads):
            primary_count = len(read_users_primary())
            replica_count = len(read_users_replica())
            staleness_log.append(primary_count - replica_count)
            time.sleep(0.01)

    sync_thread = threading.Thread(target=background_sync)
    write_thread = threading.Thread(target=writes)
    read_thread = threading.Thread(target=reads)

    sync_thread.start()
    write_thread.start()
    read_thread.start()

    write_thread.join()
    read_thread.join()
    stop_sync.set()
    sync_thread.join()

    total_reads = len(staleness_log)
    fresh_reads = staleness_log.count(0)
    stale_reads = total_reads - fresh_reads
    avg_staleness = sum(staleness_log) / total_reads
    max_staleness = max(staleness_log)

    print(f"\nStaleness Report ({num_reads} reads, {num_writes} writes):")
    print(f"  Total reads:       {total_reads}")
    print(f"  Fresh reads:       {fresh_reads} ({(fresh_reads/total_reads)*100:.1f}%)")
    print(f"  Stale reads:       {stale_reads} ({(stale_reads/total_reads)*100:.1f}%)")
    print(f"  Avg staleness:     {avg_staleness:.2f} rows behind")
    print(f"  Max staleness:     {max_staleness} rows behind")
    print("-" * 40)

if __name__ == "__main__":
    # timing benchmarks
    for reads, writes in scenarios:
        print(f"Scenario: {reads} reads, {writes} writes")
        single_time = benchmark_single_db(reads, writes)
        replica_time = benchmark_with_replica(reads, writes)
        print(f"  Single DB:    {single_time:.4f}s")
        print(f"  With Replica: {replica_time:.4f}s")
        diff = single_time - replica_time
        faster = "Replica faster" if diff > 0 else "Single DB faster"
        print(f"  {faster} by {abs(diff):.4f}s")
        print("-" * 40)

    # staleness benchmarks
    for reads, writes in scenarios:
        measure_staleness(reads, writes)