import os
from flask import Flask, render_template, request, redirect, flash, url_for
from flask_mysqldb import MySQL
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

from database import UserAuth, Address, Product, Cart

app = Flask(__name__)
app.secret_key = 'your_secret_key'

UPLOAD_FOLDER = 'static/uploads/'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)  # Ensure the folder exists
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Anu@441461'
app.config['MYSQL_DB'] = 'anuroop'

mysql = MySQL(app)

# LoginManager Configuration
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, name, email):
        self.id = id
        self.name = name
        self.email = email

@login_manager.user_loader
def load_user(user_id):
    user_data = UserAuth.get_user_by_id(user_id)
    if user_data:
        return User(user_data['id'], user_data['name'], user_data['email'])
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        mobile_number = request.form['mobile_number']
        password = request.form['password']
        success = UserAuth.register_user(name, email, mobile_number, password)
        if success:
            flash("Registration successful! Please log in.", "success")
        else:
            flash("Registration failed. Try again.", "danger")
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        account_type = request.form['account_type']
        success, account = UserAuth.login_user(email, password)
        if success:
            user = User(account['id'], account['name'], account['email'])
            login_user(user)
            flash("Login successful!", "success")
            if account_type == 'consumer':
                return redirect(url_for('consumer'))
            else:
                return redirect(url_for('business'))
        else:
            flash("Invalid credentials.", "danger")
    return redirect(url_for('index'))

@app.route('/add_address', methods=['POST', 'GET'])
@login_required
def add_address():
    if request.method == "POST":
        try:
            success = Address.add_address(
                u_id=current_user.id,
                street_no=request.form['street_no'],
                address_line1=request.form['address_line1'],
                address_line2=request.form.get('address_line2'),
                city=request.form['city'],
                region=request.form.get('region'),
                postal_code=request.form['postal_code'],
                country=request.form['country']
            )
            if success:
                flash("Address added successfully!", "success")
            else:
                flash("Failed to add address. Please try again.", "danger")
        except Exception as e:
            flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('add_address'))
    return render_template('add_address.html')

@app.route('/business')
@login_required
def business():
    return render_template('Business.html')

@app.route('/consumer')
@login_required
def consumer():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM products WHERE user_id!=%s", (current_user.id,))
    products = cursor.fetchall()
    cursor.close()
    return render_template('consumer.html', products=products)

@app.route('/upload', methods=['POST', 'GET'])
@login_required
def upload():
    if request.method == "POST":
        if 'image' not in request.files or request.files['image'].filename == '':
            flash("No file selected!", "warning")
            return redirect(url_for('upload'))

        file = request.files['image']
        filename = file.filename
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        db_file_path = f'static/uploads/{filename}'

        cursor = mysql.connection.cursor()
        cursor.execute(
            "INSERT INTO products (user_id, name, price, category, quantity, description, image_path) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (current_user.id, request.form['name'], request.form['price'], request.form['category'], request.form['quantity'], request.form['desc'], db_file_path)
        )
        mysql.connection.commit()
        cursor.close()
        flash("Product uploaded successfully!", "success")
        return redirect(url_for('view_products'))
    return render_template('upload.html')

@app.route('/view_products')
@login_required
def view_products():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM products WHERE user_id=%s", (current_user.id,))
    products = cursor.fetchall()
    cursor.close()
    return render_template('view_products.html', products=products)

# add_to_cart
# working on it
@app.route('/add_cart/<int:product_id>', methods=['GET'])
@login_required
def add_cart(product_id):
    user_id = current_user.id
    Cart.add_to_cart(user_id,product_id)
    return redirect(url_for('cart'))


@app.route('/cart')
@login_required
def cart():
    cursor = mysql.connection.cursor()

    # Correct SQL query to fetch products in the cart for the current user
    cursor.execute("""
        SELECT p.* FROM cart c
        JOIN products p ON c.product_id = p.product_id
        WHERE c.user_id = %s
    """, (current_user.id,))

    products = cursor.fetchall()
    cursor.close()

    return render_template('cart.html', products=products)

@app.route('/delete/<int:product_id>', methods = ['GET'])
def delete(product_id):
    flash("Record Has Been Deleted Successfully")
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM products WHERE product_id=%s", (product_id,))
    mysql.connection.commit()
    return redirect(url_for('view_products'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('index'))

if __name__ == '__main__':
    UserAuth.create_user_table()
    Address.create_address_table()
    Product.create_product_table()
    Cart.create_cart_table()
    app.run(debug=True)
