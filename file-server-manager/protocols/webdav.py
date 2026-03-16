"""
Servidor WebDAV - Gerencia configuração e operação do servidor WebDAV (Apache/Nginx)
"""

import subprocess
import os
from typing import Dict, List, Optional
from rich.console import Console

console = Console()


class WebDAVServer:
    """Classe para gerenciamento do servidor WebDAV"""
    
    def __init__(self, config_path: str = '/etc/file-server-manager', server_type: str = 'apache'):
        self.config_path = config_path
        self.server_type = server_type  # 'apache' ou 'nginx'
        
        if server_type == 'apache':
            self.config_file = '/etc/apache2/sites-available/webdav.conf'
            self.service_name = 'apache2'
        else:
            self.config_file = '/etc/nginx/sites-available/webdav'
            self.service_name = 'nginx'
        
        self.users_file = '/etc/apache2/.davpasswd'
        
    def is_installed(self) -> bool:
        """Verifica se o servidor WebDAV está instalado"""
        if self.server_type == 'apache':
            try:
                result = subprocess.run(
                    ['dpkg', '-l', 'apache2'],
                    capture_output=True,
                    text=True
                )
                return result.returncode == 0 and 'ii' in result.stdout
            except Exception:
                return False
        else:
            try:
                result = subprocess.run(
                    ['dpkg', '-l', 'nginx'],
                    capture_output=True,
                    text=True
                )
                return result.returncode == 0 and 'ii' in result.stdout
            except Exception:
                return False
    
    def is_running(self) -> bool:
        """Verifica se o serviço está rodando"""
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', self.service_name],
                capture_output=True,
                text=True
            )
            return result.stdout.strip() == 'active'
        except Exception:
            return False
    
    def start(self) -> bool:
        """Inicia o serviço WebDAV"""
        console.print(f"[cyan]▶ Iniciando serviço {self.server_type}...[/cyan]")
        try:
            subprocess.run(['systemctl', 'start', self.service_name], capture_output=True, timeout=30)
            console.print(f"[green]✓ Serviço {self.server_type} iniciado[/green]")
            return True
        except Exception as e:
            console.print(f"[red]✗ Erro ao iniciar: {e}[/red]")
            return False
    
    def stop(self) -> bool:
        """Para o serviço WebDAV"""
        console.print(f"[cyan]▶ Parando serviço {self.server_type}...[/cyan]")
        try:
            subprocess.run(['systemctl', 'stop', self.service_name], capture_output=True, timeout=30)
            console.print(f"[green]✓ Serviço {self.server_type} parado[/green]")
            return True
        except Exception as e:
            console.print(f"[red]✗ Erro ao parar: {e}[/red]")
            return False
    
    def restart(self) -> bool:
        """Reinicia o serviço WebDAV"""
        console.print(f"[cyan]▶ Reiniciando serviço {self.server_type}...[/cyan]")
        try:
            subprocess.run(['systemctl', 'restart', self.service_name], capture_output=True, timeout=30)
            console.print(f"[green]✓ Serviço {self.server_type} reiniciado[/green]")
            return True
        except Exception as e:
            console.print(f"[red]✗ Erro ao reiniciar: {e}[/red]")
            return False
    
    def enable(self) -> bool:
        """Habilita serviço para iniciar automaticamente"""
        try:
            subprocess.run(['systemctl', 'enable', self.service_name], capture_output=True, timeout=30)
            console.print(f"[green]✓ Serviço {self.server_type} habilitado para auto-start[/green]")
            return True
        except Exception as e:
            console.print(f"[red]✗ Erro: {e}[/red]")
            return False
    
    def get_status(self) -> Dict:
        """Obtém status do serviço WebDAV"""
        return {
            'installed': self.is_installed(),
            'running': self.is_running(),
            'service': self.service_name,
            'server_type': self.server_type,
            'config_file': self.config_file
        }
    
    def add_user(self, username: str, password: str) -> bool:
        """
        Adiciona usuário para acesso WebDAV
        
        Args:
            username: Nome do usuário
            password: Senha do usuário
        """
        console.print(f"[cyan]▶ Adicionando usuário WebDAV: {username}...[/cyan]")
        
        if self.server_type == 'apache':
            return self._add_apache_user(username, password)
        else:
            return self._add_nginx_user(username, password)
    
    def _add_apache_user(self, username: str, password: str) -> bool:
        """Adiciona usuário para Apache WebDAV"""
        try:
            # Usar htdigest para WebDAV (autenticação Digest)
            if os.path.exists(self.users_file):
                # Adicionar usuário existente
                process = subprocess.Popen(
                    ['htdigest', self.users_file, 'WebDAV Server', username],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                stdout, stderr = process.communicate(f"{password}\n".encode())
            else:
                # Criar novo arquivo
                process = subprocess.Popen(
                    ['htdigest', '-c', self.users_file, 'WebDAV Server', username],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                stdout, stderr = process.communicate(f"{password}\n".encode())
            
            console.print(f"[green]✓ Usuário {username} adicionado[/green]")
            return True
        except Exception as e:
            console.print(f"[red]✗ Erro: {e}[/red]")
            return False
    
    def _add_nginx_user(self, username: str, password: str) -> bool:
        """Adiciona usuário para Nginx WebDAV (usando htpasswd)"""
        users_file = '/etc/nginx/.davpasswd'
        
        try:
            if os.path.exists(users_file):
                process = subprocess.Popen(
                    ['htpasswd', users_file, username],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                stdout, stderr = process.communicate(f"{password}\n".encode())
            else:
                process = subprocess.Popen(
                    ['htpasswd', '-c', users_file, username],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                stdout, stderr = process.communicate(f"{password}\n".encode())
            
            console.print(f"[green]✓ Usuário {username} adicionado[/green]")
            return True
        except Exception as e:
            console.print(f"[red]✗ Erro: {e}[/red]")
            return False
    
    def remove_user(self, username: str) -> bool:
        """Remove usuário do WebDAV"""
        console.print(f"[cyan]▶ Removendo usuário WebDAV: {username}...[/cyan]")
        
        if self.server_type == 'apache':
            users_file = self.users_file
        else:
            users_file = '/etc/nginx/.davpasswd'
        
        try:
            if not os.path.exists(users_file):
                return False
            
            # Ler arquivo e remover usuário
            with open(users_file, 'r') as f:
                lines = f.readlines()
            
            with open(users_file, 'w') as f:
                for line in lines:
                    if not line.startswith(username + ':'):
                        f.write(line)
            
            console.print(f"[green]✓ Usuário {username} removido[/green]")
            return True
        except Exception as e:
            console.print(f"[red]✗ Erro: {e}[/red]")
            return False
    
    def list_users(self) -> List[str]:
        """Lista usuários WebDAV"""
        if self.server_type == 'apache':
            users_file = self.users_file
        else:
            users_file = '/etc/nginx/.davpasswd'
        
        users = []
        if os.path.exists(users_file):
            try:
                with open(users_file, 'r') as f:
                    for line in f:
                        if line.strip() and ':' in line:
                            users.append(line.split(':')[0])
            except Exception:
                pass
        
        return users
    
    def add_directory(
        self,
        path: str,
        name: str = None,
        create_path: bool = True
    ) -> bool:
        """
        Adiciona diretório para WebDAV
        
        Args:
            path: Caminho do diretório
            name: Nome amigável do diretório
            create_path: Se True, cria o diretório se não existir
        """
        if name is None:
            name = os.path.basename(path) or path
        
        console.print(f"[cyan]▶ Adicionando diretório WebDAV: {name} ({path})...[/cyan]")
        
        # Criar diretório se necessário
        if create_path and not os.path.exists(path):
            try:
                os.makedirs(path, exist_ok=True)
                console.print(f"[green]✓ Diretório criado: {path}[/green]")
            except Exception as e:
                console.print(f"[red]✗ Erro ao criar diretório: {e}[/red]")
                return False
        
        # No Apache, os diretórios são configurados no VirtualHost
        # Aqui apenas garantimos que o diretório existe
        console.print(f"[green]✓ Diretório {name} pronto para WebDAV[/green]")
        return True
    
    def enable_module(self, module: str) -> bool:
        """Habilita módulo Apache"""
        if self.server_type != 'apache':
            return False
        
        console.print(f"[cyan]▶ Habilitando módulo Apache: {module}...[/cyan]")
        
        try:
            subprocess.run(
                ['a2enmod', module],
                capture_output=True,
                timeout=30
            )
            console.print(f"[green]✓ Módulo {module} habilitado[/green]")
            return True
        except Exception as e:
            console.print(f"[red]✗ Erro: {e}[/red]")
            return False
    
    def enable_site(self, site: str = 'webdav') -> bool:
        """Habilita site Apache"""
        if self.server_type != 'apache':
            return False
        
        console.print(f"[cyan]▶ Habilitando site: {site}...[/cyan]")
        
        try:
            subprocess.run(
                ['a2ensite', site],
                capture_output=True,
                timeout=30
            )
            console.print(f"[green]✓ Site {site} habilitado[/green]")
            return True
        except Exception as e:
            console.print(f"[yellow]⚠ Aviso: {e}[/yellow]")
            return False
    
    def test_config(self) -> bool:
        """Testa configuração do servidor"""
        console.print(f"[cyan]▶ Testando configuração {self.server_type}...[/cyan]")
        
        try:
            if self.server_type == 'apache':
                result = subprocess.run(
                    ['apache2ctl', 'configtest'],
                    capture_output=True,
                    text=True
                )
            else:
                result = subprocess.run(
                    ['nginx', '-t'],
                    capture_output=True,
                    text=True
                )
            
            if result.returncode == 0 or 'Syntax OK' in result.stdout or 'Syntax OK' in result.stderr:
                console.print("[green]✓ Configuração válida[/green]")
                return True
            else:
                console.print(f"[red]✗ Erro na configuração: {result.stderr}[/red]")
                return False
        except Exception as e:
            console.print(f"[red]✗ Erro ao testar: {e}[/red]")
            return False
    
    def configure(
        self,
        port: int = 80,
        ssl_port: int = 443,
        base_path: str = "/srv/files/webdav",
        server_name: str = "localhost",
        ssl_enabled: bool = True
    ) -> bool:
        """Configura servidor WebDAV"""
        console.print("[cyan]▶ Configurando WebDAV...[/cyan]")
        
        if self.server_type == 'apache':
            # Habilitar módulos necessários
            self.enable_module('dav')
            self.enable_module('dav_fs')
            self.enable_module('dav_lock')
            self.enable_module('auth_digest')
            
            # Criar diretório de locks
            try:
                os.makedirs('/var/lib/dav', exist_ok=True)
            except Exception:
                pass
        
        return self.test_config()