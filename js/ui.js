/**
 * ui.js — Peças de interface compartilhadas entre as páginas.
 * Cabeçalho, avisos, formatação e o componente de linha do tempo do rastreio.
 */

import { ETAPAS, etapa as definicaoEtapa, indiceEtapa, categoria } from './model.js';
import * as store from './store.js';

/* ------------------------------------------------------------------ *
 * Formatação
 * ------------------------------------------------------------------ */

const fmtData = new Intl.DateTimeFormat('pt-BR', {
  day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
});

export const formatarData = (iso) => (iso ? fmtData.format(new Date(iso)) : '—');

export function formatarNumero(valor, casas = 1) {
  if (valor == null || Number.isNaN(valor)) return '—';
  return valor.toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas });
}

/** Escolhe a unidade legível: 480 g, 3,2 kg, 1,4 t. */
export function formatarMassa(kg) {
  if (kg == null || Number.isNaN(kg)) return '—';
  if (kg >= 1000) return `${formatarNumero(kg / 1000, 2)} t`;
  if (kg < 1) return `${formatarNumero(kg * 1000, 0)} g`;
  return `${formatarNumero(kg, 1)} kg`;
}

/** Massa de ouro, sempre em miligramas ou gramas. */
export function formatarOuro(kg) {
  const g = kg * 1000;
  return g < 1 ? `${formatarNumero(g * 1000, 0)} mg` : `${formatarNumero(g, 2)} g`;
}

export function formatarDuracao(horas) {
  if (horas == null || Number.isNaN(horas)) return '—';
  if (horas < 1) return `${Math.round(horas * 60)} min`;
  if (horas < 48) return `${formatarNumero(horas, 1)} h`;
  return `${formatarNumero(horas / 24, 1)} dias`;
}

/** Escapa texto vindo do usuário antes de inseri-lo com innerHTML. */
export function escapar(texto) {
  return String(texto ?? '').replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])
  );
}

/* ------------------------------------------------------------------ *
 * Cabeçalho e navegação
 * ------------------------------------------------------------------ */

// `visivel` é o teste que a entrada precisa passar para entrar no menu. Sem
// ele, a página vale para qualquer conta. Esconder o link é conveniência: quem
// digitar o endereço direto esbarra no servidor, que não entrega a página nem
// atende a API sem o papel.
const PAGINAS = [
  { href: '/', rotulo: 'Início' },
  { href: 'registrar', rotulo: 'Registrar aparelho' },
  // Ler o QR é ESCREVER na cadeia de custódia de um aparelho que é de outra
  // pessoa. Para quem não pode operar, a aba só levaria a uma tela recusada.
  { href: 'scanner', rotulo: 'Ler QR', visivel: store.podeOperar },
  { href: 'rastrear', rotulo: 'Rastrear' },
  { href: 'pontos', rotulo: 'Pontos de coleta' },
  { href: 'painel', rotulo: 'Painel' },
  { href: 'admin', rotulo: 'Administração', visivel: store.ehAdmin },
];

async function montarCabecalho() {
  const alvo = document.querySelector('[data-cabecalho]');
  if (!alvo) return;

  const atualPath = location.pathname.split('/').pop() || '/';
  const usuario = await store.usuarioAtual();

  // Nas telas públicas — a porta de entrada, a consulta e a trilha — quem não
  // entrou vê um cabeçalho sem menu: todo link dali levaria a uma página que o
  // servidor não entrega sem sessão, e oferecer caminho fechado é ruído. Vale
  // também para quem entrou com senha provisória: a sessão existe, mas está
  // presa à troca de senha, e o menu inteiro voltaria para a raiz.
  if (!usuario || usuario.senhaProvisoria) {
    alvo.innerHTML = `
      <a class="marca" href="/">
        <span class="marca-simbolo" aria-hidden="true">♻</span>
        <span><strong>e-Trilha</strong> MS</span>
      </a>
      <a class="conta-link" href="/">Entrar ou criar conta</a>`;
    return;
  }

  const paginas = PAGINAS.filter((p) => !p.visivel || p.visivel(usuario));

  const links = paginas.map(
    (p) =>
      `<a href="${p.href}"${p.href === atualPath ? ' aria-current="page"' : ''}>${p.rotulo}</a>`
  ).join('');

  alvo.innerHTML = `
    <a class="marca" href="/">
      <span class="marca-simbolo" aria-hidden="true">♻</span>
      <span><strong>e-Trilha</strong> MS</span>
    </a>
    <nav aria-label="Navegação principal">${links}</nav>
    <a class="conta-link" href="conta">
      <span class="avatar" aria-hidden="true">${escapar(usuario.nome[0].toUpperCase())}</span>
      ${escapar(usuario.nome.split(' ')[0])}
      ${usuario.papel !== 'visitante' ? seloPapel(usuario.papel) : ''}
    </a>`;
}

