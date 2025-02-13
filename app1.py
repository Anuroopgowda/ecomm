import json

import web3
from flask import Flask, render_template, request, redirect, flash, url_for, jsonify, session, abort
from flask_mysqldb import MySQL
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import csv

from requests.adapters import DEFAULT_RETRIES

from database import UserAuth, Address, Product, Cart, Order, Transaction
import os
import matplotlib.pyplot as plt
import pandas as pd
from web3 import Web3

# Connect to Ganache blockchain
ganache_url = "http://127.0.0.1:7545"  # Default Ganache RPC URL
web3 = Web3(Web3.HTTPProvider(ganache_url))

app = Flask(__name__) #init flask application
app.secret_key = 'Anu@441461' #Flask stores user session data (like login status) in a secure cookie.
                               # The secret key encrypts this session data to prevent tampering.

UPLOAD_FOLDER = 'static/uploads/'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)  # Ensure the folder exists
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Anu@441461'
app.config['MYSQL_DB'] = 'anuroop1'

mysql = MySQL(app) #establish connection between mysql and flask app

# LoginManager Configuration
login_manager = LoginManager() # manage user auth and for a session keeping user logged in all request
login_manager.init_app(app) # This links the LoginManager to the Flask application
login_manager.login_view = 'login' # if an unauthenticated user tries to access a protected route, they are redirected to the login page.

class User(UserMixin): #is used for managing user authentication and session handling with Flask-Login
    def __init__(self, id, name, email):
        self.id = id
        self.name = name
        self.email = email

@login_manager.user_loader  #load user details form database
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


# @app.route('/consumer')
# @login_required
# def consumer():
#     cursor = mysql.connection.cursor()
#     cursor.execute("SELECT * FROM products WHERE user_id!=%s AND quantity > 0", (current_user.id,))
#     products = cursor.fetchall()
#     cursor.close()
#     return render_template('consumer.html', products=products,name=current_user.name)

@app.route('/consumer')
@login_required
def consumer():
    cursor = mysql.connection.cursor()

    # Fetch products excluding those from the current user
    cursor.execute("SELECT * FROM products WHERE user_id!=%s AND quantity > 0", (current_user.id,))
    products = cursor.fetchall()

    # Fetch the total number of products in the cart for the current user
    cursor.execute("SELECT count(cart_id) FROM cart WHERE user_id = %s", (current_user.id,))
    cart_count = cursor.fetchone()[0] or 0  # If no items, default to 0
    print(cart_count)
    cursor.close()
    return render_template('consumer.html', products=products, name=current_user.name, cart_count=cart_count)

@app.route('/upload', methods=['POST', 'GET'])
@login_required
def upload():
    cur = mysql.connection.cursor()
    cur.execute('select * from blockaddress where user_id=%s', (current_user.id,))
    b_address = cur.fetchone()
    if not b_address:
        return redirect(url_for('add_block_address'))

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
    if not products:
        msg='No products to display'
        return render_template('view_products.html',msg=msg)
    cursor.close()
    return render_template('view_products.html', products=products)

# add_to_cart
# working on it
@app.route('/add_cart/<int:product_id>', methods=['GET'])
@login_required
def add_cart(product_id):
    user_id = current_user.id
    # cur=mysql.connection.cursor()
    # cur.execute('select * from cart where user_id=%s and product_id=%s',(user_id,product_id,))
    # result=cur.fetchone()
    # mysql.connection.close()
    # if result:
    #     return "<script>alert('Item already added to cart!'); window.location.href='/consumer';</script>"


    Cart.add_to_cart(user_id,product_id)
    return redirect(url_for('consumer'))


@app.route('/cart')
@login_required
def cart():
    addresses = Address.get_user_addresses(current_user.id)
    if not addresses:
        flash("Please add an address before placing an order.", "warning")
        return redirect(url_for('add_address_u'))  # Redirect to the address addition page
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


@app.route('/update_quantity/<int:product_id>/<int:quantity>', methods=['GET', 'POST'])
def update_quantity(product_id,quantity):
    print(f"{product_id} ,{quantity}")
    cur=mysql.connection.cursor()
    cur.execute('update products set quantity=quantity-%s where product_id=%s',(quantity, product_id,))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('all_order'))

