"""
Servidor NFS - Gerencia configuração e operação do servidor NFS
"""

import subprocess
import os
from typing import Dict, List, Optional
from rich.console import Console

console = Console()


class NFSServer:
    """Classe para gerenciamento do servidor NFS"""
    
    def __init__(self, config_path: str = '/etc/file-server-manager'):
        self.config_path = config_path
        self.exports_file = '/etc/exports'
        self.service_name = 'nfs-kernel-server'
        self.exports = []
        
    def is_installed(self) -> bool:
        """Verifica se o servidor NFS está instalado"""
        try:
            result = subprocess.run(
                ['dpkg', '-l', 'nfs-kernel-server'],
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
            # Tentar nome alternativo do serviço
            try:
                result = subprocess.run(
                    ['systemctl', 'is-active', 'nfs-server'],
                    capture_output=True,
                    text=True
                )
                return result.stdout.strip() == 'active'
            except Exception:
                return False
    
    def start(self) -> bool:
        """Inicia o serviço NFS"""
        console.print("[cyan]▶ Iniciando serviço NFS...[/cyan]")
        try:
            subprocess.run(['systemctl', 'start', self.service_name], capture_output=True, timeout=30)
            console.print("[green]✓ Serviço NFS iniciado[/green]")
            return True
        except Exception as e:
            console.print(f"[red]✗ Erro ao iniciar NFS: {e}[/red]")
            return False
    
    def stop(self) -> bool:
        """Para o serviço NFS"""
        console.print("[cyan]▶ Parando serviço NFS...[/cyan]")
        try:
            subprocess.run(['systemctl', 'stop', self.service_name], capture_output=True, timeout=30)
            console.print("[green]✓ Serviço NFS parado[/green]")
            return True
        except Exception as e:
            console.print(f"[red]✗ Erro ao parar NFS: {e}[/red]")
            return False
    
    def restart(self) -> bool:
        """Reinicia o serviço NFS"""
        console.print("[cyan]▶ Reiniciando serviço NFS...[/cyan]")
        try:
            subprocess.run(['systemctl', 'restart', self.service_name], capture_output=True, timeout=30)
            console.print("[green]✓ Serviço NFS reiniciado[/green]")
            return True
        except Exception as e:
            console.print(f"[red]✗ Erro ao reiniciar NFS: {e}[/red]")
            return False
    
    def enable(self) -> bool:
        """Habilita serviço para iniciar automaticamente"""
        try:
            subprocess.run(['systemctl', 'enable', self.service_name], capture_output=True, timeout=30)
            console.print("[green]✓ Serviço NFS habilitado para auto-start[/green]")
            return True
        except Exception as e:
            console.print(f"[red]✗ Erro: {e}[/red]")
            return False
    
    def get_status(self) -> Dict:
        """Obtém status do serviço NFS"""
        return {
            'installed': self.is_installed(),
            'running': self.is_running(),
            'service': self.service_name,
            'exports_file': self.exports_file,
            'exports': self.exports
        }
    
    def add_export(
        self,
        path: str,
        network: str = '*',
        options: List[str] = None,
        create_path: bool = True
    ) -> bool:
        """
        Adiciona uma exportação NFS
        
        Args:
            path: Caminho do diretório a exportar
            network: Rede ou IP permitido (ex: '192.168.1.0/24' ou '*')
            options: Lista de opções (ex: ['rw', 'sync', 'no_subtree_check'])
            create_path: Se True, cria o diretório se não existir
        """
        if options is None:
            options = ['rw', 'sync', 'no_subtree_check', 'no_root_squash']
        
        console.print(f"[cyan]▶ Adicionando exportação NFS: {path} para {network}...[/cyan]")
        
        # Criar diretório se necessário
        if create_path and not os.path.exists(path):
            try:
                os.makedirs(path, exist_ok=True)
                console.print(f"[green]✓ Diretório criado: {path}[/green]")
            except Exception as e:
                console.print(f"[red]✗ Erro ao criar diretório: {e}[/red]")
                return False
        
        # Adicionar ao arquivo exports
        export_line = f"{path} {network}({','.join(options)})"
        
        try:
            # Verificar se já existe
            if os.path.exists(self.exports_file):
                with open(self.exports_file, 'r') as f:
                    content = f.read()
                if export_line in content:
                    console.print("[yellow]⚠ Exportação já existe[/yellow]")
                    return True
            
            # Adicionar exportação
            with open(self.exports_file, 'a') as f:
                f.write(export_line + '\n')
            
            self.exports.append({'path': path, 'network': network, 'options': options})
            console.print(f"[green]✓ Exportação adicionada: {export_line}[/green]")
            
            # Exportar imediatamente
            self.exportfs()
            
            return True
        except Exception as e:
            console.print(f"[red]✗ Erro: {e}[/red]")
            return False
    
    def remove_export(self, path: str) -> bool:
        """Remove uma exportação NFS"""
        console.print(f"[cyan]▶ Removendo exportação NFS: {path}...[/cyan]")
        
        try:
            if not os.path.exists(self.exports_file):
                return False
            
            with open(self.exports_file, 'r') as f:
                lines = f.readlines()
            
            with open(self.exports_file, 'w') as f:
                for line in lines:
                    if not line.strip().startswith(path + ' '):
                        f.write(line)
            
            # Remover da lista em memória
            self.exports = [e for e in self.exports if e['path'] != path]
            
            # Exportar novamente
            self.exportfs()
            
            console.print(f"[green]✓ Exportação removida: {path}[/green]")
            return True
        except Exception as e:
            console.print(f"[red]✗ Erro: {e}[/red]")
            return False
    
    def exportfs(self) -> bool:
        """Aplica exportações NFS (equivalente a exportfs -ra)"""
        console.print("[cyan]▶ Atualizando exportações NFS...[/cyan]")
        
        try:
            # Criar diretórios necessários
            os.makedirs('/var/lib/nfs', exist_ok=True)
            os.makedirs('/var/lib/nfs/rpc_pipefs', exist_ok=True)
            
            # Exportar todas
            result = subprocess.run(
                ['exportfs', '-ra'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                console.print("[green]✓ Exportações NFS atualizadas[/green]")
                return True
            else:
                console.print(f"[red]✗ Erro: {result.stderr}[/red]")
                return False
        except Exception as e:
            console.print(f"[red]✗ Erro: {e}[/red]")
            return False
    
    def list_exports(self) -> List[Dict]:
        """Lista todas as exportações ativas"""
        try:
            result = subprocess.run(
                ['exportfs', '-v'],
                capture_output=True,
                text=True
            )
            
            exports = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 2:
                        exports.append({
                            'path': parts[0],
                            'clients': parts[1] if len(parts) > 1 else '*',
                            'options': ' '.join(parts[2:]) if len(parts) > 2 else ''
                        })
            
            self.exports = exports
            return exports
        except Exception:
            return []
    
    def show_mounts(self) -> str:
        """Mostra mounts NFS atuais"""
        try:
            result = subprocess.run(
                ['showmount', '-e', 'localhost'],
                capture_output=True,
                text=True
            )
            return result.stdout
        except Exception as e:
            return f"Erro: {e}"
    
    def configure(
        self,
        nfs_version: str = "4",
        tcp_only: bool = True
    ) -> bool:
        """Configura servidor NFS"""
        console.print(f"[cyan]▶ Configurando NFS versão {nfs_version}...[/cyan]")
        
        # Configurar /etc/nfs.conf.d/
        try:
            os.makedirs('/etc/nfs.conf.d', exist_ok=True)
            config_content = f"""# NFS Configuration
[nfsd]
vers{nfs_version}=y
"""
            with open('/etc/nfs.conf.d/local.conf', 'w') as f:
                f.write(config_content)
            console.print("[green]✓ Configuração NFS salva[/green]")
        except Exception as e:
            console.print(f"[yellow]⚠ Aviso: {e}[/yellow]")
        
        return True