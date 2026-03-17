"""
Módulo de Segurança - Gerencia SSL/TLS, fail2ban, restrições de IP e logs de auditoria
"""

import subprocess
import os
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


class SecurityManager:
    """Classe para gerenciamento de segurança do servidor de arquivos"""
    
    def __init__(self, config_path: str = '/etc/file-server-manager'):
        self.config_path = config_path
        self.ssl_dir = os.path.join(config_path, 'ssl')
        self.fail2ban_dir = '/etc/fail2ban'
        self.audit_log_file = os.path.join(config_path, 'audit.log')
        self.config_file = os.path.join(config_path, 'security_config.json')
        self.config = self._load_config()
        
    def _load_config(self) -> Dict:
        """Carrega configuração de segurança"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return self._default_config()
    
    def _default_config(self) -> Dict:
        """Retorna configuração padrão"""
        return {
            'ssl': {
                'enabled': True,
                'cert_file': '',
                'key_file': '',
                'validity_days': 365,
                'country': 'BR',
                'state': 'SP',
                'locality': 'Sao Paulo',
                'organization': 'File Server',
                'common_name': 'localhost'
            },
            'fail2ban': {
                'enabled': True,
                'ban_time': 1800,  # 30 minutos
                'find_time': 600,  # 10 minutos
                'max_retry': 5,
                'jails': ['sshd', 'vsftpd', 'proftpd']
            },
            'ip_restrictions': {
                'whitelist': [],
                'blacklist': [],
                'enabled': False
            },
            'audit': {
                'enabled': True,
                'log_file': self.audit_log_file,
                'log_level': 'INFO',
                'events': ['login', 'logout', 'file_access', 'config_change', 'user_change']
            }
        }
    
    def _save_config(self):
        """Salva configuração"""
        try:
            os.makedirs(self.config_path, exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2, default=str)
        except Exception as e:
            console.print(f"[red]✗ Erro ao salvar config: {e}[/red]")
    
    # ==================== SSL/TLS ====================
    
    def generate_ssl_certificate(
        self,
        country: str = "BR",
        state: str = "SP",
        locality: str = "Sao Paulo",
        organization: str = "File Server",
        common_name: str = "localhost",
        validity_days: int = 365,
        key_size: int = 4096,
        output_dir: str = None
    ) -> Dict[str, str]:
        """
        Gera certificado SSL auto-assinado
        
        Returns:
            Dict com caminhos do certificado e chave
        """
        if output_dir is None:
            output_dir = self.ssl_dir
        
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            console.print(f"[red]✗ Erro ao criar diretório SSL: {e}[/red]")
            return {}
        
        cert_file = os.path.join(output_dir, 'server.crt')
        key_file = os.path.join(output_dir, 'server.key')
        csr_file = os.path.join(output_dir, 'server.csr')
        
        # Atualizar config
        self.config['ssl'].update({
            'country': country,
            'state': state,
            'locality': locality,
            'organization': organization,
            'common_name': common_name,
            'validity_days': validity_days,
            'cert_file': cert_file,
            'key_file': key_file
        })
        
        console.print(Panel("[bold blue]Gerando certificado SSL...[/bold blue]"))
        
        # Gerar chave privada
        console.print("[cyan]▶ Gerando chave privada RSA {key_size}-bits...[/cyan]")
        key_cmd = [
            'openssl', 'genrsa',
            '-out', key_file,
            str(key_size)
        ]
        
        try:
            result = subprocess.run(key_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                console.print(f"[red]✗ Erro ao gerar chave: {result.stderr}[/red]")
                return {}
            console.print("[green]✓ Chave privada gerada[/green]")
        except FileNotFoundError:
            console.print("[red]✗ OpenSSL não encontrado. Instale openssl.[/red]")
            return {}
        
        # Gerar CSR (Certificate Signing Request)
        console.print("[cyan]▶ Gerando CSR...[/cyan]")
        csr_cmd = [
            'openssl', 'req', '-new',
            '-key', key_file,
            '-out', csr_file,
            '-subj', f'/C={country}/ST={state}/L={locality}/O={organization}/CN={common_name}'
        ]
        
        result = subprocess.run(csr_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            console.print(f"[red]✗ Erro ao gerar CSR: {result.stderr}[/red]")
            return {}
        console.print("[green]✓ CSR gerado[/green]")
        
        # Gerar certificado auto-assinado
        console.print(f"[cyan]▶ Gerando certificado auto-assinado (válido por {validity_days} dias)...[/cyan]")
        cert_cmd = [
            'openssl', 'x509', '-req',
            '-days', str(validity_days),
            '-in', csr_file,
            '-signkey', key_file,
            '-out', cert_file
        ]
        
        result = subprocess.run(cert_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            console.print(f"[red]✗ Erro ao gerar certificado: {result.stderr}[/red]")
            return {}
        
        # Definir permissões seguras
        os.chmod(key_file, 0o600)
        os.chmod(cert_file, 0o644)
        
        console.print(f"[green]✓ Certificado SSL gerado com sucesso![/green]")
        console.print(f"  Certificado: {cert_file}")
        console.print(f"  Chave: {key_file}")
        
        self._save_config()
        
        return {
            'cert_file': cert_file,
            'key_file': key_file,
            'csr_file': csr_file,
            'validity_days': validity_days,
            'expires': datetime.now() + timedelta(days=validity_days)
        }
    
    def verify_certificate(self, cert_file: str = None) -> Dict:
        """Verifica certificado SSL"""
        if cert_file is None:
            cert_file = self.config['ssl'].get('cert_file')
        
        if not cert_file or not os.path.exists(cert_file):
            return {'valid': False, 'message': 'Certificado não encontrado'}
        
        try:
            result = subprocess.run(
                ['openssl', 'x509', '-in', cert_file, '-text', '-noout'],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return {'valid': False, 'message': 'Certificado inválido'}
            
            # Extrair informações
            info_cmd = ['openssl', 'x509', '-in', cert_file, '-dates', '-noout']
            info_result = subprocess.run(info_cmd, capture_output=True, text=True)
            
            return {
                'valid': True,
                'message': 'Certificado válido',
                'details': info_result.stdout,
                'full_info': result.stdout
            }
        except Exception as e:
            return {'valid': False, 'message': str(e)}
    
    def check_certificate_expiry(self, cert_file: str = None, warning_days: int = 30) -> bool:
        """Verifica se certificado está próximo de expirar"""
        if cert_file is None:
            cert_file = self.config['ssl'].get('cert_file')
        
        if not cert_file or not os.path.exists(cert_file):
            return True  # Precisa gerar novo
        
        try:
            result = subprocess.run(
                ['openssl', 'x509', '-in', cert_file, '-checkend', str(warning_days * 86400), '-noout'],
                capture_output=True,
                text=True
            )
            return result.returncode != 0  # Retorna True se estiver expirando
        except Exception:
            return True
    
    # ==================== Fail2Ban ====================
    
    def setup_fail2ban(
        self,
        ban_time: int = 1800,
        find_time: int = 600,
        max_retry: int = 5,
        enabled_jails: List[str] = None
    ) -> bool:
        """
        Configura fail2ban para proteção contra brute force
        """
        if enabled_jails is None:
            enabled_jails = ['sshd', 'vsftpd']
        
        console.print(Panel("[bold blue]Configurando fail2ban...[/bold blue]"))
        
        # Criar diretórios
        try:
            os.makedirs(self.fail2ban_dir, exist_ok=True)
            os.makedirs(os.path.join(self.fail2ban_dir, 'filter.d'), exist_ok=True)
            os.makedirs(os.path.join(self.fail2ban_dir, 'jail.d'), exist_ok=True)
        except Exception as e:
            console.print(f"[yellow]⚠ Não foi possível criar diretórios: {e}[/yellow]")
        
        # Configuração jail.local
        jail_config = f"""# Fail2Ban jail configuration - Generated by File Server Manager
