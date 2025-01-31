from flask import Flask,render_template, request
from flask_mysqldb import MySQL
import os
app=Flask(__name__)
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Anu@441461'
app.config['MYSQL_DB'] = 'anuroop'
mysql = MySQL(app)

class UserAuth:
    @staticmethod
    def create_user_table():
        """Create the userAuth table if it does not already exist."""
        with app.app_context():
            cursor = mysql.connection.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS userAuth (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    mobile_number VARCHAR(15) NOT NULL,
                    password VARCHAR(25) NOT NULL
                )
            ''')
            mysql.connection.commit()
            cursor.close()

    @staticmethod
    def register_user(name, email, mobile_number, password):
        """Register a new user."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                'INSERT INTO userAuth (name, email, mobile_number, password) VALUES (%s, %s, %s, %s)',
                (name, email, mobile_number, password)
            )
            mysql.connection.commit()
            cursor.close()
            return True
        except Exception as e:
            print(f"Error during registration: {e}")
            return False

    @staticmethod
    def login_user(email, password):
        """Authenticate a user by email and password."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute('SELECT * FROM userAuth WHERE email=%s AND password=%s', (email, password))
            account = cursor.fetchone()
            cursor.close()
            if account:
                return True, {"id": account[0], "name": account[1], "email": account[2]}
            else:
                return False, None
        except Exception as e:
            print(f"Error during login: {e}")
            return False, None

    @staticmethod
    def get_user_by_id(user_id):
        """Retrieve user details based on user ID."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute('SELECT * FROM userAuth WHERE id=%s', (user_id,))
            user = cursor.fetchone()
            cursor.close()
            if user:
                # Return user details as a dictionary
                return {"id": user[0], "name": user[1], "email": user[2], "mobile_number": user[3]}
            return None
        except Exception as e:
            print(f"Error retrieving user by ID: {e}")
            return None

class Address:
    @staticmethod
    def create_address_table():
        """Create the Address table if it does not already exist."""
        with app.app_context():
            cursor = mysql.connection.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS userAddress (
                    address_id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    address VARCHAR(255),
                    FOREIGN KEY (user_id) REFERENCES userAuth(id)
                )
            ''')
            mysql.connection.commit()
            cursor.close()

    @staticmethod
    def add_address(u_id, street_no, address_line1, address_line2, city, region, postal_code, country):
        try:
            # Connect to the database and execute the query
            str1=" ".join(filter(None, map(str, [
                  street_no,
                  address_line1,
              address_line2,
                  city,
                  region,
                 postal_code,
                  country
            ])))
            cursor = mysql.connection.cursor()
            query = '''
                INSERT INTO userAddress (
                    user_id, address
                ) VALUES (%s, %s)
            '''
            cursor.execute(query, (u_id, str1))
            mysql.connection.commit()
            cursor.close()
            return True  # Successfully inserted the address
        except Exception as e:
            # Log the error for debugging purposes
            print(f"Error during address insertion: {e}")
            return False  # Insertion failed

    @staticmethod
    def get_user_addresses(user_id):
        try:
            cursor = mysql.connection.cursor()
            cursor.execute('SELECT * FROM userAddress WHERE user_id=%s', (user_id,))
            user = cursor.fetchall()
            cursor.close()
            if user:
                # Return user details as a dictionary
                return user
            return None
        except Exception as e:
            print(f"Error retrieving user by ID: {e}")
            return None


class Product:
    @staticmethod
    def create_product_table():
        with app.app_context():
            cursor = mysql.connection.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS products (
                product_id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                name VARCHAR(100) NOT NULL,
                price DECIMAL(10,2) NOT NULL,
                category VARCHAR(25) NOT NULL,
                quantity INT NOT NULL,
                description VARCHAR(255) NOT NULL,
                image_path VARCHAR(255) NOT NULL,
                FOREIGN KEY (user_id) REFERENCES userAuth(id))
            ''')
            mysql.connection.commit()
            cursor.close()

    @staticmethod
    def add_products(u_id, name, price, category, quantity, desc, file):
        print("if")
        if 'image' not in request.files:
            return "No file part"
        #
        # file = request.files['image']
        # name = request.form['name']
        # price = request.form['price']

        if file.filename == '':
            return "No selected file"

        if file:
            # Save file to the static/uploads folder
            filename = file.filename
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # Store the correct path format in the database (static/uploads/)
            db_file_path = f'static/uploads/{filename}'

            try:
                # Insert into the database
                cursor = mysql.connection.cursor()
                print(db_file_path)
                print("HI")
                cursor.execute("INSERT INTO products (user_id, name, price, category, quantity, description, image_path) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                               (u_id, name, price, category, quantity, desc, db_file_path))
                mysql.connection.commit()
                cursor.close()
                return True
            except Exception as e:
                print(f"Error during product insertion: {e}")
                return False

    @staticmethod
    def get_product_by_id(product_id):
        try:
            cursor = mysql.connection.cursor()
            cursor.execute('SELECT * FROM products WHERE product_id=%s', (product_id,))
            user = cursor.fetchone()
            cursor.close()
            if user:
                # Return user details as a dictionary
                return user
            return None
        except Exception as e:
            print(f"Error retrieving user by ID: {e}")
            return None


# CART
class Cart:
    @staticmethod
    def create_cart_table():
        """Create the cart table if it does not already exist."""
        with app.app_context():
            cursor = mysql.connection.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cart (
    cart_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    UNIQUE (user_id, product_id),  -- Prevents duplicate product entries for the same user
    FOREIGN KEY (user_id) REFERENCES userAuth(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
)

            ''')
            mysql.connection.commit()
            cursor.close()
    @staticmethod
    def add_to_cart(user_id,product_id):
        try:
            # Connect to the database and execute the query
            cursor = mysql.connection.cursor()
            query = '''
                INSERT INTO cart (
                    user_id, product_id
                ) VALUES (%s, %s)
            '''
            cursor.execute(query, (user_id, product_id))
            mysql.connection.commit()
            cursor.close()
            return True  # Successfully inserted the address
        except Exception as e:
            # Log the error for debugging purposes
            print(f"Error during  insertion: {e}")
            return False  # Insertion failed


class Order:
    @staticmethod
    def create_order_table():
        with app.app_context():
            cursor = mysql.connection.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    order_id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    product_id INT NOT NULL,
                    price INT NOT NULL,
                    quantity INT NOT NULL,
                    address_id INT NOT NULL,
                    status VARCHAR(20) DEFAULT 'Pending',
                    FOREIGN KEY (user_id) REFERENCES userAuth(id) ON DELETE CASCADE,
                    FOREIGN KEY (address_id) REFERENCES userAddress(address_id) ON DELETE CASCADE,
                    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
                )
            ''')

            mysql.connection.commit()
            cursor.close()

    @staticmethod
    def add_order(user_id,product_id,price,quantity,address_id):
        try:
            # Insert into the database
            cursor = mysql.connection.cursor()
            cursor.execute(
                "INSERT INTO orders (user_id, product_id, price, quantity, address_id) VALUES (%s, %s, %s, %s, %s)",
                (user_id, product_id, price, quantity, address_id))
            mysql.connection.commit()
            cursor.close()
            return True
        except Exception as e:
            print(f"Error during product insertion: {e}")
            return False

