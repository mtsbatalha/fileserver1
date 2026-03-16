"""
Servidor SFTP - Gerencia configuração e operação do servidor SFTP (OpenSSH)
"""

import subprocess
import os
from typing import Dict, List, Optional
from rich.console import Console

console = Console()


class SFTPServer:
    """Classe para gerenciamento do servidor SFTP"""
    
    def __init__(self, config_path: str = '/etc/file-server-manager'):
        self.config_path = config_path
        self.config_file = '/etc/ssh/sshd_config'
        self.service_name = 'sshd'
        self.sftp_only_users = []
        
    def is_installed(self) -> bool:
        """Verifica se o servidor SFTP está instalado"""
        try:
            result = subprocess.run(
                ['dpkg', '-l', 'openssh-server'],
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
        """Inicia o serviço SSH/SFTP"""
        console.print("[cyan]▶ Iniciando serviço SSH...[/cyan]")
        try:
            subprocess.run(['systemctl', 'start', self.service_name], capture_output=True, timeout=30)
            console.print("[green]✓ Serviço SSH iniciado[/green]")
            return True
        except Exception as e:
            console.print(f"[red]✗ Erro ao iniciar SSH: {e}[/red]")
            return False
    
    def stop(self) -> bool:
        """Para o serviço SSH/SFTP"""
        console.print("[yellow]⚠ Parando serviço SSH (cuidado: pode desconectar sessões remotas)...[/yellow]")
        try:
            subprocess.run(['systemctl', 'stop', self.service_name], capture_output=True, timeout=30)
            console.print("[green]✓ Serviço SSH parado[/green]")
            return True
        except Exception as e:
            console.print(f"[red]✗ Erro ao parar SSH: {e}[/red]")
            return False
    
    def restart(self) -> bool:
        """Reinicia o serviço SSH/SFTP"""
        console.print("[cyan]▶ Reiniciando serviço SSH...[/cyan]")
        try:
            subprocess.run(['systemctl', 'restart', self.service_name], capture_output=True, timeout=30)
            console.print("[green]✓ Serviço SSH reiniciado[/green]")
            return True
        except Exception as e:
            console.print(f"[red]✗ Erro ao reiniciar SSH: {e}[/red]")
            return False
    
    def enable(self) -> bool:
        """Habilita serviço para iniciar automaticamente"""
        try:
            subprocess.run(['systemctl', 'enable', self.service_name], capture_output=True, timeout=30)
            console.print("[green]✓ Serviço SSH habilitado para auto-start[/green]")
            return True
        except Exception as e:
            console.print(f"[red]✗ Erro: {e}[/red]")
            return False
    
    def get_status(self) -> Dict:
        """Obtém status do serviço SFTP"""
        return {
            'installed': self.is_installed(),
            'running': self.is_running(),
            'service': self.service_name,
            'config_file': self.config_file,
            'sftp_only_users': self.sftp_only_users
        }
    
    def add_sftp_only_user(self, username: str, home_dir: str = None) -> bool:
        """
        Adiciona usuário com acesso apenas SFTP (chrooted)
        
        Args:
            username: Nome do usuário
            home_dir: Diretório home do usuário
        """
        console.print(f"[cyan]▶ Configurando usuário SFTP-only: {username}...[/cyan]")
        
        if home_dir is None:
            home_dir = f'/srv/files/sftp/{username}'
        
        try:
            # Criar diretório com permissões corretas para chroot
            os.makedirs(home_dir, exist_ok=True)
            os.chmod(home_dir, 0o755)
            
            # Adicionar configuração ao sshd_config
            self._add_match_block(username, home_dir)
            
            self.sftp_only_users.append(username)
            console.print(f"[green]✓ Usuário {username} configurado como SFTP-only[/green]")
            return True
        except Exception as e:
            console.print(f"[red]✗ Erro: {e}[/red]")
            return False
    
    def _add_match_block(self, username: str, home_dir: str):
        """Adiciona bloco Match para usuário SFTP-only"""
        match_block = f"""
# SFTP-only user: {username}
Match User {username}
    ForceCommand internal-sftp
    ChrootDirectory {home_dir}
    PermitTunnel no
    AllowTcpForwarding no
    X11Forwarding no
"""
        
        # Verificar se já existe configuração para este usuário
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                content = f.read()
            
            # Remover bloco existente se houver
            import re
            pattern = rf'# SFTP-only user: {username}.*?(?=\n#|\nMatch|\Z)'
            content = re.sub(pattern, '', content, flags=re.DOTALL)
            
            # Adicionar novo bloco
            content += match_block
            
            with open(self.config_file, 'w') as f:
                f.write(content)
    
    def remove_sftp_only_user(self, username: str) -> bool:
        """Remove configuração SFTP-only de um usuário"""
        console.print(f"[cyan]▶ Removendo configuração SFTP-only: {username}...[/cyan]")
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    content = f.read()
                
                # Remover bloco Match
                import re
                pattern = rf'# SFTP-only user: {username}.*?(?=\n#|\nMatch|\Z)'
                content = re.sub(pattern, '', content, flags=re.DOTALL)
                
                with open(self.config_file, 'w') as f:
                    f.write(content)
            
            if username in self.sftp_only_users:
                self.sftp_only_users.remove(username)
            
            console.print(f"[green]✓ Configuração removida para {username}[/green]")
            return True
        except Exception as e:
            console.print(f"[red]✗ Erro: {e}[/red]")
            return False
    
    def get_ssh_keys(self, username: str) -> List[str]:
        """Obtém chaves SSH públicas de um usuário"""
        home_dir = os.path.expanduser(f'~{username}')
        auth_keys_file = os.path.join(home_dir, '.ssh', 'authorized_keys')
        
        keys = []
        if os.path.exists(auth_keys_file):
            try:
                with open(auth_keys_file, 'r') as f:
                    for line in f:
                        if line.strip() and not line.startswith('#'):
                            keys.append(line.strip())
            except Exception:
                pass
        
        return keys
    
    def add_ssh_key(self, username: str, public_key: str) -> bool:
        """Adiciona chave SSH pública para um usuário"""
        console.print(f"[cyan]▶ Adicionando chave SSH para {username}...[/cyan]")
        
        try:
            home_dir = os.path.expanduser(f'~{username}')
            ssh_dir = os.path.join(home_dir, '.ssh')
            auth_keys_file = os.path.join(ssh_dir, 'authorized_keys')
            
            # Criar diretório .ssh se não existir
            os.makedirs(ssh_dir, exist_ok=True)
            os.chmod(ssh_dir, 0o700)
            
            # Verificar se chave já existe
            existing_keys = self.get_ssh_keys(username)
            if public_key in existing_keys:
                console.print("[yellow]⚠ Chave já existe[/yellow]")
                return True
            
            # Adicionar chave
            with open(auth_keys_file, 'a') as f:
                f.write(public_key + '\n')
            
            os.chmod(auth_keys_file, 0o600)
            console.print("[green]✓ Chave SSH adicionada[/green]")
            return True
        except Exception as e:
            console.print(f"[red]✗ Erro: {e}[/red]")
            return False
    
    def remove_ssh_key(self, username: str, key_pattern: str) -> bool:
        """Remove chave SSH de um usuário"""
        console.print(f"[cyan]▶ Removendo chave SSH de {username}...[/cyan]")
        
        try:
            home_dir = os.path.expanduser(f'~{username}')
            auth_keys_file = os.path.join(home_dir, '.ssh', 'authorized_keys')
            
            if os.path.exists(auth_keys_file):
                with open(auth_keys_file, 'r') as f:
                    lines = f.readlines()
                
                with open(auth_keys_file, 'w') as f:
                    for line in lines:
                        if key_pattern not in line:
                            f.write(line)
                
                console.print("[green]✓ Chave SSH removida[/green]")
                return True
            
            return False
        except Exception as e:
            console.print(f"[red]✗ Erro: {e}[/red]")
            return False
    
    def test_config(self) -> bool:
        """Testa configuração do SSH"""
        console.print("[cyan]▶ Testando configuração SSH...[/cyan]")
        
        try:
            result = subprocess.run(
                ['sshd', '-t'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                console.print("[green]✓ Configuração SSH válida[/green]")
                return True
            else:
                console.print(f"[red]✗ Erro na configuração: {result.stderr}[/red]")
                return False
        except Exception as e:
            console.print(f"[red]✗ Erro ao testar: {e}[/red]")
            return False
    
    def configure(
        self,
        port: int = 22,
        permit_root_login: bool = False,
        password_auth: bool = True,
        pubkey_auth: bool = True,
        max_auth_tries: int = 3
    ) -> bool:
        """Aplica configuração ao servidor SSH/SFTP"""
        # Esta função é principalmente tratada pelo ConfigGenerator
        console.print("[cyan]▶ Testando configuração SSH...[/cyan]")
        return self.test_config()