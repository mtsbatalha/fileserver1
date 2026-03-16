#!/bin/bash
#
# File Server Manager - Script de Instalação
# Este script instala todas as dependências e configura o ambiente
#

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Funções de log
log_info() {
    echo -e "${CYAN}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[AVISO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERRO]${NC} $1"
}

# Verificar se é root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "Este script deve ser executado como root (sudo)"
        echo "Use: sudo ./install.sh"
        exit 1
    fi
}

# Verificar sistema operacional
check_os() {
    if [ -f /etc/debian_version ]; then
        OS="debian"
        log_info "Sistema Debian/Ubuntu detectado"
    else
        log_error "Este script suporta apenas Debian/Ubuntu"
        exit 1
    fi
}

# Atualizar repositórios
update_repos() {
    log_info "Atualizando repositórios..."
    apt-get update -qq
    log_success "Repositórios atualizados"
}

# Instalar dependências do sistema
install_system_deps() {
    log_info "Instalando dependências do sistema..."
    
    DEPS=(
        python3
        python3-pip
        openssl
        fail2ban
        ufw
        vsftpd
        openssh-server
        nfs-kernel-server
        samba
        apache2
        libapache2-mod-dav
        quota
    )
    
    # Instalar pacotes
    for pkg in "${DEPS[@]}"; do
        if dpkg -l | grep -q "^ii  $pkg "; then
            log_info "$pkg já está instalado"
        else
            log_info "Instalando $pkg..."
            DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "$pkg" || log_warning "Falha ao instalar $pkg"
        fi
    done
    
    log_success "Dependências do sistema instaladas"
}

# Instalar dependências Python
install_python_deps() {
    log_info "Instalando dependências Python..."
    
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    
    if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
        pip3 install -r "$SCRIPT_DIR/requirements.txt" -q
        log_success "Dependências Python instaladas"
    else
        log_error "requirements.txt não encontrado"
        exit 1
    fi
}

# Criar diretórios necessários
create_directories() {
    log_info "Criando diretórios..."
    
    BASE_DIR="/srv/files"
    CONFIG_DIR="/etc/file-server-manager"
    
    mkdir -p "$BASE_DIR"/{ftp,sftp,nfs,smb,webdav,s3/{data,certs},users}
    mkdir -p "$CONFIG_DIR"/backups
    mkdir -p /var/lib/nfs
    mkdir -p /var/lib/nfs/rpc_pipefs
    
    # Definir permissões
    chmod 755 "$BASE_DIR"
    chmod 755 "$CONFIG_DIR"
    
    log_success "Diretórios criados"
}

# Configurar fail2ban
setup_fail2ban() {
    log_info "Configurando fail2ban..."
    
    FAIL2BAN_CONF="/etc/fail2ban/jail.local"
    
    cat > "$FAIL2BAN_CONF" << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5
ignoreip = 127.0.0.1/8 ::1

[vsftpd]
enabled = true
port = 21
filter = vsftpd
logpath = /var/log/vsftpd.log

[sshd]
enabled = true
port = 22
filter = sshd
logpath = /var/log/auth.log

[apache-auth]
enabled = true
port = http,https
filter = apache-auth
logpath = /var/log/apache2/*error.log
EOF
    
    systemctl enable fail2ban
    systemctl restart fail2ban
    
    log_success "fail2ban configurado"
}

# Configurar firewall
setup_firewall() {
    log_info "Configurando firewall (UFW)..."
    
    # Habilitar UFW se não estiver
    if ! ufw status | grep -q "Status: active"; then
        log_info "Habilitando UFW..."
    fi
    
    # Regras para protocolos de arquivo
    ufw allow 21/tcp comment "FTP"
    ufw allow 40000:40100/tcp comment "FTP Passive"
    ufw allow 22/tcp comment "SFTP/SSH"
    ufw allow 2049/tcp comment "NFS"
    ufw allow 2049/udp comment "NFS"
    ufw allow 445/tcp comment "SMB"
    ufw allow 139/tcp comment "SMB NetBIOS"
    ufw allow 80/tcp comment "WebDAV HTTP"
    ufw allow 443/tcp comment "WebDAV HTTPS"
    ufw allow 9000/tcp comment "MinIO API"
    ufw allow 9001/tcp comment "MinIO Console"
    
    log_success "Firewall configurado"
}

# Gerar certificado SSL auto-assinado
generate_ssl_cert() {
    log_info "Gerando certificado SSL auto-assinado..."
    
    SSL_DIR="/etc/ssl/fileserver"
    mkdir -p "$SSL_DIR"
    
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$SSL_DIR/fileserver.key" \
        -out "$SSL_DIR/fileserver.crt" \
        -subj "/C=BR/ST=Estado/L=Cidade/O=FileServer/CN=fileserver" \
        2>/dev/null
    
    chmod 600 "$SSL_DIR/fileserver.key"
    chmod 644 "$SSL_DIR/fileserver.crt"
    
    log_success "Certificado SSL gerado"
}

# Criar configuração inicial
create_initial_config() {
    log_info "Criando configuração inicial..."
    
    CONFIG_DIR="/etc/file-server-manager"
    
    cat > "$CONFIG_DIR/config.json" << 'EOF'
{
    "base_path": "/srv/files",
    "protocols": {
        "ftp": {"enabled": false, "port": 21, "ssl": true},
        "sftp": {"enabled": false, "port": 22},
        "nfs": {"enabled": false, "port": 2049},
        "smb": {"enabled": false, "port": 445},
        "webdav": {"enabled": false, "port": 443, "ssl": true},
        "s3": {"enabled": false, "api_port": 9000, "console_port": 9001}
    },
    "security": {
        "ssl_enabled": true,
        "ssl_cert_path": "/etc/ssl/fileserver/fileserver.crt",
        "ssl_key_path": "/etc/ssl/fileserver/fileserver.key",
        "fail2ban_enabled": true,
        "firewall_enabled": true
    },
    "users": []
}
EOF
    
    log_success "Configuração inicial criada"
}

# Mostrar resumo
show_summary() {
    echo ""
    echo "============================================"
    echo -e "${GREEN}Instalação concluída com sucesso!${NC}"
    echo "============================================"
    echo ""
    echo "Para iniciar o File Server Manager:"
    echo "  sudo python3 main.py"
    echo ""
    echo "Diretórios criados:"
    echo "  /srv/files/         - Arquivos dos servidores"
    echo "  /etc/file-server-manager/ - Configurações"
    echo ""
    echo "Próximos passos:"
    echo "  1. Execute: sudo python3 main.py"
    echo "  2. Selecione 'Instalar/Configurar Protocolos'"
    echo "  3. Escolha os protocolos desejados"
    echo ""
}

# Main
main() {
    echo ""
    echo "============================================"
    echo "  File Server Manager - Instalação"
    echo "============================================"
    echo ""
    
    check_root
    check_os
    update_repos
    install_system_deps
    install_python_deps
    create_directories
    setup_fail2ban
    setup_firewall
    generate_ssl_cert
    create_initial_config
    
    show_summary
}

# Executar
main "$@"