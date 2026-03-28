import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

def get_primary_connection():
    return(
        psycopg2.connect(
            host=os.getenv("PRIMARY_HOST"),
            port=os.getenv("PRIMARY_PORT"),
            dbname=os.getenv("PRIMARY_DB"),
            user=os.getenv("PRIMARY_USER"),
            password=os.getenv("PRIMARY_PASSWORD")
        )
    )
def get_replica_connection():
    return (
        psycopg2.connect(
            host=os.getenv("REPLICA_HOST"),
            port=os.getenv("REPLICA_PORT"),
            dbname=os.getenv("REPLICA_DB"),
            user=os.getenv("REPLICA_USER"),
            password=os.getenv("REPLICA_PASSWORD")
        )
    )   

def write_user(name, email): 
    conn = get_primary_connection()
    with conn.cursor() as cursor:
        cursor.execute("INSERT INTO users (name, email) VALUES (%s, %s)", (name, email))
    conn.commit()
    conn.close()

def sync_replicas():
    conn_primary = get_primary_connection()
    conn_replica = get_replica_connection()
    with conn_primary.cursor() as primary_conn, conn_replica.cursor() as replica_conn:
        primary_conn.execute("SELECT * FROM users")
        users = primary_conn.fetchall()
        replica_conn.execute("DELETE FROM users")
        for user in users:
            replica_conn.execute("INSERT INTO users (name, email) VALUES (%s, %s)", (user[1], user[2]))
        
    conn_replica.commit()
    conn_primary.close()
    conn_replica.close()

def read_users_primary():
    conn = get_primary_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()
    conn.close()
    return users

def read_users_replica():
    conn = get_replica_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()
    conn.close()
    return users