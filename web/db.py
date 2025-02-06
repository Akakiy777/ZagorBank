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

# Данные для заполнения
owners = ['oleg']
names = [
    ("Яблоки", "Apples"),
    ("Груши", "Pears"),
    ("Бананы", "Bananas"),
    ("Апельсины", "Oranges"),
    ("Киви", "Kiwi"),
    ("Персики", "Peaches"),
    ("Вишни", "Cherries"),
    ("Сливы", "Plums"),
    ("Мандарины", "Tangerines"),
    ("Арбузы", "Watermelons"),
    ("Дыня", "Melon"),
    ("Виноград", "Grapes"),
    ("Клубника", "Strawberries"),
    ("Малина", "Raspberry"),
    ("Черника", "Blueberry"),
    ("Огурцы", "Cucumbers"),
    ("Помидоры", "Tomatoes"),
    ("Картофель", "Potatoes"),
    ("Морковь", "Carrots"),
    ("Цветная капуста", "Cauliflower")
]
descriptions = [
    "Вкусные и свежие", 
    "Сладкие и сочные", 
    "Полезные и ароматные", 
    "Идеальны для соков", 
    "Отборные и качественные", 
    "Подарок природы", 
    "Собраны с любовью", 
    "Наливные и спелые", 
    "Собраны вручную", 
    "Отличный выбор для салатов", 
    "Проверенные сорта", 
    "Прекрасный вкус", 
    "Сочные и сладкие", 
    "Идеальны для десертов", 
    "Содержат витамины", 
    "Свежие с рынка", 
    "Экологически чистые", 
    "Натуральные продукты", 
    "Собранные в сезон", 
    "Непревзойденный вкус"
]

# Генерируем и добавляем 20 товаров
for i in range(20):
    name_ru, name_en = random.choice(names)
    description = random.choice(descriptions)
    price = round(random.uniform(100, 1000), 2)  # Случайная цена от 100 до 1000
    img = '5.png'

    #cursor.execute('''
        #INSERT INTO product (owner, name, description, price, img)
        #VALUES (?, ?, ?, ?, ?)
    #''', (owners[0], f"{name_ru} ({name_en})", description, price, img))

# Сохраняем изменения и закрываем соединение
conn.commit()
conn.close()

