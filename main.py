import os
import re
from cryptography.fernet import Fernet


def generate_key():
    """Generates a secret key and stores it in a file."""
    if not os.path.exists("secret.key"):
        secret_key = Fernet.generate_key()
        with open("secret.key", "wb") as key_file:
            key_file.write(secret_key)
    else:
        with open("secret.key", "rb") as key_file:
            secret_key = key_file.read()
    return secret_key


def encrypt_password(password, secret_key):
    """Encrypts a password using Fernet encryption with a given secret key."""
    cipher = Fernet(secret_key)
    encrypted_password = cipher.encrypt(password.encode())
    return encrypted_password.decode()


def decrypt_password(encrypted_password, secret_key):
    """Decrypts an encrypted password using Fernet encryption with a given secret key."""
    cipher = Fernet(secret_key)
    decrypted_password = cipher.decrypt(encrypted_password.encode())
    return decrypted_password.decode()


def save_encrypted_password(username, password, secret_key):
    """Saves an encrypted password to a file."""
    encrypted_password = encrypt_password(password, secret_key)

    # Create or open the password file
    file_path = "passwords.txt"
    with open(file_path, "a+") as f:
        f.write(f"{username}:{encrypted_password}\n")


def check_password(username, password, secret_key):
    """Checks if a given password matches the stored encrypted password."""
    with open("passwords.txt", "r") as f:
        for line in f:
            username_stored, encrypted_password_stored = line.strip().split(":")
            if username == username_stored:
                if decrypt_password(encrypted_password_stored, secret_key) == password:
                    return True
                else:
                    return False
    return False


def find_password(username, secret_key):
    """Finds the encrypted password for a given username and decrypts it."""
    with open("passwords.txt", "r") as f:
        for line in f:
            username_stored, encrypted_password_stored = line.strip().split(":")
            if username == username_stored:
                decrypted_password = decrypt_password(encrypted_password_stored, secret_key)
                return decrypted_password
    return None


def delete_password(username):
    """Deletes the password for a given username."""
    with open("passwords.txt", "r") as f, open("temp.txt", "w") as temp:
        for line in f:
            username_stored, encrypted_password_stored = line.strip().split(":")
            if username != username_stored:
                temp.write(line)
    os.remove("passwords.txt")
    os.rename("temp.txt", "passwords.txt")


def check_password_strength(password):
    """Checks if the password meets minimum strength requirements."""
    if len(password) < 8:
        return False
    if not re.search("[a-z]", password):
        return False
    if not re.search("[A-Z]", password):
        return False
    if not re.search("[0-9]", password):
        return False
    return True


def main():
    # Generate or load the secret key
    secret_key = generate_key()

    # Master password authentication
    master_password = input("Enter master password: ")
    if master_password != "your_master_password":  # Replace with a secure master password
        print("Incorrect master password. Exiting...")
        return

    while True:
        print("\nMenu:")
        print("1. Add password")
        print("2. Check password")
        print("3. Find password")
        print("4. Delete password")
        print("5. Exit")

        choice = int(input("Enter your choice (1-5): "))

        if choice == 1:
            username = input("Enter username: ")
            password = input("Enter password: ")
            if check_password_strength(password):
                save_encrypted_password(username, password, secret_key)
                print("Password saved securely.")
            else:
                print("Password does not meet the strength requirements.")
        elif choice == 2:
            username = input("Enter username: ")
            password = input("Enter password: ")
            if check_password(username, password, secret_key):
                print("Password matches.")
            else:
                print("Password does not match.")
        elif choice == 3:
            username = input("Enter username: ")
            encrypted_password = find_password(username, secret_key)
            if encrypted_password:
                print("Encrypted password:", encrypted_password)
            else:
                print("Username not found.")
        elif choice == 4:
            username = input("Enter username: ")
            delete_password(username)
            print("Password deleted.")
        elif choice == 5:
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please enter a number between 1 and 5.")


if __name__ == "__main__":
    main()
