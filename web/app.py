from flask import *
import sqlite3
import hashlib
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = "system"
def query(command):
    with sqlite3.connect("database.db") as db:
        cursor = db.cursor()
        answer = cursor.execute(command)
        db.commit()
        return answer.fetchall()
    
@app.route("/",methods=["GET","POST"])
def index():
    if request.method == "GET":
        return render_template("index.html")
    
@app.route("/main",methods=["GET","POST"])
def main():
    if request.method == "GET":
        try:
            user=query(f"SELECT * FROM users WHERE name = '{request.cookies.get('username')}' AND password = '{hashlib.sha256(request.cookies.get('password').encode()).hexdigest()}'")
        except:
            user=[None]
        users=query(f"SELECT * FROM users")
        return render_template("main.html",user=user[0],users=users)
    
@app.route("/profile/<name>",methods=["GET","POST"])
def profile(name):
    if request.method == "GET":
        user=query(f"SELECT * FROM users WHERE name = '{request.cookies.get('username')}' AND password = '{hashlib.sha256(request.cookies.get('password').encode()).hexdigest()}'")
        this=query(f"SELECT * FROM users WHERE name = '{name}'")
        return render_template("profile.html",user=user[0],this=this[0])
    
@app.route("/reglog", methods=["GET", "POST"])
def reglog():
    if request.method == "POST":
        action = request.form.get("action")
        name = request.form.get("name")
        password = request.form.get("password")
        
        if action == "register":
            confirm_password = request.form.get("confirm_password")
            if password != confirm_password:
                flash("Пароли не совпадают!")
                return redirect(url_for('reglog'))

            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            try:
                query(f"INSERT INTO users (name, password,avatar) VALUES ('{name}', '{hashed_password}','avatar.png')")
                flash("Регистрация успешна!")
            except sqlite3.IntegrityError:
                flash("Пользователь с таким именем уже существует!")
                return redirect(url_for('reglog'))

        elif action == "login":
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            user = query(f"SELECT * FROM users WHERE name = '{name}' AND password = '{hashed_password}'")
            if user:
                resp = make_response(redirect(url_for('main')))
                resp.set_cookie('username', name)  # Сохранение имени пользователя в куки
                resp.set_cookie('password', password)  # Сохранение имени пользователя в куки
                return resp
            else:
                flash("Неверное имя пользователя или пароль!")
                return redirect(url_for('reglog'))

    return render_template("reglog.html")
    
    
@app.route("/edit/<name>", methods=["GET", "POST"])
def edit(name):
    # Проверка существования текущего пользователя
    user=query(f"SELECT * FROM users WHERE name = '{request.cookies.get('username')}' AND password = '{hashlib.sha256(request.cookies.get('password').encode()).hexdigest()}'")
    
    # Проверка существования редактируемого пользователя
    this = query(f"SELECT * FROM users WHERE name = '{name}'")
    
    if request.method == "GET":
        return render_template("edit.html", user=user[0], this=this[0])
    else:
        if 'avatar' in request.files:
            avatar = request.files['avatar']
            if avatar:
                # Убедитесь, что директория существует
                avatar_path = os.path.join("static/avatars", secure_filename(avatar.filename))
                
                # Сохраните аватар с безопасным именем
                avatar.save(avatar_path)
                
                # Обновите запись в базе данных с использованием безопасного запроса
                query(f"UPDATE users SET avatar = '{secure_filename(avatar.filename)}' WHERE name = '{name}'")
        
        # Обработка изменения информации
        change_password = False
        username = request.cookies.get('username')
        password = request.cookies.get('password')
        new_name = request.form.get("name")
        description = request.form.get("description")
        current_password = request.form.get("current_password")
        new_password = request.form.get("new_password")
        confirm_new_password = request.form.get("confirm_new_password")
        
        if new_password and new_password == confirm_new_password:
            hashed_new_password = hashlib.sha256(new_password.encode()).hexdigest()
            query(f"UPDATE users SET password = '{hashed_new_password}' WHERE name = '{name}'")
            change_password = True

        query(f"UPDATE users SET name = '{new_name}', description = '{description}' WHERE name = '{name}'")
        
        if password!=new_password and change_password:
            password=new_password
            
        if username!=new_name:
            username=new_name

        # Обработка изменения баланса (только для администраторов)
        if 1 == 1:  # Если пользователь администратор
            new_balance = request.form.get("balance")
            if new_balance:
                query(f"UPDATE users SET money = '{new_balance}' WHERE name = '{name}'")

        # Обработка удаления аккаунта
        if 'delete_account' in request.form:
            query(f"DELETE FROM users WHERE name = '{name}'")
            return redirect(url_for('reglog'))  # Перенаправление после удаления аккаунта
        resp = make_response(redirect(f"/edit/{username}"))
        resp.set_cookie("username",username)
        resp.set_cookie("password",password)
        return resp  # Перенаправление на страницу редактирования
    
@app.route("/send_money/<receiver_name>", methods=["POST"])
def send_money(receiver_name):
    user_name = request.cookies.get('username')
    
    # Получение текущего пользователя
    user = query(f"SELECT * FROM users WHERE name = '{request.cookies.get('username')}' AND password = '{hashlib.sha256(request.cookies.get('password').encode()).hexdigest()}'")[0]
    receiver = query(f"SELECT * FROM users WHERE name = '{receiver_name}'")[0]
    
    # Получение данных из формы
    amount = request.form.get("amount")
    message = request.form.get("message")
    
    # Преобразование суммы в число
    try:
        amount = float(amount)
    except ValueError:
        flash("Неверная сумма!")
        return redirect(f"/profile/{receiver_name}")
    
    # Проверка достаточности средств
    if user[3] < amount:
        flash("Недостаточно средств для выполнения операции!")
        return redirect(f"/profile/{receiver_name}")
    
    # Обновление баланса
    query(f"UPDATE users SET money = money - {amount} WHERE name = '{user_name}'")
    query(f"UPDATE users SET money = money + {amount} WHERE name = '{receiver_name}'")
    
    flash(f"Вы успешно отправили Z {amount} пользователю {receiver_name}. Сообщение: {message}")
    return redirect(f"/profile/{receiver_name}")


if __name__=="__main__":
    app.run(debug=True,port=5000)
    