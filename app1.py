import base64
import io
import json
import os
from flask import Flask, render_template, request, redirect, flash, url_for, jsonify, session
from flask_mysqldb import MySQL
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import csv
from database import UserAuth, Address, Product, Cart, Order
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use Agg backend for non-GUI environments


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
def home():
    cur=mysql.connection.cursor()
    cur.execute('select * from products where quantity>0')
    products=cur.fetchall()
    return render_template('home.html',products=products)


@app.route('/index')
def index():
    return render_template('index.html')

# @app.route('/register', methods=['POST', 'GET'])
# def register():
#     if request.method == 'POST':
#         name = request.form['name']
#         email = request.form['email']
#         mobile_number = request.form['mobile_number']
#         password = request.form['password']
#         success = UserAuth.register_user(name, email, mobile_number, password)
#         if success:
#             flash("Registration successful! Please log in.", "success")
#         else:
#             flash("Registration failed. Try again.", "danger")
#         return redirect(url_for('index'))
#     return render_template('register.html')

@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        mobile_number = request.form['mobile_number']
        password = request.form['password']

        # Check if user already exists
        if UserAuth.user_exists(email, mobile_number):
            flash("User with this email already exists. Please log in.", "warning")
            return redirect(url_for('register'))  # Keep user on the registration page

        # Register new user
        success = UserAuth.register_user(name, email, mobile_number, password)

        if success:
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for('login'))
        else:
            flash("Registration failed. Try again.", "danger")
            return redirect(url_for('register'))

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
            flash("Invalid credentials. Please try again.", "danger")
            return redirect(url_for('index'))  # Redirect ensures flash messages persist

    return render_template('index.html')  # Ensure login page is rendered properly


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

# user_address
@app.route('/add_address_u', methods=['POST', 'GET'])
@login_required
def add_address_u():
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
        return redirect(url_for('add_address_u'))
    return render_template('add_address_u.html')

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
                u.mobile_number,
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
    return render_template('consumer.html', products=products,name=current_user.name)

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
        return redirect(url_for('upload'))
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
    addresses = Address.get_user_addresses(current_user.id)  # Fetch user addresses
    # Correct SQL query to fetch products in the cart for the current user
    cursor.execute("""
        SELECT p.*,c.* FROM cart c
        JOIN products p ON c.product_id = p.product_id
        WHERE c.user_id = %s
    """, (current_user.id,))

    products = cursor.fetchall()
    cursor.close()

    return render_template('cart.html', products=products,address=addresses)

@app.route('/remove_from_cart/<int:cart_id>', methods=['POST','GET'])
def remove_from_cart(cart_id):
    user_id = current_user.id
    conn = mysql.connection.cursor()

    conn.execute("DELETE FROM cart WHERE cart_id = %s", (cart_id,))
    conn.connection.commit()
    conn.close()
    flash('Item removed from cart', 'success')

    return redirect(url_for('cart'))


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
    return redirect(url_for('home'))



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
        return redirect(url_for('add_address_u'))  # Redirect to the address addition page

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

# cart checkout
# @app.route('/checkout', methods=['POST'])
# def checkout():
#     cart = session.get('cart', [])  # Retrieve cart items from session
#     addresses = Address.get_user_addresses(current_user.id)  # Fetch user addresses
#
#     if not cart:
#         flash("Your cart is empty.", "warning")
#         return redirect(url_for('cart'))  # Redirect to cart page if empty
#
#     if not addresses:
#         flash("Please add an address before placing an order.", "warning")
#         return redirect(url_for('add_address'))  # Redirect if no address available
#
#     selected_address = request.form.get('address')  # Get selected address
#     orders = []  # Store processed orders
#
#     conn = mysql.connection.cursor()
#
#     for item in cart:
#         product_id = item['product_id']
#         quantity = int(request.form.get(f'quantity-{product_id}', 1))  # Get quantity per product
#         coupon_code = request.form.get(f'coupon-{product_id}', '')  # Get coupon per product
#
#         product = Product.get_product_by_id(product_id)  # Fetch product details
#
#         if not product:
#             flash(f"Product with ID {product_id} not found.", "danger")
#             continue
#
#         price = product[3] * quantity  # Base price calculation
#
#         if coupon_code == "ANU123":  # Apply discount
#             price *= 0.95  # 5% discount
#
#         # Insert order into database
#         conn.execute('''INSERT INTO orders (product_id, user_id, quantity, price, address_id)
#                         VALUES (%s, %s, %s, %s, %s)''',
#                      (product_id, current_user.id, quantity, price, selected_address))
#
#         orders.append({'product_id': product_id, 'quantity': quantity})  # Store order info
#
#     mysql.connection.commit()
#     conn.close()
#
#     # Clear cart after successful checkout
#     session['cart'] = []
#
#     flash("Order placed successfully!", "success")
#
#     # Redirect to update quantity for all ordered products
#     return redirect(url_for('update_quantity', orders=orders))


