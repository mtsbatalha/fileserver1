# File Server Manager

Gerenciador completo de servidores de arquivos com interface de menu interativo para Linux (Debian/Ubuntu).

## Recursos

- **Instalação automática** de múltiplos protocolos de compartilhamento de arquivos
- **Gerenciamento centralizado** de usuários e configurações
- **Segurança integrada** com SSL/TLS, fail2ban e firewall
- **Sistema de quotas** para controle de uso de disco
- **Logs de auditoria** para rastreabilidade

## Protocolos Suportados

| Protocolo | Descrição | Porta(s) |
|-----------|-----------|----------|
| **FTP** | File Transfer Protocol (vsftpd) | 21, 40000-40100 |
| **SFTP** | SSH File Transfer Protocol | 22 |
| **NFS** | Network File System | 2049 |
| **SMB/CIFS** | Server Message Block (Samba) | 445, 139 |
| **WebDAV** | Web Distributed Authoring | 80, 443 |
| **S3** | Amazon S3 Compatible (MinIO) | 9000, 9001 |

## Requisitos

- Sistema operacional: Debian 10+ ou Ubuntu 18.04+
- Python 3.7+
- Acesso root (sudo)
- Conexão com internet para download de pacotes

## Instalação

### 1. Clone ou baixe o projeto

```bash
cd /opt
git clone <repository-url> file-server-manager
cd file-server-manager
```

### 2. Instale as dependências Python

```bash
pip3 install -r requirements.txt
```

### 3. Execute o gerenciador

```bash
sudo python3 main.py
```

## Uso

### Menu Principal

Ao iniciar, você verá o menu principal com as seguintes opções:

1. **Instalar/Configurar Protocolos** - Instala e configura os servidores de arquivos
2. **Gerenciar Usuários** - Cria, edita e exclui usuários
3. **Configurar Segurança** - SSL, fail2ban, firewall
4. **Configurar Quotas** - Limites de uso de disco por usuário
5. **Ver Status dos Serviços** - Status de cada protocolo
6. **Ver Logs de Auditoria** - Histórico de ações
7. **Configurações** - Backup, restore, opções gerais

### Instalação Rápida (Todos os Protocolos)

1. Selecione "Instalar/Configurar Protocolos"
2. Escolha "Instalar TODOS os protocolos"
3. Informe o caminho base (padrão: `/srv/files`)
4. Aguarde a instalação e configuração automática

### Instalação Personalizada

1. Selecione "Instalar/Configurar Protocolos"
2. Escolha "Instalação personalizada"
3. Marque os protocolos desejados
4. Informe o caminho base
5. Aguarde a conclusão

### Gerenciamento de Usuários

#### Criar Usuário

1. Menu principal → "Gerenciar Usuários"
2. Escolha "Criar usuário"
3. Informe:
   - Nome de usuário (3-32 caracteres, inicia com letra)
   - **Senha**: Escolha entre:
     - **Gerar senha aleatória segura** (recomendado) - selecione o tamanho (8-32 caracteres)
     - **Digitar senha manualmente** - digite e confirme a senha
   - Diretório home
   - Protocolos permitidos
   - Quota (0 = ilimitado)
   - Se deve criar usuário no sistema

> **⚠ Importante**: Ao usar a senha aleatória, copie a senha exibida antes de confirmar! Ela não será mostrada novamente.

#### Gerar Senha Aleatória

O sistema inclui um gerador de senhas seguras que pode ser usado de duas formas:

**Pelo menu interativo:**
- Ao criar ou editar um usuário, selecione "Gerar senha aleatória segura"
- Escolha o tamanho: 8, 12, 16, 20, 24 ou 32 caracteres
- A senha contém: letras maiúsculas, minúsculas, números e símbolos

**Pela linha de comando:**
```bash
# Gerar 1 senha de 16 caracteres (padrão)
python3 scripts/genpass.py

# Gerar 1 senha de 20 caracteres
python3 scripts/genpass.py 20

# Gerar 5 senhas de 24 caracteres
python3 scripts/genpass.py 24 5

# Gerar 10 senhas de 32 caracteres
python3 scripts/genpass.py 32 10
```

#### Editar Usuário

1. Menu "Gerenciar Usuários"
2. Escolha "Editar usuário"
3. Selecione o usuário
4. Altere senha, home, protocolos ou status

#### Excluir Usuário

1. Menu "Gerenciar Usuários"
2. Escolha "Excluir usuário"
3. Selecione o usuário
4. Confirme a exclusão
5. Opcional: excluir home e usuário do sistema

### Configuração de Segurança

#### Gerar Certificado SSL

```bash
# Pelo menu: Segurança → Gerar Certificado SSL
# Ou manualmente:
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/private/fileserver.key \
  -out /etc/ssl/certs/fileserver.crt
```

#### Configurar Firewall

O gerenciador configura automaticamente as portas necessárias:

```bash
# Portas abertas automaticamente:
# FTP: 21, 40000-40100
# SFTP: 22
# NFS: 2049
# SMB: 445, 139
# WebDAV: 80, 443
# S3: 9000, 9001
```

## Estrutura de Diretórios

