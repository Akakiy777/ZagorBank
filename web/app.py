from flask import *
import sqlite3
import hashlib
from werkzeug.utils import secure_filename
import os
import random

app = Flask(__name__)
app.secret_key = "system"
admin = ["lol","oleg"]

def query(command, params=()):
    with sqlite3.connect("database.db") as db:
        cursor = db.cursor()
        cursor.execute(command, params)
        db.commit()
        return cursor.fetchall()

#@app.errorhandler(Exception)
def error(e):
    return render_template("error.html", error=e, text=repr(e))

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template("index.html")

@app.route("/main", methods=["GET", "POST"])
def main():
    if request.method == "GET":
        user = query("SELECT * FROM users WHERE name = ? AND password = ?", 
                     (str(request.cookies.get('username')), hashlib.sha256(str(request.cookies.get('password')).encode()).hexdigest())) 
        if not user:
            return redirect("/reglog")
        
        users = query("SELECT * FROM users")
        return render_template("main.html", auser=user[0], users=users,admin=admin)

@app.route("/profile/<name>", methods=["GET", "POST"])
def profile(name):
    if request.method == "GET":
        user = query("SELECT * FROM users WHERE name = ? AND password = ?", 
                     (str(request.cookies.get('username')), hashlib.sha256(str(request.cookies.get('password')).encode()).hexdigest())) 
        if not user:
            return redirect("/reglog")
        
        this = query("SELECT * FROM users WHERE name = ?", (name,))
        messages = query("SELECT * FROM messages")
        return render_template("profile.html", user=user[0], this=this[0], messages=messages, admin=admin)

@app.route("/reglog", methods=["GET", "POST"])
def reglog():
    if request.method == "POST":
        action = request.form.get("action")
        name = request.form.get("name")
        password = request.form.get("password")

        if action == "register":
            confirm_password = request.form.get("confirm_password")
            if password != confirm_password:
                return redirect(url_for('reglog'))

            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            try:
                query("INSERT INTO users (name, password, avatar) VALUES (?, ?, ?)", 
                      (name, hashed_password, 'avatar.png'))
            except sqlite3.IntegrityError:
                return redirect(url_for('reglog'))

        elif action == "login":
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            user = query("SELECT * FROM users WHERE name = ? AND password = ?", 
                         (name, hashed_password))
            if user:
                resp = make_response(redirect(url_for('main')))
                resp.set_cookie('username', name)
                resp.set_cookie('password', password)
                return resp
            else:
                return redirect(url_for('reglog'))

    return render_template("reglog.html")

@app.route("/edit/<name>", methods=["GET", "POST"])
def edit(name):
    user = query("SELECT * FROM users WHERE name = ? AND password = ?", 
                     (str(request.cookies.get('username')), hashlib.sha256(str(request.cookies.get('password')).encode()).hexdigest())) 
    if not user:
        return redirect("/reglog")
    
    this = query("SELECT * FROM users WHERE name = ?", (name,))
    if not this:
        return redirect("/main")

    if request.method == "POST":
        if not user[0][1] in admin and user[0][1]!=name:
            abort(403)
        return_name=user[0][1]
        new_name = request.form.get("name")
        description = request.form.get("description")
        current_password = request.form.get("current_password")
        new_password = request.form.get("new_password")
        confirm_new_password = request.form.get("confirm_new_password")
        new_balance = request.form.get("balance")
        
        if new_password and new_password == confirm_new_password:
            hashed_new_password = hashlib.sha256(new_password.encode()).hexdigest()
            query("UPDATE users SET password = ? WHERE name = ?", 
                  (hashed_new_password, name))

        query("UPDATE users SET name = ?, description = ? WHERE name = ?", 
              (new_name, description, name))

        if 'avatar' in request.files:
            avatar = request.files['avatar']
            if avatar and avatar.filename:
                avatar_path = os.path.join("static/avatars", secure_filename(avatar.filename))
                avatar.save(avatar_path)
                query("UPDATE users SET avatar = ? WHERE name = ?", 
                      (secure_filename(avatar.filename), new_name))
        if new_name!=None and user[0][1]==this[0][1]:
            return_name=new_name
        if user[0][1] in admin and new_balance:
            query(f"UPDATE users SET money = {new_balance} WHERE name = '{name}'")

        resp = make_response(redirect(f"/edit/{new_name}"))
        resp.set_cookie("username", return_name)
        return resp

    return render_template("edit.html", user=user[0], this=this[0],admin=admin)

