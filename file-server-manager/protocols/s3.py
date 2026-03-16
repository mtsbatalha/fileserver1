"""
Servidor S3 - Gerencia configuração e operação do MinIO (S3 compatible)
"""

import subprocess
import os
import json
from typing import Dict, List, Optional
from rich.console import Console

console = Console()


class S3Server:
    """Classe para gerenciamento do servidor MinIO (S3 compatible)"""
    
    def __init__(self, config_path: str = '/etc/file-server-manager'):
        self.config_path = config_path
        self.compose_file = os.path.join(config_path, 'minio-docker-compose.yml')
        self.env_file = os.path.join(config_path, '.minio.env')
        self.data_dir = '/srv/files/s3/data'
        self.certs_dir = '/srv/files/s3/certs'
        self.container_name = 'minio'
        self.api_port = 9000
        self.console_port = 9001
        
    def is_docker_installed(self) -> bool:
        """Verifica se Docker está instalado"""
        try:
            result = subprocess.run(
                ['docker', '--version'],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def is_docker_compose_installed(self) -> bool:
        """Verifica se Docker Compose está instalado"""
        try:
            # Tentar docker compose (v2)
            result = subprocess.run(
                ['docker', 'compose', 'version'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return True
        except Exception:
            pass
        
        try:
            # Tentar docker-compose (v1)
            result = subprocess.run(
                ['docker-compose', '--version'],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def is_installed(self) -> bool:
        """Verifica se o MinIO está instalado (container existe)"""
        try:
            result = subprocess.run(
                ['docker', 'ps', '-a', '--filter', f'name={self.container_name}', '--format', '{{.Names}}'],
                capture_output=True,
                text=True
            )
            return self.container_name in result.stdout
        except Exception:
            return False
    
    def is_running(self) -> bool:
        """Verifica se o container está rodando"""
        try:
            result = subprocess.run(
                ['docker', 'ps', '--filter', f'name={self.container_name}', '--format', '{{.Names}}'],
                capture_output=True,
                text=True
            )
            return self.container_name in result.stdout
        except Exception:
            return False
    
    def _get_compose_command(self) -> List[str]:
        """Retorna o comando docker-compose apropriado"""
        if self.is_docker_compose_installed():
            try:
                subprocess.run(
                    ['docker', 'compose', 'version'],
                    capture_output=True
                )
                return ['docker', 'compose', '-f', self.compose_file]
            except Exception:
                pass
        return ['docker-compose', '-f', self.compose_file]
    
    def start(self) -> bool:
        """Inicia o serviço MinIO"""
        console.print("[cyan]▶ Iniciando MinIO...[/cyan]")
        
        try:
            cmd = self._get_compose_command()
            result = subprocess.run(
                cmd + ['up', '-d'],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                console.print("[green]✓ MinIO iniciado[/green]")
                return True
            else:
                console.print(f"[red]✗ Erro: {result.stderr}[/red]")
                return False
        except Exception as e:
            console.print(f"[red]✗ Erro: {e}[/red]")
            return False
    
    def stop(self) -> bool:
        """Para o serviço MinIO"""
        console.print("[cyan]▶ Parando MinIO...[/cyan]")
        
        try:
            cmd = self._get_compose_command()
            result = subprocess.run(
                cmd + ['down'],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                console.print("[green]✓ MinIO parado[/green]")
                return True
            else:
                console.print(f"[red]✗ Erro: {result.stderr}[/red]")
                return False
        except Exception as e:
            console.print(f"[red]✗ Erro: {e}[/red]")
            return False
    
    def restart(self) -> bool:
        """Reinicia o serviço MinIO"""
        console.print("[cyan]▶ Reiniciando MinIO...[/cyan]")
        
        try:
            self.stop()
            return self.start()
        except Exception as e:
            console.print(f"[red]✗ Erro: {e}[/red]")
            return False
    
    def get_status(self) -> Dict:
        """Obtém status do serviço MinIO"""
        status = {
            'docker_installed': self.is_docker_installed(),
            'docker_compose_installed': self.is_docker_compose_installed(),
            'installed': self.is_installed(),
            'running': self.is_running(),
            'container': self.container_name,
            'api_port': self.api_port,
            'console_port': self.console_port,
            'data_dir': self.data_dir,
            'compose_file': self.compose_file
        }
        
        # Obter informações adicionais do container
        if self.is_installed():
            try:
                result = subprocess.run(
                    ['docker', 'inspect', self.container_name],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    info = json.loads(result.stdout)
                    if info:
                        status['state'] = info[0].get('State', {})
                        status['network'] = info[0].get('NetworkSettings', {})
            except Exception:
                pass
        
        return status
    
    def setup(
        self,
        api_port: int = 9000,
        console_port: int = 9001,
        root_user: str = "minioadmin",
        root_password: str = "minioadmin123",
        data_dir: str = None,
        certs_dir: str = None
    ) -> bool:
        """
        Configura e instala o MinIO
        
        Args:
            api_port: Porta da API S3
            console_port: Porta do console web
            root_user: Usuário root
            root_password: Senha root
            data_dir: Diretório de dados
            certs_dir: Diretório de certificados
        """
        console.print(Panel("[bold blue]Configurando MinIO S3 Server...[/bold blue]"))
        
        # Verificar Docker
        if not self.is_docker_installed():
            console.print("[red]✗ Docker não está instalado[/red]")
            return False
        
        if not self.is_docker_compose_installed():
            console.print("[red]✗ Docker Compose não está instalado[/red]")
            return False
        
        # Definir diretórios
        if data_dir is None:
            data_dir = self.data_dir
        if certs_dir is None:
            certs_dir = self.certs_dir
        
        self.api_port = api_port
        self.console_port = console_port
        self.data_dir = data_dir
        self.certs_dir = certs_dir
        
        # Criar diretórios
        try:
            os.makedirs(data_dir, exist_ok=True)
            os.makedirs(certs_dir, exist_ok=True)
            os.makedirs(self.config_path, exist_ok=True)
            console.print(f"[green]✓ Diretórios criados[/green]")
        except Exception as e:
            console.print(f"[red]✗ Erro ao criar diretórios: {e}[/red]")
            return False
        
        # Criar arquivo de ambiente
        env_content = f"""# MinIO Environment Variables
# Change these values for production!
MINIO_ROOT_USER={root_user}
MINIO_ROOT_PASSWORD={root_password}
MINIO_CERTS_DIR=/root/.minio/certs
"""
        
        try:
            with open(self.env_file, 'w') as f:
                f.write(env_content)
            console.print(f"[green]✓ Arquivo de ambiente criado: {self.env_file}[/green]")
        except Exception as e:
            console.print(f"[red]✗ Erro: {e}[/red]")
            return False
        
        # Criar Docker Compose file
        compose_content = f"""# MinIO Docker Compose - Generated by File Server Manager
# Generated at: {__import__('datetime').datetime.now().isoformat()}

version: '3.8'

services:
  minio:
    image: minio/minio:latest
    container_name: {self.container_name}
    ports:
      - "{api_port}:9000"
      - "{console_port}:9001"
    volumes:
      - {data_dir}:/data
      - {certs_dir}:/root/.minio/certs
    environment:
      MINIO_ROOT_USER: ${{MINIO_ROOT_USER}}
      MINIO_ROOT_PASSWORD: ${{MINIO_ROOT_PASSWORD}}
      MINIO_CERTS_DIR: ${{MINIO_CERTS_DIR}}
    command: server /data --console-address ":9001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3
    restart: unless-stopped
    networks:
      - minio_network

networks:
  minio_network:
    driver: bridge
"""
        
        try:
            with open(self.compose_file, 'w') as f:
                f.write(compose_content)
            console.print(f"[green]✓ Docker Compose criado: {self.compose_file}[/green]")
        except Exception as e:
            console.print(f"[red]✗ Erro: {e}[/red]")
            return False
        
        console.print("[green]✓ MinIO configurado com sucesso![/green]")
        console.print(f"  API: http://localhost:{api_port}")
        console.print(f"  Console: http://localhost:{console_port}")
        console.print(f"  Usuário: {root_user}")
        
        return True
    
    def create_bucket(self, bucket_name: str, access_key: str = None, secret_key: str = None) -> bool:
        """
        Cria um bucket S3
        
        Args:
            bucket_name: Nome do bucket
            access_key: Access key (opcional, usa root se não especificado)
            secret_key: Secret key (opcional, usa root se não especificado)
        """
        console.print(f"[cyan]▶ Criando bucket: {bucket_name}...[/cyan]")
        
        # Usar mc (MinIO Client) se disponível, senão usar API
        try:
            # Tentar com curl
            import urllib.request
            import json
            
            # Obter credenciais do arquivo de ambiente
            if access_key is None or secret_key is None:
                if os.path.exists(self.env_file):
                    with open(self.env_file, 'r') as f:
                        for line in f:
                            if line.startswith('MINIO_ROOT_USER='):
                                access_key = line.split('=')[1].strip()
                            elif line.startswith('MINIO_ROOT_PASSWORD='):
                                secret_key = line.split('=')[1].strip()
            
            if access_key and secret_key:
                # Usar API para criar bucket
                url = f"http://localhost:{self.api_port}/{bucket_name}"
                req = urllib.request.Request(url, method='PUT')
                req.add_header('Authorization', f'AWS {access_key}:{secret_key}')
                
                try:
                    urllib.request.urlopen(req, timeout=5)
                    console.print(f"[green]✓ Bucket {bucket_name} criado[/green]")
                    return True
                except Exception:
                    pass
            
            # Fallback: usar docker exec
            result = subprocess.run(
                ['docker', 'exec', self.container_name, 'mc', 'mb', f'/data/{bucket_name}'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                console.print(f"[green]✓ Bucket {bucket_name} criado[/green]")
                return True
            else:
                console.print(f"[yellow]⚠ Bucket pode já existir ou erro: {result.stderr}[/yellow]")
                return False
                
        except Exception as e:
            console.print(f"[red]✗ Erro: {e}[/red]")
            return False
    
    def delete_bucket(self, bucket_name: str, force: bool = False) -> bool:
        """Remove um bucket S3"""
        console.print(f"[cyan]▶ Removendo bucket: {bucket_name}...[/cyan]")
        
        try:
            if force:
                result = subprocess.run(
                    ['docker', 'exec', self.container_name, 'mc', 'rm', '-r', '-f', f'/data/{bucket_name}'],
                    capture_output=True,
                    text=True
                )
            else:
                result = subprocess.run(
                    ['docker', 'exec', self.container_name, 'mc', 'rm', f'/data/{bucket_name}'],
                    capture_output=True,
                    text=True
                )
            
            if result.returncode == 0:
                console.print(f"[green]✓ Bucket {bucket_name} removido[/green]")
                return True
            else:
                console.print(f"[red]✗ Erro: {result.stderr}[/red]")
                return False
        except Exception as e:
            console.print(f"[red]✗ Erro: {e}[/red]")
            return False
    
    def list_buckets(self) -> List[str]:
        """Lista todos os buckets"""
        buckets = []
        
        try:
            result = subprocess.run(
                ['docker', 'exec', self.container_name, 'mc', 'ls', '/data'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        # Extrair nome do bucket
                        parts = line.split()
                        if parts:
                            buckets.append(parts[-1].strip('/'))
        except Exception:
            pass
        
        return buckets
    
    def create_user(self, username: str, password: str, policy: str = "readwrite") -> bool:
        """
        Cria um usuário MinIO
        
        Args:
            username: Nome do usuário (access key)
            password: Senha (secret key)
            policy: Política (readwrite, readonly, readwriteadmin)
        """
        console.print(f"[cyan]▶ Criando usuário: {username}...[/cyan]")
        
        try:
            result = subprocess.run(
                ['docker', 'exec', self.container_name, 'mc', 'admin', 'user', 'add', 
                 'local', username, password],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                # Associar política
                subprocess.run(
                    ['docker', 'exec', self.container_name, 'mc', 'admin', 'policy', 'attach',
                     'local', policy, '--user', username],
                    capture_output=True
                )
                console.print(f"[green]✓ Usuário {username} criado com política {policy}[/green]")
                return True
            else:
                console.print(f"[red]✗ Erro: {result.stderr}[/red]")
                return False
        except Exception as e:
            console.print(f"[red]✗ Erro: {e}[/red]")
            return False
    
    def delete_user(self, username: str) -> bool:
        """Remove um usuário MinIO"""
        console.print(f"[cyan]▶ Removendo usuário: {username}...[/cyan]")
        
        try:
            result = subprocess.run(
                ['docker', 'exec', self.container_name, 'mc', 'admin', 'user', 'remove',
                 'local', username],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                console.print(f"[green]✓ Usuário {username} removido[/green]")
                return True
            else:
                console.print(f"[red]✗ Erro: {result.stderr}[/red]")
                return False
        except Exception as e:
            console.print(f"[red]✗ Erro: {e}[/red]")
            return False
    
    def list_users(self) -> List[Dict]:
        """Lista todos os usuários"""
        users = []
        
        try:
            result = subprocess.run(
                ['docker', 'exec', self.container_name, 'mc', 'admin', 'user', 'list', 'local'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line.strip() and 'user' in line.lower():
                        parts = line.split()
                        if len(parts) >= 2:
                            users.append({
                                'username': parts[0],
                                'status': parts[1] if len(parts) > 1 else 'unknown'
                            })
        except Exception:
            pass
        
        return users
    
    def get_console_url(self) -> str:
        """Retorna URL do console web"""
        return f"http://localhost:{self.console_port}"
    
    def get_api_url(self) -> str:
        """Retorna URL da API S3"""
        return f"http://localhost:{self.api_port}"