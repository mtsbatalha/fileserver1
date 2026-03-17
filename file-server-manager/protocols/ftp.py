"""
Servidor FTP - Gerencia configuração e operação do servidor FTP (vsftpd)
"""

import subprocess
import os
from typing import Dict, List, Optional
from rich.console import Console

console = Console()


class FTPServer:
    """Classe para gerenciamento do servidor FTP"""
    
    def __init__(self, config_path: str = '/etc/file-server-manager'):
        self.config_path = config_path
        self.config_file = '/etc/vsftpd.conf'
        self.service_name = 'vsftpd'
        
    def is_installed(self) -> bool:
        """Verifica se o servidor FTP está instalado"""
        try:
            result = subprocess.run(
                ['dpkg', '-l', 'vsftpd'],
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
        """Inicia o serviço FTP"""
        console.print("[cyan]▶ Iniciando serviço FTP...[/cyan]")
        try:
            subprocess.run(['systemctl', 'start', self.service_name], capture_output=True, timeout=30)
            console.print("[green]✓ Serviço FTP iniciado[/green]")
            return True
        except Exception as e:
            console.print(f"[red]✗ Erro ao iniciar FTP: {e}[/red]")
            return False
    
    def stop(self) -> bool:
        """Para o serviço FTP"""
        console.print("[cyan]▶ Parando serviço FTP...[/cyan]")
        try:
            subprocess.run(['systemctl', 'stop', self.service_name], capture_output=True, timeout=30)
            console.print("[green]✓ Serviço FTP parado[/green]")
            return True
        except Exception as e:
            console.print(f"[red]✗ Erro ao parar FTP: {e}[/red]")
            return False
    
    def restart(self) -> bool:
        """Reinicia o serviço FTP"""
        console.print("[cyan]▶ Reiniciando serviço FTP...[/cyan]")
        try:
            subprocess.run(['systemctl', 'restart', self.service_name], capture_output=True, timeout=30)
            console.print("[green]✓ Serviço FTP reiniciado[/green]")
            return True
        except Exception as e:
            console.print(f"[red]✗ Erro ao reiniciar FTP: {e}[/red]")
            return False
    
    def enable(self) -> bool:
        """Habilita serviço para iniciar automaticamente"""
        try:
            subprocess.run(['systemctl', 'enable', self.service_name], capture_output=True, timeout=30)
            console.print("[green]✓ Serviço FTP habilitado para auto-start[/green]")
            return True
        except Exception as e:
            console.print(f"[red]✗ Erro: {e}[/red]")
            return False
    
    def get_status(self) -> Dict:
        """Obtém status do serviço FTP"""
        return {
            'installed': self.is_installed(),
            'running': self.is_running(),
            'service': self.service_name,
            'config_file': self.config_file
        }
    
    def add_user(self, username: str, home_dir: str = None) -> bool:
        """Adiciona usuário à lista de usuários FTP"""
        console.print(f"[cyan]▶ Adicionando usuário {username} ao FTP...[/cyan]")
        
        try:
            # Criar arquivo de lista se não existir
            user_list_file = '/etc/vsftpd.user_list'
            chroot_list_file = '/etc/vsftpd.chroot_list'
            
            # Garantir que os arquivos existam
            if not os.path.exists(user_list_file):
                open(user_list_file, 'a').close()
                os.chmod(user_list_file, 0o644)
                console.print(f"[green]✓ Criado: {user_list_file}[/green]")
            
            if not os.path.exists(chroot_list_file):
                open(chroot_list_file, 'a').close()
                os.chmod(chroot_list_file, 0o644)
                console.print(f"[green]✓ Criado: {chroot_list_file}[/green]")
            
            # Verificar se usuário já está na lista
            with open(user_list_file, 'r') as f:
                existing_users = [line.strip() for line in f.readlines()]
            
            if username not in existing_users:
                with open(user_list_file, 'a') as f:
                    f.write(username + '\n')
                console.print(f"[green]✓ Usuário {username} adicionado à lista[/green]")
            else:
                console.print(f"[yellow]⚠ Usuário {username} já está na lista[/yellow]")
            
            # Adicionar ao chroot list se home_dir especificado
            if home_dir:
                with open(chroot_list_file, 'r') as f:
                    chroot_users = [line.strip() for line in f.readlines()]
                
                if username not in chroot_users:
                    with open(chroot_list_file, 'a') as f:
                        f.write(username + '\n')
                    console.print(f"[green]✓ Usuário {username} adicionado ao chroot[/green]")
            
            return True
        except Exception as e:
            console.print(f"[red]✗ Erro: {e}[/red]")
            return False
    
    def remove_user(self, username: str) -> bool:
        """Remove usuário da lista FTP"""
        console.print(f"[cyan]▶ Removendo usuário {username} do FTP...[/cyan]")
        
        try:
            # Remover da lista de usuários
            self._remove_from_file('/etc/vsftpd.user_list', username)
            self._remove_from_file('/etc/vsftpd.chroot_list', username)
            
            console.print(f"[green]✓ Usuário {username} removido[/green]")
            return True
        except Exception as e:
            console.print(f"[red]✗ Erro: {e}[/red]")
            return False
    
    def _remove_from_file(self, filepath: str, line_to_remove: str) -> bool:
        """Remove uma linha de um arquivo"""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    lines = f.readlines()
                
                with open(filepath, 'w') as f:
                    for line in lines:
                        if line.strip() != line_to_remove:
                            f.write(line)
                return True
        except Exception:
            pass
        return False
    
    def configure(
        self,
        port: int = 21,
        passive_ports: str = "40000-40100",
        anonymous_enable: bool = False,
        ssl_enable: bool = True,
        max_clients: int = 50,
        max_per_ip: int = 5
    ) -> bool:
        """Aplica configuração ao servidor FTP"""
        # Esta função é principalmente tratada pelo ConfigGenerator
        # Aqui apenas reiniciamos para aplicar mudanças
        console.print("[cyan]▶ Aplicando configuração FTP...[/cyan]")
        self.restart()
        return True
    
    def sync_user(self, username: str, password: str = None) -> bool:
        """
        Sincroniza usuário com o sistema para autenticação FTP
        
        Args:
            username: Nome do usuário
            password: Senha do usuário (opcional, se não existir atualiza apenas listas)
        """
        console.print(f"[cyan]▶ Sincronizando usuário FTP: {username}...[/cyan]")
        
        try:
            # Verificar se usuário existe no sistema
            result = subprocess.run(['id', username], capture_output=True, text=True)
            
            if result.returncode != 0:
                # Criar usuário no sistema
                subprocess.run([
                    'useradd', '-m', '-d', f'/srv/files/users/{username}',
                    '-s', '/usr/sbin/nologin', username
                ], capture_output=True)
                console.print(f"[green]✓ Usuário {username} criado no sistema[/green]")
            
            # Adicionar às listas do vsftpd
            self.add_user(username, f'/srv/files/users/{username}')
            
            # Se senha fornecida, atualizar senha do sistema
            if password:
                # Usar chpasswd para definir senha
                process = subprocess.Popen(
                    ['chpasswd'],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                stdout, stderr = process.communicate(f"{username}:{password}\n".encode())
                
                if process.returncode == 0:
                    console.print(f"[green]✓ Senha de {username} atualizada[/green]")
                else:
                    console.print(f"[red]✗ Erro ao atualizar senha: {stderr.decode()}[/red]")
                    return False
            
            return True
            
        except Exception as e:
            console.print(f"[red]✗ Erro: {e}[/red]")
            return False
