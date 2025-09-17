# app.py
import os
import string
import random
from flask import Flask, render_template, request, redirect, url_for, flash, make_response, abort, session
import sqlite3
import hashlib
from werkzeug.utils import secure_filename
from datetime import datetime
from functools import wraps
from datetime import datetime, timezone, timedelta


app = Flask(__name__)
app.secret_key = "system-secret-key-2024"
admin = ["admin", "owner", "alex", "oleg"]


# UTC+3 (Москва)
moscow_offset = timezone(timedelta(hours=3))
moscow_time = datetime.now(moscow_offset)

# Получаем абсолютный путь к директории проекта
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")
AVATARS_DIR = os.path.join(BASE_DIR, "static", "avatars")
VIDEOS_DIR = os.path.join(BASE_DIR, "static", "videos")
IMAGES_DIR = os.path.join(BASE_DIR, "static", "images")
PRODUCT_DIR = os.path.join(BASE_DIR, "static", "product")
FILES_DIR = os.path.join(BASE_DIR, "static", "files")  # Новая папка для файлов чата

# Создаем директории, если они не существуют
os.makedirs(AVATARS_DIR, exist_ok=True)
os.makedirs(VIDEOS_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(PRODUCT_DIR, exist_ok=True)
os.makedirs(FILES_DIR, exist_ok=True)  # Создаем папку для файлов

# Функция для генерации случайного имени файла
def generate_random_filename(length=20):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

# Функция для отправки системного сообщения
def send_system_message(username, message):
    system_message = f"[Система] {message}"
    Database.query("INSERT INTO messages (sender, receiver, message) VALUES (?, ?, ?)",
                   (username, username, system_message))

# Инициализация базы данных
def init_db():
    if not os.path.exists(DB_PATH):
        print("Создание новой базы данных...")

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Создание таблицы users
        cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            money REAL DEFAULT 0,
            description TEXT DEFAULT 'Нет описания',
            avatar TEXT DEFAULT 'default_avatar.png'
        )
        ''')

        # Создание таблицы messages
        cursor.execute('''
        CREATE TABLE messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            receiver TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            file TEXT
        )
        ''')

        # Создание таблицы orders
        cursor.execute('''
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            buyer TEXT NOT NULL,
            seller TEXT NOT NULL,
            status TEXT DEFAULT 'pending'
        )
        ''')

        # Создание таблицы posts
        cursor.execute('''
        CREATE TABLE posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL,
            owner_name TEXT NOT NULL,
            owner_description TEXT DEFAULT 'Нет описания',
            owner_money REAL DEFAULT 0,
            owner_avatar TEXT DEFAULT 'default_avatar.png',
            name TEXT NOT NULL,
            description TEXT DEFAULT 'Нет описания',
            likes INTEGER DEFAULT 0,
            text TEXT DEFAULT 'Нет текста'
        )
        ''')

        # Создание таблицы comments
        cursor.execute('''
        CREATE TABLE comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL,
            owner_name TEXT NOT NULL,
            owner_avatar TEXT DEFAULT 'default_avatar.png',
            text TEXT DEFAULT 'Нет текста',
            type TEXT NOT NULL,
            content_id INTEGER NOT NULL
        )
        ''')

        # Создание таблицы product
        cursor.execute('''
        CREATE TABLE product (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT DEFAULT 'Нет описания',
            price REAL NOT NULL,
            img TEXT DEFAULT 'default_product.png'
        )
        ''')

        # Создание таблицы videos
        cursor.execute('''
        CREATE TABLE videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL,
            owner_name TEXT NOT NULL,
            owner_description TEXT DEFAULT 'Нет описания',
            owner_money REAL DEFAULT 0,
            owner_avatar TEXT DEFAULT 'default_avatar.png',
            name TEXT NOT NULL,
            description TEXT DEFAULT 'Нет описания',
            likes INTEGER DEFAULT 0,
            video TEXT NOT NULL,
            img TEXT NOT NULL
        )
        ''')

        conn.commit()
        conn.close()
        print("База данных успешно создана!")
    else:
        # Проверяем, есть ли столбец file в таблице messages
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(messages)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'file' not in columns:
            print("Добавляем столбец file в таблицу messages...")
            cursor.execute("ALTER TABLE messages ADD COLUMN file TEXT")
            conn.commit()
        conn.close()

class Database:
    @staticmethod
    def query(command, params=()):
        with sqlite3.connect(DB_PATH) as db:
            cursor = db.cursor()
            cursor.execute(command, params)
            db.commit()
            return cursor.fetchall()

class Auth:
    @staticmethod
    def is_authenticated():
        return 'user_id' in session

    @staticmethod
    def get_current_user():
        if 'user_id' in session:
            user = Database.query("SELECT * FROM users WHERE id = ?", (session['user_id'],))
            return user[0] if user else None
        return None

    @staticmethod
    def login_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not Auth.is_authenticated():
                return redirect("/reglog")
            return f(*args, **kwargs)

        return decorated_function

    @staticmethod
    def admin_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = Auth.get_current_user()
            if not user or not (user[1] in admin):
                abort(403)
            return f(*args, **kwargs)

        return decorated_function

# Декораторы для проверки прав доступа
def owner_or_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = Auth.get_current_user()
        resource_owner = kwargs.get('name') or kwargs.get('user_name')

        if not user or (user[1] != resource_owner and not (user[1] in admin)):
            abort(403)
        return f(*args, **kwargs)

    return decorated_function

@app.errorhandler(Exception)
def error(e):
    return render_template("error.html", error=e, text=repr(e))

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template("index.html")

@app.route("/agreement", methods=["GET"])
def agreement():
    return render_template("agreement.html",auser=[],admin=admin)

@app.route("/chat/<name>/<chat>", methods=["GET", "POST"])
@Auth.login_required
def chat(name, chat):
    if request.method == "GET":
        user = Auth.get_current_user()

        this = Database.query("SELECT * FROM users WHERE name = ?", (name,))
        if not this:
            abort(404)

        currentUser = Database.query("SELECT * FROM users WHERE name = ?", (chat,))
        messages = Database.query(
            "SELECT * FROM messages WHERE (sender = ? AND receiver = ?) OR (sender = ? AND receiver = ?) ORDER BY timestamp",
            (name, chat, chat, name))
        users = Database.query("SELECT * FROM users")

        if not currentUser:
            currentUser = this

        if this[0][1] != user[1] and not (user[1] in admin):
            abort(403)

        return render_template("chat.html", auser=user, users=users, this=this[0],
                               messages=messages, admin=admin, currentUser=currentUser[0])

@app.route("/main", methods=["GET", "POST"])
@Auth.login_required
def main():
    if request.method == "GET":
        user = Auth.get_current_user()
        users = Database.query("SELECT * FROM users")
        return render_template("main.html", auser=user, users=users, admin=admin)

@app.route("/tube", methods=["GET", "POST"])
@Auth.login_required
def tube():
    if request.method == "GET":
        user = Auth.get_current_user()
        users = Database.query("SELECT * FROM users")
        posts = Database.query("SELECT * FROM posts")
        videos = Database.query("SELECT * FROM videos")
        return render_template("tube.html", auser=user, users=users, admin=admin,
                               videos=videos[::-1], posts=posts[::-1])

@app.route("/add_comment", methods=["POST"])
@Auth.login_required
def add_comment():
    user = Auth.get_current_user()
    text = request.form.get("text", "Нет текста")
    content_id = int(request.form.get("content_id", 0))
    content_type = request.form.get("content_type", "")

    if content_id and content_type:
        Database.query(
            "INSERT INTO comments (owner_id, owner_name, owner_avatar, text, content_id, type) VALUES (?, ?, ?, ?, ?, ?)",
            (user[0], user[1], user[5], text, content_id, content_type))

    if content_type == 'video':
        return redirect(f"/video/{content_id}")
    else:
        return redirect(f"/post/{content_id}")

@app.route("/edit_video/<int:video_id>", methods=["GET", "POST"])
@Auth.login_required
def edit_video(video_id):
    user = Auth.get_current_user()
    video = Database.query("SELECT * FROM videos WHERE id = ?", (video_id,))

    if not video:
        return redirect("/tube")

    if user[1] != video[0][2] and not (user[1] in admin):
        abort(403)

    if request.method == "POST":
        name = request.form.get("name", video[0][6])
        description = request.form.get("description", video[0][7])
        video_file = request.files.get('video')
        image_file = request.files.get('image')

        Database.query("UPDATE videos SET name = ?, description = ? WHERE id = ?",
                       (name, description, video_id))

        if video_file and video_file.filename:
            # Генерируем случайное имя для файла
            file_extension = os.path.splitext(video_file.filename)[1]
            random_filename = generate_random_filename() + file_extension

            video_path = os.path.join(VIDEOS_DIR, random_filename)
            video_file.save(video_path)
            Database.query("UPDATE videos SET video = ? WHERE id = ?",
                           (random_filename, video_id))

        if image_file and image_file.filename:
            # Генерируем случайное имя для файла
            file_extension = os.path.splitext(image_file.filename)[1]
            random_filename = generate_random_filename() + file_extension

            image_path = os.path.join(IMAGES_DIR, random_filename)
            image_file.save(image_path)
            Database.query("UPDATE videos SET img = ? WHERE id = ?",
                           (random_filename, video_id))

        return redirect(f"/video/{video_id}")

    return render_template("edit_video.html", user=user,auser=user, video=video[0], admin=admin)

@app.route("/edit_post/<int:post_id>", methods=["GET", "POST"])
@Auth.login_required
def edit_post(post_id):
    user = Auth.get_current_user()
    post = Database.query("SELECT * FROM posts WHERE id = ?", (post_id,))

    if not post:
        return redirect("/tube")

    if user[1] != post[0][2] and not (user[1] in admin):
        abort(403)

    if request.method == "POST":
        name = request.form.get("name", post[0][6])
        description = request.form.get("description", post[0][7])
        text = request.form.get("text", post[0][9])

        Database.query("UPDATE posts SET name = ?, description = ?, text = ? WHERE id = ?",
                       (name, description, text, post_id))

        return redirect(f"/post/{post_id}")

    return render_template("edit_post.html", user=user,auser=user, post=post[0], admin=admin)

@app.route("/like/<type>/<int:id>", methods=["POST"])
@Auth.login_required
def like(id, type):
    user = Auth.get_current_user()

    if type == 'video':
        Database.query("UPDATE videos SET likes = likes + 1 WHERE id = ?", (id,))
    elif type == 'post':
        Database.query("UPDATE posts SET likes = likes + 1 WHERE id = ?", (id,))
    else:
        abort(400)

    return redirect(request.referrer)

@app.route("/unlike/<type>/<int:id>", methods=["POST"])
@Auth.login_required
def unlike(id, type):
    user = Auth.get_current_user()

    if type == 'video':
        Database.query("UPDATE videos SET likes = likes - 1 WHERE id = ?", (id,))
    elif type == 'post':
        Database.query("UPDATE posts SET likes = likes - 1 WHERE id = ?", (id,))
    else:
        abort(400)

    return redirect(request.referrer)

@app.route("/video/<video_id>", methods=["GET"])
@Auth.login_required
def video(video_id):
    user = Auth.get_current_user()
    video = Database.query("SELECT * FROM videos WHERE id = ?", (video_id,))

    if not video:
        return redirect("/tube")

    comments = Database.query("SELECT * FROM comments WHERE content_id = ? AND type = 'video'", (video_id,))

    return render_template("video.html", auser=user, video=video[0], admin=admin, comments=comments[::-1])

@app.route("/post/<post_id>", methods=["GET"])
@Auth.login_required
def post(post_id):
    user = Auth.get_current_user()
    post = Database.query("SELECT * FROM posts WHERE id = ?", (post_id,))

    if not post:
        return redirect("/tube")

    comments = Database.query("SELECT * FROM comments WHERE content_id = ? AND type = 'post'", (post_id,))

    return render_template("post.html", auser=user, post=post[0], admin=admin, comments=comments[::-1])

@app.route("/add_video/<name>", methods=["GET", "POST"])
@Auth.login_required
@owner_or_admin_required
def add_video(name):
    user = Auth.get_current_user()
    this = Database.query("SELECT * FROM users WHERE name = ?", (name,))

    if not this:
        abort(404)

    this = this[0]

    if request.method == "POST":
        name_val = request.form.get("name", "Без названия")
        description = request.form.get("description", "Нет описания")
        video_file = request.files.get('video')
        image_file = request.files.get('image')

        if video_file and video_file.filename:
            # Генерируем случайное имя для видео файла
            video_extension = os.path.splitext(video_file.filename)[1]
            video_filename = generate_random_filename() + video_extension
            video_path = os.path.join(VIDEOS_DIR, video_filename)
            video_file.save(video_path)

            # Генерируем случайное имя для изображения
            if image_file and image_file.filename:
                image_extension = os.path.splitext(image_file.filename)[1]
                image_filename = generate_random_filename() + image_extension
                image_path = os.path.join(IMAGES_DIR, image_filename)
                image_file.save(image_path)
            else:
                image_filename = "default_video.png"

            Database.query(
                "INSERT INTO videos (owner_id, owner_name, owner_description, owner_money, owner_avatar, name, description, video, img, likes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (user[0], user[1], user[4], user[3], user[5], name_val, description, video_filename, image_filename, 0))

        return redirect("/tube")

    return render_template("add_video.html", user=user, admin=admin, auser=this)

@app.route("/add_post/<name>", methods=["GET", "POST"])
@Auth.login_required
@owner_or_admin_required
def add_post(name):
    user = Auth.get_current_user()
    this = Database.query("SELECT * FROM users WHERE name = ?", (name,))

    if not this:
        abort(404)

    this = this[0]

    if request.method == "POST":
        name_val = request.form.get("name", "Без названия")
        description = request.form.get("description", "Нет описания")
        text = request.form.get("text", "Нет текста")

        Database.query(
            "INSERT INTO posts (owner_id, owner_name, owner_description, owner_money, owner_avatar, name, description, text, likes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user[0], user[1], user[4], user[3], user[5], name_val, description, text, 0))

        return redirect("/tube")

    return render_template("add_post.html", user=user, auser=this,admin=admin)

@app.route("/profile/<name>", methods=["GET", "POST"])
@Auth.login_required
def profile(name):
    if request.method == "GET":
        user = Auth.get_current_user()
        this = Database.query("SELECT * FROM users WHERE name = ?", (name,))[0]

        if not this:
            return redirect("/main")

        messages = Database.query("SELECT * FROM messages WHERE receiver = ?", (name,))
        return render_template("profile.html", auser=user, user=this, messages=messages, admin=admin)

@app.route("/reglog", methods=["GET", "POST"])
def reglog():
    if request.method == "POST":
        action = request.form.get("action")
        name = request.form.get("name", "").strip()
        password = request.form.get("password", "").strip()

        if not name or not password:
            flash("Имя и пароль не могут быть пустыми")
            return redirect(url_for('reglog'))

        if action == "register":
            confirm_password = request.form.get("confirm_password", "").strip()
            if password != confirm_password:
                flash("Пароли не совпадают")
                return redirect(url_for('reglog'))

            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            try:
                Database.query("INSERT INTO users (name, password) VALUES (?, ?)",
                               (name, hashed_password))
                flash("Регистрация успешна. Теперь вы можете войти.")
            except sqlite3.IntegrityError:
                flash("Пользователь с таким именем уже существует")
                return redirect(url_for('reglog'))

        elif action == "login":
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            user = Database.query("SELECT * FROM users WHERE name = ? AND password = ?",
                                  (name, hashed_password))
            if user:
                session['user_id'] = user[0][0]
                session['username'] = user[0][1]
                return redirect(url_for('main'))
            else:
                flash("Неверное имя пользователя или пароль")
                return redirect(url_for('reglog'))

    return render_template("reglog.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route("/edit/<name>", methods=["GET", "POST"])
@Auth.login_required
@owner_or_admin_required
def edit(name):
    user = Auth.get_current_user()
    this = Database.query("SELECT * FROM users WHERE name = ?", (name,))

    if not this:
        return redirect("/main")

    this = this[0]

    if request.method == "POST":
        new_name = request.form.get("name", this[1])
        description = request.form.get("description", this[4])
        new_password = request.form.get("new_password", "")
        confirm_new_password = request.form.get("confirm_new_password", "")
        new_balance = request.form.get("balance", str(this[3]))

        if new_password and new_password == confirm_new_password:
            # Проверка текущего пароля
            hashed_new_password = hashlib.sha256(new_password.encode()).hexdigest()
            Database.query("UPDATE users SET password = ? WHERE name = ?",(hashed_new_password, name))
        Database.query("UPDATE users SET name = ?, description = ? WHERE name = ?",
                       (new_name, description, name))

        if 'avatar' in request.files:
            avatar = request.files['avatar']
            if avatar and avatar.filename:
                # Генерируем случайное имя для файла
                file_extension = os.path.splitext(avatar.filename)[1]
                random_filename = generate_random_filename() + file_extension

                avatar_path = os.path.join(AVATARS_DIR, random_filename)
                avatar.save(avatar_path)
                Database.query("UPDATE users SET avatar = ? WHERE name = ?",
                               (random_filename, new_name))

        if user[1] in admin:
            try:
                new_balance = float(new_balance)
                Database.query("UPDATE users SET money = ? WHERE name = ?",
                               (new_balance, name))
            except ValueError:
                flash("Неверная сумма баланса")

        # Обновляем сессию, если пользователь меняет свое имя
        if user[1] == name:
            session['username'] = new_name

        flash("Изменения сохранены")
        return redirect(f"/edit/{new_name}")

    return render_template("edit.html", auser=user, user=this, admin=admin)

@app.route("/send_money/<receiver_name>", methods=["POST"])
@Auth.login_required
def send_money(receiver_name):
    user = Auth.get_current_user()
    receiver = Database.query("SELECT * FROM users WHERE name = ?", (receiver_name,))

    if not receiver:
        flash("Получатель не найден")
        return redirect(f"/profile/{receiver_name}")

    amount_str = request.form.get("amount", "0")
    message = request.form.get("message", "")

    try:
        amount = float(amount_str)
        if amount==1e309:
            flash("Неверная сумма")
            return redirect(f"/profile/{receiver_name}")
    except ValueError:
        flash("Неверная сумма")
        return redirect(f"/profile/{receiver_name}")

    # Преобразуем баланс пользователя в float для сравнения
    try:
        user_balance = float(user[3])
    except (ValueError, TypeError):
        flash("Ошибка баланса")
        return redirect(f"/profile/{receiver_name}")

    if user_balance < amount or amount <= 0:
        flash("Недостаточно средств или неверная сумма")
        return redirect(f"/profile/{receiver_name}")

    Database.query("UPDATE users SET money = money - ? WHERE name = ?", (amount, user[1]))
    Database.query("UPDATE users SET money = money + ? WHERE name = ?", (amount, receiver_name))

    # Добавляем сообщение о переводе
    if message:
        Database.query("INSERT INTO messages (sender, receiver, message) VALUES (?, ?, ?)",
                       (user[1], receiver_name, f"Перевод: {amount}Z. Сообщение: {message}"))
    else:
        Database.query("INSERT INTO messages (sender, receiver, message) VALUES (?, ?, ?)",
                       (user[1], receiver_name, f"Перевод: {amount}Z"))

    # Отправляем системное сообщение отправителю
    send_system_message(user[1], f"Вы перевели {amount}Z пользователю {receiver_name}.")
    # Отправляем системное сообщение получателю
    send_system_message(receiver_name, f"Вам перевели {amount}Z от пользователя {user[1]}.")

    flash("Перевод выполнен успешно")
    return redirect(f"/profile/{receiver_name}")

@app.route("/money", methods=["GET", "POST"])
@Auth.login_required
def money():
    user = Auth.get_current_user()

    to_template = """<div class="flex items-center gap-3 mb-2"> <span
                                    class="material-symbols-outlined text-emerald-600">done_all</span>
                                <p class="text-emerald-600 text-lg">Успешно</p>
                            </div>

                    <p class="text-emerald-600 font-bold text-xl flex items-center gap-2"> <span
                            class="material-symbols-outlined">add_circle</span> +{amount} Z на счёт </p>"""

    out_template = """<div class="flex items-center gap-3 mb-2"> <span
                            class="material-symbols-outlined text-violet-600">done_all</span>
                        <p class="text-violet-600 text-lg">Успешно</p>
                    </div>
                    <p class="text-violet-600 flex items-center gap-2 mb-2"> <span
                            class="material-symbols-outlined">qr_code</span> Ваш код: {code} </p>
                    <p class="text-violet-600 flex items-center gap-2 mb-2"> <span
                            class="material-symbols-outlined">currency_exchange</span> Сумма обналичивания: {amount} Z
                    </p>
                    <p class="text-violet-600 font-bold text-xl flex items-center gap-2"> <span
                            class="material-symbols-outlined">person_pin_circle</span> Подойдите чтобы обналичить
                    </p>"""

    if request.method == "GET":
        return render_template("money.html", user=user,auser=user, admin=admin)

    else:
        action = request.form.get("action")
        if action == "withdraw":
            amount_str = request.form.get("amount", "0")
            try:
                amount = float(amount_str)
            except ValueError:
                flash("Неверная сумма")
                return redirect("/money")

            # Преобразуем баланс пользователя в float для сравнения
            try:
                user_balance = float(user[3])
            except (ValueError, TypeError):
                flash("Ошибка баланса")
                return redirect("/money")

            if user_balance >= amount:
                Database.query("UPDATE users SET money = money - ? WHERE name = ?", (amount, user[1]))
                code = str(random.randint(100000000, 999999999))

                # Чтение и запись в файл с абсолютным путем
                out_file = os.path.join(BASE_DIR, "out.txt")
                with open(out_file, "a") as f:
                    f.write(f"\n{code} - {amount}")

                # Отправляем системное сообщение
                send_system_message(user[1], f"Вы сняли {amount}Z. Код для обналичивания: {code}.")
                flash(out_template.format(code=code, amount=amount))
            else:
                flash("Не хватает денег")

        elif action == "deposit":
            code = request.form.get("code", "")
            to_file = os.path.join(BASE_DIR, "to.txt")

            if not code:
                flash("Введите код")
                return redirect("/money")

            found = False
            sum = 0
            new_lines = []

            if os.path.exists(to_file):
                with open(to_file, "r") as file:
                    to_lines = file.readlines()

                for line in to_lines:
                    if code in line:
                        try:
                            sum = float(line.split(" - ")[1].strip())
                            found = True
                        except (IndexError, ValueError):
                            continue
                    else:
                        new_lines.append(line)

            if found:
                # Обновляем баланс
                Database.query("UPDATE users SET money = money + ? WHERE name = ?", (sum, user[1]))

                # Записываем обновлённые строки обратно в файл
                with open(to_file, "w") as file:
                    file.writelines(new_lines)

                # Отправляем системное сообщение
                send_system_message(user[1], f"Ваш счет пополнен на {sum}Z.")
                flash(to_template.format(amount=sum))
            else:
                flash("Неверный код")

        return redirect("/money")

@app.route("/admin_money", methods=["GET", "POST"])
@Auth.login_required
@Auth.admin_required
def admin_money():
    user = Auth.get_current_user()

    if request.method == "POST":
        action = request.form.get("action")

        if action == "delete_to":
            line_to_delete = request.form.get("line", "").strip()
            to_file = os.path.join(BASE_DIR, "to.txt")

            if os.path.exists(to_file):
                with open(to_file, "r") as file:
                    lines = file.readlines()

                # Создаем новый массив без удаляемой строки
                updated_lines = []
                for i in lines:
                    if i.strip() != line_to_delete:
                        updated_lines.append(i)

                with open(to_file, "w") as file:
                    file.writelines(updated_lines)

        elif action == "delete_out":
            line_to_delete = request.form.get("line", "").strip()
            out_file = os.path.join(BASE_DIR, "out.txt")

            if os.path.exists(out_file):
                with open(out_file, "r") as file:
                    lines = file.readlines()

                # Создаем новый массив без удаляемой строки
                updated_lines = []
                for i in lines:
                    if i.strip() != line_to_delete:
                        updated_lines.append(i)

                with open(out_file, "w") as file:
                    file.writelines(updated_lines)

        elif "new_to_line" in request.form:
            new_line = request.form.get("new_to_line", "").strip()
            to_file = os.path.join(BASE_DIR, "to.txt")

            if new_line:
                with open(to_file, "a") as file:
                    file.write(new_line + "\n")

        elif "new_out_line" in request.form:
            new_line = request.form.get("new_out_line", "").strip()
            out_file = os.path.join(BASE_DIR, "out.txt")

            if new_line:
                with open(out_file, "a") as file:
                    file.write(new_line + "\n")

        remove_empty_lines(os.path.join(BASE_DIR, "to.txt"))
        remove_empty_lines(os.path.join(BASE_DIR, "out.txt"))
        flash("Изменения сохранены")
        return redirect("/admin_money")

    else:
        to_file = os.path.join(BASE_DIR, "to.txt")
        out_file = os.path.join(BASE_DIR, "out.txt")

        remove_empty_lines(to_file)
        remove_empty_lines(out_file)

        to_lines = []
        out_lines = []

        if os.path.exists(to_file):
            with open(to_file, "r") as file:
                to_lines = file.readlines()

        if os.path.exists(out_file):
            with open(out_file, "r") as file:
                out_lines = file.readlines()

        return render_template("admin_money.html", user=user,auser=user, to_lines=to_lines, out_lines=out_lines, admin=admin)

def remove_empty_lines(filename):
    if not os.path.exists(filename):
        return

    with open(filename, "r") as file:
        lines = file.readlines()

    with open(filename, "w") as file:
        for line in lines:
            if line.strip():
                file.write(line)

def generate_random_string(length):
    # Определяем набор символов: буквы верхнего регистра и цифры
    characters = string.ascii_uppercase + string.digits
    # Создаем случайную строку, выбирая символы из набора
    random_string = ''.join(random.choice(characters) for i in range(length))
    return random_string

@app.route("/send_message/<sender>/<receiver_name>", methods=["POST"])
@Auth.login_required
def send_message(receiver_name, sender):
    user = Auth.get_current_user()
    message = request.form.get("message", "").strip()
    files = request.files.getlist('files')  # Получаем список файлов

    if not message and not files:
        flash("Сообщение не может быть пустым")
        return redirect(f"/profile/{receiver_name}")

    if user[1] != sender and not (user[1] in admin):
        abort(403)

    filenames = []
    for file in files:
        if file and file.filename:
            # Генерируем случайное имя для файла
            random_filename = "("+generate_random_string(5)+")"+file.filename
            file_path = os.path.join(FILES_DIR, random_filename)
            file.save(file_path)
            filenames.append(random_filename)

    # Объединяем имена файлов через пробел
    files_str = ' '.join(filenames) if filenames else None

    Database.query("INSERT INTO messages (sender, receiver, message, file) VALUES (?, ?, ?, ?)",
                   (sender, receiver_name, message, files_str))

    return redirect(f"/chat/{sender}/{receiver_name}")

@app.route("/shop/<name>", methods=["GET", "POST"])
@Auth.login_required
def shop(name):
    user = Auth.get_current_user()
    this = Database.query("SELECT * FROM users WHERE name = ?", (name,))

    if not this:
        return redirect("/main")

    this = this[0]
    products = Database.query("SELECT * FROM product WHERE owner = ?", (name,))

    if request.method == "POST":
        return redirect(f"/shop/{name}")
    else:
        return render_template("shop.html", user=user,auser=user, this=this, admin=admin, products=products[::-1])

@app.route("/create_product/<name>", methods=["GET", "POST"])
@Auth.login_required
@owner_or_admin_required
def create_product(name):
    user = Auth.get_current_user()
    this = Database.query("SELECT * FROM users WHERE name = ?", (name,))

    if not this:
        return redirect("/main")

    this = this[0]

    if request.method == "POST":
        product_name = request.form.get("product_name", "Без названия")
        description = request.form.get("description", "Нет описания")
        price = request.form.get("price", "0")
        image = request.files.get('image')

        try:
            price = float(price)
        except ValueError:
            flash("Неверная цена")
            return redirect(f"/create_product/{name}")

        image_filename = "default_product.png"
        if image and image.filename:
            # Генерируем случайное имя для файла
            file_extension = os.path.splitext(image.filename)[1]
            random_filename = generate_random_filename() + file_extension

            image_path = os.path.join(PRODUCT_DIR, random_filename)
            image.save(image_path)
            image_filename = random_filename

        Database.query("INSERT INTO product (name, description, price, owner, img) VALUES (?, ?, ?, ?, ?)",
                       (product_name, description, price, this[1], image_filename))

        # Отправляем системное сообщение
        send_system_message(this[1], f"Вы создали товар '{product_name}' по цене {price}Z.")
        flash("Товар успешно создан")
        return redirect(f"/shop/{this[1]}")

    return render_template("create_product.html", user=user, admin=admin, auser=user,this=this)

@app.route("/edit_product/<id>", methods=["GET", "POST"])
@Auth.login_required
def edit_product(id):
    user = Auth.get_current_user()
    product = Database.query("SELECT * FROM product WHERE id = ?", (id,))

    product = product[0]
    this = Database.query("SELECT * FROM users WHERE name = ?", (product[1],))

    this = this[0]

    if request.method == "POST" and (product[4] == user[1] or (user[1] in admin)):
        product_name = request.form.get("product_name", product[2])
        description = request.form.get("description", product[3])
        price = request.form.get("price", str(product[4]))
        image = request.files.get('image')

        try:
            price = float(price)
        except ValueError:
            flash("Неверная цена")
            return redirect(f"/edit_product/{id}")

        if image and image.filename:
            # Генерируем случайное имя для файла
            file_extension = os.path.splitext(image.filename)[1]
            random_filename = generate_random_filename() + file_extension

            image_path = os.path.join(PRODUCT_DIR, random_filename)
            image.save(image_path)
            Database.query("UPDATE product SET name = ?, description = ?, price = ?, img = ? WHERE id = ?",
                           (product_name, description, price, random_filename, id))
        else:
            Database.query("UPDATE product SET name = ?, description = ?, price = ? WHERE id = ?",
                           (product_name, description, price, id))

        # Отправляем системное сообщение
        send_system_message(this[1], f"Вы отредактировали товар '{product_name}'.")
        flash("Товар успешно обновлен")
        return redirect(f"/product/{product[0]}")

    return render_template("edit_product.html", user=user,auser=user, product=product, admin=admin, this=this)

@app.route("/product/<id>", methods=["GET"])
@Auth.login_required
def product(id):
    user = Auth.get_current_user()
    product = Database.query("SELECT * FROM product WHERE id = ?", (id,))

    if not product:
        return redirect("/main")

    return render_template("product.html", user=user,auser=user, product=product[0], admin=admin)

@app.route("/buy_product/<id>", methods=["POST"])
@Auth.login_required
def buy_product(id):
    user = Auth.get_current_user()
    product = Database.query("SELECT * FROM product WHERE id = ?", (id,))

    if not product:
        return redirect("/main")

    product = product[0]

    seller = product[1]
    count = int(request.form.get("count", 1))
    total_price = count * product[4]

    # Преобразуем баланс пользователя в float для сравнения
    try:
        user_balance = float(user[3])
    except (ValueError, TypeError):
        flash("Ошибка баланса")
        return redirect(f"/shop/{seller}")

    if user_balance >= total_price:
        Database.query("UPDATE users SET money = money - ? WHERE name = ?", (total_price, user[1]))

        for i in range(count):
            # Создание нового заказа
            Database.query("INSERT INTO orders (product_id, buyer, seller, status) VALUES (?, ?, ?, ?)",
                           (id, user[1], seller, "pending"))

        # Отправляем системное сообщение покупателю
        send_system_message(user[1], f"Вы купили товар '{product[2]}' в количестве {count} шт. на сумму {total_price}Z.")
        # Отправляем системное сообщение продавцу
        send_system_message(seller, f"Пользователь {user[1]} купил ваш товар '{product[2]}' в количестве {count} шт. на сумму {total_price}Z.")

        flash("Покупка совершена успешно")
    else:
        flash("Недостаточно средств")

    return redirect(f"/shop/{seller}")

@app.route("/orders/<name>", methods=["GET"])
@Auth.login_required
@owner_or_admin_required
def orders(name):
    user = Auth.get_current_user()
    products = {}
    orders = Database.query("SELECT * FROM orders WHERE seller = ?", (name,))[::-1]

    for order in orders:
        product_id = order[1]
        if product_id not in products:
            product_data = Database.query("SELECT * FROM product WHERE id = ?", (product_id,))
            if product_data:
                products[product_id] = product_data[0]  # Сохраняем товар по ID

    return render_template("orders.html", user=user,auser=user, orders=orders[::-1], admin=admin, products=products)

@app.route("/buys/<name>", methods=["GET"])
@Auth.login_required
@owner_or_admin_required
def buys(name):
    user = Auth.get_current_user()
    orders = Database.query("SELECT * FROM orders WHERE buyer = ?", (name,))
    products = {}

    for order in orders:
        product_data = Database.query("SELECT * FROM product WHERE id = ?", (order[1],))
        if product_data:
            products[order[1]] = product_data[0]  # Сохраняем товар по ID

    return render_template("buys.html", user=user, auser=user, orders=orders[::-1], products=products, admin=admin)

@app.route("/confirm_order/<id>", methods=["POST"])
@Auth.login_required
def confirm_order(id):
    user = Auth.get_current_user()
    order = Database.query("SELECT * FROM orders WHERE id = ?", (id,))

    if not order:
        return redirect("/main")

    order = order[0]
    product_data = Database.query("SELECT * FROM product WHERE id = ?", (order[1],))

    if not product_data:
        return redirect("/main")

    product_data = product_data[0]
    seller_name = product_data[3]

    # Обновление статуса заказа на 'confirmed'
    Database.query("UPDATE orders SET status = ? WHERE id = ?", ("confirmed", id))
    Database.query("UPDATE users SET money = money + ? WHERE name = ?", (product_data[4], seller_name))

    # Отправляем системное сообщение продавцу
    send_system_message(seller_name, f"Вы подтвердили заказ на товар '{product_data[2]}' от покупателя {order[2]}.")
    # Отправляем системное сообщение покупателю
    send_system_message(order[2], f"Ваш заказ на товар '{product_data[2]}' подтвержден продавцом.")

    return redirect(f"/orders/{order[3]}")


@app.route("/login_as/<name>")
@Auth.login_required
def login_as(name):
    user = Auth.get_current_user()

    # Проверяем, что текущий пользователь - администратор
    if user[1] not in admin:
        abort(403)

    # Находим целевого пользователя
    target_user = Database.query("SELECT * FROM users WHERE name = ?", (name,))
    if not target_user:
        flash("Пользователь не найден")
        return redirect("/main")

    target_user = target_user[0]

    # Сохраняем оригинального пользователя в сессии для возможности возврата
    if 'original_user' not in session:
        session['original_user'] = {
            'id': session['user_id'],
            'name': session['username']
        }

    # Входим как целевой пользователь
    session['user_id'] = target_user[0]
    session['username'] = target_user[1]

    flash(f"Вы вошли как {name}")
    return redirect("/main")

@app.route("/revert_user")
@Auth.login_required
def revert_user():
    if 'original_user' in session:
        # Возвращаемся к оригинальному пользователю
        session['user_id'] = session['original_user']['id']
        session['username'] = session['original_user']['name']
        session.pop('original_user', None)
        flash("Вы вернулись к своему аккаунту")
    return redirect("/main")

@app.route("/delete", methods=["POST"])
@Auth.login_required
def delete():
    user = Auth.get_current_user()
    id = request.form.get("id", "")
    table = request.form.get("table", "")
    back = request.form.get("back", "")

    if not id or not table:
        return redirect("/main")

    try:
        id = int(id)
    except ValueError:
        return redirect("/main")

    if table == "users" and (user[1] in admin):
        user_to_delete = Database.query("SELECT * FROM users WHERE id = ?", (id,))
        if user_to_delete:
            username = user_to_delete[0][1]
            # Удаляем все связанные данные пользователя
            Database.query("DELETE FROM messages WHERE sender = ? OR receiver = ?", (username, username))
            Database.query("DELETE FROM product WHERE owner = ?", (username,))
            Database.query("DELETE FROM posts WHERE owner_name = ?", (username,))
            Database.query("DELETE FROM videos WHERE owner_name = ?", (username,))
            Database.query("DELETE FROM comments WHERE owner_name = ?", (username,))

            # Обрабатываем заказы
            orders = Database.query("SELECT * FROM orders WHERE buyer = ? OR seller = ?", (username, username))
            for order in orders:
                if order[4] == 'pending':  # Если заказ не подтвержден
                    product = Database.query("SELECT * FROM product WHERE id = ?", (order[1],))
                    if product:
                        # Возвращаем деньги покупателю
                        Database.query("UPDATE users SET money = money + ? WHERE name = ?",
                                       (product[0][4], order[2]))
            Database.query("DELETE FROM orders WHERE buyer = ? OR seller = ?", (username, username))

            Database.query("DELETE FROM users WHERE id = ?", (id,))
            send_system_message(user[1], f"Вы удалили пользователя {username} и все связанные данные.")

    elif table == "product":
        product = Database.query("SELECT * FROM product WHERE id = ?", (id,))
        if product and ((user[1] in admin) or product[0][1] == user[1]):
            # Возвращаем деньги за необработанные заказы
            orders = Database.query("SELECT * FROM orders WHERE product_id = ? AND status = 'pending'", (id,))
            for order in orders:
                Database.query("UPDATE users SET money = money + ? WHERE name = ?",
                               (product[0][4], order[2]))

            Database.query("DELETE FROM orders WHERE product_id = ?", (id,))
            Database.query("DELETE FROM product WHERE id = ?", (id,))
            send_system_message(user[1], f"Вы удалили товар '{product[0][2]}' и отменили связанные заказы.")

    elif table == "posts":
        post = Database.query("SELECT * FROM posts WHERE id = ?", (id,))
        if post and ((user[1] in admin) or post[0][2] == user[1]):
            Database.query("DELETE FROM comments WHERE content_id = ? AND type = 'post'", (id,))
            Database.query("DELETE FROM posts WHERE id = ?", (id,))
            send_system_message(user[1], f"Вы удалили пост '{post[0][6]}' и связанные комментарии.")

    elif table == "videos":
        video = Database.query("SELECT * FROM videos WHERE id = ?", (id,))
        if video and ((user[1] in admin) or video[0][2] == user[1]):
            Database.query("DELETE FROM comments WHERE content_id = ? AND type = 'video'", (id,))
            Database.query("DELETE FROM videos WHERE id = ?", (id,))
            send_system_message(user[1], f"Вы удалили видео '{video[0][6]}' и связанные комментарии.")

    elif table == "comments":
        comment = Database.query("SELECT * FROM comments WHERE id = ?", (id,))
        if comment and ((user[1] in admin) or comment[0][2] == user[1]):
            Database.query("DELETE FROM comments WHERE id = ?", (id,))
            send_system_message(user[1], "Вы удалили комментарий.")

    elif table == "messages":
        message = Database.query("SELECT * FROM messages WHERE id = ?", (id,))
        if message and ((user[1] in admin) or message[0][1] == user[1]):
            Database.query("DELETE FROM messages WHERE id = ?", (id,))

    elif table == "orders":
        order = Database.query("SELECT * FROM orders WHERE id = ?", (id,))
        if order:
            # Проверяем права: администратор или продавец
            if (user[1] in admin) or order[0][3] == user[1]:
                if order[0][4] == 'pending':
                    product = Database.query("SELECT * FROM product WHERE id = ?", (order[0][1],))
                    if product:
                        # Возвращаем деньги покупателю
                        Database.query("UPDATE users SET money = money + ? WHERE name = ?",
                                       (product[0][4], order[0][2]))
                Database.query("DELETE FROM orders WHERE id = ?", (id,))
                send_system_message(user[1], "Вы удалили заказ.")

    else:
        return redirect("/main")

    flash("Удаление выполнено успешно")
    if back:
        return redirect(back)
    else:
        return redirect(request.referrer)

if __name__ == "__main__":
    init_db()  # Инициализация базы данных при запуске
    app.run(debug=True, port=5000)