# Generated at: {datetime.now().isoformat()}

[DEFAULT]
# Ignorar localhost
ignoreip = 127.0.0.1/8 ::1
bantime = {ban_time}
findtime = {find_time}
maxretry = {max_retry}

# Ação padrão
banaction = iptables-multiport
protocol = tcp
chain = INPUT

# Backend
backend = auto

# Log
logtarget = /var/log/fail2ban.log
loglevel = INFO

"""
        
        # Jail para SSH
        if 'sshd' in enabled_jails:
            jail_config += """
[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 5
bantime = 1800
"""
        
        # Jail para vsftpd (FTP)
        if 'vsftpd' in enabled_jails:
            jail_config += """
[vsftpd]
enabled = true
port = ftp,ftps,ftp-data
filter = vsftpd
logpath = /var/log/vsftpd.log
maxretry = 5
bantime = 1800
"""
        
        # Jail para ProFTPD (alternativa)
        if 'proftpd' in enabled_jails:
            jail_config += """
[proftpd]
enabled = true
port = ftp,ftps,ftp-data
filter = proftpd
logpath = /var/log/proftpd/proftpd.log
maxretry = 5
bantime = 1800
"""
        
        # Jail para Samba
        if 'samba' in enabled_jails:
            jail_config += """
[samba]
enabled = true
port = 139,445
filter = samba
logpath = /var/log/samba/log.*
maxretry = 5
bantime = 1800
"""
        
        # Salvar configuração
        jail_file = os.path.join(self.fail2ban_dir, 'jail.local')
        try:
            with open(jail_file, 'w') as f:
                f.write(jail_config)
            console.print(f"[green]✓ Configuração fail2ban gerada: {jail_file}[/green]")
        except Exception as e:
            console.print(f"[red]✗ Erro: {e}[/red]")
            return False
        
        # Salvar no config
        self.config['fail2ban'].update({
            'enabled': True,
            'ban_time': ban_time,
            'find_time': find_time,
            'max_retry': max_retry,
            'jails': enabled_jails
        })
        self._save_config()
        
        # Tentar reiniciar fail2ban
        try:
            subprocess.run(['systemctl', 'restart', 'fail2ban'], capture_output=True, timeout=30)
            subprocess.run(['systemctl', 'enable', 'fail2ban'], capture_output=True, timeout=30)
            console.print("[green]✓ Fail2ban reiniciado e habilitado[/green]")
        except Exception as e:
            console.print(f"[yellow]⚠ Não foi possível reiniciar fail2ban: {e}[/yellow]")
        
        return True
    
    def get_fail2ban_status(self) -> Dict:
        """Obtém status do fail2ban"""
        try:
            result = subprocess.run(
                ['fail2ban-client', 'status'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                jails = result.stdout.split('\n')[1].strip().split(':')[1].strip()
                return {
                    'running': True,
                    'jails': jails.split(', ')
                }
            return {'running': False, 'jails': []}
        except Exception:
            return {'running': False, 'jails': []}
    
    def ban_ip(self, ip: str, jail: str = 'sshd', duration: int = 3600) -> bool:
        """Banir um IP manualmente"""
        try:
            subprocess.run(
                ['fail2ban-client', 'set', jail, 'banip', ip],
                capture_output=True,
                timeout=30
            )
            console.print(f"[green]✓ IP {ip} banido por {duration}s[/green]")
            self._audit_log('ban_ip', {'ip': ip, 'jail': jail, 'duration': duration})
            return True
        except Exception as e:
            console.print(f"[red]✗ Erro ao banir IP: {e}[/red]")
            return False
    
    def unban_ip(self, ip: str, jail: str = None) -> bool:
        """Desbanir um IP"""
        try:
            if jail:
                result = subprocess.run(
                    ['fail2ban-client', 'set', jail, 'unbanip', ip],
                    capture_output=True,
                    timeout=30
                )
            else:
                # Desbanir de todas as jails
                jails = self.get_fail2ban_status().get('jails', [])
                for j in jails:
                    subprocess.run(
                        ['fail2ban-client', 'set', j, 'unbanip', ip],
                        capture_output=True,
                        timeout=30
                    )
                console.print(f"[green]✓ IP {ip} desbanido de todas as jails[/green]")
                return True
            if result.returncode == 0:
                console.print(f"[green]✓ IP {ip} desbanido da jail {jail}[/green]")
                return True
            else:
                console.print(f"[red]✗ Falha ao desbanir IP {ip}[/red]")
                return False
        except Exception as e:
            console.print(f"[red]✗ Erro ao desbanir IP: {e}[/red]")
            return False
    
    def unban_all_ips(self) -> bool:
        """Desbanir todos os IPs de todas as jails"""
        try:
            status = self.get_fail2ban_status()
            if not status.get('running'):
                console.print("[yellow]⚠ Fail2ban não está rodando[/yellow]")
                return False
            
            jails = status.get('jails', [])
            total_unbanned = 0
            
            for jail in jails:
                # Obter IPs banidos desta jail
                result = subprocess.run(
                    ['fail2ban-client', 'get', jail, 'ipbans'],
                    capture_output=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    ips = result.stdout.strip()
                    if ips and ips != '':
                        # Extrair IPs da saída
                        import re
                        ip_list = re.findall(r'\d+\.\d+\.\d+\.\d+', ips)
                        for ip in ip_list:
                            subprocess.run(
                                ['fail2ban-client', 'set', jail, 'unbanip', ip],
                                capture_output=True,
                                timeout=30
                            )
                            total_unbanned += 1
            
            console.print(f"[green]✓ {total_unbanned} IPs desbanidos de {len(jails)} jails[/green]")
            return True
        except Exception as e:
            console.print(f"[red]✗ Erro ao desbanir todos os IPs: {e}[/red]")
            return False
    
    def display_banned_ips(self):
        """Exibe IPs banidos pelo fail2ban"""
        try:
            status = self.get_fail2ban_status()
            
            if not status.get('running'):
                console.print("[yellow]⚠ Fail2ban não está rodando[/yellow]")
                return
            
            jails = status.get('jails', [])
            
            if not jails:
                console.print("[yellow]⚠ Nenhuma jail ativa[/yellow]")
                return
            
            table = Table(title="IPs Bloqueados pelo Fail2Ban")
            table.add_column("Jail", style="cyan")
            table.add_column("IPs Bloqueados", style="red")
            table.add_column("Total", style="yellow")
            
            total_banned = 0
            
            for jail in jails:
                result = subprocess.run(
                    ['fail2ban-client', 'get', jail, 'ipbans'],
                    capture_output=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    ips = result.stdout.strip()
                    # Extrair IPs da saída
                    import re
                    ip_list = re.findall(r'\d+\.\d+\.\d+\.\d+', ips)
                    count = len(ip_list)
                    total_banned += count
                    
                    ips_display = ', '.join(ip_list) if ip_list else 'Nenhum'
                    table.add_row(jail, ips_display, str(count))
            
            console.print(table)
            console.print(f"\n[bold]Total de IPs bloqueados:[/bold] {total_banned}")
            
            if total_banned > 0:
                console.print("\n[dim]Dica: Use a opção 'Desbloquear IP' no menu de Segurança para liberar um IP específico[/dim]")
            
        except Exception as e:
            console.print(f"[red]✗ Erro ao obter IPs banidos: {e}[/red]")
            console.print("[yellow]⚠ Verifique se o fail2ban está instalado e rodando: sudo systemctl status fail2ban[/yellow]")
    
    # ==================== Restrições de IP ====================
    
    def add_ip_whitelist(self, ip: str) -> bool:
        """Adiciona IP à whitelist"""
        if ip not in self.config['ip_restrictions']['whitelist']:
            self.config['ip_restrictions']['whitelist'].append(ip)
            self._save_config()
            console.print(f"[green]✓ IP {ip} adicionado à whitelist[/green]")
        return True
    
    def remove_ip_whitelist(self, ip: str) -> bool:
        """Remove IP da whitelist"""
        if ip in self.config['ip_restrictions']['whitelist']:
            self.config['ip_restrictions']['whitelist'].remove(ip)
            self._save_config()
            console.print(f"[green]✓ IP {ip} removido da whitelist[/green]")
        return True
    
    def add_ip_blacklist(self, ip: str) -> bool:
        """Adiciona IP à blacklist"""
        if ip not in self.config['ip_restrictions']['blacklist']:
            self.config['ip_restrictions']['blacklist'].append(ip)
            self._save_config()
            console.print(f"[green]✓ IP {ip} adicionado à blacklist[/green]")
        return True
    
    def remove_ip_blacklist(self, ip: str) -> bool:
        """Remove IP da blacklist"""
        if ip in self.config['ip_restrictions']['blacklist']:
            self.config['ip_restrictions']['blacklist'].remove(ip)
            self._save_config()
            console.print(f"[green]✓ IP {ip} removido da blacklist[/green]")
        return True
    
    def get_ip_restrictions(self) -> Dict:
        """Retorna restrições de IP"""
        return self.config['ip_restrictions']
    
    # ==================== Logs de Auditoria ====================
    
    def _audit_log(self, event_type: str, details: Dict):
        """Registra evento de auditoria"""
        if not self.config['audit']['enabled']:
            return
        
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'details': details
        }
        
        try:
            os.makedirs(os.path.dirname(self.audit_log_file), exist_ok=True)
            with open(self.audit_log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            console.print(f"[yellow]⚠ Não foi possível registrar log de auditoria: {e}[/yellow]")
    
    def log_event(self, event_type: str, details: Dict):
        """
        Registra evento de auditoria publicamente
        
        Args:
            event_type: Tipo de evento (login, logout, file_access, config_change, user_change)
            details: Detalhes do evento
        """
        self._audit_log(event_type, details)
    
    def get_audit_logs(
        self,
        start_date: str = None,
        end_date: str = None,
        event_type: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Obtém logs de auditoria com filtros
        
        Args:
            start_date: Data inicial (YYYY-MM-DD)
            end_date: Data final (YYYY-MM-DD)
            event_type: Tipo de evento para filtrar
            limit: Limite de registros
        """
        logs = []
        
        if not os.path.exists(self.audit_log_file):
            return logs
        
        try:
            with open(self.audit_log_file, 'r') as f:
                for line in f:
                    try:
                        log = json.loads(line.strip())
                        
                        # Aplicar filtros
                        if event_type and log.get('event_type') != event_type:
                            continue
                        
                        if start_date:
                            log_date = log.get('timestamp', '')[:10]
                            if log_date < start_date:
                                continue
                        
                        if end_date:
                            log_date = log.get('timestamp', '')[:10]
                            if log_date > end_date:
                                continue
                        
                        logs.append(log)
                        
                        if len(logs) >= limit:
                            break
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            console.print(f"[yellow]⚠ Erro ao ler logs: {e}[/yellow]")
        
        return logs
    
    def display_audit_logs(self, limit: int = 50):
        """Exibe logs de auditoria em formato de tabela"""
        logs = self.get_audit_logs(limit=limit)
        
        if not logs:
            console.print("[yellow]⚠ Nenhum log de auditoria encontrado[/yellow]")
            return
        
        table = Table(title=f"Logs de Auditoria (últimos {len(logs)} eventos)")
        
        table.add_column("Data/Hora", style="cyan")
        table.add_column("Evento", style="yellow")
        table.add_column("Detalhes", style="green")
        
        for log in logs:
            timestamp = log.get('timestamp', 'N/A')[:19].replace('T', ' ')
            event_type = log.get('event_type', 'unknown')
            details = json.dumps(log.get('details', {}), ensure_ascii=False)
            
            table.add_row(timestamp, event_type, details[:50] + "..." if len(details) > 50 else details)
        
        console.print(table)
    
    def clear_audit_logs(self) -> bool:
        """Limpa logs de auditoria"""
        try:
            if os.path.exists(self.audit_log_file):
                with open(self.audit_log_file, 'w') as f:
                    f.write('')
                console.print("[green]✓ Logs de auditoria limpos[/green]")
            return True
        except Exception as e:
            console.print(f"[red]✗ Erro ao limpar logs: {e}[/red]")
            return False
    
    # ==================== Firewall (UFW/Firewalld) ====================
    
    def setup_firewall_rules(self, protocols: List[str]) -> bool:
        """Configura regras de firewall para os protocolos"""
        console.print(Panel("[bold blue]Configurando regras de firewall...[/bold blue]"))
        
        # Detectar tipo de firewall
        firewall_type = self._detect_firewall()
        
        if firewall_type == 'ufw':
            return self._setup_ufw_rules(protocols)
        elif firewall_type == 'firewalld':
            return self._setup_firewalld_rules(protocols)
        else:
            console.print("[yellow]⚠ Firewall não detectado ou não suportado[/yellow]")
            return False
    
    def _detect_firewall(self) -> str:
        """Detecta tipo de firewall"""
        try:
            result = subprocess.run(['ufw', 'version'], capture_output=True, text=True)
            if result.returncode == 0:
                return 'ufw'
        except Exception:
            pass
        
        try:
            result = subprocess.run(['firewall-cmd', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                return 'firewalld'
        except Exception:
            pass
        
        return 'none'
    
    def _setup_ufw_rules(self, protocols: List[str]) -> bool:
        """Configura regras UFW"""
        # Mapeamento de protocolos para portas
        port_map = {
            'ftp': ['21/tcp', '40000:40100/tcp'],
            'sftp': ['22/tcp'],
            'nfs': ['111/tcp', '111/udp', '2049/tcp', '2049/udp'],
            'smb': ['139/tcp', '445/tcp', '137/udp', '138/udp'],
            'webdav': ['80/tcp', '443/tcp'],
            's3': ['9000/tcp', '9001/tcp']
        }
        
        for protocol in protocols:
            if protocol in port_map:
                for port in port_map[protocol]:
                    try:
                        subprocess.run(
                            ['ufw', 'allow', port],
                            capture_output=True,
                            timeout=30
                        )
                        console.print(f"[green]✓ Regra UFW adicionada: {port} ({protocol})[/green]")
                    except Exception as e:
                        console.print(f"[yellow]⚠ Não foi possível adicionar regra: {e}[/yellow]")
        
        return True
    
    def _setup_firewalld_rules(self, protocols: List[str]) -> bool:
        """Configura regras firewalld"""
        # Mapeamento de protocolos para serviços
        service_map = {
            'ftp': 'ftp',
            'sftp': 'ssh',
            'nfs': 'nfs',
            'smb': 'samba',
            'webdav': ['http', 'https'],
            's3': None  # Requer porta customizada
        }
        
        for protocol in protocols:
            if protocol in service_map:
                service = service_map[protocol]
                if service:
                    services = service if isinstance(service, list) else [service]
                    for svc in services:
                        try:
                            subprocess.run(
                                ['firewall-cmd', '--permanent', '--add-service', svc],
                                capture_output=True,
                                timeout=30
                            )
                            console.print(f"[green]✓ Serviço firewalld adicionado: {svc}[/green]")
                        except Exception as e:
                            console.print(f"[yellow]⚠ Erro: {e}[/yellow]")
        
        # Recarregar firewalld
        try:
            subprocess.run(['firewall-cmd', '--reload'], capture_output=True, timeout=30)
        except Exception:
            pass
        
        return True
    
    # ==================== Status Geral ====================
    
    def get_security_status(self) -> Dict:
        """Retorna status geral de segurança"""
        return {
            'ssl': {
                'enabled': self.config['ssl']['enabled'],
                'cert_file': self.config['ssl'].get('cert_file'),
                'expires_soon': self.check_certificate_expiry()
            },
            'fail2ban': self.get_fail2ban_status(),
            'ip_restrictions': self.config['ip_restrictions'],
            'audit_enabled': self.config['audit']['enabled']
        }
    
    def display_security_status(self):
        """Exibe status de segurança"""
        status = self.get_security_status()
        
        console.print(Panel("[bold]Status de Segurança[/bold]"))
        
        # SSL
        ssl_status = "[green]✓ Habilitado[/green]" if status['ssl']['enabled'] else "[red]✗ Desabilitado[/red]"
        cert_expiry = "[yellow]⚠ Expirando em breve[/yellow]" if status['ssl'].get('expires_soon') else "[green]✓ Válido[/green]"
        console.print(f"SSL/TLS: {ssl_status} | Certificado: {cert_expiry}")
        
        # Fail2Ban
        f2b_status = "[green]✓ Rodando[/green]" if status['fail2ban'].get('running') else "[red]✗ Parado[/red]"
        console.print(f"Fail2Ban: {f2b_status}")
        
        # IP Restrictions
        whitelist_count = len(status['ip_restrictions'].get('whitelist', []))
        blacklist_count = len(status['ip_restrictions'].get('blacklist', []))
        console.print(f"IP Whitelist: {whitelist_count} | Blacklist: {blacklist_count}")
        
        # Audit
        audit_status = "[green]✓ Habilitado[/green]" if status['audit_enabled'] else "[yellow]⚠ Desabilitado[/yellow]"
        console.print(f"Auditoria: {audit_status}")