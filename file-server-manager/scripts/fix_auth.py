#!/usr/bin/env python3
"""
Script de correção de autenticação FTP/SFTP
Corrige problemas comuns de autenticação no vsftpd e SSH

Uso: sudo python3 fix_auth.py
"""

import subprocess
import os
import sys

def run_command(cmd, description=""):
    """Executa comando e retorna resultado"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, shell=isinstance(cmd, str))
        if result.returncode == 0:
            print(f"✓ {description}")
            return True, result.stdout
        else:
            print(f"✗ {description}: {result.stderr}")
            return False, result.stderr
    except Exception as e:
        print(f"✗ {description}: {e}")
        return False, str(e)

def fix_pam_config():
    """Cria configuração PAM correta para FTP"""
    print("\n=== Configurando PAM para FTP ===")
    
    pam_config = """# PAM configuration for vsftpd
# Permite autenticação de usuários do sistema

auth    required    pam_unix.so shadow nullok
account required    pam_unix.so
session required    pam_unix.so
"""
    
    # Criar /etc/pam.d/ftp
    try:
        with open('/etc/pam.d/ftp', 'w') as f:
            f.write(pam_config)
        print("✓ Criado /etc/pam.d/ftp")
    except Exception as e:
        print(f"✗ Erro ao criar /etc/pam.d/ftp: {e}")
    
    # Atualizar /etc/pam.d/vsftpd
    try:
        with open('/etc/pam.d/vsftpd', 'w') as f:
            f.write(pam_config)
        print("✓ Atualizado /etc/pam.d/vsftpd")
    except Exception as e:
        print(f"✗ Erro ao atualizar /etc/pam.d/vsftpd: {e}")

def fix_vsftpd_config():
    """Corrige configuração do vsftpd"""
    print("\n=== Corrigindo vsftpd.conf ===")
    
    config_file = '/etc/vsftpd.conf'
    
    if not os.path.exists(config_file):
        print(f"✗ {config_file} não encontrado")
        return
    
    try:
        with open(config_file, 'r') as f:
            content = f.read()
        
        # Verificar e adicionar configurações necessárias
        needed_configs = [
            ('check_shell=NO', 'check_shell=NO'),
            ('pam_service_name=ftp', 'pam_service_name=ftp'),
            ('userlist_enable=YES', 'userlist_enable=YES'),
            ('userlist_deny=NO', 'userlist_deny=NO'),
            ('allow_writeable_chroot=YES', 'allow_writeable_chroot=YES'),
        ]
        
        for check, config_line in needed_configs:
            if check not in content:
                content += f"\n# Correção automática\n{config_line}\n"
                print(f"✓ Adicionado: {config_line}")
        
        with open(config_file, 'w') as f:
            f.write(content)
        print(f"✓ {config_file} atualizado")
        
    except Exception as e:
        print(f"✗ Erro ao corrigir {config_file}: {e}")

def fix_user_shells():
    """Corrige shells dos usuários para permitir login FTP"""
    print("\n=== Corrigindo shells dos usuários ===")
    
    # Listar usuários do sistema que têm home em /srv/files/users/
    try:
        result = subprocess.run(
            "awk -F: '$6 ~ /\/srv\/files\/users/ {print $1}' /etc/passwd",
            capture_output=True, text=True, shell=True
        )
        
        users = result.stdout.strip().split('\n')
        users = [u for u in users if u]
        
        if not users:
            print("⚠ Nenhum usuário encontrado em /srv/files/users/")
            return
        
        for username in users:
            # Mudar shell para /bin/bash
            run_command(
                ['usermod', '-s', '/bin/bash', username],
                f"Shell de {username} alterado para /bin/bash"
            )
            
    except Exception as e:
        print(f"✗ Erro ao corrigir shells: {e}")

def fix_home_permissions():
    """Corrige permissões dos diretórios home"""
    print("\n=== Corrigindo permissões dos diretórios home ===")
    
    base_dir = '/srv/files/users'
    
    if not os.path.exists(base_dir):
        print(f"✗ {base_dir} não existe")
        return
    
    for username in os.listdir(base_dir):
        home_dir = os.path.join(base_dir, username)
        
        if not os.path.isdir(home_dir):
            continue
        
        # Definir ownership do home para root (necessário para chroot)
        run_command(
            ['chown', 'root:root', home_dir],
            f"{home_dir} -> root:root"
        )
        
        # Permissões 755
        run_command(
            ['chmod', '755', home_dir],
            f"{home_dir} -> 755"
        )
        
        # Criar diretório upload se não existir
        upload_dir = os.path.join(home_dir, 'upload')
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir, exist_ok=True)
            print(f"✓ Criado {upload_dir}")
        
        # Definir ownership do upload para o usuário
        run_command(
            ['chown', f'{username}:{username}', upload_dir],
            f"{upload_dir} -> {username}:{username}"
        )

def restart_services():
    """Reinicia serviços"""
    print("\n=== Reiniciando serviços ===")
    
    services = ['vsftpd', 'sshd']
    
    for service in services:
        run_command(
            ['systemctl', 'restart', service],
            f"Reiniciado {service}"
        )

def test_ftp_auth():
    """Testa autenticação FTP"""
    print("\n=== Testando autenticação FTP ===")
    
    # Verificar se vsftpd está rodando
    result = subprocess.run(
        ['systemctl', 'is-active', 'vsftpd'],
        capture_output=True, text=True
    )
    
    if result.stdout.strip() != 'active':
        print("✗ vsftpd não está rodando")
        print("  Tente: sudo systemctl start vsftpd")
    else:
        print("✓ vsftpd está rodando")
    
    # Verificar portas
    result = subprocess.run(
        "ss -tlnp | grep ':21' || netstat -tlnp | grep ':21'",
        capture_output=True, text=True, shell=True
    )
    
    if ':21' in result.stdout:
        print("✓ Porta 21 está aberta")
    else:
        print("✗ Porta 21 não está aberta")

def main():
    """Função principal"""
    print("=" * 60)
    print("CORREÇÃO DE AUTENTICAÇÃO FTP/SFTP")
    print("=" * 60)
    
    # Verificar root
    if os.geteuid() != 0:
        print("\n✗ ERRO: Execute como root (sudo)")
        sys.exit(1)
    
    print("\nEste script irá:")
    print("  1. Configurar PAM para permitir autenticação FTP")
    print("  2. Corrigir vsftpd.conf")
    print("  3. Ajustar shells dos usuários")
    print("  4. Corrigir permissões dos diretórios home")
    print("  5. Reiniciar serviços")
    print("  6. Testar configuração")
    
    input("\nPressione ENTER para continuar ou Ctrl+C para cancelar...")
    
    # Executar correções
    fix_pam_config()
    fix_vsftpd_config()
    fix_user_shells()
    fix_home_permissions()
    restart_services()
    test_ftp_auth()
    
    print("\n" + "=" * 60)
    print("CORREÇÃO CONCLUÍDA!")
    print("=" * 60)
    print("\nPróximos passos:")
    print("  1. Teste o login FTP: ftp localhost")
    print("  2. Verifique os logs: sudo tail -f /var/log/vsftpd.log")
    print("  3. Se ainda houver problemas, verifique /var/log/auth.log")
    print("\nDica: Use o utilitário 'Redefinir Senha' no menu principal")
    print("      para garantir que as senhas estejam sincronizadas.")

if __name__ == "__main__":
    main()