@app.route('/checkout', methods=['POST'])
def checkout():
    try:
        # Extract cart data from form
        cart_data = request.form.get("cart_data")
        cart_items = json.loads(cart_data)  # Convert JSON string to Python object

        for item in cart_items:
            cart_id = item["product_id"]
            quantity = item["quantity"]
            subtotal = item["subtotal"]
            address_id = item["address_id"]
            conn=mysql.connection.cursor()
            conn.execute('''select * from cart where cart_id=%s''',(cart_id,))
            cart_details=conn.fetchall()
            mysql.connection.commit()
            conn.close()
            product_id=cart_details[0][2]

            print(product_id)
            conn = mysql.connection.cursor()
            conn.execute('''INSERT INTO orders (product_id, user_id, quantity, price, address_id)
                                        VALUES (%s, %s, %s, %s, %s)''',
                         (product_id, current_user.id, quantity, subtotal, address_id))
            mysql.connection.commit()
            conn.close()
            conn = mysql.connection.cursor()
            conn.execute('''delete from cart where product_id=%s''',
                         (product_id,))
            mysql.connection.commit()
            conn.close()
            cur = mysql.connection.cursor()
            cur.execute('update products set quantity=quantity-%s where product_id=%s', (quantity, product_id,))
            mysql.connection.commit()
            cur.close()
            flash("Order placed successfully!", "success")





        return redirect(url_for("all_order"))  # Redirect to order confirmation page

    except Exception as e:
         # Rollback if error occurs
        return jsonify({"error": str(e)}), 500



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
        cursor.execute("SELECT * FROM orders WHERE user_id = %s order by order_id desc", (user_id,))
        orders = cursor.fetchall()

        # Close cursor
        cursor.close()

        cur1=mysql.connection.cursor()
        cur1.execute('select name from products where product_id=%s',(orders[0][2],))
        product_name=cur1.fetchall()
        cur1.close()

        cur2=mysql.connection.cursor()
        cur2.execute('select address from userAddress where address_id=%s',(orders[0][5],))
        address_d=cur2.fetchall()
        cur2.close()
        # Render the view_all_order.html page with the fetched orders
        return render_template('view_all_order.html', orders=orders,product_name=product_name,address_d=address_d)

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


CONTACT_FILE = "contact.csv"

