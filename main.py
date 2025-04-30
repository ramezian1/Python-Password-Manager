import os
import re
from cryptography.fernet import Fernet
import secrets  # <-- Import secrets module
import string   # <-- Import string module


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
    # Return as bytes, Fernet expects bytes for decryption
    return encrypted_password


def decrypt_password(encrypted_password_bytes, secret_key):
    """Decrypts an encrypted password using Fernet encryption with a given secret key."""
    cipher = Fernet(secret_key)
    # Ensure input is bytes
    if isinstance(encrypted_password_bytes, str):
        encrypted_password_bytes = encrypted_password_bytes.encode()
    decrypted_password = cipher.decrypt(encrypted_password_bytes)
    return decrypted_password.decode()


def save_encrypted_password(username, password, secret_key):
    """Saves an encrypted password to a file."""
    encrypted_password_bytes = encrypt_password(password, secret_key)
    # Store the base64 representation of the bytes as string
    encrypted_password_str = encrypted_password_bytes.decode('utf-8')

    # Create or open the password file
    file_path = "passwords.txt"
    with open(file_path, "a+") as f:
        f.write(f"{username}:{encrypted_password_str}\n")


def check_password(username, password_to_check, secret_key):
    """Checks if a given password matches the stored encrypted password."""
    try:
        with open("passwords.txt", "r") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    username_stored, encrypted_password_stored_str = line.strip().split(":", 1)
                    if username == username_stored:
                        # Decrypt the stored password (string -> bytes -> decrypt -> string)
                        decrypted_stored_password = decrypt_password(encrypted_password_stored_str.encode('utf-8'), secret_key)
                        # Compare with the password provided by the user
                        if decrypted_stored_password == password_to_check:
                            return True
                        else:
                            # Found the user, but password doesn't match
                            return False
                except ValueError:
                    print(f"Warning: Skipping malformed line in passwords.txt: {line.strip()}")
                    continue
                except Exception as e:
                    print(f"Error processing line for user {username_stored}: {e}")
                    return False # Indicate an error or uncertainty
        # Username not found in the file
        return False
    except FileNotFoundError:
        print("Password file not found.")
        return False


def find_password(username, secret_key):
    """Finds the encrypted password for a given username and decrypts it."""
    try:
        with open("passwords.txt", "r") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    username_stored, encrypted_password_stored_str = line.strip().split(":", 1)
                    if username == username_stored:
                         # Decrypt and return
                        decrypted_password = decrypt_password(encrypted_password_stored_str.encode('utf-8'), secret_key)
                        # Return the decrypted password string
                        return decrypted_password
                except ValueError:
                    print(f"Warning: Skipping malformed line in passwords.txt: {line.strip()}")
                    continue
                except Exception as e:
                     print(f"Error processing line for user {username_stored}: {e}")
                     return None # Indicate an error
        # Username not found
        return None
    except FileNotFoundError:
        print("Password file not found.")
        return None


def delete_password(username):
    """Deletes the password for a given username."""
    temp_file_path = "temp.txt"
    original_file_path = "passwords.txt"
    found = False
    try:
        with open(original_file_path, "r") as f, open(temp_file_path, "w") as temp:
            for line in f:
                if not line.strip(): # Skip empty lines
                    temp.write(line)
                    continue
                try:
                    username_stored, _ = line.strip().split(":", 1)
                    if username != username_stored:
                        temp.write(line) # Keep lines for other users
                    else:
                        found = True # Mark that we found and skipped the user
                except ValueError:
                    print(f"Warning: Keeping malformed line during delete: {line.strip()}")
                    temp.write(line) # Keep malformed lines just in case

        # Replace the original file with the temporary file
        os.remove(original_file_path)
        os.rename(temp_file_path, original_file_path)
        return found # Return True if deleted, False otherwise

    except FileNotFoundError:
        print(f"'{original_file_path}' not found. Nothing to delete.")
        # Clean up temp file if it was created
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        return False
    except Exception as e:
        print(f"An error occurred during deletion: {e}")
        # Attempt cleanup
        if os.path.exists(temp_file_path):
             os.remove(temp_file_path)
        return False


