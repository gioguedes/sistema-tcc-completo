#!/usr/bin/env bash
# Sobe o sistema em modo normal para o ensaio em água e exporta os dados de hora em hora.
# Uso: bash ferramentas/ensaio.sh      Parar: powershell -File ferramentas/parar.ps1
R="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
B="${ENSAIO_BACKUP:-$(cygpath -u "$USERPROFILE")/OneDrive/Área de Trabalho/TCC/ensaio-agua}"
export ML_INTERVALO_S=300 ML_DEMO_MINUTOS=0

if curl -s -o /dev/null --max-time 3 http://127.0.0.1:8000/; then echo "o sistema já está no ar"; exit 0; fi

for i in $(seq 1 120); do docker version --format '{{.Server.Version}}' > /dev/null 2>&1 && break; sleep 5; done

banco() { docker exec piscicultura-timescaledb sh -c "$1"; }
PSQL='psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
# grava em .tmp e só troca se deu certo: uma falha não pode apagar o último backup bom
exportar() {  # exportar <arquivo> <comando>
  banco "$2" > "$B/$1.tmp" 2>> "$B/backup.log" && mv -f "$B/$1.tmp" "$B/$1" || echo "$(date '+%F %T') falha em $1" >> "$B/backup.log"
}

mkdir -p "$B"
while true; do
  exportar leituras.csv "$PSQL -c \"COPY (SELECT l.ts, t.grandeza, l.valor, l.unidade FROM leituras l JOIN sensores s ON s.id = l.id_sensor JOIN tipos_sensor t ON t.id = s.id_tipo ORDER BY l.ts, t.grandeza) TO STDOUT WITH CSV HEADER\""
  exportar previsoes.csv "$PSQL -c \"COPY (SELECT * FROM previsoes ORDER BY 1) TO STDOUT WITH CSV HEADER\""
  exportar banco.dump 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc'
  sleep 3600
done &

exec bash "$R/ferramentas/demonstracao.sh"