/**
 * Preenche o rodapé, que era a mesma linha copiada em oito arquivos — e já
 * tinha divergido em dois textos diferentes, que é o que sempre acontece com
 * um conteúdo repetido à mão. Agora existe num lugar só.
 *
 * A marca `nao-imprimir` fica no HTML de cada página, e não aqui: quem decide
 * se o rodapé sai no papel é a página (a folha de etiquetas não quer), não o
 * componente.
 */
function montarRodape() {
  const alvo = document.querySelector('[data-rodape]');
  if (alvo) alvo.textContent = 'e-Trilha MS · Protótipo acadêmico — DAC 262 TADS.';
}

/* ------------------------------------------------------------------ *
 * Avisos
 * ------------------------------------------------------------------ */

export function aviso(mensagem, tipo = 'ok') {
  let caixa = document.querySelector('.avisos');
  if (!caixa) {
    caixa = document.createElement('div');
    caixa.className = 'avisos';
    caixa.setAttribute('role', 'status');
    caixa.setAttribute('aria-live', 'polite');
    document.body.append(caixa);
  }
  const item = document.createElement('div');
  item.className = `aviso aviso-${tipo}`;
  item.textContent = mensagem;
  caixa.append(item);
  setTimeout(() => item.classList.add('saindo'), 4200);
  setTimeout(() => item.remove(), 4800);
}

/** Selo com o papel da conta. Visitante não recebe selo: é o normal. */
export function seloPapel(papel) {
  const def = store.PAPEIS[papel];
  if (!def) return '';
  return `<span class="selo selo-papel selo-${papel}">${escapar(def.rotulo)}</span>`;
}

/* ------------------------------------------------------------------ *
 * Confirmação de ação definitiva
 * ------------------------------------------------------------------ */

/**
 * Abre um `<dialog>` modal e resolve com o que a pessoa respondeu.
 *
 * É a máquina compartilhada por `confirmar()` e `confirmarComSenha()`, que
 * eram duas cópias da mesma coisa: montar o diálogo, garantir UMA resposta,
 * fechar e limpar. O que muda entre as duas é só o miolo do formulário e o que
 * conta como "sim" — e é isso que os parâmetros descrevem.
 *
 * A resposta é dada no CLIQUE, e não no evento `close` do diálogo: assim a
 * promessa não depende da entrega assíncrona desse evento, que se mostrou pouco
 * confiável em navegador sem interface (usado nos testes). O guarda
 * `respondido` garante uma resposta só, venha ela do botão, do Esc ou do close.
 *
 * @param {string} titulo    cabeçalho do diálogo.
 * @param {string} corpo     HTML já montado por quem chamou.
 * @param {string} alerta    faixa vermelha opcional.
 * @param {string} miolo     HTML entre o alerta e os botões.
 * @param {string} textoOk   rótulo do botão que confirma.
 * @param {string} textoNao  rótulo do botão que desiste.
 * @param {string} classeOk  classe extra do botão que confirma.
 * @param {*}      recusa    valor com que a promessa resolve ao desistir.
 * @param {Function} aoAbrir recebe o diálogo e devolve `() => valor do "sim"`.
 */
