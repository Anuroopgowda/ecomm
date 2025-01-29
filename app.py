from flask import Flask, render_template, request, redirect, flash, url_for
from flask_mysqldb import MySQL
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import os
from database import UserAuth, Address, Product

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
        return render_template('index.html')
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
            if account_type == 'consumer':
                return render_template('consumer.html', name=account['name'])
            elif account_type == 'business':
                return render_template('Business.html', name=account['name'])
        else:
            return render_template('index.html', error="Invalid credentials")
    return render_template('index.html')

@app.route('/add_address', methods=['POST', 'GET'])
@login_required
def add_address():
    # Retrieve the logged-in user's ID
    u_id = current_user.id

    if request.method == "POST":
        try:
            # Collect form data
            street_no = request.form['street_no']
            address_line1 = request.form['address_line1']
            address_line2 = request.form.get('address_line2')  # Optional field
            city = request.form['city']
            region = request.form.get('region')  # Optional field
            postal_code = request.form['postal_code']
            country = request.form['country']

            # Save the address using the static method
            success = Address.add_address(
                u_id=u_id,
                street_no=street_no,
                address_line1=address_line1,
                address_line2=address_line2,
                city=city,
                region=region,
                postal_code=postal_code,
                country=country
            )

            if success:
                flash("Address added successfully!", "success")
            else:
                flash("Failed to add address. Please try again.", "danger")
        except Exception as e:
            flash(f"An error occurred: {str(e)}", "danger")

    # Render the form (both for GET requests and after POST submission)
    return render_template('add_address.html', id=u_id)

@app.route('/business')
@login_required
def business():
    return render_template('Business.html')

@app.route('/consumer')
@login_required
def consumer():
    u_id = current_user.id
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM products WHERE user_id!=%s ", (u_id,))
    products = cursor.fetchall()
    cursor.close()
    return render_template('consumer.html',products=products)


@app.route('/upload', methods=['POST','GET'])
@login_required
def upload():
    if request.method=="POST":
        if 'image' not in request.files:
            return "No file part"

        product_name = request.form['name']
        price = request.form['price']
        quantity = request.form['quantity']
        category = request.form['category']
        description = request.form['desc']
        file = request.files['image']
        # file = request.files['image']
        # name = request.form['name']
        # price = request.form['price']

        if file.filename == '':
            return "No selected file"
        u_id = current_user.id
        if file:
            # Save file to the static/uploads folder
            filename = file.filename
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # Store the correct path format in the database (static/uploads/)
            db_file_path = f'static/uploads/{filename}'

            # Insert into the database
            cursor = mysql.connection.cursor()
            cursor.execute(
                "INSERT INTO products (user_id, name, price, category, quantity, description, image_path) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (u_id, product_name, price, category, quantity, description, db_file_path))
            mysql.connection.commit()
            cursor.close()

            return redirect(url_for('upload'))
    return render_template('upload.html')


# Route to display products
@app.route('/view_products')
@login_required
def view_products():
    u_id=current_user.id
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM products WHERE user_id=%s ",(u_id,))
    products = cursor.fetchall()
    cursor.close()
    return render_template('view_products.html', products=products)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')

if __name__ == '__main__':
    UserAuth.create_user_table()
    Address.create_address_table()
    Product.create_product_table()
    app.run(debug=True)
