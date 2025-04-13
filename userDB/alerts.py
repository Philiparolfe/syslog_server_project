# Download the helper library from https://www.twilio.com/docs/python/install
from twilio.rest import Client
import yaml
from cryptography.fernet import Fernet
from user_handler import UserManager

class AlertHandler:
    def __init__(self, __key="../secret.key", __config_file_path = "../config.yaml"):
        self.key_file = __key
        self.config_file_path = __config_file_path
        

    def encrypt_twilio_credentials(self, key_file_path = "../secret.key", config_file_path = "../config.yaml"):
        # Load encryption key
        with open(key_file_path, "rb") as key_file:
            key = key_file.read()
        cipher = Fernet(key)

        # Load YAML
        with open(config_file_path, "r") as file:
            yaml_data = yaml.safe_load(file)

        # Encrypt flat keys
        twilio = yaml_data["twilio_config"]
        twilio["account_sid"] = cipher.encrypt(twilio["account_sid"].encode()).decode()
        twilio["auth_token"] = cipher.encrypt(twilio["auth_token"].encode()).decode()
        twilio["phone_number"] = cipher.encrypt(twilio["phone_number"].encode()).decode()

        # Save back
        with open(config_file_path, "w") as file:
            yaml.dump(yaml_data, file, default_flow_style=False)
        
    def send_alert(self, message):
        user_manager = UserManager("users.db")

        key_file_path = self.key_file
        # Load encryption key
        with open(key_file_path, "rb") as key_file:
            key = key_file.read()
        cipher = Fernet(key)
        with open(self.config_file_path, "r") as file:
            yaml_data = yaml.safe_load(file)

        twilio = yaml_data["twilio_config"]

        account_sid = cipher.decrypt(twilio["account_sid"].encode()).decode()
        auth_token = cipher.decrypt(twilio["auth_token"].encode()).decode()
        phone_number = cipher.decrypt(twilio["phone_number"].encode()).decode()

        alert_numbers = user_manager.get_all_phone_numbers()
        client = Client(account_sid, auth_token)

        for each_number in alert_numbers:
            message = client.messages.create(
                body=f"{message}",
                from_=f"{phone_number}",
                to=f"{each_number}",
            )

            print(message.body)
        
