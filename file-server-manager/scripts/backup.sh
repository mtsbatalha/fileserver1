#!/bin/bash
#
# Script de Backup - File Server Manager
# Cria backup das configurações e lista de usuários
#

set -e

BACKUP_DIR="/var/backups/file-server-manager"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/backup_$DATE.tar.gz"

# Cores
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}=== Backup do File Server Manager ===${NC}"

# Criar diretório de backup
mkdir -p "$BACKUP_DIR"

# Arquivos para backup
FILES_TO_BACKUP=(
    "/etc/file-server-manager/config.json"
    "/etc/file-server-manager/users.json"
    "/etc/file-server-manager/audit.log"
    "/etc/vsftpd.conf"
    "/etc/ssh/sshd_config"
    "/etc/exports"
    "/etc/samba/smb.conf"
    "/etc/apache2/sites-available/webdav.conf"
    "/etc/apache2/.davpasswd"
    "/etc/ssl/fileserver"
    "/etc/fail2ban/jail.local"
    "/etc/fail2ban/filter.d"
)

# Criar lista de arquivos existentes
EXISTING_FILES=()
for file in "${FILES_TO_BACKUP[@]}"; do
    if [ -e "$file" ]; then
        EXISTING_FILES+=("$file")
        echo -e "${GREEN}✓${NC} Adicionado: $file"
    fi
done

# Criar arquivo de backup
if [ ${#EXISTING_FILES[@]} -gt 0 ]; then
    tar -czf "$BACKUP_FILE" "${EXISTING_FILES[@]}" 2>/dev/null || true
    echo -e "${GREEN}✓${NC} Backup criado: $BACKUP_FILE"
    
    # Mostrar tamanho
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo -e "${GREEN}✓${NC} Tamanho: $SIZE"
else
    echo -e "Nenhum arquivo de configuração encontrado"
    exit 1
fi

# Manter apenas últimos 10 backups
cd "$BACKUP_DIR"
ls -t backup_*.tar.gz | tail -n +11 | xargs -r rm

echo -e "${GREEN}✓${NC} Backup concluído!"
echo ""
echo "Backups disponíveis:"
ls -lh "$BACKUP_DIR"/backup_*.tar.gz | awk '{print $9, $5}'