content = """#!/bin/bash
set -e

echo "[replica-setup] Checking connection to mysql-primary..."
until mysql -h mysql-primary -u root -prootpass -e "SELECT 1;" > /dev/null 2>&1; do
  echo "[replica-setup] Waiting for mysql-primary..."
  sleep 2
done
echo "[replica-setup] mysql-primary is ready!"

echo "[replica-setup] Checking connection to mysql-replica..."
until mysql -h mysql-replica -u root -prootpass -e "SELECT 1;" > /dev/null 2>&1; do
  echo "[replica-setup] Waiting for mysql-replica..."
  sleep 2
done
echo "[replica-setup] mysql-replica is ready!"

echo "[replica-setup] Creating replication user on mysql-primary..."
mysql -h mysql-primary -u root -prootpass <<EOSQL
CREATE USER IF NOT EXISTS 'repl'@'%' IDENTIFIED WITH mysql_native_password BY 'replpass';
GRANT REPLICATION SLAVE ON *.* TO 'repl'@'%';
FLUSH PRIVILEGES;
EOSQL

echo "[replica-setup] Configuring replication on mysql-replica..."
mysql -h mysql-replica -u root -prootpass <<EOSQL
STOP REPLICA;
RESET REPLICA ALL;
CHANGE REPLICATION SOURCE TO
  SOURCE_HOST='mysql-primary',
  SOURCE_PORT=3306,
  SOURCE_USER='repl',
  SOURCE_PASSWORD='replpass',
  SOURCE_AUTO_POSITION=1;
START REPLICA;
SET PERSIST read_only = ON;
SET PERSIST super_read_only = ON;
EOSQL

echo "[replica-setup] Bekleniyor (5 saniye)..."
sleep 5

echo "[replica-setup] Guncel Replika Durumu:"
mysql -h mysql-replica -u root -prootpass -e "SHOW REPLICA STATUS\\G"

echo "[replica-setup] Kurulum basariyla tamamlandi ve replika salt okunur yapildi!"
exit 0
"""

with open("db/replica-setup.sh", "w", newline="\n", encoding="utf-8") as f:
    f.write(content)

print("db/replica-setup.sh updated with SET PERSIST")
