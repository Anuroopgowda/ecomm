import os
from flask import Flask, render_template, request, redirect, flash, url_for, jsonify
from flask_mysqldb import MySQL
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import csv
from database import UserAuth, Address, Product, Cart, Order

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
    try:
        # Create a cursor
        cursor = mysql.connection.cursor()
        # Fetch orders related to the business user's products
        cursor.execute("""
            SELECT 
                o.order_id, 
                u.name as uname, 
                p.name, 
                o.price, 
                o.quantity, 
                a.address,
                o.status
            FROM orders o
            JOIN products p ON o.product_id = p.product_id
            JOIN userAuth u ON o.user_id = u.id
            JOIN userAddress a ON o.address_id = a.address_id
            WHERE p.user_id = %s
            ORDER BY o.order_id DESC
        """, (current_user.id,))

        orders = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description]  # Get column names
        orders = [dict(zip(column_names, row)) for row in orders]
        cursor.close()
        return render_template('Business.html', name=current_user.id, orders=orders)

    except Exception as e:
        print(f"Error fetching orders: {e}")
        return render_template('error.html', message="Unable to fetch business orders.")


@app.route('/consumer')
@login_required
def consumer():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM products WHERE user_id!=%s AND quantity > 0", (current_user.id,))
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

# @app.route('/all_order')
# @login_required
# def all_order():
#     return render_template('view_all_order.html')







# @app.route('/buy/<int:product_id>', methods=['GET', 'POST'])
# @login_required
# def buy(product_id):
#     product = Product.get_product_by_id(product_id)  # Fetch product details
#     addresses = Address.get_user_addresses(current_user.id)  # Fetch user addresses
#
#     # If no address is found, prompt the user to add one
#     if not addresses:
#         flash("Please add an address before placing an order.", "warning")
#         return redirect(url_for('add_address'))  # Redirect to the address addition page
#
#     if request.method == 'POST':
#         selected_address = request.form['address']
#         quantity = int(request.form['quantity'])
#         # updating the quantity of the product
#         conn = mysql.connection.cursor()
#         conn.execute('UPDATE products SET quantity = quantity - %s WHERE product_id = %s', (quantity, product_id))
#         mysql.connection.commit()
#         conn.close()
#
#         # Process order logic here (e.g., deduct stock, create order entry)
#
#         flash("Order placed successfully!", "success")
#         return redirect(url_for('order_confirmation'))  # Redirect after placing the order
#
#     return render_template('buy.html', product=product, addresses=addresses)

# working
@app.route('/update_quantity/<int:product_id>/<int:quantity>', methods=['GET', 'POST'])
def update_quantity(product_id,quantity):
    print(f"{product_id} ,{quantity}")
    cur=mysql.connection.cursor()
    cur.execute('update products set quantity=quantity-%s where product_id=%s',(quantity, product_id,))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('all_order'))

@app.route('/buy/<int:product_id>', methods=['GET', 'POST'])
def buy(product_id):
    product = Product.get_product_by_id(product_id)  # Fetch product details
    addresses = Address.get_user_addresses(current_user.id)  # Fetch user addresses

    if not addresses:
        flash("Please add an address before placing an order.", "warning")
        return redirect(url_for('add_address'))  # Redirect to the address addition page

    if request.method == 'POST':
        selected_address = request.form['address']
        quantity = int(request.form['quantity'])
        print(f"Received quantity: {quantity}")
        conn = mysql.connection.cursor()
        conn.execute('''INSERT INTO orders (product_id, user_id, quantity, price, address_id)
                            VALUES (%s, %s, %s, %s, %s)''',
                         (product_id, current_user.id, quantity, product[3] * quantity, selected_address))
        mysql.connection.commit()
        conn.close()


        flash("Order placed successfully!", "success")
        return redirect(url_for('update_quantity',product_id=product_id,quantity=quantity))


    return render_template('buy.html', product=product, addresses=addresses)




@app.route('/add_order', methods=['POST'])
@login_required
def add_order():
    try:
        # Parse JSON data from the frontend
        data = request.get_json()

        # Get the current user_id from Flask-Login
        user_id = current_user.id

        # Extract other data from the frontend request
        product_id = data.get('product_id')
        quantity = data.get('quantity')
        total_price = data.get('total_price')
        address_id = data.get('address_id')

        # Call the static method to add the order to the database
        success = Order.add_order(user_id, product_id, total_price, quantity, address_id)

        if success:
            flash("Order placed successfully!", "success")  # Optional: Flash message
            return jsonify({"success": True, "redirect_url": url_for('all_order')})
        else:
            return jsonify({"success": False, "message": "Failed to place order. Please try again."}), 500

    except Exception as e:
        # Handle any errors
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/all_order')
@login_required
def all_order():
    try:
        # Create a cursor
        cursor = mysql.connection.cursor()

        # Get the current logged-in user's ID
        user_id = current_user.id

        # Fetch the orders for the current user
        cursor.execute("SELECT * FROM orders WHERE user_id = %s", (user_id,))
        orders = cursor.fetchall()

        # Close cursor
        cursor.close()

        # Render the view_all_order.html page with the fetched orders
        return render_template('view_all_order.html', orders=orders)

    except Exception as e:
        print(f"Error: {e}")
        return render_template('error.html', message="Unable to fetch orders.")

# working on it
@app.route('/mark_delivered/<int:order_id>', methods=['POST'])
def mark_delivered(order_id):
    try:
        conn = mysql.connection.cursor()
        conn.execute('UPDATE orders SET status = %s WHERE order_id = %s', ("Delivered", order_id))
        mysql.connection.commit()  # Commit the changes
        conn.close()  # Close the cursor
        return redirect(url_for('business'))
    except Exception as e:
        print(f"Error updating order status: {e}")
        return render_template('error.html', message="Unable to update order status.")

# Path to store reviews
REVIEWS_FILE = "reviews.csv"

# Ensure CSV file has headers
if not os.path.exists(REVIEWS_FILE):
    with open(REVIEWS_FILE, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Product ID", "User ID", "Rating", "Review"])

@app.route('/review/<int:product_id>/<int:user_id>', methods=['GET', 'POST'])
def review(product_id, user_id):
    if request.method == 'POST':
        review_text = request.form['review']
        rating = request.form['rating']

        # Store review in a CSV file
        with open(REVIEWS_FILE, 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([product_id, user_id, rating, review_text])

        return redirect(url_for('all_order'))

    return render_template('review.html', product_id=product_id, user_id=user_id)

if __name__ == '__main__':
    # UserAuth.create_user_table()
    # Address.create_address_table()
    # Product.create_product_table()
    # Cart.create_cart_table()
    # Order.create_order_table()
    app.run(debug=True)
