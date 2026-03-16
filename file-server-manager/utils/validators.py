"""
Validadores - Funções de validação de entrada
"""

import re
import os
import socket
from typing import Optional, Tuple


class Validators:
    """Classe com funções de validação"""
    
    @staticmethod
    def validate_username(username: str) -> Tuple[bool, str]:
        """
        Valida nome de usuário
        
        Regras:
        - 3-32 caracteres
        - Apenas letras, números, underscore e hífen
        - Deve começar com letra
        """
        if not username:
            return False, "Nome de usuário não pode ser vazio"
        
        if len(username) < 3:
            return False, "Nome de usuário deve ter pelo menos 3 caracteres"
        
        if len(username) > 32:
            return False, "Nome de usuário deve ter no máximo 32 caracteres"
        
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', username):
            return False, "Nome de usuário deve começar com letra e conter apenas letras, números, underscore e hífen"
        
        return True, ""
    
    @staticmethod
    def validate_password(password: str) -> Tuple[bool, str]:
        """
        Valida senha
        
        Regras:
        - Mínimo 8 caracteres
        - Pelo menos uma letra maiúscula
        - Pelo menos uma letra minúscula
        - Pelo menos um número
        - Pelo menos um caractere especial
        """
        if not password:
            return False, "Senha não pode ser vazia"
        
        if len(password) < 8:
            return False, "Senha deve ter pelo menos 8 caracteres"
        
        if not re.search(r'[A-Z]', password):
            return False, "Senha deve conter pelo menos uma letra maiúscula"
        
        if not re.search(r'[a-z]', password):
            return False, "Senha deve conter pelo menos uma letra minúscula"
        
        if not re.search(r'\d', password):
            return False, "Senha deve conter pelo menos um número"
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "Senha deve conter pelo menos um caractere especial"
        
        return True, ""
    
    @staticmethod
    def validate_weak_password(password: str) -> Tuple[bool, str]:
        """
        Valida senha (versão fraca, apenas tamanho mínimo)
        Útil para senhas de serviço ou quando políticas menos rigorosas são necessárias
        """
        if not password:
            return False, "Senha não pode ser vazia"
        
        if len(password) < 6:
            return False, "Senha deve ter pelo menos 6 caracteres"
        
        return True, ""
    
    @staticmethod
    def validate_ip_address(ip: str) -> Tuple[bool, str]:
        """Valida endereço IP (IPv4 ou IPv6)"""
        if not ip:
            return False, "Endereço IP não pode ser vazio"
        
        # IPv4
        ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if re.match(ipv4_pattern, ip):
            parts = ip.split('.')
            for part in parts:
                if int(part) > 255:
                    return False, f"Octeto inválido: {part}"
            return True, ""
        
        # IPv6 (simplificado)
        if ':' in ip:
            try:
                socket.inet_pton(socket.AF_INET6, ip)
                return True, ""
            except Exception:
                pass
        
        # CIDR notation
        if '/' in ip:
            ip_part = ip.split('/')[0]
            return Validators.validate_ip_address(ip_part)
        
        return False, "Endereço IP inválido"
    
    @staticmethod
    def validate_port(port: int) -> Tuple[bool, str]:
        """Valida número de porta"""
        if not isinstance(port, int):
            return False, "Porta deve ser um número inteiro"
        
        if port < 1 or port > 65535:
            return False, "Porta deve estar entre 1 e 65535"
        
        return True, ""
    
    @staticmethod
    def validate_path(path: str, must_exist: bool = False) -> Tuple[bool, str]:
        """Valida caminho de arquivo/diretório"""
        if not path:
            return False, "Caminho não pode ser vazio"
        
        if not path.startswith('/'):
            return False, "Caminho deve ser absoluto (começar com /)"
        
        if must_exist and not os.path.exists(path):
            return False, f"Caminho não existe: {path}"
        
        # Verificar caracteres inválidos
        if '\0' in path:
            return False, "Caminho contém caracteres inválidos"
        
        return True, ""
    
    @staticmethod
    def validate_domain(domain: str) -> Tuple[bool, str]:
        """Valida nome de domínio"""
        if not domain:
            return False, "Domínio não pode ser vazio"
        
        # Padrão simples para domínio
        pattern = r'^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
        if re.match(pattern, domain):
            return True, ""
        
        # localhost é válido
        if domain == 'localhost':
            return True, ""
        
        return False, "Domínio inválido"
    
    @staticmethod
    def validate_email(email: str) -> Tuple[bool, str]:
        """Valida endereço de email"""
        if not email:
            return False, "Email não pode ser vazio"
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(pattern, email):
            return True, ""
        
        return False, "Email inválido"
    
    @staticmethod
    def validate_quota_mb(quota: int) -> Tuple[bool, str]:
        """Valida quota em MB"""
        if not isinstance(quota, int):
            return False, "Quota deve ser um número inteiro"
        
        if quota < 0:
            return False, "Quota não pode ser negativa"
        
        if quota > 1048576:  # 1 TB
            return False, "Quota muito grande (máximo 1 TB)"
        
        return True, ""
    
    @staticmethod
    def validate_protocol(protocol: str) -> Tuple[bool, str]:
        """Valida nome de protocolo"""
        valid_protocols = ['ftp', 'sftp', 'nfs', 'smb', 'webdav', 's3']
        
        if not protocol:
            return False, "Protocolo não pode ser vazio"
        
        if protocol.lower() not in valid_protocols:
            return False, f"Protocolo inválido. Válidos: {', '.join(valid_protocols)}"
        
        return True, ""
    
    @staticmethod
    def validate_workgroup(workgroup: str) -> Tuple[bool, str]:
        """Valida nome de workgroup (Samba)"""
        if not workgroup:
            return False, "Workgroup não pode ser vazio"
        
        if len(workgroup) > 15:
            return False, "Workgroup deve ter no máximo 15 caracteres"
        
        if not re.match(r'^[a-zA-Z0-9_-]+$', workgroup):
            return False, "Workgroup contém caracteres inválidos"
        
        return True, ""
    
    @staticmethod
    def validate_nfs_options(options: list) -> Tuple[bool, str]:
        """Valida opções de exportação NFS"""
        valid_options = [
            'rw', 'ro', 'sync', 'async', 'no_subtree_check', 'subtree_check',
            'no_root_squash', 'root_squash', 'all_squash', 'anonuid', 'anongid',
            'secure', 'insecure', 'nohide', 'hide', 'crossmnt', 'nocrossmnt',
            'fsid', 'noacl', 'wdelay', 'no_wdelay'
        ]
        
        for option in options:
            # Opções com valor (ex: anonuid=1000)
            if '=' in option:
                key = option.split('=')[0]
                if key not in ['anonuid', 'anongid', 'fsid']:
                    return False, f"Opção NFS inválida: {option}"
            else:
                if option not in valid_options:
                    return False, f"Opção NFS inválida: {option}"
        
        return True, ""