# @app.route('/buy/<int:product_id>', methods=['GET', 'POST'])
# def buy(product_id):
#     product = Product.get_product_by_id(product_id)  # Fetch product details
#     addresses = Address.get_user_addresses(current_user.id)  # Fetch user addresses
#
#     if not addresses:
#         flash("Please add an address before placing an order.", "warning")
#         return redirect(url_for('add_address_u'))  # Redirect to the address addition page
#
#     if request.method == 'POST':
#         selected_address = request.form['address']
#         quantity = int(request.form['quantity'])
#         print(f"Received quantity: {quantity}")
#         conn = mysql.connection.cursor()
#         conn.execute('''INSERT INTO orders (product_id, user_id, quantity, price, address_id)
#                             VALUES (%s, %s, %s, %s, %s)''',
#                          (product_id, current_user.id, quantity, product[3] * quantity, selected_address))
#         mysql.connection.commit()
#         conn.close()
#
#
#         flash("Order placed successfully!", "success")
#         return redirect(url_for('update_quantity',product_id=product_id,quantity=quantity))
#
#
#     return render_template('buy.html', product=product, addresses=addresses)


# working on it
@app.route('/buy/<int:product_id>', methods=['GET', 'POST'])
@login_required
def buy(product_id):
    product = Product.get_product_by_id(product_id)  # Fetch product details
    addresses = Address.get_user_addresses(current_user.id)  # Fetch user addresses

    if not addresses:
        flash("Please add an address before placing an order.", "warning")
        return redirect(url_for('add_address_u'))  # Redirect to add address page

    if request.method == 'POST':
        selected_address = request.form['address']
        quantity = int(request.form['quantity'])
        total_price = product[3] * quantity  # Assuming product[3] contains price

        # Redirect to the payment page
        return redirect(url_for('payment', product_id=product_id, quantity=quantity, total_price=total_price, address_id=selected_address))

    return render_template('buy.html', product=product, addresses=addresses)


from web3 import Web3
# DEFAULT_RECEIVER = "0xF9988540e0aDd5Ba02F052f30BFE02E197438aF5"
@app.route('/payment', methods=['GET', 'POST'])
@login_required
def payment():
    product_id = request.args.get('product_id', type=int)
    quantity = request.args.get('quantity', type=int)
    total_price = request.args.get('total_price', type=float)
    address_id = request.args.get('address_id', type=int)

    if request.method == 'POST':
        product_id = request.form['product_id']
        cur = mysql.connection.cursor()
        cur.execute(
            'select b.block_address,p.user_id from products p,blockaddress b where p.user_id=b.user_id and product_id= %s',
            (product_id,))
        addr=cur.fetchone()
        DEFAULT_RECEIVER=addr[0]
        receiver_id=addr[1]
        print(DEFAULT_RECEIVER)
        mysql.connection.commit()
        cur.close()
        # Simulate payment processing (Replace with real payment gateway)
        payment_status = request.form.get('payment_status')  # This should come from your payment gateway
        b_address=request.form['sender']
        private_key=request.form['private_key']
        amount=float(request.form['amount'])
        if not web3.is_address(b_address) or not web3.is_address(DEFAULT_RECEIVER):
            return jsonify({"status": "failed", "message": "Invalid Ethereum address"})

        # Convert amount to Wei
        value = web3.to_wei(amount, "ether")

        # Get nonce (transaction count) for sender
        nonce = web3.eth.get_transaction_count(b_address)

        # Create transaction
        txn = {
            "nonce": nonce,
            "to": DEFAULT_RECEIVER,
            "value": value,
            "gas": 21000,
            "gasPrice": web3.to_wei("10", "gwei")
        }

        # Sign transaction with sender's private key
        signed_txn = web3.eth.account.sign_transaction(txn, private_key)

        # Send transaction
        txn_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
        if txn_hash:
        # if payment_status == "success":
            product_id=request.form['product_id']
            quantity=request.form['quantity']
            total_price=request.form['total_price']
            address_id=request.form['address_id']
            Transaction.add_to_transaction(current_user.id,receiver_id,product_id,total_price,amount)

            conn = mysql.connection.cursor()
            conn.execute('''INSERT INTO orders (product_id, user_id, quantity, price, address_id)
                            VALUES (%s, %s, %s, %s, %s)''',
                         (product_id, current_user.id, quantity, total_price, address_id))
            mysql.connection.commit()
            conn.close()

            flash("Payment successful! Order placed successfully!", "success")
            return redirect(url_for('update_quantity', product_id=product_id, quantity=quantity))
        else:
            flash("Payment failed. Please try again.", "danger")
            return redirect(url_for('buy', product_id=product_id))

    return render_template('payment.html', product_id=product_id, quantity=quantity, total_price=total_price, address_id=address_id)




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
        # cursor.execute("SELECT * FROM orders WHERE user_id = %s order by order_id desc", (user_id,))
        cursor.execute("select o.*,p.name,u.address from orders o left join products p on o.product_id=p.product_id left join useraddress u on o.address_id=u.address_id where o.user_id=%s order by o.order_id desc",(user_id,))
        orders = cursor.fetchall()
        if not orders:
            msg='no order'
            return render_template('view_all_order.html',msg=msg)
        # Close cursor
        cursor.close()

        # cur1=mysql.connection.cursor()
        # cur1.execute('select name from products where product_id=%s',(orders[0][2],))
        # product_name=cur1.fetchall()
        # cur1.close()
        #
        # cur2=mysql.connection.cursor()
        # cur2.execute('select address from userAddress where address_id=%s',(orders[0][5],))
        # address_d=cur2.fetchall()
        # cur2.close()
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
        print("review function:",product_id,user_id)
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

