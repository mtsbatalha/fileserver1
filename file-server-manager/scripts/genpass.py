#!/usr/bin/env python3
"""
Gerador de Senhas Aleatórias Seguras
Uso: python3 genpass.py [tamanho] [quantidade]
"""

import secrets
import string
import sys


def generate_password(length: int = 16) -> str:
    """
    Gera uma senha aleatória segura
    
    Args:
        length: Tamanho da senha (padrão: 16)
    
    Returns:
        Senha aleatória contendo letras maiúsculas, minúsculas, números e símbolos
    """
    uppercase = string.ascii_uppercase
    lowercase = string.ascii_lowercase
    digits = string.digits
    symbols = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    
    # Garantir pelo menos um de cada tipo
    password = [
        secrets.choice(uppercase),
        secrets.choice(lowercase),
        secrets.choice(digits),
        secrets.choice(symbols)
    ]
    
    # Completar com caracteres aleatórios
    all_chars = uppercase + lowercase + digits + symbols
    password.extend(secrets.choice(all_chars) for _ in range(length - 4))
    
    # Embaralhar
    secrets.SystemRandom().shuffle(password)
    
    return ''.join(password)


def main():
    # Parse argumentos
    length = 16
    count = 1
    
    if len(sys.argv) > 1:
        try:
            length = int(sys.argv[1])
            if length < 8:
                print("⚠ Tamanho mínimo recomendado: 8 caracteres")
                length = 8
            if length > 64:
                print("⚠ Tamanho máximo: 64 caracteres")
                length = 64
        except ValueError:
            print("Uso: python3 genpass.py [tamanho] [quantidade]")
            print("  tamanho: número de caracteres (padrão: 16)")
            print("  quantidade: número de senhas (padrão: 1)")
            sys.exit(1)
    
    if len(sys.argv) > 2:
        try:
            count = int(sys.argv[2])
            if count < 1:
                count = 1
            if count > 100:
                count = 100
        except ValueError:
            print("Quantidade deve ser um número inteiro")
            sys.exit(1)
    
    # Gerar senhas
    print(f"\n{'='*50}")
    print(f"  Gerador de Senhas Seguras")
    print(f"  Tamanho: {length} caracteres")
    print(f"  Quantidade: {count}")
    print(f"{'='*50}\n")
    
    for i in range(count):
        password = generate_password(length)
        num = i + 1
        print(f"  [{num:2d}] {password}")
    
    print(f"\n{'='*50}")
    print("  ⚠ Copie as senhas agora!")
    print("  Elas não serão exibidas novamente.")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()