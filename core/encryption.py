
from django.conf import settings
from cryptography.fernet import Fernet, InvalidToken


# Inicializa o Fernet com a chave das configurações
# É importante converter a chave para bytes

# Pega a PRIMEIRA chave da lista definida no settings.py
key = settings.FERNET_KEYS[0].encode()
fernet = Fernet(key)

def encrypt_data(data: str) -> str:
    """Criptografa uma string e retorna o texto cifrado."""
    if not data:
        return ""
    
    encrypted_data = fernet.encrypt(data.encode())
    return encrypted_data.decode()

def decrypt_data(encrypted_data: str) -> str:
    """Descriptografa um texto cifrado e retorna a string original."""
    if not encrypted_data:
        return ""
    
    try:
        # Converte de volta para bytes antes de descriptografar
        decrypted_data = fernet.decrypt(encrypted_data.encode())
        return decrypted_data.decode()
    except InvalidToken:
        # Retorna um valor padrão ou lança um erro se o token for inválido
        # Isso pode acontecer se o dado no banco não for criptografado
        return "## DADO INVÁLIDO ##"
