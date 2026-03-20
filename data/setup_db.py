"""
data/setup_db.py
Creates a sample e-commerce SQLite database for demo.
Run: python data/setup_db.py
"""
import sqlite3, os, random
from datetime import date, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "sample.db")

conn = sqlite3.connect(DB_PATH)
c    = conn.cursor()

c.executescript("""
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS categories;

CREATE TABLE categories (
    id   INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE products (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    category_id INTEGER REFERENCES categories(id),
    price       REAL NOT NULL,
    stock       INTEGER DEFAULT 0
);

CREATE TABLE customers (
    id         INTEGER PRIMARY KEY,
    name       TEXT NOT NULL,
    email      TEXT UNIQUE,
    country    TEXT,
    created_at DATE
);

CREATE TABLE orders (
    id          INTEGER PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id),
    status      TEXT CHECK(status IN ('pending','processing','shipped','delivered','cancelled')),
    total       REAL,
    created_at  DATE
);

CREATE TABLE order_items (
    id         INTEGER PRIMARY KEY,
    order_id   INTEGER REFERENCES orders(id),
    product_id INTEGER REFERENCES products(id),
    quantity   INTEGER,
    unit_price REAL
);
""")

# Seed data
categories = [("Electronics",), ("Clothing",), ("Books",), ("Home & Garden",), ("Sports",)]
c.executemany("INSERT INTO categories(name) VALUES(?)", categories)

products = [
    ("MacBook Pro 14",   1, 1999.99, 50),
    ("iPhone 15",        1,  999.99, 120),
    ("AirPods Pro",      1,  249.99, 200),
    ("USB-C Hub",        1,   49.99, 500),
    ("T-Shirt Basic",    2,   19.99, 1000),
    ("Denim Jacket",     2,   89.99, 300),
    ("Running Shoes",    5,  129.99, 150),
    ("Python Cookbook",  3,   39.99, 400),
    ("Clean Code",       3,   34.99, 350),
    ("Coffee Maker",     4,   79.99, 80),
    ("Yoga Mat",         5,   29.99, 250),
    ("Smart Watch",      1,  299.99, 180),
]
c.executemany("INSERT INTO products(name,category_id,price,stock) VALUES(?,?,?,?)", products)

customers = [
    ("Alice Johnson",  "alice@example.com",  "USA"),
    ("Bob Smith",      "bob@example.com",    "UK"),
    ("Carol White",    "carol@example.com",  "Canada"),
    ("David Lee",      "david@example.com",  "Australia"),
    ("Emma Wilson",    "emma@example.com",   "USA"),
    ("Frank Brown",    "frank@example.com",  "Germany"),
    ("Grace Kim",      "grace@example.com",  "South Korea"),
    ("Henry Davis",    "henry@example.com",  "USA"),
]
base_date = date(2024, 1, 1)
for i, (name, email, country) in enumerate(customers):
    c.execute("INSERT INTO customers(name,email,country,created_at) VALUES(?,?,?,?)",
              (name, email, country, base_date + timedelta(days=i*10)))

statuses = ['pending','processing','shipped','delivered','cancelled']
for oid in range(1, 51):
    cid      = random.randint(1, 8)
    status   = random.choices(statuses, weights=[5,10,20,60,5])[0]
    odate    = base_date + timedelta(days=random.randint(0, 365))
    total    = 0
    c.execute("INSERT INTO orders(customer_id,status,total,created_at) VALUES(?,?,0,?)", (cid, status, odate))
    for _ in range(random.randint(1,4)):
        pid   = random.randint(1, 12)
        qty   = random.randint(1, 3)
        price = c.execute("SELECT price FROM products WHERE id=?", (pid,)).fetchone()[0]
        total += qty * price
        c.execute("INSERT INTO order_items(order_id,product_id,quantity,unit_price) VALUES(?,?,?,?)", (oid,pid,qty,price))
    c.execute("UPDATE orders SET total=? WHERE id=?", (round(total,2), oid))

conn.commit()
conn.close()

print(f"Sample database created: {DB_PATH}")
print("Tables: categories, products, customers, orders, order_items")
print("50 orders, 8 customers, 12 products, 5 categories")
