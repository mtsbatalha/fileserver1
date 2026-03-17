"""
Gerenciador de Usuários - CRUD de usuários para servidores de arquivos
"""

import subprocess
import os
import json
import hashlib
import secrets
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import bcrypt

console = Console()


class UserManager:
    """Classe para gerenciamento de usuários do servidor de arquivos"""
    
    def __init__(self, config_path: str = '/etc/file-server-manager'):
        self.config_path = config_path
        self.users_file = os.path.join(config_path, 'users.json')
        self.users = self._load_users()
        
    def _load_users(self) -> Dict:
        """Carrega usuários do arquivo de configuração"""
        if os.path.exists(self.users_file):
            try:
                with open(self.users_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                console.print(f"[yellow]⚠ Erro ao carregar usuários: {e}[/yellow]")
        return {'users': [], 'groups': {}}
    
    def _save_users(self):
        """Salva usuários no arquivo de configuração"""
        try:
            os.makedirs(self.config_path, exist_ok=True)
            with open(self.users_file, 'w') as f:
                json.dump(self.users, f, indent=2, default=str)
        except Exception as e:
            console.print(f"[red]✗ Erro ao salvar usuários: {e}[/red]")
    
    def _hash_password(self, password: str) -> str:
        """Gera hash da senha usando bcrypt"""
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def _verify_password(self, password: str, hashed: str) -> bool:
        """Verifica se a senha corresponde ao hash"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception:
            return False
    
    def create_user(
        self,
        username: str,
        password: str,
        home_dir: str = None,
        protocols: List[str] = None,
        quota_mb: int = None,
        ip_whitelist: List[str] = None,
        expiration: str = None,
        create_system_user: bool = False
    ) -> Dict[str, Any]:
        """
        Cria um novo usuário
        
        Args:
            username: Nome do usuário
            password: Senha (será hasheada)
            home_dir: Diretório home do usuário
            protocols: Lista de protocolos que o usuário pode acessar
            quota_mb: Quota de disco em MB
            ip_whitelist: Lista de IPs permitidos
            expiration: Data de expiração (YYYY-MM-DD)
            create_system_user: Se True, cria usuário no sistema também
        """
        # Verificar se usuário já existe
        if self.get_user(username):
            return {'success': False, 'message': f'Usuário {username} já existe'}
        
        # Configurações padrão
        if protocols is None:
            protocols = ['ftp', 'sftp', 'smb']
        
        if home_dir is None:
            home_dir = f'/srv/files/users/{username}'
        
        user_data = {
            'username': username,
            'password_hash': self._hash_password(password),
            'home_dir': home_dir,
            'protocols': protocols,
            'quota_mb': quota_mb,
            'ip_whitelist': ip_whitelist or [],
            'expiration': expiration,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'enabled': True,
            'system_user': create_system_user,
            'groups': [],
            'permissions': {
                'read': True,
                'write': True,
                'delete': True,
                'execute': False
            }
        }
        
        # CORREÇÃO: Sempre criar usuário no sistema operacional para autenticação FTP/SFTP/PAM
        # O vsftpd e SSH usam PAM (Pluggable Authentication Modules) que autentica via /etc/passwd e /etc/shadow
        if not self._create_system_user(username, home_dir, password):
            # Se falhar, ainda tentamos criar usuário no sistema para garantir autenticação
            console.print(f"[yellow]⚠ Tentando método alternativo para criar usuário {username}...[/yellow]")
            # Tentar criar com método alternativo (adduser)
            try:
                subprocess.run([
                    'adduser', '--disabled-login', '--home', home_dir, '--gecos', 'File Server User', username
                ], capture_output=True, timeout=30)
                # Definir senha
                self._update_system_password(username, password)
            except Exception as e:
                console.print(f"[yellow]⚠ Erro no método alternativo: {e}[/yellow]")
        
        # CORREÇÃO: Sempre sincronizar com FTP independente de create_system_user
        # O vsftpd requer usuários do sistema para autenticação via PAM
        if 'ftp' in protocols:
            self._sync_ftp_user(username, password)
        
        # CORREÇÃO: Garantir que diretório home existe e tem permissões corretas
        try:
            os.makedirs(home_dir, exist_ok=True)
            # Tentar definir propriedade (pode falhar sem root)
            try:
                import pwd
                uid = pwd.getpwnam(username).pw_uid
                gid = pwd.getpwnam(username).pw_gid
                os.chown(home_dir, uid, gid)
            except:
                pass  # Sem permissões para chown
            os.chmod(home_dir, 0o755)
        except Exception as e:
            console.print(f"[yellow]⚠ Aviso ao criar diretório home: {e}[/yellow]")
        
        # Adicionar usuário à lista
        self.users['users'].append(user_data)
        self._save_users()
        
        console.print(f"[green]✓ Usuário {username} criado com sucesso![/green]")
        return {'success': True, 'user': user_data}
    
    def _create_system_user(self, username: str, home_dir: str, password: str = None) -> bool:
        """Cria usuário no sistema operacional"""
        try:
            # Verificar se já existe
            result = subprocess.run(
                ['id', username],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                console.print(f"[yellow]⚠ Usuário {username} já existe no sistema[/yellow]")
                # Atualizar senha se fornecida
                if password:
                    self._update_system_password(username, password)
                return True
            
            # CORREÇÃO: Usar /bin/bash como shell para permitir autenticação FTP
            # O vsftpd com check_shell=NO permite login mesmo com shell nologin,
            # mas algumas versões do PAM podem ter problemas
            # Vamos usar /bin/bash e depois restringir via configuração
            cmd = [
                'useradd',
                '-m',
                '-d', home_dir,
                '-s', '/bin/bash',  # CORREÇÃO: Usar bash para permitir autenticação
                username
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                console.print(f"[red]✗ Erro ao criar usuário: {result.stderr}[/red]")
                return False
            
            # CORREÇÃO: Criar e configurar diretório home com permissões corretas
            self._setup_home_directory(username, home_dir)
            
            # Definir senha se fornecida
            if password:
                self._update_system_password(username, password)
            
            console.print(f"[green]✓ Usuário {username} criado no sistema[/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]✗ Erro: {str(e)}[/red]")
            return False
    
    def _setup_home_directory(self, username: str, home_dir: str) -> bool:
        """Configura diretório home com permissões corretas para FTP/SFTP"""
        try:
            import pwd
            
            # Obter UID e GID do usuário
            uid = pwd.getpwnam(username).pw_uid
            gid = pwd.getpwnam(username).pw_gid
            
            # Criar diretório se não existir
            os.makedirs(home_dir, exist_ok=True)
            
            # CORREÇÃO CRÍTICA: Para chroot jail funcionar corretamente:
            # 1. O diretório home deve ser owned por root
            # 2. O diretório home NÃO pode ser writable pelo usuário
            # 3. Criar um subdiretório 'upload' que o usuário pode escrever
            
            # Definir ownership do home para root (necessário para chroot)
            os.chown(home_dir, 0, 0)  # root:root
            os.chmod(home_dir, 0o755)  # rwxr-xr-x
            
            # Criar subdiretório para upload
            upload_dir = os.path.join(home_dir, 'upload')
            os.makedirs(upload_dir, exist_ok=True)
            os.chown(upload_dir, uid, gid)
            os.chmod(upload_dir, 0o755)
            
            # Criar arquivo de boas-vindas
            welcome_file = os.path.join(home_dir, '.message')
            with open(welcome_file, 'w') as f:
                f.write(f"Bem-vindo ao servidor de arquivos, {username}!\\n")
                f.write("Use o diretório 'upload' para enviar arquivos.\\n")
            os.chown(welcome_file, uid, gid)
            
            console.print(f"[green]✓ Diretório home configurado: {home_dir}[/green]")
            console.print(f"[dim]  - Upload em: {upload_dir}[/dim]")
            return True
            
        except Exception as e:
            console.print(f"[yellow]⚠ Erro ao configurar diretório home: {e}[/yellow]")
            return False
    
    def _update_system_password(self, username: str, password: str) -> bool:
        """Atualiza senha de usuário no sistema"""
        try:
            process = subprocess.Popen(
                ['chpasswd'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate(f"{username}:{password}\n".encode())
            
            if process.returncode == 0:
                console.print(f"[green]✓ Senha de {username} atualizada no sistema[/green]")
                return True
            else:
                console.print(f"[red]✗ Erro ao atualizar senha: {stderr.decode()}[/red]")
                return False
        except Exception as e:
            console.print(f"[red]✗ Erro: {str(e)}[/red]")
            return False
    
    def _sync_ftp_user(self, username: str, password: str = None) -> bool:
        """Sincroniza usuário com servidor FTP"""
        try:
            from protocols.ftp import FTPServer
            ftp_server = FTPServer(self.config_path)
            
            # Adicionar às listas do vsftpd
            ftp_server.add_user(username, f'/srv/files/users/{username}')
            
            # Atualizar senha do sistema para autenticação FTP/PAM
            if password:
                self._update_system_password(username, password)
            
            console.print(f"[green]✓ Usuário {username} sincronizado com FTP[/green]")
            return True
        except Exception as e:
            console.print(f"[yellow]⚠ Não foi possível sincronizar com FTP: {e}[/yellow]")
            return False
    
    def _get_uid(self, username: str) -> int:
        """Obtém UID do usuário"""
        try:
            result = subprocess.run(
                ['id', '-u', username],
                capture_output=True,
                text=True
            )
            return int(result.stdout.strip())
        except Exception:
            return 1000  # Default
    
    def _get_gid(self, username: str) -> int:
        """Obtém GID do usuário"""
        try:
            result = subprocess.run(
                ['id', '-g', username],
                capture_output=True,
                text=True
            )
            return int(result.stdout.strip())
        except Exception:
            return 1000  # Default
    
    def get_user(self, username: str) -> Optional[Dict]:
        """Obtém informações de um usuário"""
        for user in self.users.get('users', []):
            if user['username'] == username:
                return user
        return None
    
    def list_users(self) -> List[Dict]:
        """Lista todos os usuários"""
        return self.users.get('users', [])
    
    def update_user(
        self,
        username: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Atualiza informações de um usuário
        
        Args:
            username: Nome do usuário
            **kwargs: Campos para atualizar (password, home_dir, protocols, etc.)
        """
        user = self.get_user(username)
        if not user:
            return {'success': False, 'message': f'Usuário {username} não encontrado'}
        
        # Atualizar campos
        if 'password' in kwargs:
            user['password_hash'] = self._hash_password(kwargs['password'])
            
            # CORREÇÃO: Sempre atualizar senha no sistema operacional para autenticação FTP/SFTP
            # Independente de ser system_user ou não
            self._update_system_password(username, kwargs['password'])
            
            # CORREÇÃO: Sincronizar com FTP após atualizar senha
            if 'ftp' in user.get('protocols', []) or kwargs.get('protocols', user.get('protocols', [])).count('ftp') > 0:
                self._sync_ftp_user(username, kwargs['password'])
        
        if 'home_dir' in kwargs:
            user['home_dir'] = kwargs['home_dir']
        
        if 'protocols' in kwargs:
            user['protocols'] = kwargs['protocols']
        
        if 'quota_mb' in kwargs:
            user['quota_mb'] = kwargs['quota_mb']
        
        if 'ip_whitelist' in kwargs:
            user['ip_whitelist'] = kwargs['ip_whitelist']
        
        if 'expiration' in kwargs:
            user['expiration'] = kwargs['expiration']
        
        if 'enabled' in kwargs:
            user['enabled'] = kwargs['enabled']
        
        if 'permissions' in kwargs:
            user['permissions'].update(kwargs['permissions'])
        
        user['updated_at'] = datetime.now().isoformat()
        self._save_users()
        
        # Atualizar usuário no sistema se necessário
        if user.get('system_user'):
            if 'home_dir' in kwargs:
                try:
                    subprocess.run(
                        ['usermod', '-d', kwargs['home_dir'], username],
                        capture_output=True
                    )
                except Exception:
                    pass
            
            # Atualizar senha no sistema e FTP se password foi alterada
            if 'password' in kwargs:
                self._update_system_password(username, kwargs['password'])
                if 'ftp' in user.get('protocols', []):
                    self._sync_ftp_user(username, kwargs['password'])
        
        console.print(f"[green]✓ Usuário {username} atualizado![/green]")
        return {'success': True, 'user': user}
    
    def delete_user(self, username: str, delete_home: bool = False, delete_system: bool = False) -> Dict[str, Any]:
        """
        Exclui um usuário
        
        Args:
            username: Nome do usuário
            delete_home: Se True, remove o diretório home
            delete_system: Se True, remove o usuário do sistema também
        """
        user = self.get_user(username)
        if not user:
            return {'success': False, 'message': f'Usuário {username} não encontrado'}
        
        # Remover da lista
        self.users['users'] = [u for u in self.users['users'] if u['username'] != username]
        self._save_users()
        
        # Remover diretório home se solicitado
        if delete_home and os.path.exists(user['home_dir']):
            try:
                import shutil
                shutil.rmtree(user['home_dir'])
                console.print(f"[green]✓ Diretório {user['home_dir']} removido[/green]")
            except Exception as e:
                console.print(f"[yellow]⚠ Não foi possível remover diretório: {e}[/yellow]")
        
        # Remover usuário do sistema se solicitado
        if delete_system and user.get('system_user'):
            try:
                subprocess.run(
                    ['userdel', '-r' if delete_home else '', username],
                    capture_output=True
                )
                console.print(f"[green]✓ Usuário {username} removido do sistema[/green]")
            except Exception as e:
                console.print(f"[yellow]⚠ Não foi possível remover do sistema: {e}[/yellow]")
        
        console.print(f"[green]✓ Usuário {username} excluído![/green]")
        return {'success': True}
    
    def verify_credentials(self, username: str, password: str) -> bool:
        """Verifica credenciais do usuário"""
        user = self.get_user(username)
        if not user:
            return False
        
        if not user.get('enabled', True):
            return False
        
        # Verificar expiração
        if user.get('expiration'):
            try:
                exp_date = datetime.fromisoformat(user['expiration'])
                if exp_date < datetime.now():
                    return False
            except Exception:
                pass
        
        return self._verify_password(password, user['password_hash'])
    
    def set_quota(self, username: str, quota_mb: int) -> Dict[str, Any]:
        """Define quota de disco para um usuário"""
        user = self.get_user(username)
        if not user:
            return {'success': False, 'message': f'Usuário {username} não encontrado'}
        
        user['quota_mb'] = quota_mb
        user['updated_at'] = datetime.now().isoformat()
        self._save_users()
        
        # Aplicar quota no sistema se usuário for system_user
        if user.get('system_user'):
            self._apply_quota(username, quota_mb)
        
        console.print(f"[green]✓ Quota de {quota_mb}MB definida para {username}[/green]")
        return {'success': True}
    
    def _apply_quota(self, username: str, quota_mb: int):
        """Aplica quota no sistema de arquivos"""
        try:
            # Converter para KB (unidade usada pelo quota)
            quota_kb = quota_mb * 1024
            
            # Comando para definir quota (requer quota habilitado no filesystem)
            cmd = [
                'setquota',
                '-u', username,
                str(quota_kb), str(quota_kb + quota_kb * 0.1),  # soft e hard
                '0', '0',  # inodes
                '/'
            ]
            
            subprocess.run(cmd, capture_output=True)
        except Exception as e:
            console.print(f"[yellow]⚠ Não foi possível aplicar quota: {e}[/yellow]")
    
    def add_to_group(self, username: str, group: str) -> Dict[str, Any]:
        """Adiciona usuário a um grupo"""
        user = self.get_user(username)
        if not user:
            return {'success': False, 'message': f'Usuário {username} não encontrado'}
        
        if 'groups' not in user:
            user['groups'] = []
        
        if group not in user['groups']:
            user['groups'].append(group)
        
        user['updated_at'] = datetime.now().isoformat()
        self._save_users()
        
        console.print(f"[green]✓ {username} adicionado ao grupo {group}[/green]")
        return {'success': True}
    
    def remove_from_group(self, username: str, group: str) -> Dict[str, Any]:
        """Remove usuário de um grupo"""
        user = self.get_user(username)
        if not user:
            return {'success': False, 'message': f'Usuário {username} não encontrado'}
        
        if 'groups' in user and group in user['groups']:
            user['groups'].remove(group)
            user['updated_at'] = datetime.now().isoformat()
            self._save_users()
            console.print(f"[green]✓ {username} removido do grupo {group}[/green]")
        
        return {'success': True}
    
    def display_users_table(self):
        """Exibe tabela formatada de usuários"""
        table = Table(title="Usuários do Servidor de Arquivos")
        
        table.add_column("Username", style="cyan")
        table.add_column("Home Dir", style="green")
        table.add_column("Protocolos", style="yellow")
        table.add_column("Quota (MB)", style="magenta")
        table.add_column("Status", style="blue")
        table.add_column("Criação", style="white")
        
        for user in self.list_users():
            status = "[green]Ativo[/green]" if user.get('enabled', True) else "[red]Inativo[/red]"
            protocolos = ", ".join(user.get('protocols', []))
            created = user.get('created_at', 'N/A')[:10] if user.get('created_at') else 'N/A'
            
            table.add_row(
                user['username'],
                user.get('home_dir', 'N/A'),
                protocolos,
                str(user.get('quota_mb', 'Ilimitado')),
                status,
                created
            )
        
        console.print(table)
    
    def export_users(self, output_file: str) -> bool:
        """Exporta usuários para arquivo JSON"""
        try:
            with open(output_file, 'w') as f:
                json.dump(self.users, f, indent=2)
            console.print(f"[green]✓ Usuários exportados para {output_file}[/green]")
            return True
        except Exception as e:
            console.print(f"[red]✗ Erro na exportação: {e}[/red]")
            return False
    
    def import_users(self, input_file: str) -> bool:
        """Importa usuários de arquivo JSON"""
        try:
            with open(input_file, 'r') as f:
                imported = json.load(f)
            
            # Mesclar usuários
            existing_usernames = {u['username'] for u in self.users.get('users', [])}
            
            for user in imported.get('users', []):
                if user['username'] not in existing_usernames:
                    self.users['users'].append(user)
            
            self._save_users()
            console.print(f"[green]✓ Usuários importados de {input_file}[/green]")
            return True
        except Exception as e:
            console.print(f"[red]✗ Erro na importação: {e}[/red]")
            return False