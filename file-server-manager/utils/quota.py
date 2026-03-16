"""
Quota Manager - Gerenciamento de quotas de disco
"""

import subprocess
import os
import re
from typing import Dict, List, Optional, Tuple
from rich.console import Console

console = Console()


class QuotaManager:
    """Classe para gerenciamento de quotas de disco"""
    
    def __init__(self):
        self.quota_enabled = self._check_quota_support()
        
    def _check_quota_support(self) -> bool:
        """Verifica se quota está disponível no sistema"""
        try:
            result = subprocess.run(
                ['which', 'quota'],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def is_quota_installed(self) -> bool:
        """Verifica se pacote quota está instalado"""
        try:
            result = subprocess.run(
                ['dpkg', '-l', 'quota'],
                capture_output=True,
                text=True
            )
            return result.returncode == 0 and 'ii' in result.stdout
        except Exception:
            return False
    
    def enable_quota(self, partition: str = '/') -> bool:
        """
        Habilita quota em uma partição
        
        Args:
            partition: Partição para habilitar quota (ex: '/', '/home')
        """
        console.print(f"[cyan]▶ Habilitando quota em {partition}...[/cyan]")
        
        if not self.is_quota_installed():
            console.print("[red]✗ Pacote quota não instalado. Execute: apt install quota[/red]")
            return False
        
        # Obter dispositivo da partição
        try:
            result = subprocess.run(
                ['findmnt', '-n', '-o', 'SOURCE', partition],
                capture_output=True,
                text=True
            )
            device = result.stdout.strip()
            
            if not device:
                console.print(f"[red]✗ Não foi possível encontrar dispositivo para {partition}[/red]")
                return False
        except Exception as e:
            console.print(f"[red]✗ Erro: {e}[/red]")
            return False
        
        # Verificar se quota já está habilitada no fstab
        try:
            with open('/etc/fstab', 'r') as f:
                fstab_content = f.read()
            
            # Procurar entrada da partição
            for line in fstab_content.split('\n'):
                if device in line and not line.startswith('#'):
                    if 'usrquota' in line and 'grpquota' in line:
                        console.print("[green]✓ Quota já está habilitada no fstab[/green]")
                        return True
                    break
        except Exception as e:
            console.print(f"[yellow]⚠ Aviso: {e}[/yellow]")
        
        console.print("[yellow]⚠ Quota requer configuração manual do fstab e reboot[/yellow]")
        console.print("Adicione 'usrquota,grpquota' às opções da partição em /etc/fstab")
        
        return False
    
    def set_user_quota(
        self,
        username: str,
        soft_limit_mb: int,
        hard_limit_mb: int,
        partition: str = '/'
    ) -> bool:
        """
        Define quota para um usuário
        
        Args:
            username: Nome do usuário
            soft_limit_mb: Limite brando em MB (aviso)
            hard_limit_mb: Limite rígido em MB (bloqueio)
            partition: Partição
        """
        console.print(f"[cyan]▶ Definindo quota para {username}: {soft_limit_mb}MB (soft), {hard_limit_mb}MB (hard)[/cyan]")
        
        if not self.quota_enabled:
            console.print("[yellow]⚠ Quota pode não estar habilitada[/yellow]")
        
        # Converter para KB (unidade usada pelo setquota)
        soft_limit_kb = soft_limit_mb * 1024
        hard_limit_kb = hard_limit_mb * 1024
        
        try:
            result = subprocess.run(
                ['setquota', '-u', username, str(soft_limit_kb), str(hard_limit_kb), '0', '0', partition],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                console.print(f"[green]✓ Quota definida para {username}[/green]")
                return True
            else:
                console.print(f"[red]✗ Erro: {result.stderr}[/red]")
                return False
        except Exception as e:
            console.print(f"[red]✗ Erro: {e}[/red]")
            return False
    
    def get_user_quota(self, username: str, partition: str = '/') -> Optional[Dict]:
        """Obtém quota atual de um usuário"""
        try:
            result = subprocess.run(
                ['quota', '-u', username, '-w'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return self._parse_quota_output(result.stdout, username)
            return None
        except Exception:
            return None
    
    def _parse_quota_output(self, output: str, username: str) -> Dict:
        """Analisa saída do comando quota"""
        quota_info = {
            'username': username,
            'filesystems': []
        }
        
        for line in output.split('\n'):
            if line.strip() and not line.startswith('#'):
                parts = line.split()
                if len(parts) >= 5:
                    try:
                        quota_info['filesystems'].append({
                            'filesystem': parts[0],
                            'blocks_used': int(parts[1]),
                            'quota_soft': int(parts[2]),
                            'quota_hard': int(parts[3]),
                            'files_used': int(parts[4]) if len(parts) > 4 else 0
                        })
                    except ValueError:
                        pass
        
        return quota_info
    
    def list_user_quotas(self, partition: str = '/') -> List[Dict]:
        """Lista quotas de todos os usuários"""
        quotas = []
        
        try:
            result = subprocess.run(
                ['repquota', '-as'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.startswith('#') or not line.strip():
                        continue
                    
                    parts = line.split()
                    if len(parts) >= 5:
                        username = parts[0]
                        if username not in ['root', 'Block', '***']:
                            try:
                                quotas.append({
                                    'username': username,
                                    'blocks_used': int(parts[1]),
                                    'quota_soft': int(parts[2]),
                                    'quota_hard': int(parts[3]),
                                    'files_used': int(parts[4]) if len(parts) > 4 else 0
                                })
                            except ValueError:
                                pass
        except Exception:
            pass
        
        return quotas
    
    def remove_user_quota(self, username: str, partition: str = '/') -> bool:
        """Remove quota de um usuário (define como 0)"""
        console.print(f"[cyan]▶ Removendo quota de {username}...[/cyan]")
        
        return self.set_user_quota(username, 0, 0, partition)
    
    def set_group_quota(
        self,
        groupname: str,
        soft_limit_mb: int,
        hard_limit_mb: int,
        partition: str = '/'
    ) -> bool:
        """Define quota para um grupo"""
        console.print(f"[cyan]▶ Definindo quota para grupo {groupname}...[/cyan]")
        
        soft_limit_kb = soft_limit_mb * 1024
        hard_limit_kb = hard_limit_mb * 1024
        
        try:
            result = subprocess.run(
                ['setquota', '-g', groupname, str(soft_limit_kb), str(hard_limit_kb), '0', '0', partition],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                console.print(f"[green]✓ Quota definida para grupo {groupname}[/green]")
                return True
            else:
                console.print(f"[red]✗ Erro: {result.stderr}[/red]")
                return False
        except Exception as e:
            console.print(f"[red]✗ Erro: {e}[/red]")
            return False
    
    def get_disk_usage(self, path: str = '/') -> Dict:
        """Obtém uso de disco de um caminho"""
        try:
            result = subprocess.run(
                ['du', '-sh', path],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                output = result.stdout.strip()
                parts = output.split()
                return {
                    'path': path,
                    'usage': parts[0] if parts else 'unknown',
                    'usage_bytes': self._parse_size_to_bytes(parts[0]) if len(parts) > 0 else 0
                }
        except Exception:
            pass
        
        return {'path': path, 'usage': 'unknown', 'usage_bytes': 0}
    
    def _parse_size_to_bytes(self, size_str: str) -> int:
        """Converte string de tamanho (ex: '1.5G') para bytes"""
        units = {'K': 1024, 'M': 1024**2, 'G': 1024**3, 'T': 1024**4}
        
        try:
            match = re.match(r'([\d.]+)([KMGT]?)', size_str)
            if match:
                value = float(match.group(1))
                unit = match.group(2)
                return int(value * units.get(unit, 1))
        except Exception:
            pass
        
        return 0
    
    def get_filesystem_info(self, partition: str = '/') -> Dict:
        """Obtém informações do filesystem"""
        try:
            result = subprocess.run(
                ['df', '-h', partition],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) >= 2:
                    parts = lines[1].split()
                    return {
                        'filesystem': parts[0],
                        'size': parts[1],
                        'used': parts[2],
                        'available': parts[3],
                        'use_percent': parts[4],
                        'mountpoint': parts[5] if len(parts) > 5 else partition
                    }
        except Exception:
            pass
        
        return {}
    
    def display_quota_report(self, partition: str = '/'):
        """Exibe relatório de quotas"""
        console.print(f"\n[bold]Relatório de Quotas - Partição: {partition}[/bold]\n")
        
        # Informações do filesystem
        fs_info = self.get_filesystem_info(partition)
        if fs_info:
            console.print(f"Filesystem: {fs_info.get('filesystem', 'N/A')}")
            console.print(f"Tamanho: {fs_info.get('size', 'N/A')} | Usado: {fs_info.get('used', 'N/A')} | Disponível: {fs_info.get('available', 'N/A')}")
            console.print()
        
        # Quotas de usuários
        quotas = self.list_user_quotas(partition)
        
        if quotas:
            from rich.table import Table
            table = Table(title="Quotas de Usuários")
            
            table.add_column("Usuário", style="cyan")
            table.add_column("Usado (KB)", style="yellow")
            table.add_column("Soft (MB)", style="magenta")
            table.add_column("Hard (MB)", style="red")
            table.add_column("Arquivos", style="green")
            
            for q in quotas:
                table.add_row(
                    q['username'],
                    str(q['blocks_used']),
                    str(q['quota_soft'] // 1024) if q['quota_soft'] > 0 else 'Ilimitado',
                    str(q['quota_hard'] // 1024) if q['quota_hard'] > 0 else 'Ilimitado',
                    str(q['files_used'])
                )
            
            console.print(table)
        else:
            console.print("[yellow]⚠ Nenhuma quota configurada ou quota não habilitada[/yellow]")