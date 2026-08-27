-- ==========================================================================
-- e-Trilha MS — esquema do banco (SQLite)
-- ==========================================================================

PRAGMA foreign_keys = ON;

-- Versão do esquema. `banco.preparar()` recria o banco quando a versão gravada
-- no arquivo é diferente desta. Como os dados são de demonstração e vêm de
-- dados/*.json, recriar é mais simples e mais seguro do que migrar.
PRAGMA user_version = 6;

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
-- O papel decide o que a conta pode fazer:
--
--   visitante  registra os próprios aparelhos e consulta — é o padrão de quem
--              se cadastra pela tela;
--   operador   além disso, ESCREVE na cadeia de custódia pelo leitor de QR;
--   admin      concede e revoga o papel de operador e redefine senhas.
--
-- O padrão é `visitante` de propósito: ninguém ganha poder de escrita só por
-- criar uma conta. Quem promove é um admin, e a promoção fica registrada em
-- `alteracoes_conta`.
--
-- `ponto_id` amarra o operador ao local onde ele trabalha. O servidor usa esse
-- vínculo para carimbar o evento, em vez de aceitar o local que a tela mandou.
CREATE TABLE usuarios (
  id         TEXT PRIMARY KEY,
  nome       TEXT NOT NULL,
  email      TEXT NOT NULL UNIQUE COLLATE NOCASE,
  senha_hash TEXT NOT NULL,
  criado_em  TEXT NOT NULL,
  papel      TEXT NOT NULL DEFAULT 'visitante'
             CHECK (papel IN ('visitante', 'operador', 'admin')),
  ponto_id   TEXT REFERENCES pontos (id) ON DELETE SET NULL,

  -- 1 enquanto a senha em vigor tiver sido definida por OUTRA PESSOA: a
  -- sorteada na carga inicial e a redefinida por um admin. Nos dois casos
  -- existe alguém, além do dono, que conhece a senha — e enquanto isso for
  -- verdade a conta não prova quem a está usando. O servidor então só aceita
  -- desta conta a própria troca de senha, até que o dono escolha a dele.
  --
  -- Quem se cadastra pela tela escolhe a senha na hora, e nasce com 0.
  senha_provisoria INTEGER NOT NULL DEFAULT 0 CHECK (senha_provisoria IN (0, 1))
);

CREATE INDEX idx_usuarios_papel ON usuarios (papel);

-- --------------------------------------------------------------------------
-- Trilha de administração das contas
--
-- Promover alguém a operador é dar poder de escrever no histórico dos
-- aparelhos. Essa concessão precisa da mesma prestação de contas que ela
-- protege: quem alterou, o que alterou e quando. Também é somente de
-- acréscimo, pelos mesmos gatilhos usados nos eventos.
--
-- `de` e `para` guardam o valor antigo e o novo. Numa troca de senha ficam
-- vazios: o que importa registrar é que houve redefinição, nunca o segredo.
--
-- O NOME de quem foi alterado e de quem alterou é copiado para cá no momento
-- do registro, e as colunas de id NÃO têm chave estrangeira. É deliberado: uma
-- trilha de auditoria não pode depender da existência da linha que ela
-- descreve. Com FK, excluir uma conta seria recusado pelo banco — ou, pior,
-- apagaria em cascata justamente o registro de que ela existiu. Do jeito que
-- está, a conta pode ser excluída e a trilha continua legível, dizendo quem
-- era e o que foi feito.
-- --------------------------------------------------------------------------
CREATE TABLE alteracoes_conta (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  alvo_id     TEXT,
  alvo_nome   TEXT NOT NULL,
  autor_id    TEXT,
  autor_nome  TEXT NOT NULL,
  acao        TEXT NOT NULL,
  de          TEXT NOT NULL DEFAULT '',
  para        TEXT NOT NULL DEFAULT '',
  em          TEXT NOT NULL
);

CREATE INDEX idx_alteracoes_alvo ON alteracoes_conta (alvo_id, em);

CREATE TRIGGER alteracoes_sem_update
BEFORE UPDATE ON alteracoes_conta
BEGIN
  SELECT RAISE(ABORT, 'A trilha de administração é somente de acréscimo: alterar é proibido.');
END;

CREATE TRIGGER alteracoes_sem_delete
BEFORE DELETE ON alteracoes_conta
BEGIN
  SELECT RAISE(ABORT, 'A trilha de administração é somente de acréscimo: apagar é proibido.');
END;

-- --------------------------------------------------------------------------
-- Itens (dispositivos descartados)
--
-- Todo item tem dono: registrar exige conta. `dono_id` é o que separa "meus
-- aparelhos" dos aparelhos de outra pessoa — a consulta pública pelo código
-- continua aberta, mas a LISTAGEM é sempre a do dono.
--
-- ON DELETE SET NULL: excluir a conta não apaga o aparelho. O histórico da
-- cadeia de custódia é somente de acréscimo e vale por si; o que se perde é o
-- vínculo com a pessoa, que é justamente o dado pessoal.
-- --------------------------------------------------------------------------
CREATE TABLE itens (
  codigo          TEXT PRIMARY KEY,
  categoria       TEXT NOT NULL,
  marca           TEXT NOT NULL DEFAULT '',
  peso_kg         REAL NOT NULL CHECK (peso_kg > 0),
  dono_id         TEXT REFERENCES usuarios (id) ON DELETE SET NULL,
  ponto_origem_id TEXT REFERENCES pontos (id),
  criado_em       TEXT NOT NULL,
  atualizado_em   TEXT NOT NULL,
  etapa_atual     TEXT NOT NULL,
  demo            INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX idx_itens_dono      ON itens (dono_id);
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
-- --------------------------------------------------------------------------
-- Atestado de apagamento seguro
--
-- Aparelhos com memória não volátil saem de casa ou da empresa com dados
-- dentro. Na triagem, quem recebe declara QUAL é a mídia e COMO os dados foram
-- destruídos — e o método precisa ser eficaz para aquele tipo de mídia
-- (ver backend/modelo.py). Uma linha por item, e nunca mais alterada.
-- --------------------------------------------------------------------------
CREATE TABLE apagamentos (
  item_codigo TEXT PRIMARY KEY REFERENCES itens (codigo) ON DELETE RESTRICT,
  midia       TEXT NOT NULL,
  metodo      TEXT NOT NULL,
  responsavel TEXT NOT NULL DEFAULT '',
  em          TEXT NOT NULL
);

CREATE TRIGGER apagamentos_sem_update
BEFORE UPDATE ON apagamentos
BEGIN
  SELECT RAISE(ABORT, 'O atestado de apagamento é definitivo: alterar é proibido.');
END;

CREATE TRIGGER apagamentos_sem_delete
BEFORE DELETE ON apagamentos
BEGIN
  SELECT RAISE(ABORT, 'O atestado de apagamento é definitivo: apagar é proibido.');
END;

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
