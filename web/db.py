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

# Clean up
conn.close()
