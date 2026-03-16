#!/bin/bash
#
# Script de Monitoramento - File Server Manager
# Verifica status dos serviços, uso de disco e conexões ativas
#

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}  Monitoramento - File Server Manager${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""
echo "Data: $(date)"
echo ""

# ============================================
# Status dos Serviços
# ============================================
echo -e "${CYAN}=== Status dos Serviços ===${NC}"

check_service() {
    local name=$1
    local service=$2
    
    if systemctl is-active --quiet "$service" 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} $name"
        return 0
    else
        echo -e "  ${RED}✗${NC} $name (inativo)"
        return 1
    fi
}

SERVICES_DOWN=0

check_service "FTP (vsftpd)" "vsftpd" || ((SERVICES_DOWN++))
check_service "SFTP (SSH)" "sshd" || ((SERVICES_DOWN++))
check_service "NFS" "nfs-kernel-server" || ((SERVICES_DOWN++))
check_service "SMB (Samba)" "smbd" || ((SERVICES_DOWN++))
check_service "WebDAV (Apache)" "apache2" || ((SERVICES_DOWN++))

# Verificar MinIO (Docker)
if docker ps 2>/dev/null | grep -q minio; then
    echo -e "  ${GREEN}✓${NC} S3 (MinIO)"
else
    echo -e "  ${YELLOW}○${NC} S3 (MinIO) - não verificado via Docker"
fi

echo ""

# ============================================
# Uso de Disco
# ============================================
echo -e "${CYAN}=== Uso de Disco ===${NC}"

df -h /srv/files 2>/dev/null | tail -1 | awk '{
    printf "  /srv/files: %s usado de %s (%s)\n", $3, $2, $5
}' || echo "  Diretório /srv/files não encontrado"

echo ""

# ============================================
# Espaço por Diretório
# ============================================
echo -e "${CYAN}=== Espaço por Diretório ===${NC}"

if [ -d /srv/files ]; then
    du -sh /srv/files/* 2>/dev/null | sort -hr | head -10 | while read size dir; do
        printf "  %-30s %s\n" "$(basename $dir)" "$size"
    done
else
    echo "  Diretório /srv/files não encontrado"
fi

echo ""

# ============================================
# Conexões Ativas
# ============================================
echo -e "${CYAN}=== Conexões Ativas ===${NC}"

# FTP
FTP_CONN=$(netstat -an 2>/dev/null | grep ":21 " | grep ESTABLISHED | wc -l)
echo -e "  FTP: $FTP_CONN conexões"

# SSH/SFTP
SSH_CONN=$(netstat -an 2>/dev/null | grep ":22 " | grep ESTABLISHED | wc -l)
echo -e "  SFTP/SSH: $SSH_CONN conexões"

# SMB
SMB_CONN=$(netstat -an 2>/dev/null | grep ":445 " | grep ESTABLISHED | wc -l)
echo -e "  SMB: $SMB_CONN conexões"

# HTTP/HTTPS (WebDAV)
WEBDAV_CONN=$(netstat -an 2>/dev/null | grep -E ":(80|443) " | grep ESTABLISHED | wc -l)
echo -e "  WebDAV: $WEBDAV_CONN conexões"

echo ""

# ============================================
# Logs Recentes (Erros)
# ============================================
echo -e "${CYAN}=== Erros Recentes ===${NC}"

# Verificar logs do sistema
if [ -f /var/log/syslog ]; then
    ERRORS=$(grep -i "error\|fail\|critical" /var/log/syslog 2>/dev/null | tail -5)
    if [ -n "$ERRORS" ]; then
        echo "$ERRORS" | sed 's/^/  /'
    else
        echo -e "  ${GREEN}Nenhum erro recente${NC}"
    fi
fi

echo ""

# ============================================
# Alertas
# ============================================
echo -e "${CYAN}=== Alertas ===${NC}"

ALERTS=0

# Verificar espaço em disco
DISK_USAGE=$(df /srv/files 2>/dev/null | tail -1 | awk '{print $5}' | tr -d '%')
if [ -n "$DISK_USAGE" ] && [ "$DISK_USAGE" -gt 80 ]; then
    echo -e "  ${RED}⚠${NC} Uso de disco acima de 80% ($DISK_USAGE%)"
    ((ALERTS++))
fi

# Verificar serviços down
if [ "$SERVICES_DOWN" -gt 0 ]; then
    echo -e "  ${YELLOW}⚠${NC} $SERVICES_DOWN serviço(s) inativo(s)"
    ((ALERTS++))
fi

# Verificar fail2ban
if systemctl is-active --quiet fail2ban 2>/dev/null; then
    BANS=$(fail2ban-client status 2>/dev/null | grep "Currently banned" | awk '{print $4}')
    if [ -n "$BANS" ] && [ "$BANS" -gt 0 ]; then
        echo -e "  ${YELLOW}⚠${NC} $BANS IP(s) banido(s) pelo fail2ban"
    fi
fi

if [ "$ALERTS" -eq 0 ]; then
    echo -e "  ${GREEN}✓${NC} Nenhum alerta"
fi

echo ""
echo -e "${CYAN}============================================${NC}"
echo ""

# Resumo
echo "Resumo:"
echo "  Serviços ativos: $((5 - SERVICES_DOWN))/5"
echo "  Alertas: $ALERTS"
echo ""

exit $ALERTS