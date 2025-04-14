from cryptography.fernet import Fernet
import os
import getpass
from user_handler import UserManager

KEY_FILE = "../secret.key"

if not os.path.exists(KEY_FILE):
    key = Fernet.generate_key()
    with open(KEY_FILE, "wb") as key_file:
            key_file.write(key)

prompt = input("Create default admin user? (y/n)")
if prompt in ["y", "Y", 'yes', 'Yes', "YES"]:      
    print("lets create a admin user..")
    password = getpass.getpass(prompt="create password for admin:  ")
    phone = input("enter valid phone number (for alerts):   ")
    email = input('enter email address:  ')
    user_manager = UserManager("users.db")
    user_manager.add_user("admin", f"{password}", f"{email}", f"{phone}")
    print("username: admin default-password: admin added to users database")
    user_manager.close()
else:
     print("will not create admin user..\n")