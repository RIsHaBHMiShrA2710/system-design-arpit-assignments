# 🤔 Things to Think About — Sharding

---

## 1. Why do we pass `user_id` explicitly instead of using `SERIAL`? What problem would `SERIAL` cause across multiple shards?

### The Problem

`SERIAL` (or `BIGSERIAL`) is an **auto-incrementing counter local to one database**. Each shard maintains its own independent counter, so multiple shards will happily generate the **same ID**.

### Example

| Action | shard_0 generates | shard_1 generates | shard_2 generates |
|---|---|---|---|
| 1st insert | `user_id = 1` | `user_id = 1` | `user_id = 1` |
| 2nd insert | `user_id = 2` | `user_id = 2` | `user_id = 2` |

Now you have **three different users all with `user_id = 1`**. If you ever need to merge data or query across shards, these collisions make it impossible to tell users apart.

### How We Fix It

We generate a **globally unique ID before writing** and pass it in. Common strategies:

| Strategy | How it works |
|---|---|
| **UUID** | Random 128-bit ID — virtually no collisions |
| **Snowflake ID** | Encodes timestamp + machine-id + sequence (Twitter invented this) |
| **App-level counter** | A central service hands out unique IDs (adds a single point of failure) |
| **Range-based** | Shard 0 uses IDs 1–1 000 000, Shard 1 uses 1 000 001–2 000 000, etc. |

By passing `user_id` explicitly, our **router** (`user_id % num_shards`) can deterministically compute the correct shard, which is the whole point of sharding.

---

## 2. What happens if you want to read **all** users in a sharded setup? How is that different from single shard?

### Single Shard (easy)

```sql
SELECT * FROM users;   -- one query, one database, done ✅
```

### Sharded Setup (harder)

Every shard only holds a **subset** of users. To get *all* users you must:

1. **Query every shard** independently.
2. **Merge the results** in your application.

```python
def read_all_users_sharded():
    all_users = []
    for shard_num in range(NUM_SHARDS):
        conn = get_shard_connection(shard_num)
        with conn.cursor() as cur:
            cur.execute("SELECT user_id, name, email FROM users;")
            all_users.extend(cur.fetchall())
        conn.close()
    return all_users
```

### Why This Matters

| Concern | Single Shard | Sharded |
|---|---|---|
| Number of queries | 1 | N (one per shard) |
| Sorting | Handled by DB | Must sort in app after merging |
| Pagination | `LIMIT / OFFSET` works normally | Complex — each shard has partial data |
| Aggregations (`COUNT`, `AVG`) | One query | Must aggregate partial results from each shard |

> **Takeaway:** Sharding optimises single-key lookups but makes **scatter-gather** queries (anything touching all data) more expensive and complex.

---

## 3. What if you want to find a user by `email` instead of `user_id`? Which shard do you check?

### The Dilemma

Our router is based on `user_id`:

```python
shard = user_id % num_shards
```

If you only have an **email**, you don't know the `user_id`, so you **can't compute the shard**. You're stuck.

### What You Have to Do — Scatter-Gather

Query **every** shard and hope one of them has the email:

```python
def find_user_by_email(email):
    for shard_num in range(NUM_SHARDS):
        conn = get_shard_connection(shard_num)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT user_id, name, email FROM users WHERE email = %s;",
                (email,),
            )
            row = cur.fetchone()
        conn.close()
        if row:
            return row
    return None
```

This is **O(N shards)** instead of **O(1)** — you lose the main benefit of sharding.

### Solutions in the Real World

| Solution | How it works | Trade-off |
|---|---|---|
| **Secondary index table** | A small lookup table mapping `email → user_id` stored in a single DB or cache | Extra write on every insert; single point of failure |
| **Shard by email instead** | Use `hash(email) % num_shards` as the router | Now lookups by `user_id` become scatter-gather! |
| **Dual-write / dual-shard** | Maintain two shard mappings (one by `user_id`, one by `email`) | Double the storage and write complexity |
| **Search index (Elasticsearch)** | Index all users in a search engine; use it for non-primary-key lookups | Additional infrastructure to maintain |

> **Takeaway:** Sharding gives you **fast lookups on the shard key** but makes lookups on *any other field* expensive. Choose your shard key wisely — it should be the field you query by **most often**.
