import sqlite3
import random

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# Check if the 'users' table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
print(cursor.fetchall())

# Check the schema of the 'users' table
cursor.execute("PRAGMA table_info(users);")
print(cursor.fetchall())

# Check the schema of the 'users' table
cursor.execute("PRAGMA table_info(videos);")
print(cursor.fetchall())

# Check the schema of the 'users' table
cursor.execute("PRAGMA table_info(posts);")
print(cursor.fetchall())

# Check the schema of the 'users' table
cursor.execute("PRAGMA table_info(comments);")
print(cursor.fetchall())

# Сохраняем изменения и закрываем соединение
conn.commit()
conn.close()
