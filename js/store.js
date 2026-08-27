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
      // Envia o cookie de sessão, que é o que identifica o usuário logado.
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
    const erro = new Error(dados?.erro ?? `O servidor respondeu com erro ${resposta.status}.`);
    // 401 (falta entrar) e 403 (entrou, mas a conta não tem o papel) pedem
    // respostas diferentes da tela, então o status sobe junto com a mensagem.
    erro.status = resposta.status;
    throw erro;
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

/**
 * Conjunto que alimenta o painel de indicadores e os números da home.
 *
 * Não existe chamada que devolva "todos os itens": uma conta comum só enxerga
 * os próprios aparelhos. O que vem daqui é o recorte que o servidor considera
 * seguro mostrar — sem código e sem dono para quem não é operador —, junto de
 * `detalhado`, que diz se os aparelhos vieram identificados.
 */
export async function painel() {
  return api('/painel');
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
 * Registra o avanço do item para a próxima etapa. Exige conta de operador.
 *
 * A validação da transição roda NO SERVIDOR, dentro da transação e sobre a
 * etapa lida do banco. Se for recusada, a mensagem do servidor sobe como erro
 * e a tela apenas a exibe.
 *
 * O responsável NÃO é enviado daqui: quem assina o evento é a conta
 * autenticada, e quem preenche esse campo é o servidor. Um nome digitado na
 * tela não provaria nada sobre quem realmente registrou a passagem.
 */
export async function registrarEvento(
  codigo,
  { etapa, pontoId, observacao, apagamento = null }
) {
  return api(`/itens/${encodeURIComponent(codigo)}/eventos`, {
    metodo: 'POST',
    // `apagamento` só é usado ao concluir a triagem de um aparelho com mídia
    // de dados; nas demais etapas o servidor ignora o campo.
    corpo: { etapa, pontoId, observacao, apagamento },
  });
}

/* ------------------------------------------------------------------ *
 * Conta e sessão
 *
 * A conta é OBRIGATÓRIA para tudo o que lista ou grava: registrar um aparelho,
 * imprimir etiquetas, ver "meus aparelhos", ler QR e administrar. Fica de fora
 * uma coisa só, de propósito — CONSULTAR A TRILHA POR CÓDIGO. Quem entregou um
 * celular no ecoponto tem a etiqueta na mão e não deve precisar de cadastro
 * para ver onde o aparelho está: é exatamente o que o projeto promete.
 *
 * A autenticação acontece INTEIRA NO SERVIDOR. Daqui só sai o que o formulário
 * preencheu; nada aqui vê ou guarda senha, nem decide quem está logado. A senha
 * vai para o servidor, que a guarda com PBKDF2 (sal aleatório e milhares de
 * iterações), e a sessão volta como cookie assinado e HttpOnly — que o
 * JavaScript da página não consegue ler, o que limita o estrago de um XSS.
 * Continua faltando HTTPS, necessário em uso real para a senha não trafegar em
 * texto claro na rede.
 *
 * `meusItens` não recebe parâmetro de propósito: quem é o dono sai do cookie
 * de sessão, no servidor. Se a tela informasse o id do dono, bastaria trocá-lo
 * na chamada para ver os aparelhos de outra pessoa.
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
  // As três verificações abaixo existem só para responder rápido a quem está
  // digitando. As que valem são as do servidor, que roda as mesmas — a tela
  // valida para ajudar, o servidor valida para valer.
  if (!nome?.trim()) throw new Error('Informe seu nome.');
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email ?? '')) throw new Error('E-mail inválido.');
  if ((senha ?? '').length < 6) throw new Error('A senha precisa ter ao menos 6 caracteres.');

  return api('/usuarios', {
    metodo: 'POST',
    corpo: { nome: nome.trim(), email: email.trim(), senha },
  });
}

export async function abrirSessao({ email, senha }) {
  return api('/sessao', { metodo: 'POST', corpo: { email: (email ?? '').trim(), senha } });
}

export async function encerrarSessao() {
  return api('/sessao', { metodo: 'DELETE' });
}

/* ------------------------------------------------------------------ *
 * Administração de contas
 *
 * Todas estas chamadas exigem papel `admin`, e quem verifica isso é o
 * servidor. A tela de administração some do menu para quem não é admin, mas é
 * o 403 do servidor que de fato fecha a porta.
 * ------------------------------------------------------------------ */

export async function listarUsuarios() {
  return api('/admin/usuarios');
}

/**
 * Altera papel, ponto vinculado ou senha de uma conta.
 *
 * Só vão no corpo os campos realmente informados: mandar `pontoId: null` sem
 * querer desvincularia o operador do posto dele.
 */
export async function atualizarUsuario(id, mudancas) {
  return api(`/admin/usuarios/${encodeURIComponent(id)}`, {
    metodo: 'PATCH',
    corpo: mudancas,
  });
}

/**
 * Todos os aparelhos com etapa, ponto de origem, dono e nº de leituras.
 *
 * `painel()` serve os indicadores com os dados anonimizados; esta versão traz
 * o cruzamento identificado que só a administração usa.
 */
export async function listarItensAdmin() {
  return api('/admin/itens');
}

/**
 * Exclui uma conta. Exige a senha de quem está excluindo — é a única ação da
 * tela de administração que não tem volta.
 */
export async function excluirUsuario(id, senha) {
  return api(`/admin/usuarios/${encodeURIComponent(id)}`, {
    metodo: 'DELETE',
    corpo: { senha },
  });
}

/** Trilha inteira, ou só a de uma conta quando `usuarioId` é informado. */
export async function listarAlteracoes(usuarioId = null) {
  const consulta = usuarioId ? `?usuario=${encodeURIComponent(usuarioId)}` : '';
  return api(`/admin/alteracoes${consulta}`);
}

/* ------------------------------------------------------------------ *
 * Demonstração
 * ------------------------------------------------------------------ */

/**
 * Recria o banco do servidor com os dados de exemplo. Exige conta de admin.
 *
 * A resposta NÃO traz as senhas novas: elas saem no terminal do servidor. Mandar
 * senha pela rede contradiria o motivo de não gravá-la em arquivo, e aqui ainda
 * não há HTTPS.
 */
export async function reiniciar() {
  return api('/demo/reiniciar', { metodo: 'POST' });
}

/* ------------------------------------------------------------------ *
 * Papéis
 *
 * Estas funções servem para a TELA decidir o que mostrar — esconder um botão
 * que não vai funcionar é gentileza com o usuário, não segurança. Quem impede
 * de fato é o servidor, que confere o papel a cada requisição e responde 401
 * ou 403. Por isso nada aqui guarda o papel: ele vem do servidor a cada
 * consulta, e uma revogação passa a valer na hora.
 * ------------------------------------------------------------------ */

export const PAPEIS = {
  visitante: { rotulo: 'Visitante', descricao: 'Registra e acompanha os próprios aparelhos, e mais nada.' },
  operador: { rotulo: 'Operador', descricao: 'Registra a passagem dos aparelhos pelas etapas.' },
  admin: { rotulo: 'Administrador', descricao: 'Gerencia as contas e os papéis.' },
};

/** Pode gravar na cadeia de custódia (ler QR e avançar etapa)? */
export const podeOperar = (usuario) =>
  usuario?.papel === 'operador' || usuario?.papel === 'admin';

export const ehAdmin = (usuario) => usuario?.papel === 'admin';

/**
 * Guarda de página: devolve o usuário quando ele tem um dos papéis pedidos, ou
 * `null` quando não tem — cabe à página desenhar o convite para entrar.
 */
export async function exigirPapel(...papeis) {
  const usuario = await usuarioAtual();
  return usuario && papeis.includes(usuario.papel) ? usuario : null;
}
