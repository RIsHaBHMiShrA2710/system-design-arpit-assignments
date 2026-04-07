import psycopg2
import os
from dotenv import load_dotenv

# Load .env from repo root regardless of where this file is called from
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

def get_postgres_connection():
    return psycopg2.connect(
        host=os.getenv("SHARD_0_HOST"),
        port=os.getenv("SHARD_0_PORT"),
        dbname=os.getenv("SHARD_0_DB"),
        user=os.getenv("SHARD_0_USER"),
        password=os.getenv("SHARD_0_PASSWORD")
    )

