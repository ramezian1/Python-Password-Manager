import os
from cryptography.fernet import Fernet


def encrypt_password(password, secret_key):
    """Encrypts a password using AES with a given secret key."""
    cipher = Fernet(secret_key)
    encrypted_password = cipher.encrypt(password.encode())
    return encrypted_password.decode()


def decrypt_password(encrypted_password, secret_key):
    """Decrypts an encrypted password using AES with a given secret key."""
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


def main():
    # Generate a strong secret key
    secret_key = Fernet.generate_key()

    while True:
        print("Menu:")
        print("1. Add password")
        print("2. Check password")
        print("3. Find password")
        print("4. Delete password")
        print("5. Exit")

        choice = int(input("Enter your choice (1-5): "))

        if choice == 1:
            username = input("Enter username: ")
            password = input("Enter password: ")
            save_encrypted_password(username, password, secret_key)
            print("Password saved securely.")
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
