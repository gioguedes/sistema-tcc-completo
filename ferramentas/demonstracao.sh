#!/usr/bin/env bash
# Sobe o sistema inteiro para a demonstração ao vivo, a partir da raiz do repositório, em qualquer máquina.
# ML a cada 15 s olhando só os últimos 2 min (ML_DEMO_MINUTOS), para o painel acompanhar a troca de copo.
# Cada serviço roda num laço: se cair, volta em 10 s (quedas em .demo_logs/reinicios.log).
# O serviço de alertas sobe junto e só envia com a URL do webhook preenchida no painel (Configurações).
# Uso: bash ferramentas/demonstracao.sh      Senha do painel: SENHA_PAINEL (padrão abaixo).
R="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
L="$R/.demo_logs"; mkdir -p "$L"
export PYTHONIOENCODING=utf-8 ML_INTERVALO_S=${ML_INTERVALO_S:-15} ML_DEMO_MINUTOS=${ML_DEMO_MINUTOS:-2} API_PORTA=8000
export API_JWT_SEGREDO=$(python -c "import secrets;print(secrets.token_urlsafe(48))")
SENHA_PAINEL="${SENHA_PAINEL:-piscicultura2026}"
if ls "$L"/*.log > /dev/null 2>&1; then
  A="$L/arquivo-$(date '+%Y-%m-%d_%H%M%S')"; mkdir -p "$A"; mv "$L"/*.log "$A"/
fi

sempre() {  # sempre <nome> <pasta> <comando...>: reinicia o serviço quando ele sai
  local nome=$1 pasta=$2; shift 2
  while true; do
    echo "$(date '+%F %T') $nome iniciado" >> "$L/reinicios.log"
    ( cd "$pasta" && "$@" ) >> "$L/$nome.log" 2>&1
    echo "$(date '+%F %T') $nome saiu (rc=$?), reiniciando em 10 s" >> "$L/reinicios.log"
    sleep 10
  done
}

cd "$R/backend"
docker compose up -d timescaledb > "$L/docker.log" 2>&1 || { echo "Docker não subiu o banco (Docker Desktop aberto?)"; cat "$L/docker.log"; exit 1; }
for i in $(seq 1 30); do docker compose exec -T timescaledb pg_isready -q && break; sleep 2; done
.venv/Scripts/python.exe -m alembic upgrade head > "$L/migracoes.log" 2>&1 || { echo "falha nas migrações"; cat "$L/migracoes.log"; exit 1; }
.venv/Scripts/python.exe -m src.db.seed > "$L/seed.log" 2>&1 || { echo "falha no seed"; cat "$L/seed.log"; exit 1; }
SENHA_PAINEL="$SENHA_PAINEL" .venv/Scripts/python.exe -c "
import os
from src.config import Settings
from src.db.session import criar_engine, criar_session_factory
from src.api.usuarios import definir_usuario
S=criar_session_factory(criar_engine(Settings()))
with S() as s:
    definir_usuario(s,'teste@tcc.local',os.environ['SENHA_PAINEL'],nome='Demonstração',perfil='admin'); s.commit()
" > "$L/usuario.log" 2>&1 || { echo "falha ao criar usuário"; cat "$L/usuario.log"; exit 1; }

sempre ingestao "$R/backend" .venv/Scripts/python.exe -u -m src.main &
for i in $(seq 1 30); do grep -q assinando "$L/ingestao.log" 2>/dev/null && break; sleep 1; done
sempre api "$R/backend" .venv/Scripts/python.exe -u -m src.api &
sempre ml "$R/ml" .venv/Scripts/python.exe -u -m src.servico &
sempre alertas "$R/ml" .venv/Scripts/python.exe -u -m src.servico.alertas &
sempre painel "$R/dashboard" npx vite --port 5173 --strictPort &
echo "sistema no ar: painel em http://localhost:5173 (teste@tcc.local / $SENHA_PAINEL); logs em $L"
wait