# Ensure CSV file has headers
if not os.path.exists(CONTACT_FILE):
    with open(CONTACT_FILE, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["NAME", "EMAIL ID", "QUERY"])

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        query = request.form['query']

        # Store review in a CSV file
        with open(CONTACT_FILE, 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([name, email, query])

        return redirect(url_for('contact'))

    return render_template('contact_us.html')

@app.route('/search_filter', methods=['GET'])
@login_required
def search_filter():
    try:
        # Get search query, price filter, and category filter from request
        search_query = request.args.get('query', '').strip().lower()
        filter_option = request.args.get('filter', 'default')
        category_filter = request.args.get('category', 'all').lower()

        conn = mysql.connection.cursor()

        # Base SQL query: Exclude current user's products
        query = "SELECT * FROM products WHERE user_id != %s AND quantity > 0 AND LOWER(name) LIKE %s"
        params = (current_user.id, f"%{search_query}%")

        # Apply category filter
        if category_filter != "all":
            query += " AND LOWER(category) = %s"
            params += (category_filter,)

        # Apply sorting based on price filter
        if filter_option == "low-to-high":
            query += " ORDER BY price ASC"
        elif filter_option == "high-to-low":
            query += " ORDER BY price DESC"

        conn.execute(query, params)
        products = conn.fetchall()
        conn.close()

        # Convert product data to JSON format
        product_list = []
        for product in products:
            product_list.append({
                "product_id": product[0],
                "user_id": product[1],
                "name": product[2],
                "price": product[3],
                "category": product[4],
                "quantity": product[5],
                "description": product[6],
                "image_path": product[7]
            })

        return jsonify(product_list)  # Return JSON response

    except Exception as e:
        return jsonify({"error": str(e)}), 500  # Return error response


# @app.route('/update_product/<int:product_id>',methods=['POST','GET'])
# def update_p(product_id):
#     if request.method=='POST':
#         # if 'image' not in request.files or request.files['image'].filename == '':
#         #     flash("No file selected!", "warning")
#         #     return redirect(url_for('update_product',product_id=product_id))
#         print("anuroop")
#         file = request.files['image']
#         filename = file.filename
#         file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
#         file.save(file_path)
#         db_file_path = f'static/uploads/{filename}'
#         conn=mysql.connection.cursor()
#         conn.execute('''UPDATE products
#                 SET name = %s, price = %s, category = %s, quantity = %s, description = %s, image_path = %s
#                 WHERE user_id = %s AND id = %s ''',(request.form['name'], request.form['price'], request.form['category'], request.form['quantity'],
#                  request.form['desc'], db_file_path, current_user.id, product_id))
#         mysql.connection.commit()
#         conn.close()
#         return redirect(url_for('view_products'))
#     print("anuroop 1")
#     conn=mysql.connection.cursor()
#     conn.execute('select * from products where product_id=%s',(product_id,))
#     product=conn.fetchone()
#     mysql.connection.commit()
#     conn.close()
#     return render_template('update_product.html',product=product)

@app.route('/update_product/<int:product_id>', methods=['POST', 'GET'])
def update_p(product_id):
    conn = mysql.connection.cursor()
    conn.execute('SELECT * FROM products WHERE product_id = %s', (product_id,))
    product = conn.fetchone()
    conn.close()

    if request.method == 'POST':
        file = request.files.get('image')
        if file and file.filename != '':
            filename = file.filename
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            db_file_path = f'static/uploads/{filename}'
        else:
            db_file_path = product[7]  # Keep existing image if no new file is uploaded

        conn = mysql.connection.cursor()
        conn.execute('''
            UPDATE products 
            SET name = %s, price = %s, category = %s, quantity = %s, description = %s, image_path = %s
            WHERE user_id = %s AND product_id = %s
        ''', (request.form['name'], request.form['price'], request.form['category'], request.form['quantity'],
              request.form['desc'], db_file_path, current_user.id, product_id))

        mysql.connection.commit()
        conn.close()
        return redirect(url_for('view_products' ))

    return render_template('update_product.html', product=product)


# analysis

# Sample review data
reviews = [
    {'product_id': 5, 'user_id': 1, 'rating': 2, 'review_text': 'good'},
    {'product_id': 6, 'user_id': 1, 'rating': 2, 'review_text': 'good'},
    {'product_id': 7, 'user_id': 9, 'rating': 4, 'review_text': 'good'},
    {'product_id': 5, 'user_id': 9, 'rating': 1, 'review_text': 'bad'},
    {'product_id': 8, 'user_id': 2, 'rating': 5, 'review_text': 'Excellent product!'},
    {'product_id': 5, 'user_id': 3, 'rating': 3, 'review_text': 'Average quality'},
    {'product_id': 6, 'user_id': 4, 'rating': 4, 'review_text': 'Very useful and durable'},
    {'product_id': 7, 'user_id': 5, 'rating': 5, 'review_text': 'Highly recommended!'},
    {'product_id': 8, 'user_id': 6, 'rating': 1, 'review_text': 'Not worth the price'},
    {'product_id': 5, 'user_id': 7, 'rating': 4, 'review_text': 'Good value for money'},
    {'product_id': 6, 'user_id': 8, 'rating': 3, 'review_text': 'Satisfactory performance'},
    {'product_id': 7, 'user_id': 10, 'rating': 2, 'review_text': 'Could be better'},
    {'product_id': 8, 'user_id': 11, 'rating': 5, 'review_text': 'Amazing! Loved it!'},
    {'product_id': 5, 'user_id': 12, 'rating': 1, 'review_text': 'Worst experience ever'},
    {'product_id': 6, 'user_id': 13, 'rating': 5, 'review_text': 'Superb quality!'},
    {'product_id': 7, 'user_id': 14, 'rating': 3, 'review_text': 'Not bad, but expected better'},
    {'product_id': 8, 'user_id': 15, 'rating': 4, 'review_text': 'Great product, good support'},
]


# Convert review data to a pandas DataFrame
df = pd.DataFrame(reviews)
# @app.route('/review_analysis/<int:product_id>', methods=['GET'])
# def review_analysis(product_id):
#     # Filter reviews for the given product
#     product_reviews = df[df['product_id'] == product_id]
#
#     # Analyze ratings
#     rating_analysis = product_reviews['rating'].value_counts().sort_index()
#     rating_analysis = rating_analysis.to_dict()  # Convert to dict for JSON response
#
#     return jsonify(rating_analysis)

@app.route('/review_analysis/<int:product_id>', methods=['GET'])
def review_analysis(product_id):
    product_reviews = df[df['product_id'] == product_id]

    if product_reviews.empty:
        return jsonify({"message": "No reviews found for this product"}), 404

    # Analyze ratings
    rating_analysis = product_reviews['rating'].value_counts().sort_index()

    # Generate visualization
    plt.figure(figsize=(6, 4))
    plt.bar(rating_analysis.index, rating_analysis.values, color=['red', 'orange', 'yellow', 'lightgreen', 'green'])
    plt.xlabel("Ratings")
    plt.ylabel("Count")
    plt.title(f"Review Analysis for Product {product_id}")
    plt.xticks(range(1, 6))  # Rating scale from 1 to 5
    plt.grid(axis='y', linestyle='--', alpha=0.7)

    # Save plot to a buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    encoded_image = base64.b64encode(buffer.getvalue()).decode('utf-8')
    buffer.close()
    plt.close()  # Close the plot to free memory

    # Recommendation based on average rating
    avg_rating = product_reviews['rating'].mean()
    recommendation = "Recommended" if avg_rating >= 3 else "Not Recommended"
    print(rating_analysis.to_dict())
    return jsonify({
        "ratings": rating_analysis.to_dict(),
        "average_rating": round(avg_rating, 2),
        "recommendation": recommendation,
        "chart": f"data:image/png;base64,{encoded_image}"
    })

if __name__ == '__main__':
    # UserAuth.create_user_table()
    # Address.create_address_table()
    # Product.create_product_table()
    # Cart.create_cart_table()
    # Order.create_order_table()
    app.run(debug=True)