@app.route("/send_money/<receiver_name>", methods=["POST"])
def send_money(receiver_name):
    user_name = request.cookies.get('username')
    user = query("SELECT * FROM users WHERE name = ? AND password = ?", 
                     (str(request.cookies.get('username')), hashlib.sha256(str(request.cookies.get('password')).encode()).hexdigest())) 
    if not user:
        return redirect(f"/profile/{receiver_name}")

    receiver = query("SELECT * FROM users WHERE name = ?", (receiver_name,))
    if not receiver:
        return redirect(f"/profile/{receiver_name}")

    amount = request.form.get("amount")
    message = request.form.get("message")
    
    try:
        amount = float(amount)
    except ValueError:
        return redirect(f"/profile/{receiver_name}")

    if user[0][3] < amount or 0>amount:
        return redirect(f"/profile/{receiver_name}")

    query("UPDATE users SET money = money - ? WHERE name = ?", (amount, user_name))
    query("UPDATE users SET money = money + ? WHERE name = ?", (amount, receiver_name))

    return redirect(f"/profile/{receiver_name}")

@app.route("/money", methods=["GET", "POST"])
def money():
    user_name = request.cookies.get('username')
    user = query("SELECT * FROM users WHERE name = ? AND password = ?", 
                 (user_name, hashlib.sha256(str(request.cookies.get('password')).encode()).hexdigest())) 
    if not user:
        return redirect("/reglog")
    
    to = ["""<div class="flex items-center gap-3 mb-2"> <span
                                    class="material-symbols-outlined text-emerald-600">done_all</span>
                                <p class="text-emerald-600 text-lg">Успешно</p>
                            </div>
                    
                    <p class="text-emerald-600 font-bold text-xl flex items-center gap-2"> <span
                            class="material-symbols-outlined">add_circle</span> +""",""" Z на счёт </p>"""]
    
    out = ["""<div class="flex items-center gap-3 mb-2"> <span
                            class="material-symbols-outlined text-violet-600">done_all</span>
                        <p class="text-violet-600 text-lg">Успешно</p>
                    </div>
                    <p class="text-violet-600 flex items-center gap-2 mb-2"> <span
                            class="material-symbols-outlined">qr_code</span> Ваш код: """,""" </p>
                    <p class="text-violet-600 flex items-center gap-2 mb-2"> <span
                            class="material-symbols-outlined">currency_exchange</span> Сумма обналичивания: """,""" Z
                    </p>
                    <p class="text-violet-600 font-bold text-xl flex items-center gap-2"> <span
                            class="material-symbols-outlined">person_pin_circle</span> Подойдите чтобы обналичить
                    </p>"""]
    
    if request.method == "GET":
        return render_template("money.html", user=user[0], admin=admin)
    
    else:
        action = request.form.get("action")
        if action == "withdraw":
            amount = request.form.get("amount")
            try:
                amount=float(amount)
            except:
                flash("Не верная сумма")
            if user[0][3]>=amount:
                query(f"UPDATE users SET money = money-{amount} WHERE name = '{user[0][1]}'")
                code=str(random.randint(100000000,999999999))
                out_text = open("out.txt","r").read()
                open("out.txt","w").write(out_text+f"\n{code} - {amount}")
                flash(out[0]+code+out[1]+str(amount)+out[2])
            else:
                flash("Не хватает денег")
        
        elif action == "deposit":
            code = request.form.get("code")
            with open("to.txt", "r") as file:
                to_lines = file.readlines()
            
            found = False
            sum = 0
            
            # Новый список для записи в файл без строки с найденным кодом
            new_lines = []
            for line in to_lines:
                if code in line:
                    # Извлекаем сумму
                    sum = float(line.split(" - ")[1].strip())
                    found = True
                else:
                    new_lines.append(line)  # Сохраняем все линии, кроме найденной
            
            if found:
                # Обновляем баланс
                query("UPDATE users SET money = money + ? WHERE name = ?", (sum, user_name))
                
                # Записываем обновлённые строки обратно в файл
                with open("to.txt", "w") as file:
                    file.writelines(new_lines)
                
                message = to[0] + str(sum) + to[1]
                flash(message)
            else:
                flash("Не правильный код")

        return redirect("/money")
    
