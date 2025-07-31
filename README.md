# Python Script - Password Manager 🔐

This Python-based password manager helps users securely save, store, generate, and encrypt passwords. The application uses **Fernet** encryption from the `cryptography` library to ensure that your passwords are protected.

## Features ✨

-   **Add Password**: Securely store a password for a specific username.
    -   Optionally **generate** a strong, secure password automatically.
    -   Checks the strength of manually entered passwords.
-   **Check Password**: Verify if a given password matches the stored encrypted password.
-   **Find Password**: Retrieve and **decrypt** the stored password for a given username.
-   **Delete Password**: Remove a stored password entry for a given username.
-   **Master Password**: Requires entering a master password to authenticate and access the password manager.
-   **Secure Storage**: Uses Fernet symmetric encryption. The encryption key is stored locally in `secret.key`, and encrypted passwords are in `passwords.txt`.

## Requirements 📋

-   **Python**: Ensure Python 3 is installed on your system.
-   **IDE**: You can use any IDE, such as PyCharm, VS Code, or even a simple text editor to edit the script.

## Installation ⚙️

1.  Clone or download this repository/script to your local machine.
2.  Install the required Python library by running:
    ```bash
    pip install cryptography
    ```

## How to Use 🚀

1.  **Run the Script**:
    Execute the Python script (`.py` file) in your terminal or IDE.
    ```bash
    python your_script_name.py
    ```

2.  **Enter Master Password**:
    Upon running the script for the first time, it will create a `secret.key` file for encryption. You will be prompted to enter the master password to authenticate yourself.
    -   **Important**: You should change the hardcoded master password (`"masterpass"`) in the script to a strong, unique password that only you know.
    ```python
    # Locate this section in the main() function and change "masterpass"
    master_password_attempt = input("Enter master password: ")
    if master_password_attempt != "your_strong_master_password": # Replace "masterpass" here
        print("Incorrect master password. Exiting...")
        return
    ```

3.  **Menu Options**:
    After successful authentication, the menu will appear with the following options:
    -   **1. Add password**:
        -   Enter the username.
        -   You'll be asked if you want to **generate** a secure password (`y/n`).
        -   If 'y', a strong password will be generated, displayed, and saved.
        -   If 'n', you'll be prompted to enter a password manually. The script will check its strength (length, lowercase, uppercase, number) before saving. If it's weak, it won't be saved, and you'll see the reason.
    -   **2. Check password**: Enter a username and password to see if it matches the stored entry.
    -   **3. Find password**: Enter a username to retrieve and **display the decrypted password**. *Be cautious about using this option in insecure environments.*
    -   **4. Delete password**: Enter a username to remove its password entry from the storage file.
    -   **5. Exit**: Exit the application.

4.  **Password Storage**:
    -   Passwords are encrypted using **Fernet** symmetric encryption.
    -   The unique secret key is generated once and stored in `secret.key`. **Do not lose or share this file!** If lost, your passwords cannot be decrypted.
    -   Encrypted passwords (along with usernames) are stored line-by-line in `passwords.txt`.

## Security 🔒

-   **Master Password**: Access to the manager is protected by a master password. Choose a strong one and keep it secret. Consider hashing the master password in future versions for better security instead of plain text comparison.
-   **Encryption**: All stored passwords are encrypted using Fernet.
-   **Key Management**: The `secret.key` file is crucial. Back it up securely. Anyone with access to this key file *and* the `passwords.txt` file can decrypt your passwords.
-   **Password Generation**: The generation feature creates passwords with uppercase, lowercase, digits, and symbols, meeting common complexity requirements.
-   **Decryption Display**: The "Find Password" option displays the password in plain text. Be mindful of shoulder surfing or using this feature on compromised systems.

## License 📜

This project is licensed under the MIT License - see the [LICENSE](Python-Password-Manager/LICENSE) for more.

---

*Original script structure by Robert Mezian, with modifications.*