function dialogo({ titulo, corpo = '', alerta = '', miolo = '', textoOk, textoNao,
                   classeOk = '', recusa, aoAbrir }) {
  return new Promise((resolver) => {
    const caixa = document.createElement('dialog');
    caixa.className = 'confirmacao';
    caixa.innerHTML = `
      <h2>${escapar(titulo)}</h2>
      ${corpo}
      ${alerta ? `<div class="faixa faixa-alerta">${alerta}</div>` : ''}
      ${miolo}
      <div class="botoes confirmacao-botoes">
        <button class="botao botao-secundario" type="button" data-resposta="nao">${escapar(textoNao)}</button>
        <button class="botao ${classeOk}" type="button" data-resposta="sim">${escapar(textoOk)}</button>
      </div>`;

    let respondido = false;
    const responder = (valor) => {
      if (respondido) return;
      respondido = true;
      if (caixa.open) caixa.close();
      caixa.remove();
      resolver(valor);
    };

    document.body.append(caixa);
    caixa.showModal();

    // `aoAbrir` monta o que é específico de cada diálogo e devolve como ler o
    // "sim". Roda DEPOIS de `showModal()`, e não antes, porque é onde cada um
    // escolhe quem recebe o foco: `showModal()` foca sozinho o primeiro
    // elemento focável — o botão de cancelar — e sobrescreveria a escolha.
    // É o que põe o cursor no campo de senha em `confirmarComSenha()`.
    const valorDoSim = aoAbrir?.(caixa, responder) ?? (() => true);

    caixa.querySelector('[data-resposta="sim"]')
      .addEventListener('click', () => responder(valorDoSim()));
    caixa.querySelector('[data-resposta="nao"]')
      .addEventListener('click', () => responder(recusa));
    // Esc (evento `cancel`) e qualquer outro fechamento equivalem a desistir.
    caixa.addEventListener('cancel', () => responder(recusa));
    caixa.addEventListener('close', () => responder(recusa));
  });
}

/**
 * Pergunta antes de gravar algo que não tem volta, mostrando exatamente o que
 * será gravado.
 *
 * Usa `<dialog>` nativo, e não o `confirm()` do navegador, por três motivos:
 * o `confirm()` só aceita texto puro (não caberia o resumo do que vai ser
 * registrado), trava a thread da página, e tem aparência de erro do sistema em
 * vez de decisão consciente.
 *
 * O botão de cancelar vem PRIMEIRO no DOM e recebe o foco ao abrir, de
 * propósito: um Enter distraído volta para a correção em vez de confirmar.
 * Fechar pelo Esc também equivale a cancelar.
 *
 * @returns {Promise<boolean>} true se a pessoa confirmou.
 */
export function confirmar({ titulo, corpo = '', alerta = '', confirmar: textoOk = 'Confirmar',
                            cancelar: textoNao = 'Voltar e corrigir' }) {
  return dialogo({
    titulo, corpo, alerta, textoOk, textoNao, recusa: false,
    aoAbrir: (caixa) => {
      caixa.querySelector('[data-resposta="nao"]').focus();
      return () => true;
    },
  });
}

/**
 * Confirmação que exige a senha de quem está agindo.
 *
 * Existe para o caso em que saber QUEM está logado não basta: a sessão pode
 * estar aberta numa máquina que ficou sozinha, e a ação não tem volta. É o
 * mesmo raciocínio do `sudo`, que pergunta a senha mesmo já sabendo quem você é.
 *
 * Abre por cima do que estiver na tela — inclusive de outro diálogo —, e o que
 * fica atrás escurece, deixando claro que a decisão é sobre aquilo.
 *
 * @returns {Promise<string|null>} a senha digitada, ou null se desistiu.
 */
export function confirmarComSenha({ titulo, corpo = '', alerta = '',
                                    confirmar: textoOk = 'Confirmar',
                                    rotuloSenha = 'Sua senha' }) {
  return dialogo({
    titulo, corpo, alerta, textoOk, textoNao: 'Cancelar',
    classeOk: 'botao-perigo', recusa: null,
    miolo: `
      <div class="campo">
        <label for="senha-confirmacao">${escapar(rotuloSenha)}</label>
        <input id="senha-confirmacao" type="password" autocomplete="current-password">
      </div>`,
    aoAbrir: (caixa, responder) => {
      const campo = caixa.querySelector('#senha-confirmacao');
      const valor = () => campo.value || null;
      // Enter no campo confirma: é o gesto natural de quem acabou de digitar.
      campo.addEventListener('keydown', (ev) => {
        if (ev.key === 'Enter') { ev.preventDefault(); responder(valor()); }
      });
      campo.focus();
      return valor;
    },
  });
}

/* ------------------------------------------------------------------ *
 * Troca de senha
 * ------------------------------------------------------------------ */

