# Python Script - Password Manager 🔐

This Python-based password manager helps users securely save, store, and encrypt passwords. The application uses **Fernet** encryption to ensure that your passwords are protected.

## Features ✨

- **Add Password**: Securely store a password for a specific username.
- **Check Password**: Verify if a given password matches the stored encrypted password.
- **Find Password**: Retrieve the encrypted password for a given username.
- **Delete Password**: Remove a stored password for a given username.
- **Master Password**: Requires entering a master password to authenticate and access the password manager.

## Requirements 📋

- **Python**: Ensure Python is installed on your system.
- **IDE**: You can use any IDE, such as PyCharm, VS Code, or even a simple text editor to edit the script.

## Installation ⚙️

1. Clone or download this repository to your local machine.
2. Install the required Python libraries by running:
   ```bash
   pip install cryptography
   ```

## How to Use 🚀

1. **Run the Script**: 
   Execute the script in your terminal or IDE.

2. **Enter Master Password**: 
   Upon running the script, you will be prompted to enter the master password to authenticate yourself. Replace the placeholder `"masterpass"` with a strong, secure password in the script, or keep as `"masterpass"`.
   NOTE: Upon running script, a "secret.key" file will be created. This will ensure that your passwords are safely stored in a file (see step 5).
   
   Example:
   ```python
   master_password = input("Enter master password: ")
   if master_password != "masterpass":  # Replace with your chosen strong password
       print("Incorrect master password. Exiting...")
       return
   ```

4. **Menu Options**:
   After successful authentication, the menu will appear with the following options:
   - **1. Add password**: Add a new password for a username.
   - **2. Check password**: Verify if the password entered matches the stored password.
   - **3. Find password**: Retrieve the encrypted password for a specific username.
   - **4. Delete password**: Delete the password for a specific username.
   - **5. Exit**: Exit the application.

5. **Password Storage**:
   - Passwords are encrypted using **Fernet** encryption.
   - The secret key is stored in a file (`secret.key`) to persist across program runs.
   - Passwords are stored in a file (`passwords.txt`).

## Security 🔒

- **Master Password**: The master password is used to authenticate and access the password manager. Ensure this password is strong and unique.
- **Encryption**: All passwords are encrypted using **Fernet** encryption for secure storage.

## License 📜

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

All code was written by Robert Mezian.
