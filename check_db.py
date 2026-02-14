import sqlite3

conn = sqlite3.connect('babycare.db')
c = conn.cursor()

# Get all tables
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = c.fetchall()
print("=== Tables in Database ===")
for table in tables:
    print(f"  - {table[0]}")

# Get contacts count
c.execute("SELECT COUNT(*) FROM contacts")
count = c.fetchone()[0]
print(f"\n=== Contacts Table ===")
print(f"Total contacts: {count}")

if count > 0:
    c.execute("SELECT * FROM contacts")
    for row in c.fetchall():
        print(f"\nID: {row[0]}")
        print(f"Name: {row[1]}")
        print(f"Email: {row[2]}")
        print(f"Message: {row[3][:50]}...")
        print(f"Date: {row[4]}")

# Get products count
c.execute("SELECT COUNT(*) FROM products")
products_count = c.fetchone()[0]
print(f"\n=== Products Table ===")
print(f"Total products: {products_count}")

# Get cart count
c.execute("SELECT COUNT(*) FROM cart")
cart_count = c.fetchone()[0]
print(f"\n=== Cart Table ===")
print(f"Total cart items: {cart_count}")

conn.close()
