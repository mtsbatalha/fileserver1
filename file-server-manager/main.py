#!/usr/bin/env python3
"""
File Server Manager - Gerenciador de Servidor de Arquivos
Script principal com menu interativo para configuração e gerenciamento
de servidores FTP, SFTP, NFS, SMB, WebDAV e S3

Uso: sudo python3 main.py
"""

import sys
import os
import json
import secrets
import string

# Adicionar caminho do projeto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm, IntPrompt, FloatPrompt
from rich.menu import Menu

console = Console()

# Importar módulos
from core.installer import Installer
from core.user_manager import UserManager
from core.config_generator import ConfigGenerator
from core.security import SecurityManager
from protocols.ftp import FTPServer
from protocols.sftp import SFTPServer
from protocols.nfs import NFSServer
from protocols.smb import SMBServer
from protocols.webdav import WebDAVServer
from protocols.s3 import S3Server
from utils.quota import QuotaManager
from utils.logger import AuditLogger
from utils.validators import Validators


class FileServerManager:
    """Classe principal do gerenciador de servidores de arquivos"""
    
    PROTOCOLS = {
        'ftp': {'name': 'FTP', 'desc': 'File Transfer Protocol'},
        'sftp': {'name': 'SFTP', 'desc': 'SSH File Transfer Protocol'},
        'nfs': {'name': 'NFS', 'desc': 'Network File System'},
        'smb': {'name': 'SMB/CIFS', 'desc': 'Server Message Block'},
        'webdav': {'name': 'WebDAV', 'desc': 'Web Distributed Authoring and Versioning'},
        's3': {'name': 'S3 (MinIO)', 'desc': 'Amazon S3 Compatible'}
    }
    
    def __init__(self):
        self.config_path = '/etc/file-server-manager'
        self.installer = Installer()
        self.user_manager = UserManager(self.config_path)
        self.config_generator = ConfigGenerator(self.config_path)
        self.security_manager = SecurityManager(self.config_path)
        self.quota_manager = QuotaManager()
        self.logger = AuditLogger(config_path=self.config_path)
        
        # Inicializar servidores
        self.servers = {
            'ftp': FTPServer(self.config_path),
            'sftp': SFTPServer(self.config_path),
            'nfs': NFSServer(self.config_path),
            'smb': SMBServer(self.config_path),
            'webdav': WebDAVServer(self.config_path),
            's3': S3Server(self.config_path)
        }
        
        # Carregar configuração
        self.config = self.config_generator.get_all_configs()
        self.base_path = self.config.get('base_path', '/srv/files')
    
    def clear_screen(self):
        """Limpa a tela"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self, title: str = "File Server Manager"):
        """Exibe cabeçalho"""
        console.print(Panel(
            f"[bold cyan]{title}[/bold cyan]\n"
            f"[dim]Gerenciador de Servidores de Arquivos[/dim]",
            style="bold cyan",
            border_style="cyan"
        ))
    
    def print_menu(self, options: list, title: str = "Menu"):
        """Exibe menu com opções"""
        console.print(f"\n[bold]{title}[/bold]")
        for i, option in enumerate(options, 1):
            if isinstance(option, tuple):
                key, desc = option
                console.print(f"  [green]{i}.[/green] {desc} ({key})")
            else:
                console.print(f"  [green]{i}.[/green] {option}")
        console.print()
    
    def main_menu(self):
        """Menu principal"""
        while True:
            self.clear_screen()
            self.print_header()
            
            # Status rápido
            config = self.config_generator.get_all_configs()
            active_protocols = [p for p, c in config.get('protocols', {}).items() if c.get('enabled')]
            
            console.print(f"\n[bold]Protocolos instalados:[/bold] {len(active_protocols)}")
            for proto in active_protocols:
                console.print(f"  [green]✓[/green] {proto.upper()}")
            
            self.print_menu([
                "Instalar/Configurar Protocolos",
                "Gerenciar Usuários",
                "Configurar Segurança",
                "Configurar Quotas",
                "Ver Status dos Serviços",
                "Ver Logs de Auditoria",
                "Configurações",
                "Sair"
            ], "Menu Principal")
            
            choice = Prompt.ask("Escolha uma opção", choices=["1", "2", "3", "4", "5", "6", "7", "0"], default="0")
            
            if choice == "0":
                console.print("[green]✓ Até logo![/green]")
                break
            elif choice == "1":
                self.protocols_menu()
            elif choice == "2":
                self.users_menu()
            elif choice == "3":
                self.security_menu()
            elif choice == "4":
                self.quota_menu()
            elif choice == "5":
                self.status_menu()
            elif choice == "6":
                self.logs_menu()
            elif choice == "7":
                self.settings_menu()
    
    def protocols_menu(self):
        """Menu de protocolos"""
        while True:
            self.clear_screen()
            self.print_header("Protocolos")
            
            self.print_menu([
                "Instalar TODOS os protocolos",
                "Instalação personalizada",
                "Configurar FTP",
                "Configurar SFTP",
                "Configurar NFS",
                "Configurar SMB/CIFS",
                "Configurar WebDAV",
                "Configurar S3 (MinIO)",
                "Voltar"
            ], "Gerenciar Protocolos")
            
            choice = Prompt.ask("Escolha uma opção", choices=["1", "2", "3", "4", "5", "6", "7", "8", "0"], default="0")
            
            if choice == "0":
                break
            elif choice == "1":
                self.install_all_protocols()
            elif choice == "2":
                self.install_custom_protocols()
            elif choice == "3":
                self.configure_protocol('ftp')
            elif choice == "4":
                self.configure_protocol('sftp')
            elif choice == "5":
                self.configure_protocol('nfs')
            elif choice == "6":
                self.configure_protocol('smb')
            elif choice == "7":
                self.configure_protocol('webdav')
            elif choice == "8":
                self.configure_protocol('s3')
            
            Prompt.ask("\nPressione Enter para continuar")
    
    def install_all_protocols(self):
        """Instala todos os protocolos"""
        self.clear_screen()
        self.print_header("Instalar Todos os Protocolos")
        
        if not Confirm.ask("Deseja instalar TODOS os protocolos? Isso pode levar algum tempo."):
            return
        
        # Verificar root
        if os.geteuid() != 0:
            console.print("[red]✗ É necessário executar como root (sudo)[/red]")
            return
        
        # Instalar pacotes
        self.installer.install_packages(['all'])
        
        # Criar diretórios
        self.base_path = Prompt.ask("Caminho base para arquivos", default="/srv/files")
        self.installer.create_directories(self.base_path, list(self.PROTOCOLS.keys()))
        
        # Gerar configurações
        self.generate_all_configs()
        
        # Configurar segurança
        if Confirm.ask("Deseja configurar fail2ban e SSL?", default=True):
            self.security_manager.setup_fail2ban()
            self.security_manager.generate_ssl_certificate()
        
        # Habilitar serviços
        self.installer.setup_services(['all'])
        
        console.print("\n[green]✓ Instalação completa! Reinicie o servidor se necessário.[/green]")
    
    def install_custom_protocols(self):
        """Instalação personalizada de protocolos"""
        self.clear_screen()
        self.print_header("Instalação Personalizada")
        
        console.print("Selecione os protocolos para instalar:\n")
        
        selected = []
        for key, info in self.PROTOCOLS.items():
            if Confirm.ask(f"  [ ] {info['name']} - {info['desc']}", default=False):
                selected.append(key)
        
        if not selected:
            console.print("[yellow]⚠ Nenhum protocolo selecionado[/yellow]")
            return
        
        console.print(f"\n[bold]Selecionados:[/bold] {', '.join(selected)}")
        
        if not Confirm.ask("Continuar com instalação?"):
            return
        
        # Instalar
        if os.geteuid() != 0:
            console.print("[red]✗ É necessário executar como root (sudo)[/red]")
            return
        
        self.installer.install_packages(selected)
        
        self.base_path = Prompt.ask("Caminho base para arquivos", default="/srv/files")
        self.installer.create_directories(self.base_path, selected)
        
        # Gerar configurações para selecionados
        for proto in selected:
            self.generate_protocol_config(proto)
        
        self.installer.setup_services(selected)
        
        console.print("\n[green]✓ Instalação concluída![/green]")
    
    def generate_all_configs(self):
        """Gera configurações para todos os protocolos"""
        console.print("\n[cyan]▶ Gerando configurações...[/cyan]")
        
        # FTP
        self.config_generator.generate_ftp_config(
            ssl_enable=True,
            ssl_cert_file=self.config['security']['ssl_cert_path'],
            ssl_key_file=self.config['security']['ssl_key_path']
        )
        
        # SFTP
        self.config_generator.generate_sftp_config()
        
        # NFS
        self.config_generator.generate_nfs_config()
        
        # SMB
        self.config_generator.generate_smb_config()
        
        # WebDAV
        self.config_generator.generate_webdav_config(
            base_path=f"{self.base_path}/webdav",
            ssl_enabled=True
        )
        
        # S3 (MinIO)
        self.config_generator.generate_minio_config(
            data_dir=f"{self.base_path}/s3/data"
        )
        
        console.print("[green]✓ Configurações geradas[/green]")
    
    def generate_protocol_config(self, protocol: str):
        """Gera configuração para um protocolo específico"""
        if protocol == 'ftp':
            self.config_generator.generate_ftp_config()
        elif protocol == 'sftp':
            self.config_generator.generate_sftp_config()
        elif protocol == 'nfs':
            self.config_generator.generate_nfs_config()
        elif protocol == 'smb':
            self.config_generator.generate_smb_config()
        elif protocol == 'webdav':
            self.config_generator.generate_webdav_config()
        elif protocol == 's3':
            self.config_generator.generate_minio_config()
    
    def configure_protocol(self, protocol: str):
        """Configura um protocolo específico"""
        self.clear_screen()
        self.print_header(f"Configurar {self.PROTOCOLS.get(protocol, {}).get('name', protocol).upper()}")
        
        server = self.servers.get(protocol)
        if not server:
            console.print("[red]✗ Protocolo não suportado[/red]")
            return
        
        # Exibir status atual
        status = server.get_status()
        console.print(f"\n[bold]Status:[/bold]")
        console.print(f"  Instalado: {'[green]Sim[/green]' if status.get('installed') else '[red]Não[/red]'}")
        console.print(f"  Rodando: {'[green]Sim[/green]' if status.get('running') else '[red]Não[/red]'}")
        
        console.print("\n[bold]Ações:[/bold]")
        self.print_menu([
            "Iniciar serviço",
            "Parar serviço",
            "Reiniciar serviço",
            "Habilitar auto-start",
            "Gerar configuração",
            "Voltar"
        ])
        
        choice = Prompt.ask("Escolha", choices=["1", "2", "3", "4", "5", "0"], default="0")
        
        if choice == "1":
            server.start()
        elif choice == "2":
            server.stop()
        elif choice == "3":
            server.restart()
        elif choice == "4":
            server.enable()
        elif choice == "5":
            self.generate_protocol_config(protocol)
    
    def users_menu(self):
        """Menu de gerenciamento de usuários"""
        while True:
            self.clear_screen()
            self.print_header("Gerenciar Usuários")
            
            # Listar usuários
            users = self.user_manager.list_users()
            if users:
                table = Table(title="Usuários")
                table.add_column("Nome", style="cyan")
                table.add_column("Home", style="green")
                table.add_column("Protocolos", style="yellow")
                table.add_column("Quota (MB)", style="magenta")
                table.add_column("Status", style="blue")
                
                for user in users:
                    status = "[green]Ativo[/green]" if user.get('enabled') else "[red]Inativo[/red]"
                    table.add_row(
                        user['username'],
                        user.get('home_dir', 'N/A'),
                        ', '.join(user.get('protocols', [])),
                        str(user.get('quota_mb', 'Ilimitado')),
                        status
                    )
                console.print(table)
            else:
                console.print("[yellow]⚠ Nenhum usuário cadastrado[/yellow]")
            
            self.print_menu([
                "Criar usuário",
                "Editar usuário",
                "Excluir usuário",
                "Definir quota",
                "Exportar usuários",
                "Importar usuários",
                "Voltar"
            ])
            
            choice = Prompt.ask("Escolha", choices=["1", "2", "3", "4", "5", "6", "0"], default="0")
            
            if choice == "0":
                break
            elif choice == "1":
                self.create_user()
            elif choice == "2":
                self.edit_user()
            elif choice == "3":
                self.delete_user()
            elif choice == "4":
                self.set_user_quota()
            elif choice == "5":
                self.export_users()
            elif choice == "6":
                self.import_users()
            
            Prompt.ask("\nPressione Enter para continuar")
    
    @staticmethod
    def generate_random_password(length: int = 16) -> str:
        """
        Gera uma senha aleatória segura
        
        Args:
            length: Tamanho da senha (padrão: 16)
        
        Returns:
            Senha aleatória contendo letras maiúsculas, minúsculas, números e símbolos
        """
        # Caracteres para compor a senha
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
    
    def create_user(self):
        """Cria novo usuário"""
        self.clear_screen()
        self.print_header("Criar Usuário")
        
        # Nome de usuário
        while True:
            username = Prompt.ask("Nome de usuário")
            valid, msg = Validators.validate_username(username)
            if valid:
                break
            console.print(f"[red]✗ {msg}[/red]")
        
        # Opção de senha aleatória ou manual
        console.print("\n[bold]Opções de Senha:[/bold]")
        console.print("  1. Gerar senha aleatória segura (recomendado)")
        console.print("  2. Digitar senha manualmente")
        
        password_choice = Prompt.ask("Escolha uma opção", choices=["1", "2"], default="1")
        
        if password_choice == "1":
            # Gerar senha aleatória
            length = IntPrompt.ask("Tamanho da senha", default=16, choices=["8", "12", "16", "20", "24", "32"])
            password = self.generate_random_password(length)
            
            # Exibir senha
            console.print(f"\n[bold green]Senha gerada:[/bold green] [yellow]{password}[/yellow]")
            console.print("[dim]⚠ Copie esta senha! Ela não será exibida novamente.[/dim]")
            
            # Confirmar que copiou
            if not Confirm.ask("\nVocê copiou a senha?", default=False):
                console.print("[yellow]⚠ Usuário não criado. Copie a senha antes de continuar.[/yellow]")
                Prompt.ask("\nPressione Enter para voltar ao menu")
                return
        else:
            # Senha manual
            while True:
                password = Prompt.ask("Senha", password=True)
                password_confirm = Prompt.ask("Confirmar senha", password=True)
                
                if password != password_confirm:
                    console.print("[red]✗ Senhas não coincidem[/red]")
                    continue
                
                valid, msg = Validators.validate_weak_password(password)
                if valid:
                    break
                console.print(f"[yellow]⚠ {msg}[/yellow]")
                if not Confirm.ask("Deseja usar esta senha mesmo assim?", default=False):
                    continue
                break
        
        # Diretório home
        home_dir = Prompt.ask("Diretório home", default=f"/srv/files/users/{username}")
        
        # Protocolos
        console.print("\nProtocolos permitidos:")
        protocols = []
        for key, info in self.PROTOCOLS.items():
            if Confirm.ask(f"  {info['name']}", default=True):
                protocols.append(key)
        
        # Quota
        quota_str = Prompt.ask("Quota em MB (0 = ilimitado)", default="0")
        quota_mb = int(quota_str) if quota_str.isdigit() else None
        if quota_mb == 0:
            quota_mb = None
        
        # Criar usuário no sistema?
        create_system = Confirm.ask("Criar usuário no sistema operacional?", default=True)
        
        # Criar
        result = self.user_manager.create_user(
            username=username,
            password=password,
            home_dir=home_dir,
            protocols=protocols,
            quota_mb=quota_mb,
            create_system_user=create_system
        )
        
        if result['success']:
            self.logger.log_user_create(username)
            console.print(f"[green]✓ Usuário {username} criado com sucesso![/green]")
        else:
            console.print(f"[red]✗ Erro: {result['message']}[/red]")
    
    def edit_user(self):
        """Edita usuário existente"""
        users = self.user_manager.list_users()
        if not users:
            console.print("[yellow]⚠ Nenhum usuário para editar[/yellow]")
            return
        
        console.print("Usuários disponíveis:")
        for i, user in enumerate(users, 1):
            console.print(f"  {i}. {user['username']}")
        
        choice = Prompt.ask("Selecione", choices=[str(i) for i in range(1, len(users) + 1)])
        user = users[int(choice) - 1]
        
        console.print(f"\nEditando: {user['username']}")
        console.print(f"  Home: {user.get('home_dir', 'N/A')}")
        console.print(f"  Protocolos: {', '.join(user.get('protocols', []))}")
        
        # Opções de edição
        self.print_menu([
            "Alterar senha",
            "Alterar diretório home",
            "Alterar protocolos",
            "Ativar/Desativar",
            "Voltar"
        ])
        
        edit_choice = Prompt.ask("Escolha", choices=["1", "2", "3", "4", "0"])
        
        if edit_choice == "1":
            console.print("\n[bold]Opções de Senha:[/bold]")
            console.print("  1. Gerar senha aleatória segura")
            console.print("  2. Digitar senha manualmente")
            
            pwd_choice = Prompt.ask("Escolha", choices=["1", "2"], default="1")
            
            if pwd_choice == "1":
                length = IntPrompt.ask("Tamanho da senha", default=16)
                new_password = self.generate_random_password(length)
                console.print(f"\n[bold green]Senha gerada:[/bold green] [yellow]{new_password}[/yellow]")
                console.print("[dim]⚠ Copie esta senha! Ela não será exibida novamente.[/dim]")
                
                if not Confirm.ask("\nVocê copiou a senha?", default=False):
                    console.print("[yellow]⚠ Senha não alterada.[/yellow]")
                    return
            else:
                new_password = Prompt.ask("Nova senha", password=True)
            
            self.user_manager.update_user(user['username'], password=new_password)
        elif edit_choice == "2":
            new_home = Prompt.ask("Novo diretório home", default=user.get('home_dir', ''))
            self.user_manager.update_user(user['username'], home_dir=new_home)
        elif edit_choice == "3":
            console.print("Protocolos (marque os permitidos):")
            protocols = []
            for key, info in self.PROTOCOLS.items():
                current = key in user.get('protocols', [])
                if Confirm.ask(f"  {info['name']}", default=current):
                    protocols.append(key)
            self.user_manager.update_user(user['username'], protocols=protocols)
        elif edit_choice == "4":
            current = user.get('enabled', True)
            self.user_manager.update_user(user['username'], enabled=not current)
    
    def delete_user(self):
        """Exclui usuário"""
        users = self.user_manager.list_users()
        if not users:
            console.print("[yellow]⚠ Nenhum usuário para excluir[/yellow]")
            return
        
        console.print("Usuários disponíveis:")
        for i, user in enumerate(users, 1):
            console.print(f"  {i}. {user['username']}")
        
        choice = Prompt.ask("Selecione", choices=[str(i) for i in range(1, len(users) + 1)])
        user = users[int(choice) - 1]
        
        if not Confirm.ask(f"Tem certeza que deseja excluir {user['username']}?"):
            return
        
        delete_home = Confirm.ask("Excluir diretório home?", default=False)
        delete_system = Confirm.ask("Excluir do sistema operacional?", default=False) if user.get('system_user') else False
        
        result = self.user_manager.delete_user(
            user['username'],
            delete_home=delete_home,
            delete_system=delete_system
        )
        
        if result['success']:
            self.logger.log_user_delete(user['username'])
            console.print(f"[green]✓ Usuário {user['username']} excluído[/green]")
    
    def set_user_quota(self):
        """Define quota de usuário"""
        users = self.user_manager.list_users()
        if not users:
            console.print("[yellow]⚠ Nenhum usuário[/yellow]")
            return
        
        console.print("Usuários:")
        for i, user in enumerate(users, 1):
            current_quota = user.get('quota_mb', 'Ilimitado')
            console.print(f"  {i}. {user['username']} (Quota: {current_quota} MB)")
        
        choice = Prompt.ask("Selecione", choices=[str(i) for i in range(1, len(users) + 1)])
        user = users[int(choice) - 1]
        
        quota_str = Prompt.ask("Nova quota em MB (0 = ilimitado)", default="0")
        quota_mb = int(quota_str) if quota_str.isdigit() else None
        if quota_mb == 0:
            quota_mb = None
        
        self.user_manager.set_quota(user['username'], quota_mb)
    
    def export_users(self):
        """Exporta usuários para arquivo"""
        output_file = Prompt.ask("Arquivo de saída", default="users_backup.json")
        self.user_manager.export_users(output_file)
    
    def import_users(self):
        """Importa usuários de arquivo"""
        input_file = Prompt.ask("Arquivo de entrada", default="users_backup.json")
        if os.path.exists(input_file):
            self.user_manager.import_users(input_file)
        else:
            console.print(f"[red]✗ Arquivo não encontrado: {input_file}[/red]")
    
    def security_menu(self):
        """Menu de segurança"""
        while True:
            self.clear_screen()
            self.print_header("Segurança")
            
            self.security_manager.display_security_status()
            
            self.print_menu([
                "Gerar Certificado SSL",
                "Verificar Certificado",
                "Configurar Fail2Ban",
                "Gerenciar IP Whitelist",
                "Gerenciar IP Blacklist",
                "Configurar Firewall",
                "Voltar"
            ])
            
            choice = Prompt.ask("Escolha", choices=["1", "2", "3", "4", "5", "6", "0"], default="0")
            
            if choice == "0":
                break
            elif choice == "1":
                self.security_manager.generate_ssl_certificate()
            elif choice == "2":
                result = self.security_manager.verify_certificate()
                console.print(f"Status: {result}")
            elif choice == "3":
                self.security_manager.setup_fail2ban()
            elif choice == "4":
                ip = Prompt.ask("IP para whitelist")
                self.security_manager.add_ip_whitelist(ip)
            elif choice == "5":
                ip = Prompt.ask("IP para blacklist")
                self.security_manager.add_ip_blacklist(ip)
            elif choice == "6":
                protocols = list(self.PROTOCOLS.keys())
                self.security_manager.setup_firewall_rules(protocols)
            
            Prompt.ask("\nPressione Enter para continuar")
    
    def quota_menu(self):
        """Menu de quotas"""
        while True:
            self.clear_screen()
            self.print_header("Gerenciar Quotas")
            
            self.quota_manager.display_quota_report()
            
            self.print_menu([
                "Habilitar Quota (requer reboot)",
                "Definir Quota para Usuário",
                "Remover Quota",
                "Ver Uso de Disco",
                "Voltar"
            ])
            
            choice = Prompt.ask("Escolha", choices=["1", "2", "3", "4", "0"], default="0")
            
            if choice == "0":
                break
            elif choice == "1":
                partition = Prompt.ask("Partição", default="/")
                self.quota_manager.enable_quota(partition)
            elif choice == "2":
                username = Prompt.ask("Nome de usuário")
                soft = IntPrompt.ask("Limite brando (MB)", default=1000)
                hard = IntPrompt.ask("Limite rígido (MB)", default=1500)
                self.quota_manager.set_user_quota(username, soft, hard)
            elif choice == "3":
                username = Prompt.ask("Nome de usuário")
                self.quota_manager.remove_user_quota(username)
            elif choice == "4":
                path = Prompt.ask("Caminho", default="/srv/files")
                usage = self.quota_manager.get_disk_usage(path)
                console.print(f"Uso de {path}: {usage.get('usage', 'N/A')}")
            
            Prompt.ask("\nPressione Enter para continuar")
    
    def status_menu(self):
        """Menu de status"""
        self.clear_screen()
        self.print_header("Status dos Serviços")
        
        table = Table(title="Status dos Protocolos")
        table.add_column("Protocolo", style="cyan")
        table.add_column("Instalado", style="green")
        table.add_column("Rodando", style="blue")
        table.add_column("Porta", style="yellow")
        
        ports = {'ftp': '21', 'sftp': '22', 'nfs': '2049', 'smb': '445', 'webdav': '443', 's3': '9000'}
        
        for key, server in self.servers.items():
            status = server.get_status()
            installed = "[green]✓[/green]" if status.get('installed') else "[red]✗[/red]"
            running = "[green]✓[/green]" if status.get('running') else "[red]✗[/red]"
            table.add_row(
                key.upper(),
                installed,
                running,
                ports.get(key, 'N/A')
            )
        
        console.print(table)
        
        # Status do sistema
        console.print("\n[bold]Status do Sistema:[/bold]")
        fs_info = self.quota_manager.get_filesystem_info()
        if fs_info:
            console.print(f"  Disco: {fs_info.get('used', 'N/A')} / {fs_info.get('size', 'N/A')} ({fs_info.get('use_percent', 'N/A')})")
    
    def logs_menu(self):
        """Menu de logs"""
        while True:
            self.clear_screen()
            self.print_header("Logs de Auditoria")
            
            self.print_menu([
                "Ver últimos 50 eventos",
                "Ver por tipo",
                "Limpar logs",
                "Voltar"
            ])
            
            choice = Prompt.ask("Escolha", choices=["1", "2", "3", "0"], default="0")
            
            if choice == "0":
                break
            elif choice == "1":
                self.logger.display_audit_logs(limit=50)
            elif choice == "2":
                event_type = Prompt.ask("Tipo de evento", choices=[
                    'login', 'logout', 'user_change', 'config_change', 
                    'file_access', 'security', 'error'
                ])
                self.logger.display_audit_logs(limit=50)
            elif choice == "3":
                if Confirm.ask("Tem certeza?"):
                    self.logger.clear_logs()
            
            Prompt.ask("\nPressione Enter para continuar")
    
    def settings_menu(self):
        """Menu de configurações"""
        while True:
            self.clear_screen()
            self.print_header("Configurações")
            
            config = self.config_generator.get_all_configs()
            
            console.print(f"[bold]Caminho base:[/bold] {config.get('base_path', '/srv/files')}")
            console.print(f"[bold]SSL Habilitado:[/bold] {config.get('security', {}).get('ssl_enabled', True)}")
            
            self.print_menu([
                "Alterar caminho base",
                "Backup de configurações",
                "Restaurar configurações",
                "Voltar"
            ])
            
            choice = Prompt.ask("Escolha", choices=["1", "2", "3", "0"], default="0")
            
            if choice == "0":
                break
            elif choice == "1":
                new_path = Prompt.ask("Novo caminho base", default=self.base_path)
                self.base_path = new_path
                config['base_path'] = new_path
                self.config_generator._save_config()
            elif choice == "2":
                backup_path = self.config_generator.backup_configs()
                console.print(f"[green]✓ Backup criado: {backup_path}[/green]")
            elif choice == "3":
                console.print("[yellow]⚠ Restauração manual requerida[/yellow]")


def main():
    """Função principal"""
    console.print("\n[bold cyan]File Server Manager[/bold cyan]\n")
    
    # Verificar se é root (necessário para a maioria das operações)
    if os.geteuid() != 0:
        console.print("[yellow]⚠ Aviso: Execute como root (sudo) para todas as funcionalidades[/yellow]\n")
    
    manager = FileServerManager()
    manager.main_menu()


if __name__ == "__main__":
    main()