```
/srv/files/
├── ftp/          # Arquivos FTP
├── sftp/         # Arquivos SFTP (chroot)
├── nfs/          # Exportações NFS
├── smb/          # Shares SMB
├── webdav/       # Arquivos WebDAV
├── s3/           # Dados MinIO
│   ├── data/
│   └── certs/
└── users/        # Homes dos usuários
    └── username/

/etc/file-server-manager/
├── config.json   # Configuração principal
├── users.json    # Banco de usuários
├── audit.log     # Logs de auditoria
└── backups/      # Backups de configuração
```

## Arquivos de Configuração

| Arquivo | Descrição |
|---------|-----------|
| `/etc/vsftpd.conf` | Configuração FTP |
| `/etc/ssh/sshd_config` | Configuração SFTP |
| `/etc/exports` | Exportações NFS |
| `/etc/samba/smb.conf` | Configuração SMB |
| `/etc/apache2/sites-available/webdav.conf` | WebDAV (Apache) |
| `/etc/file-server-manager/config.json` | Configuração principal |

## Comandos Úteis

### Verificar status dos serviços

```bash
sudo systemctl status vsftpd      # FTP
sudo systemctl status sshd        # SFTP
sudo systemctl status nfs-kernel-server  # NFS
sudo systemctl status smbd        # SMB
sudo systemctl status apache2     # WebDAV
docker ps | grep minio            # S3
```

### Reiniciar serviços

```bash
sudo systemctl restart vsftpd
sudo systemctl restart sshd
sudo systemctl restart nfs-kernel-server
sudo systemctl restart smbd
sudo systemctl restart apache2
docker restart minio
```

### Logs

```bash
# Logs do sistema
sudo tail -f /var/log/vsftpd.log
sudo tail -f /var/log/auth.log
sudo tail -f /var/log/samba/*.log
sudo journalctl -u apache2

# Logs de auditoria do File Server Manager
cat /etc/file-server-manager/audit.log
```

## Acesso aos Serviços

### FTP
```
ftp://server-ip/
# Porta: 21
# Usuários: usuários do sistema com home em /srv/files/ftp
```

### SFTP
```
sftp://username@server-ip
# Porta: 22
# Chroot: /srv/files/sftp/username
```

### NFS
```bash
# No cliente:
sudo mount server-ip:/srv/files/nfs /mnt
```

### SMB/CIFS
```
\\server-ip\share-name
# Porta: 445
# Shares configurados no smb.conf
```

### WebDAV
```
http://server-ip/
https://server-ip/ (com SSL)
# Porta: 80/443
```

### S3 (MinIO)
```
# Console Web: http://server-ip:9001
# API S3: http://server-ip:9000
# Access Key: minioadmin (padrão)
# Secret Key: minioadmin123 (padrão)
```

## Backup e Restauração

### Backup de Configurações

```bash
# Pelo menu: Configurações → Backup de configurações
# Ou manualmente:
sudo cp -r /etc/file-server-manager /backup/location
sudo cp /etc/vsftpd.conf /backup/location/
sudo cp /etc/samba/smb.conf /backup/location/
sudo cp /etc/exports /backup/location/
```

### Restaurar Configurações

```bash
sudo cp /backup/location/* /etc/file-server-manager/
sudo systemctl restart vsftpd smbd nfs-kernel-server apache2
```

## Troubleshooting

### FTP não conecta
```bash
sudo systemctl status vsftpd
sudo tail -f /var/log/vsftpd.log
sudo ufw allow 21/tcp
sudo ufw allow 40000:40100/tcp
```

### SFTP acesso negado
```bash
# Verificar permissões do diretório chroot
sudo chmod 755 /srv/files/sftp
sudo chmod 755 /srv/files/sftp/username
sudo chown root:root /srv/files/sftp
```

### NFS mount falha
```bash
sudo exportfs -ra
sudo systemctl restart nfs-kernel-server
showmount -e localhost
```

### SMB shares não aparecem
```bash
testparm -s
sudo systemctl restart smbd
sudo ufw allow 445/tcp
```

## Segurança

### Melhores Práticas

1. **Sempre use SSL/TLS** para FTP e WebDAV
2. **Desabilite login root** via SSH
3. **Use chaves SSH** em vez de senhas
4. **Configure fail2ban** para proteção contra brute-force
5. **Mantenha o sistema atualizado**
6. **Use quotas** para limitar uso de disco
7. **Revise logs regularmente**

### Configurar fail2ban

O gerenciador configura automaticamente jails para:
- vsftpd (FTP)
- sshd (SFTP)
- apache (WebDAV)

```bash
sudo fail2ban-client status
sudo fail2ban-client status vsftpd
sudo fail2ban-client status sshd
```

## API e Integração

### Arquivo de Configuração JSON

```json
{
  "base_path": "/srv/files",
  "protocols": {
    "ftp": {"enabled": true, "port": 21, "ssl": true},
    "sftp": {"enabled": true, "port": 22},
    "nfs": {"enabled": true, "port": 2049},
    "smb": {"enabled": true, "port": 445},
    "webdav": {"enabled": true, "port": 443, "ssl": true},
    "s3": {"enabled": true, "api_port": 9000, "console_port": 9001}
  },
  "security": {
    "ssl_enabled": true,
    "ssl_cert_path": "/etc/ssl/certs/fileserver.crt",
    "ssl_key_path": "/etc/ssl/private/fileserver.key",
    "fail2ban_enabled": true,
    "firewall_enabled": true
  }
}
```

## Licença

MIT License - Use livremente.

## Suporte

Para issues e dúvidas, abra um ticket no repositório do projeto.