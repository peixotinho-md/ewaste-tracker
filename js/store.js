/**
 * store.js — Camada de acesso a dados do e-Trilha MS.
 *
 * ESTA É A ÚNICA PORTA DE DADOS DA APLICAÇÃO.
 * Nenhuma tela fala com o servidor diretamente.
 *
 * Na primeira versão do protótipo, as funções daqui liam e gravavam no
 * `localStorage` do navegador. Todas já eram assíncronas justamente para que a
 * troca pelo servidor não exigisse mexer em nenhuma tela — e foi exatamente o
 * que aconteceu: só o corpo destas funções mudou, de acesso local para chamadas
 * HTTP à API em `backend/app.py`. As páginas continuam iguais.
 *
 * Os dados agora ficam no SQLite do servidor, e não mais no navegador: dois
 * computadores diferentes enxergam a mesma cadeia de custódia.
 */

const BASE = '/api';

/**
 * Faz a chamada HTTP e traduz a resposta.
 *
 * Erros de regra de negócio chegam como HTTP 400 com `{"erro": "..."}` — a
 * mensagem já vem pronta do servidor e é a mesma que a tela exibe. Quem decide
 * o que é permitido é o servidor, não o navegador: qualquer pessoa consegue
 * chamar a API por fora da tela.
 */
async function api(caminho, { metodo = 'GET', corpo = null, nuloEm404 = false } = {}) {
  let resposta;
  try {
    resposta = await fetch(BASE + caminho, {
      method: metodo,
      // Envia o cookie de sessão, que identifica o usuário logado ou o visitante.
      credentials: 'same-origin',
      headers: corpo ? { 'Content-Type': 'application/json' } : undefined,
      body: corpo ? JSON.stringify(corpo) : undefined,
    });
  } catch {
    throw new Error(
      'Sem conexão com o servidor. Confira se o e-Trilha MS está em execução ' +
      '(python backend/app.py).'
    );
  }

  const dados = await resposta.json().catch(() => null);

  if (!resposta.ok) {
    if (nuloEm404 && resposta.status === 404) return null;
    throw new Error(dados?.erro ?? `O servidor respondeu com erro ${resposta.status}.`);
  }
  return dados;
}

/** Ping usado pelo cabeçalho para avisar quando o servidor está fora do ar. */
export async function verificarServidor() {
  try {
    return await api('/saude');
  } catch {
    return null;
  }
}

/* ------------------------------------------------------------------ *
 * Pontos de coleta
 * ------------------------------------------------------------------ */

export async function listarPontos() {
  return api('/pontos');
}

/** Municípios distintos que têm ponto cadastrado, em ordem alfabética. */
export async function listarMunicipiosComPonto() {
  const pontos = await listarPontos();
  return [...new Set(pontos.map((p) => p.municipio))].sort((a, b) =>
    a.localeCompare(b, 'pt-BR')
  );
}

/* ------------------------------------------------------------------ *
 * Itens (dispositivos)
 * ------------------------------------------------------------------ */

export async function listarItens() {
  return api('/itens');
}

/** Todos os eventos — usado pelo painel de indicadores. */
export async function listarTodosEventos() {
  return api('/eventos');
}

export async function obterItem(codigo) {
  return api(`/itens/${encodeURIComponent(codigo)}`, { nuloEm404: true });
}

/**
 * Tudo que a tela de rastreio precisa numa chamada só: o item, seus eventos já
 * ordenados e o ponto de coleta de cada evento resolvido pelo servidor.
 */
export async function obterRastreio(codigo) {
  return api(`/itens/${encodeURIComponent(codigo)}/rastreio`, { nuloEm404: true });
}

/**
 * Cadastra um dispositivo. O servidor gera o código de rastreio e grava o
 * evento REGISTRADO na mesma transação.
 */
export async function criarItem({ categoria, marca, pesoKg, pontoOrigemId, responsavel }) {
  return api('/itens', {
    metodo: 'POST',
    corpo: { categoria, marca, pesoKg, pontoOrigemId, responsavel },
  });
}

/**
 * Registra o avanço do item para a próxima etapa.
 *
 * A validação da transição roda NO SERVIDOR, dentro da transação e sobre a
 * etapa lida do banco. Se for recusada, a mensagem do servidor sobe como erro
 * e a tela apenas a exibe.
 */
export async function registrarEvento(codigo, { etapa, pontoId, responsavel, observacao }) {
  return api(`/itens/${encodeURIComponent(codigo)}/eventos`, {
    metodo: 'POST',
    corpo: { etapa, pontoId, responsavel, observacao },
  });
}

/* ------------------------------------------------------------------ *
 * Conta (opcional) e sessão
 *
 * O cookie de sessão identifica tanto o usuário logado quanto o visitante sem
 * conta. Por isso `meusItens` serve aos dois casos: o servidor sabe de quem
 * são os itens sem que a tela precise informar.
 * ------------------------------------------------------------------ */

export async function usuarioAtual() {
  try {
    const { usuario } = await api('/sessao');
    return usuario;
  } catch {
    // Cabeçalho não pode quebrar a página por causa de um servidor fora do ar.
    return null;
  }
}

export async function meusItens() {
  return api('/meus-itens');
}

export async function cadastrarUsuario({ nome, email, senha }) {
  return api('/usuarios', { metodo: 'POST', corpo: { nome, email, senha } });
}

export async function abrirSessao({ email, senha }) {
  return api('/sessao', { metodo: 'POST', corpo: { email, senha } });
}

export async function encerrarSessao() {
  return api('/sessao', { metodo: 'DELETE' });
}

/* ------------------------------------------------------------------ *
 * Demonstração
 * ------------------------------------------------------------------ */

/** Recria o banco do servidor com os dados de exemplo. */
export async function reiniciar() {
  return api('/demo/reiniciar', { metodo: 'POST' });
}