@app.route("/admin_money", methods=["GET", "POST"])
def admin_money():
    user_name = request.cookies.get('username')
    user = query("SELECT * FROM users WHERE name = ? AND password = ?", 
                 (user_name, hashlib.sha256(str(request.cookies.get('password')).encode()).hexdigest())) 
    if not user:
        return redirect("/reglog")
    
    if request.method == "POST" and user[0][1] in admin:
        action = request.form.get("action")
        
        if action == "delete_to":
            line_to_delete = request.form.get("line").strip()  # Удаляем пробелы и символы перевода строки
            with open("to.txt", "r") as file:
                lines = file.readlines()

            # Создаем новый массив без удаляемой строки
            updated_lines = []
            for i in lines:
                if i.strip() != line_to_delete:  # Сравниваем с удалением пробелов
                    updated_lines.append(i)

            with open("to.txt", "w") as file:
                file.writelines(updated_lines)  # Записываем обратно обновленный массив

        elif action == "delete_out":
            line_to_delete = request.form.get("line").strip()  # Удаляем пробелы и символы перевода строки
            with open("out.txt", "r") as file:
                lines = file.readlines()

            # Создаем новый массив без удаляемой строки
            updated_lines = []
            for i in lines:
                if i.strip() != line_to_delete:  # Сравниваем с удалением пробелов
                    updated_lines.append(i)

            with open("out.txt", "w") as file:
                file.writelines(updated_lines)  # Записываем обратно обновленный массив


        elif "new_to_line" in request.form:
            new_line = request.form.get("new_to_line")
            with open("to.txt", "a") as file:
                file.write(new_line + "\n")

        elif "new_out_line" in request.form:
            new_line = request.form.get("new_out_line")
            with open("out.txt", "a") as file:
                file.write(new_line + "\n")

        remove_empty_lines("to.txt")
        remove_empty_lines("out.txt")

        return redirect("/admin_money")

    else:
        remove_empty_lines("to.txt")
        remove_empty_lines("out.txt")
        
        with open("to.txt", "r") as file:
            to_lines = file.readlines()

        with open("out.txt", "r") as file:
            out_lines = file.readlines()

        return render_template("admin_money.html", user=user[0], to_lines=to_lines, out_lines=out_lines, admin=admin)

def remove_empty_lines(filename):
    with open(filename, "r") as file:
        lines = file.readlines()
    
    with open(filename, "w") as file:
        for line in lines:
            if line.strip():  # Записываем только непустые строки
                file.write(line)
                
@app.route("/send_message/<receiver_name>", methods=["POST"])
def send_message(receiver_name):
    user_name = request.cookies.get('username')
    user = query("SELECT * FROM users WHERE name = ? AND password = ?", 
                 (user_name, hashlib.sha256(str(request.cookies.get('password')).encode()).hexdigest())) 
    if not user:
        return redirect("/reglog")

    message = request.form.get("message")
    
    if not message:
        return redirect(f"/profile/{receiver_name}")

    query("INSERT INTO messages (sender, receiver, message) VALUES (?, ?, ?)", 
          (user_name, receiver_name, message))
    
    return redirect(f"/profile/{receiver_name}")

