import os
import sqlite3
import bcrypt
import phonenumbers

class UserManager:
    def __init__(self, dbfile):
        self.dbfile = dbfile
        self.conn = sqlite3.connect(self.dbfile)
        self.create_db()

    def format_phone_number(self, raw_phone):
        """Format the phone number into E.164 format like +15555555555"""
        try:
            number = phonenumbers.parse(raw_phone, "CA")  # Use "US" as default country code or make it dynamic
            if phonenumbers.is_valid_number(number):
                return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)
            else:
                print("⚠️ Invalid phone number.")
                return None
        except phonenumbers.NumberParseException:
            print("❌ Failed to parse phone number.")
            return None

    def create_db(self):
        """Create the users table if it doesn't exist."""
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                user TEXT UNIQUE,
                password TEXT,
                email TEXT,
                phone TEXT
            )
        ''')
        self.conn.commit()

    def encrypt_password(self, password):
        """Hash the password using bcrypt."""
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def check_password(self, plain_password, hashed_password):
        """Verify the provided password against the stored hash."""
        return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())

    def add_user(self, username, password, email, phone):
        """Add a new user to the database securely."""
        
        try:
            formatted_phone = self.format_phone_number(phone)
            if not formatted_phone:
                print("❌ Could not add user: Invalid phone number.")
                return False
            with self.conn as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO users (user, password, email, phone) VALUES (?, ?, ?, ?)",
                    (username.strip().lower(), self.encrypt_password(password), email.strip().lower(), formatted_phone)
                )
                print(f"User '{username}' added to database ✅")
                #print(f"{formatted_phone}")
                return True
        except sqlite3.IntegrityError:
            print(f"⚠️ Username or email already exists.")
            return False
        except sqlite3.Error as e:
            print(f"❌ SQLite error: {e}")
            return False
        
    def del_user(self, username):
        """Delete a user from the database securely."""
        try:
            with self.conn as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM users WHERE user = ?",
                    (username.strip().lower(),)
                )
                if cursor.rowcount == 0:
                    print(f"⚠️ User '{username}' not found.")
                    return False
                else:
                    print(f"✅ User '{username}' deleted from database.")
                    return True
        except sqlite3.Error as e:
            print(f"❌ SQLite error: {e}")
            return False
          
    def auth_user(self, username, plain_password):
        """Checks a user's stored hashed password from the database."""
        try:
            with self.conn as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT password FROM users WHERE user = ?;",
                    (username.strip().lower(),)
                )
                result = cursor.fetchone()
                if result is None:
                    print(f"⚠️ User '{username}' not found.")
                    return False
                return self.check_password(plain_password, result[0])
        except sqlite3.Error as e:
            print(f"❌ SQLite error: {e}")
            return False
        
    def get_all_phone_numbers(self):
        """Return a list of unique phone numbers using SQL DISTINCT."""
        try:
            with self.conn as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT phone FROM users WHERE phone IS NOT NULL")
                rows = cursor.fetchall()
                return [row[0] for row in rows]
        except sqlite3.Error as e:
            print(f"❌ SQLite error while fetching phone numbers: {e}")
            return []
        
    def close(self):
        self.conn.close()

    def __del__(self):
        self.conn.close()


