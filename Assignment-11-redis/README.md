# Assignment 11 — Redis: Put/Get Data & Benchmark vs PostgreSQL
 
## 📖 Concept
 
Redis is an **in-memory data store** — unlike PostgreSQL which writes to disk, Redis
keeps everything in RAM. This makes it orders of magnitude faster for reads and writes.
 
```
PostgreSQL request flow:
  App → TCP connect → Auth → Parse SQL → Disk read/write → Return → Close connection
 
Redis request flow:
  App → Send command → RAM read/write → Return
```
 
Redis is commonly used for:
- **Caching** — store frequently read DB results so you don't hit the DB every time
- **Session storage** — store user sessions with automatic expiry (TTL)
- **Pub/Sub messaging** — realtime message broadcasting (Assignment 16)
- **Bloom filters** — probabilistic data structures (Assignment 23)
 
---
 
## 🛠️ Setup
 
### Prerequisites
- Docker installed and running
- Python 3.x
- Virtual environment activated
 
### Start Redis via Docker
```bash
docker run -d --name redis-local -p 6379:6379 redis
```
 
Verify it's running:
```bash
docker exec -it redis-local redis-cli ping
# Expected output: PONG
```
 
### Python Dependencies
```bash
pip install redis psycopg2-binary python-dotenv
```
 
---
 
## 📁 File Structure
 
```
Assignment-11-redis/
├── main.py       # Redis and PostgreSQL read/write functions
├── benchmark.py  # Compare Redis vs PostgreSQL timings
├── db.py         # Shared PostgreSQL connection helper
└── README.md
```
 
---
 
## 🔧 How It Works
 
### main.py
 
**Redis functions:**
- `set_user(user_id, name, email)` — stores user as a Redis hash with key `user:{user_id}`
- `get_user(user_id)` — retrieves user hash from Redis by key
 
**PostgreSQL functions:**
- `set_user_postgres(user_id, name, email)` — inserts/updates user in PostgreSQL
- `get_user_postgres(user_id)` — retrieves user by id from PostgreSQL
 
### Why Redis Hashes?
A Redis hash stores multiple fields under one key — perfect for a user object:
```
Key: user:1
Fields:
  name  → "Alice"
  email → "alice@example.com"
```
 
Alternative would be storing a JSON string, but hashes let you update
individual fields without rewriting the entire object.
 
### Key Naming Convention
```
user:{user_id}   →   user:1, user:2, user:42
```
This namespace pattern avoids key collisions if you store multiple entity
types in the same Redis instance (e.g. `post:1`, `session:abc123`).
 
---
 
## 📊 Benchmark Results
 
### Setup
- Redis running on Docker (localhost:6379)
- PostgreSQL running locally (localhost:5432)
- New connection opened per PostgreSQL operation (no connection pooling)
 
### Results
 
```
Scenario: 100 users
  Writes:  Redis 0.0495s  |  PostgreSQL 4.4691s   → Redis faster by 98.9%
  Reads:   Redis 0.0526s  |  PostgreSQL 5.1503s   → Redis faster by 99.0%
  Mixed:   Redis 0.0972s  |  PostgreSQL 10.2639s  → Redis faster by 99.1%
 
Scenario: 200 users
  Writes:  Redis 0.0833s  |  PostgreSQL 11.0977s  → Redis faster by 99.2%
  Reads:   Redis 0.1411s  |  PostgreSQL 9.6290s   → Redis faster by 98.5%
  Mixed:   Redis 0.1855s  |  PostgreSQL 19.9315s  → Redis faster by 99.1%
 
Scenario: 500 users
  Writes:  Redis 0.3180s  |  PostgreSQL 25.3996s  → Redis faster by 98.7%
  Reads:   Redis 0.2434s  |  PostgreSQL 24.9062s  → Redis faster by 99.0%
```
 
Redis is consistently **~99% faster** than PostgreSQL across all scenarios.
 
---
 
## 🧠 Key Learnings
 
### Why Redis is ~99% Faster
 
Every PostgreSQL operation in this benchmark:
1. Opens a new TCP connection
2. Authenticates with the server
3. Parses and plans the SQL query
4. Reads from or writes to disk
5. Returns the result
6. Closes the connection
 
Every Redis operation:
1. Sends a command over a persistent connection
2. Reads from or writes to RAM
3. Returns the result
 
**RAM access is ~100,000x faster than disk access.** That's the core reason.
 
### Why PostgreSQL is So Slow Here Specifically
The benchmark opens a **new connection per operation**. In production,
connection pooling (pgBouncer) eliminates steps 1, 2, and 6 for most requests.
Even with pooling though, Redis would still be significantly faster because
of the RAM vs disk difference.
 
### Redis Scaling
```
100 users  →  Redis takes 0.05s  (0.5ms per operation)
200 users  →  Redis takes 0.08s  (0.4ms per operation)
500 users  →  Redis takes 0.32s  (0.6ms per operation)
```
Redis scales almost linearly — each additional operation costs roughly the same.
 
---
 
## ⚠️ When NOT to Use Redis as Primary Storage
 
Redis is fast but comes with tradeoffs:
 
| Concern | Detail |
|---|---|
| **Persistence** | Data lives in RAM — if Redis restarts, data is lost by default |
| **Storage size** | RAM is expensive — you can't store terabytes in Redis |
| **Querying** | No SQL — you can't do complex joins or aggregations |
| **Durability** | PostgreSQL has ACID guarantees, Redis does not by default |
 
### The Right Pattern — Redis as a Cache
```
Read request
    │
    ├── Check Redis first (cache hit?) ──→ YES → return data instantly
    │
    └── NO (cache miss) → query PostgreSQL → store result in Redis → return data
```
 
This way PostgreSQL remains the **source of truth** and Redis acts as a
**fast lookup layer** in front of it. Cache hit rates of 80-90% in production
mean most requests never touch PostgreSQL at all.
 
---
 
## 🔄 Real World vs This Benchmark
 
| Aspect | This Benchmark | Production |
|---|---|---|
| PostgreSQL connections | New per operation | Connection pooling (pgBouncer) |
| Redis usage | Standalone store | Cache in front of PostgreSQL |
| Data persistence | Not configured | Redis AOF/RDB snapshots enabled |
| Redis connections | New per operation | Persistent connection pool |
| Data size | Hundreds of rows | Millions of cached keys with TTL |
 
---
 
## 💡 Redis CLI Quick Reference
 
```bash
# Connect to Redis CLI
docker exec -it redis-local redis-cli
 
# Set a hash
HSET user:1 name "Alice" email "alice@example.com"
 
# Get a hash
HGETALL user:1
 
# Set a string with TTL (expires in 60 seconds)
SET session:abc123 "user_data" EX 60
 
# Check TTL
TTL session:abc123
 
# Delete a key
DEL user:1
 
# Flush all keys
FLUSHDB
```