@app.route("/shop/<name>", methods=["GET","POST"])
def shop(name):
    user_name = request.cookies.get('username')
    user = query("SELECT * FROM users WHERE name = ? AND password = ?", 
                 (user_name, hashlib.sha256(str(request.cookies.get('password')).encode()).hexdigest())) 
    if not user:
        return redirect("/reglog")
    this = query("SELECT * FROM users WHERE name = ?", (name,))
    if not this:
        return redirect("/main")
    products = query("SELECT * FROM product WHERE owner = ?", (name,))

    if request.method == "POST":
        return redirect(f"/shop/{name}")
    else:
        return render_template("shop.html",user=user[0],this=this[0],admin=admin,products=products)
    
@app.route("/create_product/<name>", methods=["GET", "POST"])
def create_product(name):
    user_name = request.cookies.get('username')
    user = query("SELECT * FROM users WHERE name = ? AND password = ?", 
                 (user_name, hashlib.sha256(str(request.cookies.get('password')).encode()).hexdigest())) 
    if not user:
        return redirect("/reglog")
    this = query("SELECT * FROM users WHERE name = ?", (name,))
    if not this:
        return redirect("/main")
    
    if request.method == "POST" and (user[0][1]==this[0][1] or user[0][1] in admin):
        product_name = request.form.get("product_name")
        description = request.form.get("description")
        price = float(request.form.get("price"))
        image = request.files['image']
        
        if image and image.filename:
            image_path = os.path.join("static/product", secure_filename(image.filename))
            image.save(image_path)

            query("INSERT INTO product (name, description, price, owner, img) VALUES (?, ?, ?, ?, ?)", 
                  (product_name, description, price, this[0][1], secure_filename(image.filename)))
            
            return redirect(f"/shop/{this[0][1]}")

    return render_template("create_product.html", user=user[0], admin=admin,this=this[0])

@app.route("/edit_product/<id>", methods=["GET", "POST"])
def edit_product(id):
    user_name = request.cookies.get('username')
    user = query("SELECT * FROM users WHERE name = ? AND password = ?", 
                 (user_name, hashlib.sha256(str(request.cookies.get('password')).encode()).hexdigest())) 
    if not user:
        return redirect("/reglog")
    
    product = query("SELECT * FROM product WHERE id = ?", (id,))
    if not product:
        return redirect("/main")
    
    this = query("SELECT * FROM users WHERE name = ?", (product[0][1],))
    if not this:
        return redirect("/main")

    if request.method == "POST" and (product[0][1] == user[0][1] or user[0][1] in admin):
        product_name = request.form.get("product_name")
        description = request.form.get("description")
        price = float(request.form.get("price"))
        image = request.files['image']

        if image and image.filename:
            image_path = os.path.join("static/product", secure_filename(image.filename))
            image.save(image_path)
            query("UPDATE product SET name = ?, description = ?, price = ?, img = ? WHERE id = ?", 
                  (product_name, description, price, secure_filename(image.filename), id))
        else:
            query("UPDATE product SET name = ?, description = ?, price = ? WHERE id = ?", 
                  (product_name, description, price, id))
        
        return redirect(f"/shop/{product[0][1]}")

    return render_template("edit_product.html", user=user[0], product=product[0], admin=admin,this=this[0])

@app.route("/product/<id>", methods=["GET"])
def product(id):
    user_name = request.cookies.get('username')
    user = query("SELECT * FROM users WHERE name = ? AND password = ?", 
                 (user_name, hashlib.sha256(str(request.cookies.get('password')).encode()).hexdigest())) 
    if not user:
        return redirect("/reglog")

    product = query("SELECT * FROM product WHERE id = ?", (id,))
    if not product:
        return redirect("/main")
    
    return render_template("product.html", user=user[0], product=product[0], admin=admin)

