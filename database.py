import sqlite3

DB_PATH = 'data/shop.db'

def create_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    return any(col[1] == column_name for col in cursor.fetchall())

def add_column_if_missing(cursor, table_name, column_name, column_def):
    """Add a column to a table if it doesn't already exist."""
    if not column_exists(cursor, table_name, column_name):
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")

def init_db():
    conn = create_connection()
    c = conn.cursor()

    # Customers table
    c.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Products table
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Credit Transactions
    c.execute('''
        CREATE TABLE IF NOT EXISTS credit_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            status TEXT DEFAULT 'Unpaid',
            FOREIGN KEY (customer_id) REFERENCES customers (id)
        )
    ''')

    # Credit Items
    c.execute('''
        CREATE TABLE IF NOT EXISTS credit_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            total_price REAL NOT NULL,
            FOREIGN KEY (transaction_id) REFERENCES credit_transactions (id),
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    ''')

    # Payments table
    c.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id INTEGER NOT NULL,
            amount REAL,
            method TEXT,
            date TEXT,
            FOREIGN KEY (transaction_id) REFERENCES credit_transactions (id)
        )
    ''')

    # ---- Migration: ensure all required columns exist ----
    add_column_if_missing(c, "payments", "amount", "REAL NOT NULL DEFAULT 0")
    add_column_if_missing(c, "payments", "method", "TEXT NOT NULL DEFAULT 'Cash'")
    add_column_if_missing(c, "payments", "date", "TEXT NOT NULL DEFAULT ''")

    conn.commit()
    conn.close()