# review analysis
# Ensure 'static/' directory exists
STATIC_DIR = "static/chart"
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)


@app.route('/review_analysis/<int:product_id>')
@login_required
def review_analysis(product_id):
    df = pd.read_csv('reviews.csv', on_bad_lines='skip')
    product_reviews = df[df['product_id'] == product_id]
    print(product_id)
    print(product_reviews)

    if product_reviews.empty:
        return "No reviews available for this product."

    # **Sentiment Classification**
    product_reviews['sentiment'] = product_reviews['rating'].apply(
        lambda x: 'Positive' if x >= 4 else 'Neutral' if x == 3 else 'Negative'
    )

    # **Count Sentiment Distribution**
    sentiment_counts = product_reviews['sentiment'].value_counts()

    # **Decision Logic**
    positive_count = sentiment_counts.get('Positive', 0)
    neutral_count = sentiment_counts.get('Neutral', 0)
    negative_count = sentiment_counts.get('Negative', 0)
    total_reviews = len(product_reviews)

    if positive_count / total_reviews > 0.5:
        recommendation = "✅ Recommended to Buy! Most users are satisfied."
        color = "green"
    elif negative_count / total_reviews > 0.5:
        recommendation = "❌ Not Recommended. Too many bad reviews."
        color = "red"
    else:
        recommendation = "⚠️ Mixed Reviews – Consider Carefully."
        color = "orange"

    # **Generate Donut Chart**
    plt.figure(figsize=(6, 6))
    colors = ['#dc3545', '#ffc107','#28a745']  # Green, Yellow, Red
    plt.pie(
        sentiment_counts, labels=sentiment_counts.index, autopct='%1.1f%%',
        colors=colors, startangle=140, wedgeprops={'edgecolor': 'black'}
    )
    plt.gca().add_artist(plt.Circle((0, 0), 0.5, color='white'))  # Donut hole
    plt.title(f"Sentiment Analysis for Product {product_id}")

    # **Save the Plot**
    img_path = f"static/sentiment_chart_{product_id}.png"
    plt.savefig(img_path)
    plt.close()

    return render_template(
        'review_analysis.html',
        product_id=product_id,
        recommendation=recommendation,
        color=color,
        img_path=img_path,
        reviews=product_reviews.to_dict(orient='records')
    )

# ethereum address




@app.route('/add_block_address', methods=['POST', 'GET'])
@login_required
def add_block_address():
    user_id = current_user.id
    if request.method == 'POST':
        eth_address = request.form.get('ethAddress')

        # Validate Ethereum address
        if not Web3.is_address(eth_address):
            flash("Invalid Ethereum address!", "danger")
            return redirect(url_for('add_block_address'))

        try:
            cur = mysql.connection.cursor()
            cur.execute('SELECT * FROM blockaddress WHERE user_id = %s AND block_address = %s', (user_id, eth_address,))
            existing_entry = cur.fetchone()
            if existing_entry:
                flash("Ethereum address already added!", "warning")
                return redirect(url_for('add_block_address'))

            cur.execute('INSERT INTO blockaddress (user_id, block_address) VALUES (%s, %s)', (user_id, eth_address,))
            mysql.connection.commit()
            flash("Ethereum address added successfully!", "success")
        except Exception as e:
            mysql.connection.rollback()
            flash(f"Database error: {str(e)}", "danger")
        finally:
            cur.close()

        return redirect(url_for('business'))
    cur=mysql.connection.cursor()
    cur.execute('select * from blockaddress where user_id=%s',(user_id,))
    b_address=cur.fetchone()
    if b_address:
        msg='Ethereum address already added!'
        color='green'
    else:
        msg='Please add you Ethereum address!'
        color='red'
    return render_template('blockaddress.html',msg=msg,color=color)


@app.route('/transaction_b',methods=['POST','GET'])
def transaction_b():
    cur=mysql.connection.cursor()
    cur.execute('select * from transaction where receiver_id=%s',(current_user.id,))
    transaction=cur.fetchall()
    mysql.connection.commit()
    cur.close()
    msg='No Transaction!'
    if not transaction:
        return render_template('transaction_b.html',msg=msg)
    return render_template('transaction_b.html',transaction=transaction)

