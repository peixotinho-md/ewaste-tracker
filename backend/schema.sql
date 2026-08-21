-- ==========================================================================
-- e-Trilha MS — esquema do banco (SQLite)
-- ==========================================================================

PRAGMA foreign_keys = ON;

-- --------------------------------------------------------------------------
-- Pontos de coleta
-- --------------------------------------------------------------------------
CREATE TABLE pontos (
  id         TEXT PRIMARY KEY,
  nome       TEXT NOT NULL,
  tipo       TEXT NOT NULL,
  municipio  TEXT NOT NULL,
  endereco   TEXT,
  lat        REAL NOT NULL,
  lng        REAL NOT NULL,
  aceita     TEXT NOT NULL,   -- lista de categorias em JSON
  horario    TEXT,
  telefone   TEXT
);

CREATE INDEX idx_pontos_municipio ON pontos (municipio);

-- --------------------------------------------------------------------------
-- Usuários (a conta é opcional em todo o fluxo)
-- --------------------------------------------------------------------------
CREATE TABLE usuarios (
  id         TEXT PRIMARY KEY,
  nome       TEXT NOT NULL,
  email      TEXT NOT NULL UNIQUE COLLATE NOCASE,
  senha_hash TEXT NOT NULL,
  criado_em  TEXT NOT NULL
);

-- --------------------------------------------------------------------------
-- Itens (dispositivos descartados)
--
-- Um item pertence a um usuário (dono_id) OU a um visitante sem conta
-- (visitante_id, guardado no cookie de sessão). Ao criar conta, os itens do
-- visitante são adotados pelo usuário.
-- --------------------------------------------------------------------------
CREATE TABLE itens (
  codigo          TEXT PRIMARY KEY,
  categoria       TEXT NOT NULL,
  marca           TEXT NOT NULL DEFAULT '',
  peso_kg         REAL NOT NULL CHECK (peso_kg > 0),
  dono_id         TEXT REFERENCES usuarios (id) ON DELETE SET NULL,
  visitante_id    TEXT,
  ponto_origem_id TEXT REFERENCES pontos (id),
  criado_em       TEXT NOT NULL,
  atualizado_em   TEXT NOT NULL,
  etapa_atual     TEXT NOT NULL,
  demo            INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX idx_itens_dono      ON itens (dono_id);
CREATE INDEX idx_itens_visitante ON itens (visitante_id);
CREATE INDEX idx_itens_etapa     ON itens (etapa_atual);

-- --------------------------------------------------------------------------
-- Eventos — a cadeia de custódia propriamente dita
-- --------------------------------------------------------------------------
CREATE TABLE eventos (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  item_codigo TEXT NOT NULL REFERENCES itens (codigo) ON DELETE RESTRICT,
  etapa       TEXT NOT NULL,
  ponto_id    TEXT REFERENCES pontos (id),
  responsavel TEXT NOT NULL DEFAULT '',
  observacao  TEXT NOT NULL DEFAULT '',
  em          TEXT NOT NULL
);

CREATE INDEX idx_eventos_item ON eventos (item_codigo, em);

-- --------------------------------------------------------------------------
-- O histórico é SOMENTE DE ACRÉSCIMO, e quem garante isso é o banco.
--
-- Não adianta a aplicação prometer que não reescreve eventos: um bug, um
-- script de manutenção ou alguém com acesso ao banco poderiam apagar a prova
-- de que um aparelho passou por uma etapa. Estes gatilhos recusam qualquer
-- UPDATE ou DELETE na tabela de eventos, no nível do próprio SQLite.
--
-- (DROP TABLE não dispara gatilhos, e é por isso que reiniciar a demonstração
--  recria o banco inteiro em vez de apagar linhas.)
-- --------------------------------------------------------------------------
CREATE TRIGGER eventos_sem_update
BEFORE UPDATE ON eventos
BEGIN
  SELECT RAISE(ABORT, 'O histórico de eventos é somente de acréscimo: alterar é proibido.');
END;

CREATE TRIGGER eventos_sem_delete
BEFORE DELETE ON eventos
BEGIN
  SELECT RAISE(ABORT, 'O histórico de eventos é somente de acréscimo: apagar é proibido.');
END;