/**
 * Liga o formulário de troca de senha ao servidor.
 *
 * Duas telas pedem a mesma coisa por motivos diferentes — `conta`, quando a
 * pessoa quer trocar, e a raiz, quando o servidor EXIGE a troca porque a senha
 * em vigor foi definida por outra pessoa. A moldura das duas é legitimamente
 * diferente (uma é uma seção entre outras, a outra é a tela inteira), mas a
 * regra é uma só: conferir a repetição aqui, mandar ao servidor e reagir.
 *
 * Era o mesmo bloco escrito duas vezes. Com a regra em dois lugares, corrigir a
 * conferência num deles deixaria o outro para trás — e o campo "repita a nova"
 * existe justamente para pegar um erro de digitação numa senha que ninguém vê
 * enquanto digita.
 *
 * Os ids dos campos são os mesmos nas duas telas, e é o que permite um handler
 * só; o formulário é procurado DENTRO dele para não depender da ordem em que
 * cada página desenha o conteúdo.
 *
 * @param {string} sucesso  aviso mostrado quando a troca dá certo.
 * @param {Function} depois o que fazer em seguida — recarregar, sair, navegar.
 */
export function ligarTrocaDeSenha({ sucesso, depois }) {
  const formulario = document.getElementById('form-senha');
  if (!formulario) return;

  formulario.addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const nova = document.getElementById('s-nova').value;
    if (nova !== document.getElementById('s-confirma').value) {
      aviso('A confirmação não confere com a nova senha.', 'erro');
      return;
    }
    try {
      await store.trocarSenha({
        senhaAtual: document.getElementById('s-atual').value,
        senhaNova: nova,
      });
      aviso(sucesso);
      depois(formulario);
    } catch (erro) {
      aviso(erro.message, 'erro');
    }
  });
}

/* ------------------------------------------------------------------ *
 * Linha do tempo do rastreio
 * ------------------------------------------------------------------ */

/**
 * Monta a trilha completa: todas as etapas do fluxo, marcando as já cumpridas,
 * a atual e as que ainda faltam. Mostrar as etapas futuras é intencional — a
 * pessoa entende o caminho inteiro que o aparelho ainda vai percorrer.
 */
export function linhaDoTempo(rastreio) {
  const { item, eventos } = rastreio;
  const atual = indiceEtapa(item.etapaAtual);
  const eventoDe = new Map(eventos.map((e) => [e.etapa, e]));

  return `<ol class="trilha">${ETAPAS.map((def, i) => {
    const ev = eventoDe.get(def.id);
    const estado = i < atual ? 'concluida' : i === atual ? 'atual' : 'futura';
    const local = ev?.ponto ? `${escapar(ev.ponto.nome)} — ${escapar(ev.ponto.municipio)}` : null;

    return `
      <li class="trilha-item trilha-${estado}">
        <div class="trilha-marca" aria-hidden="true">${i < atual ? '✓' : i + 1}</div>
        <div class="trilha-corpo">
          <h3>${escapar(def.rotulo)}
            ${estado === 'atual' ? '<span class="etiqueta etiqueta-atual">etapa atual</span>' : ''}
          </h3>
          <p class="trilha-descricao">${escapar(def.descricao)}</p>
          ${ev ? `
            <dl class="trilha-dados">
              <div><dt>Quando</dt><dd>${formatarData(ev.em)}</dd></div>
              ${local ? `<div><dt>Onde</dt><dd>${local}</dd></div>` : ''}
              <div><dt>Responsável</dt><dd>${escapar(ev.responsavel)}</dd></div>
              ${ev.observacao ? `<div><dt>Observação</dt><dd>${escapar(ev.observacao)}</dd></div>` : ''}
            </dl>` : `<p class="trilha-pendente">Ainda não realizada. Responsável previsto: ${escapar(def.ator)}.</p>`}
        </div>
      </li>`;
  }).join('')}</ol>`;
}

/** Selo colorido com a etapa atual do item. */
export function seloEtapa(etapaId) {
  const def = definicaoEtapa(etapaId);
  if (!def) return '';
  return `<span class="selo selo-${etapaId.toLowerCase()}">${escapar(def.rotulo)}</span>`;
}

