"""
Módulo de Instalação - Gerencia a instalação de pacotes em diferentes distribuições Linux
"""

import subprocess
import shutil
import os
from typing import List, Dict, Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel

console = Console()


class Installer:
    """Classe responsável pela instalação de pacotes e serviços"""
    
    # Pacotes necessários para cada protocolo
    PACKAGES = {
        'ftp': {
            'debian': ['vsftpd', 'openssl'],
            'redhat': ['vsftpd', 'openssl'],
        },
        'sftp': {
            'debian': ['openssh-server', 'openssh-sftp-server'],
            'redhat': ['openssh-server', 'openssh-sftp-server'],
        },
        'nfs': {
            'debian': ['nfs-kernel-server', 'nfs-common'],
            'redhat': ['nfs-utils', 'nfs4-acl-tools'],
        },
        'smb': {
            'debian': ['samba', 'samba-vfs-modules'],
            'redhat': ['samba', 'samba-client', 'samba-common-tools'],
        },
        'webdav': {
            'debian': ['apache2', 'libapache2-mod-dav', 'libapache2-mod-dav-fs'],
            'redhat': ['httpd', 'mod_dav', 'mod_dav_fs'],
        },
        's3': {
            'debian': ['docker.io', 'docker-compose'],
            'redhat': ['docker', 'docker-compose'],
        },
        'security': {
            'debian': ['fail2ban', 'ufw', 'certbot'],
            'redhat': ['fail2ban', 'firewalld', 'certbot'],
        },
        'quota': {
            'debian': ['quota', 'quotatool'],
            'redhat': ['quota', 'xfs_quota'],
        },
        'utils': {
            'debian': ['htop', 'net-tools', 'curl', 'wget', 'vim'],
            'redhat': ['htop', 'net-tools', 'curl', 'wget', 'vim'],
        }
    }
    
    # Serviços correspondentes
    SERVICES = {
        'ftp': 'vsftpd',
        'sftp': 'sshd',
        'nfs': 'nfs-server',
        'smb': ['smbd', 'nmbd'],
        'webdav': 'apache2',
        's3': 'docker',
    }
    
    def __init__(self):
        self.distro_type = self._detect_distro()
        self.installed_packages = []
        self.config_path = '/etc/file-server-manager'
        
    def _detect_distro(self) -> str:
        """Detecta o tipo de distribuição Linux"""
        if os.path.exists('/etc/debian-version'):
            return 'debian'
        elif os.path.exists('/etc/redhat-release') or os.path.exists('/etc/centos-release'):
            return 'redhat'
        elif os.path.exists('/etc/os-release'):
            with open('/etc/os-release', 'r') as f:
                content = f.read().lower()
                if 'ubuntu' in content or 'debian' in content:
                    return 'debian'
                elif 'redhat' in content or 'centos' in content or 'rhel' in content:
                    return 'redhat'
        return 'debian'  # Default para Debian/Ubuntu
    
    def _run_command(self, command: List[str], description: str = "") -> bool:
        """Executa um comando e retorna o resultado"""
        try:
            if description:
                console.print(f"[cyan]▶ {description}...[/cyan]")
            
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                console.print(f"[red]✗ Erro:[/red] {result.stderr}")
                return False
            
            return True
        except subprocess.TimeoutExpired:
            console.print("[red]✗ Timeout na execução do comando[/red]")
            return False
        except Exception as e:
            console.print(f"[red]✗ Erro: {str(e)}[/red]")
            return False
    
    def update_packages(self) -> bool:
        """Atualiza a lista de pacotes do sistema"""
        console.print(Panel("[bold blue]Atualizando lista de pacotes...[/bold blue]"))
        
        if self.distro_type == 'debian':
            return self._run_command(['apt-get', 'update'], "Atualizando repositórios")
        else:
            return self._run_command(['yum', 'makecache'], "Atualizando cache")
    
    def install_packages(self, protocols: List[str], update_first: bool = True) -> bool:
        """
        Instala pacotes para os protocolos especificados
        
        Args:
            protocols: Lista de protocolos para instalar ('all' para todos)
            update_first: Se True, atualiza a lista de pacotes antes
        """
        if 'all' in protocols:
            protocols = list(self.PACKAGES.keys())
        
        # Coletar todos os pacotes necessários
        all_packages = set()
        for protocol in protocols:
            if protocol in self.PACKAGES:
                all_packages.update(self.PACKAGES[protocol].get(self.distro_type, []))
        
        if not all_packages:
            console.print("[yellow]⚠ Nenhum pacote para instalar[/yellow]")
            return True
        
        console.print(Panel(f"[bold green]Instalando pacotes para: {', '.join(protocols)}[/bold green]"))
        console.print(f"[cyan]Pacotes:[/cyan] {', '.join(all_packages)}")
        
        # Atualizar pacotes se solicitado
        if update_first:
            if not self.update_packages():
                console.print("[yellow]⚠ Falha na atualização, continuando...[/yellow]")
        
        # Instalar pacotes
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Instalando pacotes...", total=None)
            
            if self.distro_type == 'debian':
                cmd = ['apt-get', 'install', '-y'] + list(all_packages)
            else:
                cmd = ['yum', 'install', '-y'] + list(all_packages)
            
            success = self._run_command(cmd, "Instalação em andamento")
            
            if success:
                self.installed_packages.extend(all_packages)
                console.print("[green]✓ Pacotes instalados com sucesso![/green]")
            else:
                console.print("[red]✗ Falha na instalação de pacotes[/red]")
            
            return success
    
    def enable_service(self, service_name: str) -> bool:
        """Habilita e inicia um serviço"""
        console.print(f"[cyan]▶ Habilitando serviço: {service_name}[/cyan]")
        
        # Tentar systemctl primeiro, depois service
        commands = [
            ['systemctl', 'enable', service_name],
            ['systemctl', 'start', service_name],
        ]
        
        for cmd in commands:
            try:
                subprocess.run(cmd, capture_output=True, timeout=30)
            except Exception as e:
                console.print(f"[yellow]⚠ Aviso: {str(e)}[/yellow]")
        
        return True
    
    def setup_services(self, protocols: List[str]) -> bool:
        """Configura e inicia serviços para os protocolos"""
        console.print(Panel("[bold blue]Configurando serviços...[/bold blue]"))
        
        for protocol in protocols:
            if protocol in self.SERVICES:
                service = self.SERVICES[protocol]
                if isinstance(service, list):
                    for svc in service:
                        self.enable_service(svc)
                else:
                    self.enable_service(service)
        
        console.print("[green]✓ Serviços configurados![/green]")
        return True
    
    def create_directories(self, base_path: str, protocols: List[str]) -> bool:
        """Cria diretórios necessários para os protocolos"""
        console.print(Panel(f"[bold blue]Criando estrutura de diretórios em {base_path}...[/bold blue]"))
        
        directories = {
            'base': base_path,
            'ftp': f'{base_path}/ftp',
            'sftp': f'{base_path}/sftp',
            'nfs': f'{base_path}/nfs',
            'smb': f'{base_path}/smb',
            'webdav': f'{base_path}/webdav',
            'users': f'{base_path}/users',
            'logs': f'{base_path}/logs',
            'backup': f'{base_path}/backup',
        }
        
        for proto in protocols:
            if proto in directories:
                try:
                    os.makedirs(directories[proto], exist_ok=True)
                    console.print(f"[green]✓ Criado: {directories[proto]}[/green]")
                except Exception as e:
                    console.print(f"[red]✗ Erro ao criar {directories[proto]}: {e}[/red]")
                    return False
        
        # Criar diretório de configuração
        try:
            os.makedirs(self.config_path, exist_ok=True)
        except Exception as e:
            console.print(f"[yellow]⚠ Aviso: Não foi possível criar {self.config_path}: {e}[/yellow]")
        
        return True
    
    def is_package_installed(self, package: str) -> bool:
        """Verifica se um pacote está instalado"""
        try:
            if self.distro_type == 'debian':
                result = subprocess.run(
                    ['dpkg', '-l', package],
                    capture_output=True,
                    text=True
                )
                return result.returncode == 0 and 'ii' in result.stdout
            else:
                result = subprocess.run(
                    ['rpm', '-q', package],
                    capture_output=True,
                    text=True
                )
                return result.returncode == 0
        except Exception:
            return False
    
    def check_prerequisites(self) -> Dict[str, bool]:
        """Verifica pré-requisitos do sistema"""
        console.print(Panel("[bold]Verificando pré-requisitos...[/bold]"))
        
        checks = {
            'root': os.geteuid() == 0,
            'python3': shutil.which('python3') is not None,
            'systemctl': shutil.which('systemctl') is not None,
        }
        
        for check, result in checks.items():
            status = "[green]✓[/green]" if result else "[red]✗[/red]"
            console.print(f"{status} {check}")
        
        return checks
    
    def uninstall_protocol(self, protocol: str) -> bool:
        """Remove pacotes de um protocolo específico"""
        if protocol not in self.PACKAGES:
            console.print(f"[red]Protocolo {protocol} não encontrado[/red]")
            return False
        
        packages = self.PACKAGES[protocol].get(self.distro_type, [])
        
        console.print(Panel(f"[bold red]Removendo {protocol}...[/bold red]"))
        
        if self.distro_type == 'debian':
            cmd = ['apt-get', 'remove', '--purge', '-y'] + packages
        else:
            cmd = ['yum', 'remove', '-y'] + packages
        
        return self._run_command(cmd, f"Removendo {protocol}")