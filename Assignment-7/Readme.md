# Assignment 7 — Read Replicas (PostgreSQL)

## 📖 Concept

In a typical application, most traffic is **reads** (SELECT) and fewer are **writes** (INSERT/UPDATE/DELETE). A single database handling all of this becomes a bottleneck under load.

**Read Replicas** solve this by:
- Having one **Primary** server that handles all writes
- Having one or more **Replica** servers that sync from primary and handle all reads

```
Your App
   │
   ├── Writes (INSERT/UPDATE/DELETE) ──→ Primary DB
   └── Reads  (SELECT)              ──→ Replica DB
```

---

## 🛠️ Setup

### Prerequisites
- PostgreSQL installed locally
- pgAdmin installed
- Python 3.x
- Virtual environment activated

### Python Dependencies
```bash
pip install psycopg2-binary python-dotenv
```

### Database Setup (pgAdmin)
1. Create a database named `primary_db`
2. Create a database named `replica_db`
3. Run the following in both databases:

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100)
);
```

### Environment Variables
Create a `.env` file in the root of the project:

```
PRIMARY_HOST=localhost
PRIMARY_PORT=5432
PRIMARY_DB=primary_db
PRIMARY_USER=postgres
PRIMARY_PASSWORD=your_password

REPLICA_HOST=localhost
REPLICA_PORT=5432
REPLICA_DB=replica_db
REPLICA_USER=postgres
REPLICA_PASSWORD=your_password
```

---

## 📁 File Structure

```
Assignment-7/
├── main.py         # DB connections, read, write, sync functions
├── benchmark.py    # Benchmarking and staleness measurement
├── .env            # Environment variables (never commit this)
└── README.md
```

---

## 🔧 How It Works

### main.py
- `get_primary_connection()` — returns a connection to primary DB
- `get_replica_connection()` — returns a connection to replica DB
- `write_user(name, email)` — inserts a user into primary only
- `sync_replicas()` — manually copies all data from primary to replica (simulates replication)
- `read_users_primary()` — reads all users from primary
- `read_users_replica()` — reads all users from replica

### benchmark.py
Two types of benchmarks are run:

**1. Timing Benchmark**
Compares total time taken for concurrent reads and writes on:
- Single DB (all operations on primary)
- Read Replica setup (writes to primary, reads from replica, sync in background)

**2. Staleness Measurement**
Measures how often reads from the replica return stale (outdated) data compared to primary during concurrent operations.

---

## 📊 Sample Results

### Timing
```
Scenario: 400 reads, 10 writes
  Single DB:    22.1090s
  With Replica: 21.3796s
  Replica faster by 0.7294s
```

### Staleness
```
Staleness Report (100 reads, 10 writes):
  Total reads:       100
  Fresh reads:       94 (94.0%)
  Stale reads:       6 (6.0%)
  Avg staleness:     0.12 rows behind
  Max staleness:     3 rows behind
```

---

## 🧠 Key Learnings

### Why replica is faster
- Reads and writes no longer compete for the same database connection
- Under high concurrent load, separating read and write traffic reduces contention
- The more reads you have, the bigger the benefit

### Why the difference is small on a single machine
- Both databases share the same CPU, RAM, and disk I/O
- In production, primary and replica run on separate physical servers
- The real benefit shows at thousands of concurrent connections

### Replication Lag
- The replica is always slightly behind the primary — this is called **replication lag**
- In our simulation, sync runs every 100ms in the background
- Some reads will return stale data during this window
- More writes = higher staleness because the replica has more catching up to do

### When is staleness acceptable?
| Use Case | Stale Reads OK? |
|---|---|
| Twitter like counter | ✅ Yes |
| Product catalogue | ✅ Yes |
| Bank account balance | ❌ No |
| Stock trade execution | ❌ No |

### When do you need multiple replicas?
- Read traffic is too high for one replica to handle
- Replicas in different geographic regions (serve users closer to them)
- Dedicated replica for heavy analytics/reporting queries

---

## 🔄 Real World vs This Simulation

| Aspect | Real PostgreSQL | This Simulation |
|---|---|---|
| Sync mechanism | WAL streaming (automatic) | Manual full copy every 100ms |
| Replication lag | Milliseconds | ~100ms |
| Separate hardware | Yes | No (same machine) |
| Write to replica | Not possible (read-only) | Possible but avoided |
| Connection handling | Connection pooling (pgBouncer) | New connection per operation |

---

## 📝 Notes
- This assignment uses PostgreSQL instead of MySQL — all concepts (replication, lag, read scaling) are identical
- `sync_replicas()` is a manual simulation — real PostgreSQL streaming replication handles this automatically via WAL logs
- Connection pooling (e.g. pgBouncer) would significantly improve benchmark numbers in a real setup