@app.route("/buy_product/<id>", methods=["POST"])
def buy_product(id):
    user_name = request.cookies.get('username')
    user = query("SELECT * FROM users WHERE name = ? AND password = ?", 
                 (user_name, hashlib.sha256(str(request.cookies.get('password')).encode()).hexdigest())) 
    if not user:
        return redirect("/reglog")

    product = query("SELECT * FROM product WHERE id = ?", (id,))
    if not product:
        return redirect("/main")

    seller = product[0][1]
    count = int(request.form.get("count"))
    
    if user[0][3]>=count*product[0][4]:
        query(f"UPDATE users SET money=money-{count*product[0][4]} WHERE name='{user_name}'")

    for i in range(count):
        # Создание нового заказа
        query("INSERT INTO orders (product_id, buyer, seller, status) VALUES (?, ?, ?, ?)", 
            (id, user_name, seller, "pending"))

    return redirect(f"/shop/{seller}")

@app.route("/orders/<name>", methods=["GET"])
def orders(name):
    user_name = request.cookies.get('username')
    user = query("SELECT * FROM users WHERE name = ? AND password = ?", 
                 (user_name, hashlib.sha256(str(request.cookies.get('password')).encode()).hexdigest())) 
    if not user:
        return redirect("/reglog")
    products = []
    orders = query("SELECT * FROM orders WHERE seller = ?", (name,))[::-1]
    for i in orders:
        products.append(query(f"SELECT * FROM product WHERE id={i[1]}")[0])
    
    return render_template("orders.html", user=user[0], orders=orders, admin=admin,products=products)

@app.route("/buys/<name>", methods=["GET"])
def buys(name):
    user_name = request.cookies.get('username')
    user = query("SELECT * FROM users WHERE name = ? AND password = ?", 
                 (user_name, hashlib.sha256(str(request.cookies.get('password')).encode()).hexdigest())) 
    if not user:
        return redirect("/reglog")

    orders = query("SELECT * FROM orders WHERE buyer = ?", (name,))
    products = []
    for order in orders:
        products.append(query("SELECT * FROM product WHERE id = ?", (order[1],))[0]) 

    return render_template("buys.html", user=user[0], orders=orders, products=products, admin=admin)


@app.route("/confirm_order/<id>", methods=["POST"])
def confirm_order(id):
    user_name = request.cookies.get('username')
    user = query("SELECT * FROM users WHERE name = ? AND password = ?", 
                 (user_name, hashlib.sha256(str(request.cookies.get('password')).encode()).hexdigest())) 
    if not user:
        return redirect("/reglog")
    product_price = query("SELECT * FROM product WHERE id = ?", (query("SELECT * FROM orders WHERE id = ?", (id,))[0][1],))[0][4]
    this_name = query("SELECT * FROM product WHERE id = ?", (query("SELECT * FROM orders WHERE id = ?", (id,))[0][1],))[0][1]

    # Обновление статуса заказа на 'confirmed'
    query("UPDATE orders SET status = ? WHERE id = ?", ("confirmed", id))
    query(f"UPDATE users SET money=money+{product_price} WHERE name='{this_name}'")

    return redirect(f"/orders/{this_name}")

@app.route("/delete", methods=["POST"])
def delete():
    user_name = request.cookies.get('username')
    user = query("SELECT * FROM users WHERE name = ? AND password = ?", 
                 (user_name, hashlib.sha256(str(request.cookies.get('password')).encode()).hexdigest()))

    if not user:
        return redirect("/reglog")
    
    id = request.form.get("id")
    table = request.form.get("table")
    back = request.form.get("back")
    
    if not id or not table or not back:
        return redirect("/main")

    if table == "users" and user[0][1] in admin:
        query("DELETE FROM users WHERE id=?", (id,))
    elif table == "product" and (user[0][1] in admin or query("SELECT * FROM product WHERE id=?",(id,))[0][1] == user[0][1]):
        query("DELETE FROM product WHERE id=?", (id,))
    else:
        return redirect("/main")
    
    return redirect(back)
    
if __name__ == "__main__":
    app.run(debug=True, port=5000)
