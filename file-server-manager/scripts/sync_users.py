#!/usr/bin/env python3
"""
Script para sincronizar usuários com o sistema operacional
Útil para corrigir problemas de autenticação FTP/SFTP
"""

import sys
import os

# Adicionar caminho do projeto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
from rich.prompt import Confirm

console = Console()

def sync_all_users():
    """Sincroniza todos os usuários com o sistema"""
    from core.user_manager import UserManager
    
    user_manager = UserManager()
    users = user_manager.list_users()
    
    if not users:
        console.print("[yellow]⚠ Nenhum usuário cadastrado[/yellow]")
        return
    
    console.print(f"[cyan]Encontrados {len(users)} usuários[/cyan]\n")
    
    for user in users:
        username = user['username']
        home_dir = user.get('home_dir', f'/srv/files/users/{username}')
        protocols = user.get('protocols', ['ftp', 'sftp', 'smb'])
        
        console.print(f"\n[bold]Sincronizando: {username}[/bold]")
        
        # Criar/atualizar usuário no sistema
        user_manager._create_system_user(username, home_dir, None)
        
        # Sincronizar com FTP se necessário
        if 'ftp' in protocols:
            user_manager._sync_ftp_user(username, None)
        
        # Criar diretório home
        try:
            os.makedirs(home_dir, exist_ok=True)
            console.print(f"[green]✓ Diretório home verificado: {home_dir}[/green]")
        except Exception as e:
            console.print(f"[yellow]⚠ Erro ao criar diretório: {e}[/yellow]")


def set_user_password(username: str, password: str):
    """Define senha para um usuário específico"""
    from core.user_manager import UserManager
    
    user_manager = UserManager()
    
    # Atualizar senha no sistema
    success = user_manager._update_system_password(username, password)
    
    if success:
        # Sincronizar com FTP
        user_manager._sync_ftp_user(username, password)
        console.print(f"[green]✓ Senha de {username} atualizada com sucesso![/green]")
    else:
        console.print(f"[red]✗ Falha ao atualizar senha de {username}[/red]")


def main():
    """Função principal"""
    console.print("\n[bold cyan]Sincronizador de Usuários - File Server Manager[/bold cyan]\n")
    
    # Verificar root
    if os.geteuid() != 0:
        console.print("[red]✗ Este script deve ser executado como root (sudo)[/red]")
        sys.exit(1)
    
    console.print("[bold]Opções:[/bold]")
    console.print("  1. Sincronizar TODOS os usuários")
    console.print("  2. Definir senha para usuário específico")
    console.print("  3. Sair")
    
    choice = input("\nEscolha uma opção [1/2/3]: ").strip()
    
    if choice == "1":
        sync_all_users()
    elif choice == "2":
        username = input("Nome de usuário: ").strip()
        if username:
            password = input("Nova senha: ").strip()
            if password:
                set_user_password(username, password)
            else:
                console.print("[yellow]⚠ Senha vazia não é permitida[/yellow]")
        else:
            console.print("[yellow]⚠ Nome de usuário vazio[/yellow]")
    elif choice == "3":
        console.print("[green]✓ Saindo...[/green]")
    else:
        console.print("[yellow]⚠ Opção inválida[/yellow]")


if __name__ == "__main__":
    main()