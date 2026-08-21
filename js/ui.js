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

  const links = PAGINAS.map(
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
      ${usuario ? `<span class="avatar" aria-hidden="true">${escapar(usuario.nome[0].toUpperCase())}</span> ${escapar(usuario.nome.split(' ')[0])}`
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
