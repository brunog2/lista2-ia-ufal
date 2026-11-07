#!/usr/bin/env bash
# Sobe um Neo4j temporário (sem autenticação, sem porta exposta), carrega o grafo,
# roda as consultas, grava a saída e remove o container. Uso: bash validar_neo4j.sh
set -euo pipefail
cd "$(dirname "$0")"
NOME=q14-neo4j-validacao
IMAGEM=neo4j:5.26-community
trap 'docker rm -f "$NOME" >/dev/null 2>&1 || true' EXIT

docker run -d --name "$NOME" -e NEO4J_AUTH=none "$IMAGEM" >/dev/null
until docker exec "$NOME" cypher-shell "RETURN 1" >/dev/null 2>&1; do sleep 2; done

{
  echo "# Validação no $IMAGEM em $(date -I)"
  docker exec -i "$NOME" cypher-shell --format plain < arboviroses.cypher
  docker exec "$NOME" cypher-shell --format plain \
    "MATCH (n:Entidade) WITH count(n) AS entidades MATCH (c:Classe) WITH entidades, count(c) AS classes
     MATCH ()-[r]->() RETURN entidades, classes, count(r) AS relacoes"
  docker exec -i "$NOME" cypher-shell --format plain < consultas.cypher
} | tee saida_validacao.txt