@app.route('/transaction_c',methods=['POST','GET'])
def transaction_c():
    cur=mysql.connection.cursor()
    cur.execute('select * from transaction where sender_id=%s',(current_user.id,))
    transaction=cur.fetchall()
    mysql.connection.commit()
    cur.close()
    msg = 'No Transaction!'
    if not transaction:
        return render_template('transaction_c.html',msg=msg)
    return render_template('transaction_c.html',transaction=transaction)


@app.route('/buy_all', methods=['POST', 'GET'])
@login_required
def buy_all():
    if request.method == "POST":
        cart_data = request.form.get("cart_data")  # For form submission
        if not cart_data:
            return abort(400, "Error: cart_data is missing")  # Proper error handling

        try:
            cart_items = json.loads(cart_data)  # Parse JSON
            print("new",cart_items)  # Debugging
            return render_template('buy_all.html', cart_items=cart_items)
        except json.JSONDecodeError as e:
            return abort(400, f"JSON Decode Error: {str(e)}")

    return abort(405, "Method Not Allowed")

@app.route('/payment_all', methods=['POST'])
@login_required
def payment_all():
    cart_data = request.form.get("cart_data")
    total_price = request.form.get("total_price")
    total_eth = request.form.get("total_eth")
    sender = request.form.get("eth_address")
    private_key = request.form.get("private_key")

    if not all([cart_data, total_price, total_eth, sender, private_key]):
        return abort(400, "Error: Missing required data")

    try:
        cart_items = json.loads(cart_data)  # Parse JSON
        print("Received Cart Data:", cart_items)  # Print data to terminal
        print("Total Price:", total_price)
        print("Total ETH Amount:", total_eth)
        print("Ethereum Address:", sender)
        print("Private Key:", private_key)

        if not web3.is_address(sender):
            return jsonify({"status": "failed", "message": "Invalid Ethereum sender address"})

        conn = mysql.connection.cursor()

        for index, cart in enumerate(cart_items):
            conn.execute('''SELECT b.block_address, p.user_id FROM products p 
                            JOIN blockaddress b ON p.user_id = b.user_id 
                            WHERE product_id = %s''', (cart['product_id'],))
            addr = conn.fetchone()

            if not addr:
                print(f"Product ID {cart['product_id']} not found, skipping!")
                continue

            print('Product Owner Address:', addr)

            amount_eth = (cart['subtotal'] / float(total_price)) * float(total_eth)
            value = web3.to_wei(amount_eth, "ether")

            # nonce = web3.eth.get_transaction_count(sender) + index
            # gas_price = web3.eth.gas_price
            min_gas_price = web3.to_wei(10, "gwei")  # Minimum Gas Price
            gas_price = max(int(web3.eth.gas_price * 1.2), min_gas_price)  # Increase by 20%

            nonce = web3.eth.get_transaction_count(sender, "pending")  # Ensure correct nonce

            txn = {
                "nonce": nonce,
                "to": addr[0],
                "value": value,
                "gas": 21000,
                "gasPrice": gas_price
            }

            print(f"Signing transaction for {cart['product_id']}...")
            signed_txn = web3.eth.account.sign_transaction(txn, private_key)
            txn_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)

            if txn_hash:
                print(f"Transaction successful for product {cart['product_id']}")
                Transaction.add_to_transaction(current_user.id, addr[1], cart['product_id'], cart['subtotal'],
                                               amount_eth)

                conn.execute('''INSERT INTO orders (product_id, user_id, quantity, price, address_id)
                                VALUES (%s, %s, %s, %s, %s)''',
                             (cart['product_id'], current_user.id, cart['quantity'], cart['subtotal'],
                              cart['address_id']))
                mysql.connection.commit()
                conn.execute('''delete from cart where product_id=%s''',
                             (cart['product_id'],))
                mysql.connection.commit()
                conn.execute('update products set quantity=quantity-%s where product_id=%s', (cart['quantity'], cart['product_id'],))
                mysql.connection.commit()

        conn.close()
        flash("Payment successful! Orders placed successfully!", "success")
        return redirect(url_for('all_order'))

    except json.JSONDecodeError as e:
        return abort(400, f"JSON Decode Error: {str(e)}")
    except Exception as e:
        return abort(500, f"Server Error: {str(e)}")


if __name__ == '__main__':
    # UserAuth.create_user_table()
    # Address.create_address_table()
    # Product.create_product_table()
    # Cart.create_cart_table()
    # Order.create_order_table()
    # UserAuth.create_block_address()
    # Transaction.create_transaction_table()
    app.run(debug=True)
