import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# Check if the 'users' table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
print(cursor.fetchall())

# Check the schema of the 'users' table
cursor.execute("PRAGMA table_info(users);")
print(cursor.fetchall())

# Check the schema of the 'users' table
cursor.execute("SELECT * FROM users;")
print(cursor.fetchall())

# Check the schema of the 'messages' table
cursor.execute("PRAGMA table_info(messages);")
print(cursor.fetchall())

# Check the schema of the 'product' table
cursor.execute("PRAGMA table_info(product);")
print(cursor.fetchall())

# Check the schema of the 'product' table
cursor.execute("SELECT * FROM product;")
print(cursor.fetchall())

# Check the schema of the 'orders' table
cursor.execute("PRAGMA table_info(orders);")
print(cursor.fetchall())

# Check the schema of the 'orders' table
cursor.execute("SELECT * FROM orders;")
print(cursor.fetchall())

# Delete query
query = '''
DELETE FROM product WHERE id = 1
'''

# Execute the delete query
cursor.execute(query)
conn.commit()

# Check the products after deletion
cursor.execute("SELECT * FROM product;")
print(cursor.fetchall())

# Clean up
conn.close()
