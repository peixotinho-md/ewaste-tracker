/**
 * auth.js — Conta de usuário OPCIONAL.
 *
 * Nada no fluxo principal exige login: registrar um dispositivo, imprimir a
 * etiqueta, ler o QR e consultar o rastreio funcionam como visitante. A conta
 * serve só para reunir num lugar só os aparelhos que a pessoa já enviou.
 *
 * A autenticação acontece INTEIRA NO SERVIDOR. Este arquivo só encaminha o que
 * o formulário preencheu e devolve a resposta; ele não vê nem guarda senha, e
 * não decide quem está logado.
 *
 * O que mudou da versão sem back-end:
 *
 *   antes  a senha virava um hash SHA-256 no próprio navegador e ficava no
 *          localStorage — rápido de quebrar e visível para quem tivesse acesso
 *          à máquina;
 *   agora  a senha vai para o servidor, que a guarda com PBKDF2 (sal aleatório
 *          e milhares de iterações), e a sessão é um cookie assinado, marcado
 *          como HttpOnly — ou seja, o JavaScript da página não consegue lê-lo,
 *          o que limita o estrago de uma falha de XSS.
 *
 * Continua faltando HTTPS: em uso real, a senha não pode trafegar em texto
 * claro. Na demonstração isso não é problema porque tudo acontece dentro da
 * própria máquina (localhost).
 */

import * as store from './store.js';

export async function cadastrar({ nome, email, senha }) {
  // As validações abaixo existem só para responder rápido ao usuário.
  // As que valem são as do servidor, que roda as mesmas verificações.
  if (!nome?.trim()) throw new Error('Informe seu nome.');
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email ?? '')) throw new Error('E-mail inválido.');
  if ((senha ?? '').length < 6) throw new Error('A senha precisa ter ao menos 6 caracteres.');

  return store.cadastrarUsuario({ nome: nome.trim(), email: email.trim(), senha });
}

export async function entrar({ email, senha }) {
  return store.abrirSessao({ email: (email ?? '').trim(), senha });
}

export async function sair() {
  await store.encerrarSessao();
}

export const atual = store.usuarioAtual;

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
  visitante: { rotulo: 'Visitante', descricao: 'Registra e consulta os próprios aparelhos.' },
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
  const usuario = await atual();
  return usuario && papeis.includes(usuario.papel) ? usuario : null;
}
