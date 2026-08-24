/**
 * ui.js — Peças de interface compartilhadas entre as páginas.
 * Cabeçalho, avisos, formatação e o componente de linha do tempo do rastreio.
 */

import { ETAPAS, etapa as definicaoEtapa, indiceEtapa, categoria } from './model.js';
import * as store from './store.js';
import * as auth from './auth.js';

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

const PAGINAS = [
  { href: 'index.html', rotulo: 'Início' },
  { href: 'registrar.html', rotulo: 'Registrar aparelho' },
  { href: 'scanner.html', rotulo: 'Ler QR' },
  { href: 'rastrear.html', rotulo: 'Rastrear' },
  { href: 'pontos.html', rotulo: 'Pontos de coleta' },
  { href: 'painel.html', rotulo: 'Painel' },
];

async function montarCabecalho() {
  const alvo = document.querySelector('[data-cabecalho]');
  if (!alvo) return;

  const atualPath = location.pathname.split('/').pop() || 'index.html';
  const usuario = await auth.atual();

  // A administração só aparece para quem é admin. Esconder o link é
  // conveniência: a rota da API continua fechada por conta própria, no
  // servidor, para quem tentar abrir a página direto pela URL.
  const paginas = auth.ehAdmin(usuario)
    ? [...PAGINAS, { href: 'admin.html', rotulo: 'Administração' }]
    : PAGINAS;

  const links = paginas.map(
    (p) =>
      `<a href="${p.href}"${p.href === atualPath ? ' aria-current="page"' : ''}>${p.rotulo}</a>`
  ).join('');

  alvo.innerHTML = `
    <a class="marca" href="index.html">
      <span class="marca-simbolo" aria-hidden="true">♻</span>
      <span><strong>e-Trilha</strong> MS</span>
    </a>
    <nav aria-label="Navegação principal">${links}</nav>
    <a class="conta-link" href="conta.html">
      ${usuario ? `<span class="avatar" aria-hidden="true">${escapar(usuario.nome[0].toUpperCase())}</span>
                   ${escapar(usuario.nome.split(' ')[0])}
                   ${usuario.papel !== 'visitante' ? seloPapel(usuario.papel) : ''}`
                : 'Entrar <span class="opcional">(opcional)</span>'}
    </a>`;
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
  const def = auth.PAPEIS[papel];
  if (!def) return '';
  return `<span class="selo selo-papel selo-${papel}">${escapar(def.rotulo)}</span>`;
}

/* ------------------------------------------------------------------ *
 * Confirmação de ação definitiva
 * ------------------------------------------------------------------ */

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
                            cancelar: textoCancelar = 'Voltar e corrigir' }) {
  return new Promise((resolver) => {
    const dialogo = document.createElement('dialog');
    dialogo.className = 'confirmacao';
    dialogo.innerHTML = `
      <h2>${escapar(titulo)}</h2>
      ${corpo}
      ${alerta ? `<div class="faixa faixa-alerta">${alerta}</div>` : ''}
      <div class="botoes confirmacao-botoes">
        <button class="botao botao-secundario" type="button" data-resposta="nao">${escapar(textoCancelar)}</button>
        <button class="botao" type="button" data-resposta="sim">${escapar(textoOk)}</button>
      </div>`;

    // A resposta é dada no clique, e não no evento `close` do diálogo: assim a
    // promessa não depende da entrega assíncrona desse evento, que se mostrou
    // pouco confiável em navegador sem interface (usado nos testes). O guarda
    // `respondido` garante uma resposta só, venha ela do botão ou do Esc.
    let respondido = false;
    const responder = (ok) => {
      if (respondido) return;
      respondido = true;
      if (dialogo.open) dialogo.close();
      dialogo.remove();
      resolver(ok);
    };

    dialogo.querySelectorAll('[data-resposta]').forEach((botao) =>
      botao.addEventListener('click', () => responder(botao.dataset.resposta === 'sim'))
    );
    // Esc (evento `cancel`) e qualquer outro fechamento equivalem a desistir.
    dialogo.addEventListener('cancel', () => responder(false));
    dialogo.addEventListener('close', () => responder(false));

    document.body.append(dialogo);
    dialogo.showModal();
    dialogo.querySelector('[data-resposta="nao"]').focus();
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
  return new Promise((resolver) => {
    const dialogo = document.createElement('dialog');
    dialogo.className = 'confirmacao';
    dialogo.innerHTML = `
      <h2>${escapar(titulo)}</h2>
      ${corpo}
      ${alerta ? `<div class="faixa faixa-alerta">${alerta}</div>` : ''}
      <div class="campo">
        <label for="senha-confirmacao">${escapar(rotuloSenha)}</label>
        <input id="senha-confirmacao" type="password" autocomplete="current-password">
      </div>
      <div class="botoes confirmacao-botoes">
        <button class="botao botao-secundario" type="button" data-resposta="nao">Cancelar</button>
        <button class="botao botao-perigo" type="button" data-resposta="sim">${escapar(textoOk)}</button>
      </div>`;

    let respondido = false;
    const responder = (senha) => {
      if (respondido) return;
      respondido = true;
      if (dialogo.open) dialogo.close();
      dialogo.remove();
      resolver(senha);
    };

    const campo = dialogo.querySelector('#senha-confirmacao');
    const confirmarAgora = () => responder(campo.value || null);

    dialogo.querySelector('[data-resposta="sim"]').addEventListener('click', confirmarAgora);
    dialogo.querySelector('[data-resposta="nao"]').addEventListener('click', () => responder(null));
    // Enter no campo de senha confirma: é o gesto natural de quem acabou de digitar.
    campo.addEventListener('keydown', (ev) => {
      if (ev.key === 'Enter') { ev.preventDefault(); confirmarAgora(); }
    });
    dialogo.addEventListener('cancel', () => responder(null));
    dialogo.addEventListener('close', () => responder(null));

    document.body.append(dialogo);
    dialogo.showModal();
    campo.focus();
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
    <a class="cartao-item" href="rastrear.html?c=${encodeURIComponent(item.codigo)}">
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
  registrarServiceWorker();
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