/** Linha resumida de um item, usada nas listagens da conta e do painel. */
export function cartaoItem(item) {
  const cat = categoria(item.categoria);
  return `
    <a class="cartao-item" href="rastrear?c=${encodeURIComponent(item.codigo)}">
      <div class="cartao-item-topo">
        <code>${escapar(item.codigo)}</code>
        ${seloEtapa(item.etapaAtual)}
      </div>
      <strong>${escapar(cat?.rotulo ?? item.categoria)}</strong>
      ${item.marca ? `<span class="sutil">${escapar(item.marca)}</span>` : ''}
      <span class="sutil">${formatarMassa(item.pesoKg)} · atualizado em ${formatarData(item.atualizadoEm)}</span>
    </a>`;
}

/* ------------------------------------------------------------------ *
 * Inicialização das páginas
 * ------------------------------------------------------------------ */

/**
 * Toda página chama isto antes de desenhar qualquer coisa: confere se o
 * servidor responde, monta o cabeçalho e registra o service worker que dá o
 * funcionamento offline.
 */
export async function iniciarPagina() {
  const saude = await store.verificarServidor();
  if (!saude) avisarServidorFora();
  await montarCabecalho();
  montarRodape();
  await marcarContaDeReserva();
  registrarServiceWorker();
}

/**
 * Marca a sessão da conta de reserva, em toda página, enquanto ela durar.
 *
 * A reserva é a chave de emergência do sistema: um administrador que não
 * aparece na tela de administração e que ninguém consegue excluir por lá. Ela
 * resolve o dia em que o acesso ao admin do dia a dia se perde — e vira um
 * problema no dia seguinte, se a pessoa achar mais prático continuar usando.
 * A administração passaria a depender de uma conta invisível, sem selo no
 * cabeçalho e sem linha na lista de contas.
 *
 * Por isso são duas peças, e não uma. A FAIXA diz o que fazer e some da vista
 * ao rolar a página; a MARCA D'ÁGUA não sai da frente e não é lida, é notada —
 * é o que ainda avisa dez minutos depois, quando a faixa já ficou para trás.
 * Ela é `aria-hidden`, porque texto girado e repetido catorze vezes não ajuda
 * quem usa leitor de tela: para esse caso quem carrega o recado é a faixa.
 */
async function marcarContaDeReserva() {
  if (!store.ehReserva(await store.usuarioAtual())) return;

  const faixa = document.createElement('div');
  faixa.className = 'faixa faixa-alerta';
  faixa.style.cssText = 'margin:0;border-radius:0;text-align:center';
  faixa.innerHTML = `
    <strong>Você entrou na conta de reserva.</strong>
    Ela existe só para quando o acesso a <code>admin@etrilha.ms</code> se perder:
    redefina a senha daquela conta em <a href="admin">Administração</a>, volte a
    usá-la e saia daqui. Esta conta não aparece na lista de contas.`;
  document.body.prepend(faixa);

  const marca = document.createElement('div');
  marca.className = 'marca-dagua';
  marca.setAttribute('aria-hidden', 'true');
  // Cada faixa diagonal repete o recado para que ele apareça inteiro em
  // qualquer largura de tela — no celular, só um pedaço da linha cabe.
  const recado = 'conta reserva · use só se perder o acesso ao admin · ';
  marca.innerHTML = Array.from(
    { length: 14 },
    () => `<span>${recado.repeat(8)}</span>`
  ).join('');
  document.body.append(marca);
}

/**
 * Sem servidor, toda tela quebraria com mensagens soltas de erro. Uma faixa
 * fixa explicando o que fazer é mais útil do que um erro por operação.
 */
function avisarServidorFora() {
  const faixa = document.createElement('div');
  faixa.className = 'faixa faixa-alerta';
  faixa.style.cssText = 'margin:0;border-radius:0;text-align:center';
  faixa.innerHTML = `
    <strong>Servidor fora do ar.</strong>
    Se você estiver on-line, inicie o back-end com
    <code>python backend/app.py</code> e recarregue a página.
    Sem conexão, as consultas mostram os últimos dados guardados pelo navegador.`;
  document.body.prepend(faixa);
}

function registrarServiceWorker() {
  if (!('serviceWorker' in navigator)) return;
  // Em file:// o registro falha por design (não há origem segura); ignoramos
  // silenciosamente para não poluir o console durante o desenvolvimento.
  if (location.protocol === 'file:') return;
  navigator.serviceWorker.register('sw.js').catch(() => {});
}
