"""
Logger - Sistema de logs e auditoria
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from rich.console import Console

console = Console()


class AuditLogger:
    """Classe para registro de logs de auditoria"""
    
    def __init__(self, log_file: str = None, config_path: str = '/etc/file-server-manager'):
        if log_file is None:
            log_file = os.path.join(config_path, 'audit.log')
        
        self.log_file = log_file
        self.config_path = config_path
        
        # Garantir diretório existe
        try:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
        except Exception:
            pass
        
        # Configurar logger padrão
        self.logger = logging.getLogger('FileServerAudit')
        self.logger.setLevel(logging.INFO)
        
        # Handler para arquivo
        try:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.INFO)
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        except Exception:
            pass
    
    def log(self, event_type: str, message: str, details: Dict = None, level: str = 'INFO'):
        """
        Registra evento de auditoria
        
        Args:
            event_type: Tipo de evento (login, logout, file_access, config_change, user_change, error)
            message: Mensagem descritiva
            details: Detalhes adicionais em formato dict
            level: Nível do log (INFO, WARNING, ERROR, CRITICAL)
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'message': message,
            'details': details or {},
            'level': level
        }
        
        # Log no arquivo JSON
        try:
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception:
            pass
        
        # Log via logging padrão
        log_method = getattr(self.logger, level.lower(), self.logger.info)
        log_method(f"[{event_type}] {message}")
    
    def log_login(self, username: str, success: bool, ip: str = None, protocol: str = None):
        """Registra tentativa de login"""
        self.log(
            'login',
            f"Login {'bem-sucedido' if success else 'falhou'} para usuário: {username}",
            {
                'username': username,
                'success': success,
                'ip': ip,
                'protocol': protocol
            },
            'INFO' if success else 'WARNING'
        )
    
    def log_logout(self, username: str, protocol: str = None):
        """Registra logout de usuário"""
        self.log(
            'logout',
            f"Usuário {username} desconectado",
            {'username': username, 'protocol': protocol},
            'INFO'
        )
    
    def log_user_create(self, username: str, created_by: str = 'system'):
        """Registra criação de usuário"""
        self.log(
            'user_change',
            f"Usuário criado: {username}",
            {'username': username, 'created_by': created_by},
            'INFO'
        )
    
    def log_user_update(self, username: str, changes: List[str], updated_by: str = 'system'):
        """Registra atualização de usuário"""
        self.log(
            'user_change',
            f"Usuário atualizado: {username}",
            {'username': username, 'changes': changes, 'updated_by': updated_by},
            'INFO'
        )
    
    def log_user_delete(self, username: str, deleted_by: str = 'system'):
        """Registra exclusão de usuário"""
        self.log(
            'user_change',
            f"Usuário excluído: {username}",
            {'username': username, 'deleted_by': deleted_by},
            'WARNING'
        )
    
    def log_config_change(self, component: str, changes: Dict, changed_by: str = 'system'):
        """Registra mudança de configuração"""
        self.log(
            'config_change',
            f"Configuração alterada: {component}",
            {'component': component, 'changes': changes, 'changed_by': changed_by},
            'INFO'
        )
    
    def log_file_access(self, username: str, path: str, action: str, protocol: str = None):
        """Registra acesso a arquivo"""
        self.log(
            'file_access',
            f"Acesso a arquivo: {path} ({action})",
            {'username': username, 'path': path, 'action': action, 'protocol': protocol},
            'INFO'
        )
    
    def log_error(self, error: str, component: str = None, details: Dict = None):
        """Registra erro"""
        self.log(
            'error',
            f"Erro: {error}",
            {'component': component, 'details': details or {}},
            'ERROR'
        )
    
    def log_security_event(self, event: str, ip: str = None, details: Dict = None):
        """Registra evento de segurança"""
        self.log(
            'security',
            f"Evento de segurança: {event}",
            {'ip': ip, 'details': details or {}},
            'WARNING'
        )
    
    def get_logs(
        self,
        start_date: str = None,
        end_date: str = None,
        event_type: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Obtém logs com filtros
        
        Args:
            start_date: Data inicial (YYYY-MM-DD)
            end_date: Data final (YYYY-MM-DD)
            event_type: Tipo de evento para filtrar
            limit: Limite de registros
        """
        logs = []
        
        if not os.path.exists(self.log_file):
            return logs
        
        try:
            with open(self.log_file, 'r') as f:
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
        except Exception:
            pass
        
        return logs
    
    def clear_logs(self) -> bool:
        """Limpa todos os logs"""
        try:
            with open(self.log_file, 'w') as f:
                f.write('')
            console.print("[green]✓ Logs limpos[/green]")
            return True
        except Exception as e:
            console.print(f"[red]✗ Erro ao limpar logs: {e}[/red]")
            return False
    
    def display_audit_logs(self, limit: int = 50):
        """Exibe logs de auditoria formatados"""
        logs = self.get_logs(limit=limit)
        
        if not logs:
            console.print("[yellow]⚠ Nenhum log encontrado[/yellow]")
            return
        
        from rich.table import Table
        table = Table(title=f"Logs de Auditoria (últimos {len(logs)} eventos)")
        
        table.add_column("Data/Hora", style="cyan")
        table.add_column("Tipo", style="yellow")
        table.add_column("Mensagem", style="green")
        table.add_column("Nível", style="red")
        
        for log in logs:
            table.add_row(
                log.get('timestamp', 'N/A')[:19].replace('T', ' '),
                log.get('event_type', 'N/A'),
                log.get('message', 'N/A')[:50],
                log.get('level', 'INFO')
            )
        
        console.print(table)
    
    def rotate_logs(self, max_size_mb: int = 10, keep_backups: int = 5) -> bool:
        """
        Rotaciona logs se exceder tamanho máximo
        
        Args:
            max_size_mb: Tamanho máximo em MB antes de rotacionar
            keep_backups: Número de backups a manter
        """
        try:
            if not os.path.exists(self.log_file):
                return True
            
            file_size_mb = os.path.getsize(self.log_file) / (1024 * 1024)
            
            if file_size_mb >= max_size_mb:
                # Rotacionar backups existentes
                for i in range(keep_backups, 0, -1):
                    old_file = f"{self.log_file}.{i}"
                    new_file = f"{self.log_file}.{i + 1}"
                    if os.path.exists(old_file):
                        if i == keep_backups:
                            os.remove(old_file)
                        else:
                            os.rename(old_file, new_file)
                
                # Mover log atual para backup
                os.rename(self.log_file, f"{self.log_file}.1")
                
                # Criar novo arquivo de log
                with open(self.log_file, 'w') as f:
                    f.write('')
                
                console.print("[green]✓ Logs rotacionados[/green]")
                return True
            
            return True
        except Exception as e:
            console.print(f"[red]✗ Erro ao rotacionar logs: {e}[/red]")
            return False