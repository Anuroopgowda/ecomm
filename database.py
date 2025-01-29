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
                    street_no INT,
                    address_line1 VARCHAR(255) NOT NULL,
                    address_line2 VARCHAR(255),
                    city VARCHAR(20) NOT NULL,
                    region VARCHAR(100),
                    postal_code VARCHAR(20),
                    country VARCHAR(100),
                    FOREIGN KEY (user_id) REFERENCES userAuth(id)
                )
            ''')
            mysql.connection.commit()
            cursor.close()

    @staticmethod
    def add_address(u_id, street_no, address_line1, address_line2, city, region, postal_code, country):
        try:
            # Connect to the database and execute the query
            cursor = mysql.connection.cursor()
            query = '''
                INSERT INTO userAddress (
                    user_id, street_no, address_line1, address_line2,
                    city, region, postal_code, country
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            '''
            cursor.execute(query, (u_id, street_no, address_line1, address_line2, city, region, postal_code, country))
            mysql.connection.commit()
            cursor.close()
            return True  # Successfully inserted the address
        except Exception as e:
            # Log the error for debugging purposes
            print(f"Error during address insertion: {e}")
            return False  # Insertion failed

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

