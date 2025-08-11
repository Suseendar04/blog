from db_function import get_connection

def create_table():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS blogs (
            id UUID PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL
        );
    """)
    cur.execute("""
        ALTER TABLE blogs ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE;
    """)
    conn.commit()
    cur.close()
    conn.close()

if __name__ == "__main__":
    create_table()
