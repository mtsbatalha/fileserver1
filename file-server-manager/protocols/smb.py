"""
Servidor SMB/CIFS - Gerencia configuração e operação do servidor Samba
"""

import subprocess
import os
import json
from typing import Dict, List, Optional
from rich.console import Console

console = Console()


class SMBServer:
    """Classe para gerenciamento do servidor Samba (SMB/CIFS)"""
    
    def __init__(self, config_path: str = '/etc/file-server-manager'):
        self.config_path = config_path
        self.config_file = '/etc/samba/smb.conf'
        self.service_names = ['smbd', 'nmbd']
        self.shares = []
        
    def is_installed(self) -> bool:
        """Verifica se o Samba está instalado"""
        try:
            result = subprocess.run(
                ['dpkg', '-l', 'samba'],
                capture_output=True,
                text=True
            )
            return result.returncode == 0 and 'ii' in result.stdout
        except Exception:
            return False
    
    def is_running(self) -> bool:
        """Verifica se os serviços estão rodando"""
        try:
            for service in self.service_names:
                result = subprocess.run(
                    ['systemctl', 'is-active', service],
                    capture_output=True,
                    text=True
                )
                if result.stdout.strip() != 'active':
                    return False
            return True
        except Exception:
            return False
    
    def start(self) -> bool:
        """Inicia os serviços Samba"""
        console.print("[cyan]▶ Iniciando serviços Samba...[/cyan]")
        try:
            for service in self.service_names:
                subprocess.run(['systemctl', 'start', service], capture_output=True, timeout=30)
            console.print("[green]✓ Serviços Samba iniciados[/green]")
            return True
        except Exception as e:
            console.print(f"[red]✗ Erro ao iniciar Samba: {e}[/red]")
            return False
    
    def stop(self) -> bool:
        """Para os serviços Samba"""
        console.print("[cyan]▶ Parando serviços Samba...[/cyan]")
        try:
            for service in self.service_names:
                subprocess.run(['systemctl', 'stop', service], capture_output=True, timeout=30)
            console.print("[green]✓ Serviços Samba parados[/green]")
            return True
        except Exception as e:
            console.print(f"[red]✗ Erro ao parar Samba: {e}[/red]")
            return False
    
    def restart(self) -> bool:
        """Reinicia os serviços Samba"""
        console.print("[cyan]▶ Reiniciando serviços Samba...[/cyan]")
        try:
            for service in self.service_names:
                subprocess.run(['systemctl', 'restart', service], capture_output=True, timeout=30)
            console.print("[green]✓ Serviços Samba reiniciados[/green]")
            return True
        except Exception as e:
            console.print(f"[red]✗ Erro ao reiniciar Samba: {e}[/red]")
            return False
    
    def enable(self) -> bool:
        """Habilita serviços para iniciar automaticamente"""
        try:
            for service in self.service_names:
                subprocess.run(['systemctl', 'enable', service], capture_output=True, timeout=30)
            console.print("[green]✓ Serviços Samba habilitados para auto-start[/green]")
            return True
        except Exception as e:
            console.print(f"[red]✗ Erro: {e}[/red]")
            return False
    
    def get_status(self) -> Dict:
        """Obtém status dos serviços Samba"""
        return {
            'installed': self.is_installed(),
            'running': self.is_running(),
            'services': self.service_names,
            'config_file': self.config_file,
            'shares': self.shares
        }
    
    def add_share(
        self,
        name: str,
        path: str,
        comment: str = "",
        browseable: bool = True,
        read_only: bool = False,
        guest_ok: bool = False,
        create_mask: str = "0644",
        directory_mask: str = "0755",
        valid_users: List[str] = None,
        create_path: bool = True
    ) -> bool:
        """
        Adiciona um share Samba
        
        Args:
            name: Nome do share
            path: Caminho do diretório
            comment: Descrição do share
            browseable: Se o share aparece na lista
            read_only: Se é apenas leitura
            guest_ok: Permite acesso sem autenticação
            create_mask: Permissões para arquivos criados
            directory_mask: Permissões para diretórios criados
            valid_users: Lista de usuários permitidos
            create_path: Se True, cria o diretório se não existir
        """
        console.print(f"[cyan]▶ Adicionando share Samba: {name} ({path})...[/cyan]")
        
        # Criar diretório se necessário
        if create_path and not os.path.exists(path):
            try:
                os.makedirs(path, exist_ok=True)
                os.chmod(path, 0o755)
                console.print(f"[green]✓ Diretório criado: {path}[/green]")
            except Exception as e:
                console.print(f"[red]✗ Erro ao criar diretório: {e}[/red]")
                return False
        
        # Ler configuração atual
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                content = f.read()
        else:
            content = "[global]\n   workgroup = WORKGROUP\n   security = user\n"
        
        # Verificar se share já existe
        if f"[{name}]" in content:
            console.print(f"[yellow]⚠ Share {name} já existe[/yellow]")
            return True
        
        # Criar configuração do share
        share_config = f"""
[{name}]
   comment = {comment if comment else name}
   path = {path}
   browseable = {'yes' if browseable else 'no'}
   read only = {'yes' if read_only else 'no'}
   guest ok = {'yes' if guest_ok else 'no'}
   create mask = {create_mask}
   directory mask = {directory_mask}
"""
        
        if valid_users:
            share_config += f"   valid users = {', '.join(valid_users)}\n"
        
        # Adicionar à configuração
        content += share_config
        
        try:
            with open(self.config_file, 'w') as f:
                f.write(content)
            
            self.shares.append({
                'name': name,
                'path': path,
                'browseable': browseable,
                'read_only': read_only
            })
            
            console.print(f"[green]✓ Share {name} adicionado[/green]")
            
            # Testar configuração
            self.test_config()
            
            return True
        except Exception as e:
            console.print(f"[red]✗ Erro: {e}[/red]")
            return False
    
    def remove_share(self, name: str) -> bool:
        """Remove um share Samba"""
        console.print(f"[cyan]▶ Removendo share Samba: {name}...[/cyan]")
        
        try:
            if not os.path.exists(self.config_file):
                return False
            
            with open(self.config_file, 'r') as f:
                content = f.read()
            
            # Encontrar e remover o share
            import re
            pattern = rf'\[{re.escape(name)}\].*?(?=\n\[|\Z)'
            content = re.sub(pattern, '', content, flags=re.DOTALL)
            
            with open(self.config_file, 'w') as f:
                f.write(content)
            
            # Remover da lista em memória
            self.shares = [s for s in self.shares if s['name'] != name]
            
            console.print(f"[green]✓ Share {name} removido[/green]")
            
            # Testar configuração
            self.test_config()
            
            return True
        except Exception as e:
            console.print(f"[red]✗ Erro: {e}[/red]")
            return False
    
    def list_shares(self) -> List[Dict]:
        """Lista todos os shares"""
        shares = []
        
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                content = f.read()
            
            import re
            # Encontrar todas as seções [share_name]
            pattern = r'\[([^\]]+)\]\s*\n((?:[^\n]*\n)*?)(?=\[|\Z)'
            matches = re.findall(pattern, content)
            
            for name, config in matches:
                if name.lower() != 'global':
                    shares.append({
                        'name': name,
                        'config': config.strip()
                    })
        
        self.shares = shares
        return shares
    
    def add_user(self, username: str, password: str = None) -> bool:
        """
        Adiciona usuário ao Samba
        
        Args:
            username: Nome do usuário (deve existir no sistema)
            password: Senha do usuário (opcional, será solicitada se não fornecida)
        """
        console.print(f"[cyan]▶ Adicionando usuário Samba: {username}...[/cyan]")
        
        try:
            # Verificar se usuário existe no sistema
            result = subprocess.run(
                ['id', username],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                console.print(f"[red]✗ Usuário {username} não existe no sistema[/red]")
                return False
            
            # Adicionar ao Samba
            if password:
                # Usar senha fornecida
                process = subprocess.Popen(
                    ['smbpasswd', '-a', username],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                stdout, stderr = process.communicate(
                    f"{password}\n{password}\n".encode()
                )
                
                if process.returncode == 0:
                    console.print(f"[green]✓ Usuário {username} adicionado ao Samba[/green]")
                    return True
                else:
                    console.print(f"[red]✗ Erro: {stderr.decode()}[/red]")
                    return False
            else:
                console.print("[yellow]⚠ Use 'smbpasswd -a username' para adicionar senha[/yellow]")
                return False
        except Exception as e:
            console.print(f"[red]✗ Erro: {e}[/red]")
            return False
    
    def remove_user(self, username: str) -> bool:
        """Remove usuário do Samba"""
        console.print(f"[cyan]▶ Removendo usuário Samba: {username}...[/cyan]")
        
        try:
            result = subprocess.run(
                ['smbpasswd', '-x', username],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                console.print(f"[green]✓ Usuário {username} removido do Samba[/green]")
                return True
            else:
                console.print(f"[red]✗ Erro: {result.stderr}[/red]")
                return False
        except Exception as e:
            console.print(f"[red]✗ Erro: {e}[/red]")
            return False
    
    def set_user_password(self, username: str, password: str) -> bool:
        """Define senha de um usuário Samba"""
        console.print(f"[cyan]▶ Alterando senha de {username}...[/cyan]")
        
        try:
            process = subprocess.Popen(
                ['smbpasswd', '-s', username],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate(
                f"{password}\n{password}\n".encode()
            )
            
            if process.returncode == 0:
                console.print(f"[green]✓ Senha de {username} alterada[/green]")
                return True
            else:
                console.print(f"[red]✗ Erro: {stderr.decode()}[/red]")
                return False
        except Exception as e:
            console.print(f"[red]✗ Erro: {e}[/red]")
            return False
    
    def list_users(self) -> List[str]:
        """Lista usuários Samba"""
        try:
            result = subprocess.run(
                ['pdbedit', '-L'],
                capture_output=True,
                text=True
            )
            
            users = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    parts = line.split(':')
                    if parts:
                        users.append(parts[0])
            
            return users
        except Exception:
            return []
    
    def test_config(self) -> bool:
        """Testa configuração do Samba"""
        console.print("[cyan]▶ Testando configuração Samba...[/cyan]")
        
        try:
            result = subprocess.run(
                ['testparm', '-s'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                console.print("[green]✓ Configuração Samba válida[/green]")
                return True
            else:
                console.print(f"[red]✗ Erro na configuração: {result.stderr}[/red]")
                return False
        except Exception as e:
            console.print(f"[red]✗ Erro ao testar: {e}[/red]")
            return False
    
    def configure(
        self,
        workgroup: str = "WORKGROUP",
        server_string: str = "File Server",
        security: str = "user"
    ) -> bool:
        """Configurações globais do Samba"""
        console.print("[cyan]▶ Configurando Samba...[/cyan]")
        
        # Ler configuração atual
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                content = f.read()
        else:
            content = ""
        
        # Atualizar seção global
        import re
        
        global_section = f"""[global]
   workgroup = {workgroup}
   server string = {server_string}
   security = {security}
   log file = /var/log/samba/%m.log
   max log size = 1000
"""
        
        # Substituir ou adicionar seção global
        if '[global]' in content:
            pattern = r'\[global\].*?(?=\n\[|\Z)'
            content = re.sub(pattern, global_section.strip(), content, flags=re.DOTALL)
        else:
            content = global_section + content
        
        try:
            with open(self.config_file, 'w') as f:
                f.write(content)
            
            console.print("[green]✓ Configuração global aplicada[/green]")
            return self.test_config()
        except Exception as e:
            console.print(f"[red]✗ Erro: {e}[/red]")
            return False