def check_password_strength(password):
    """Checks if the password meets minimum strength requirements."""
    if len(password) < 8:
        print("  Reason: Password is too short (minimum 8 characters).")
        return False
    if not re.search("[a-z]", password):
        print("  Reason: Password needs at least one lowercase letter.")
        return False
    if not re.search("[A-Z]", password):
        print("  Reason: Password needs at least one uppercase letter.")
        return False
    if not re.search("[0-9]", password):
        print("  Reason: Password needs at least one number.")
        return False
    # Optional: check for symbols
    # if not re.search(r"[\W_]", password): # \W matches non-alphanumeric, _ is included
    #     print("  Reason: Password needs at least one special character.")
    #     return False
    return True

# --- New Function ---
def generate_secure_password(length=16):
    """Generates a secure password meeting complexity requirements."""
    if length < 8:
        length = 8 # Ensure minimum length

    # Define character sets
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    # Add symbols for stronger passwords
    symbols = string.punctuation # !"#$%&'()*+,-./:;<=>?@[\]^_`{|}~

    # Ensure at least one character from required sets
    password_chars = [
        secrets.choice(lowercase),
        secrets.choice(uppercase),
        secrets.choice(digits),
        secrets.choice(symbols) # Make symbols mandatory for generated ones
    ]

    # Fill the rest of the password length
    # Combine all allowed characters
    all_chars = lowercase + uppercase + digits + symbols
    password_chars += [secrets.choice(all_chars) for _ in range(length - len(password_chars))]

    # Shuffle the list of characters randomly
    secrets.SystemRandom().shuffle(password_chars)

    # Join the characters to form the final password string
    return "".join(password_chars)
# --- End New Function ---


def main():
    # Generate or load the secret key
    secret_key = generate_key()

    # Master password authentication (consider a more secure way than hardcoding)
    master_password_attempt = input("Enter master password: ")
    # Example: Store a hash of the master password instead of plain text
    # For simplicity here, we keep the plain text comparison
    if master_password_attempt != "masterpass":  # Replace "masterpass" with a secure master password
        print("Incorrect master password. Exiting...")
        return

    while True:
        print("\nMenu:")
        print("1. Add password")
        print("2. Check password")
        print("3. Find password (Decrypt & Show)")
        print("4. Delete password")
        print("5. Exit")

        choice_str = input("Enter your choice (1-5): ")
        try:
            choice = int(choice_str)
        except ValueError:
            print("Invalid input. Please enter a number.")
            continue

        if choice == 1:
            username = input("Enter username: ")
            # --- Modified Section ---
            generate = input("Generate a secure password? (y/n): ").lower()
            if generate == 'y':
                password = generate_secure_password() # Generate password
                print(f"Generated Password: {password}") # Show the user the password
                # Generated password inherently meets strength requirements defined in generator
                save_encrypted_password(username, password, secret_key)
                print("Generated password saved securely.")
            else:
                password = input("Enter password manually: ") # Ask for manual input
                if check_password_strength(password): # Check strength
                    save_encrypted_password(username, password, secret_key)
                    print("Password saved securely.")
                else:
                    print("Password does not meet the strength requirements. Not saved.")
            # --- End Modified Section ---

        elif choice == 2:
            username = input("Enter username: ")
            password = input("Enter password to check: ")
            match = check_password(username, password, secret_key)
            if match is True: # Explicit check for True
                 print("Password matches.")
            elif match is False: # Explicit check for False (means user found, but password wrong, or user not found)
                 print("Password does not match or username not found.")
            else: # Handles potential error cases if check_password returned None
                 print("Could not verify password due to an error.")

        elif choice == 3:
            username = input("Enter username to find password for: ")
            decrypted_password = find_password(username, secret_key)
            if decrypted_password:
                # Be careful about printing passwords to the screen!
                print(f"Decrypted password for {username}: {decrypted_password}")
            elif decrypted_password is None and os.path.exists("passwords.txt"): # Check if None was explicitly returned vs file not found
                 print("Username not found.")
            # No message if file didn't exist, find_password prints that

        elif choice == 4:
            username = input("Enter username to delete: ")
            if delete_password(username):
                 print(f"Password entry for '{username}' deleted.")
            else:
                 # Message printed within delete_password if file not found
                 # Or if user wasn't found in the file
                 print(f"Username '{username}' not found, nothing deleted.")


        elif choice == 5:
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please enter a number between 1 and 5.")


if __name__ == "__main__":
    # Create dummy files if they don't exist to prevent errors on first run for some functions
    if not os.path.exists("secret.key"):
        print("Generating secret key file...")
        generate_key()
    if not os.path.exists("passwords.txt"):
        print("Creating empty password file...")
        with open("passwords.txt", "w") as f:
            pass # Create empty file

    main()