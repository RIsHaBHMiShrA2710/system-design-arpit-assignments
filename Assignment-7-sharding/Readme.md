# Assignment 7 — Sharding (PostgreSQL)

## 📖 Concept

Read Replicas solve the **read scaling** problem. But what if your **write load** is too
high for one primary to handle? Or your data is so large it doesn't fit on one machine?

That's where **Sharding** comes in. You split your data across multiple databases — each
database owns a **subset of the data**:

```
User IDs → Router → hash(user_id) % 3
                          │
              ┌───────────┼───────────┐
           shard_0     shard_1     shard_2
         (ids 0,3,6…) (ids 1,4,7…) (ids 2,5,8…)
```

Each shard is an independent database. No single machine holds all the data.

---

## 🔀 Sharding Strategy — Hash Based

```python
shard_number = user_id % num_shards
```

With 3 shards:
- user_id 7  → 7  % 3 = 1 → shard_1
- user_id 12 → 12 % 3 = 0 → shard_0
- user_id 5  → 5  % 3 = 2 → shard_2

The **router** runs this calculation before every read and write to determine
which shard to talk to.

### Why not SERIAL for user_id?
`SERIAL` auto-increments independently on each shard — shard_0 would generate
id=1, shard_1 would also generate id=1. You'd have duplicate IDs across shards.
Instead, IDs must be generated globally (e.g. UUIDs, or a centralised ID service).

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
Create 3 databases:
- `shard_0` — acts as both the single shard DB and shard 0
- `shard_1`
- `shard_2`

Run this in all three:
```sql
CREATE TABLE IF NOT EXISTS users (
    user_id  BIGINT PRIMARY KEY,
    name     VARCHAR(100),
    email    VARCHAR(255)
);
```

### Environment Variables
Add to your `.env` file:
```
SHARD_0_HOST=localhost
SHARD_0_PORT=5432
SHARD_0_DB=shard_0
SHARD_0_USER=postgres
SHARD_0_PASSWORD=your_password

SHARD_1_HOST=localhost
SHARD_1_PORT=5432
SHARD_1_DB=shard_1
SHARD_1_USER=postgres
SHARD_1_PASSWORD=your_password

SHARD_2_HOST=localhost
SHARD_2_PORT=5432
SHARD_2_DB=shard_2
SHARD_2_USER=postgres
SHARD_2_PASSWORD=your_password
```

---

## 📁 File Structure

```
Assignment-7-sharding/
├── main.py       # connections, router, read/write functions
├── benchmark.py  # single shard vs 3 shards timing comparison
├── .env          # environment variables (never commit this)
└── README.md
```

---

## 🔧 How It Works

### main.py
- `get_single_shard_connection()` — connects to shard_0 as the un-sharded DB
- `get_shard_connection(shard_num)` — connects to shard 0, 1, or 2
- `get_shard_number(user_id)` — the router: returns which shard owns this user_id
- `write_user_single(user_id, name, email)` — writes to shard_0 only
- `write_user_sharded(user_id, name, email)` — routes to correct shard and writes
- `read_user_single(user_id)` — reads from shard_0 only
- `read_user_sharded(user_id)` — routes to correct shard and reads
- `setup_all()` — creates users table on all databases
- `clean_db()` — clears users table on all databases before each benchmark run

### benchmark.py
Compares total time for reads and writes between:
- **Single shard** — all operations hit shard_0 only
- **Sharded (x3)** — operations distributed across shard_0, shard_1, shard_2

Also prints shard distribution to verify even data spread.

---

## 📊 Benchmark Results

### Low Volume
```
Scenario: 100 reads, 100 writes
  Single Shard : 5.2740s
  Sharded (x3) : 4.6416s
  ✅ Sharded faster by 0.6324s (12.0%)

Scenario: 500 reads, 100 writes
  Single Shard : 24.9500s
  Sharded (x3) : 24.9684s
  ⚠️  Single faster by 0.0185s (0.1%)

Scenario: 100 reads, 500 writes
  Single Shard : 23.9838s
  Sharded (x3) : 23.5763s
  ✅ Sharded faster by 0.4075s (1.7%)
```

### High Volume
```
Scenario: 1000 reads, 1000 writes
  Single Shard : 48.4655s
  Sharded (x3) : 49.8894s
  ⚠️  Single faster by 1.4239s (2.9%)

Scenario: 5000 reads, 1000 writes
  Single Shard : 235.2944s
  Sharded (x3) : 243.7671s
  ⚠️  Single faster by 8.4727s (3.5%)

Scenario: 1000 reads, 5000 writes
  Single Shard : 242.8436s
  Sharded (x3) : 243.1779s
  ⚠️  Single faster by 0.3343s (0.1%)
```

---

## 🧠 Key Learnings

### The Crossover Pattern

| Volume | Winner | Why |
|---|---|---|
| Low (100 ops) | Sharding ✅ | Distribution benefit > routing overhead |
| Medium (500 ops) | Roughly equal | Benefits and costs cancel out |
| High (5000+ ops) | Single DB ⚠️ | Connection overhead accumulates |

### Why Single DB Wins at High Volume on a Single Machine
Every operation opens and closes a new connection. With 5000 operations:
- Sharded: 5000 × (routing cost + connection cost)
- Single: 5000 × (connection cost only)

The routing overhead accumulates and outweighs the distribution benefit when
everything runs on the same hardware.

### Why This Reverses in Production

| Factor | This Benchmark | Production |
|---|---|---|
| Hardware | 1 machine, shared disk | Separate servers per shard |
| Connections | New connection per op | Connection pooling (pgBouncer) |
| Data size | Hundreds of rows | Millions of rows per shard |
| Concurrency | Sequential ops | Thousands of concurrent users |

### What Sharding is Actually For
Sharding is not about raw speed on a single machine. It solves:
- **Storage limits** — when one DB literally cannot store all your data
- **Write throughput ceiling** — a single PostgreSQL instance handles ~10,000 writes/sec max
- **Horizontal scaling** — add more shards as your data grows

Companies like Instagram only introduced sharding when they hit the ceiling of
what a single DB could handle — not before.

---

## ⚠️ Sharding Tradeoffs

| Operation | Single DB | Sharded |
|---|---|---|
| Write by user_id | Simple | Router needed |
| Read by user_id | Simple | Router needed |
| Read ALL users | Simple SELECT | Must query all shards and merge |
| Find by email | Simple WHERE | Must query all shards (no shard key) |
| Joins across users | Simple JOIN | Very complex or impossible |
| Transactions | Simple | Distributed transactions needed |

Sharding adds significant complexity. Always exhaust vertical scaling and
read replicas before introducing sharding.

---

## 🔄 Real World vs This Simulation

| Aspect | Real Sharding | This Simulation |
|---|---|---|
| ID generation | UUID / centralised service | Manual integer IDs |
| Connection handling | pgBouncer connection pooling | New connection per operation |
| Hardware | Separate servers per shard | Same machine |
| Shard routing | Middleware (e.g. Vitess) | Manual in application code |
| Rebalancing | Complex resharding process | Not covered |