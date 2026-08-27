/**
 * qr.js — Geração e leitura de QR Code.
 *
 * As bibliotecas ficam em vendor/ e são carregadas como scripts clássicos nas
 * páginas que precisam delas, expondo os globais `qrcode` e `jsQR`:
 *
 *   <script src="vendor/qrcode.js"></script>   (geração)
 *   <script src="vendor/jsqr.js"></script>     (leitura, plano B)
 *
 * Nada aqui depende de internet: o app inteiro funciona offline.
 */

import { normalizarCodigo } from './model.js';

/* ------------------------------------------------------------------ *
 * Geração
 * ------------------------------------------------------------------ */

/**
 * O QR carrega a URL de rastreio, não só o código. Assim, quem apontar o app
 * de câmera do próprio celular para a etiqueta já cai na página do aparelho,
 * sem precisar ter o e-Trilha instalado. O código continua legível embaixo do
 * QR para digitação manual quando a etiqueta estiver danificada.
 */
export function urlDeRastreio(codigo) {
  const base = new URL('rastrear', location.href);
  base.searchParams.set('c', codigo);
  return base.toString();
}

/** Devolve o QR como SVG (string), que imprime nítido em qualquer tamanho. */
export function svgQR(texto, { cellSize = 4, margin = 2 } = {}) {
  if (typeof window.qrcode !== 'function') {
    throw new Error('vendor/qrcode.js não foi carregado nesta página.');
  }
  const qr = window.qrcode(0, 'M'); // tipo 0 = escolhe a versão automaticamente
  qr.addData(texto);
  qr.make();
  return qr.createSvgTag({ cellSize, margin, scalable: true });
}

/** Insere o QR de um código dentro de um elemento. */
export function desenharQR(elemento, codigo, opcoes) {
  elemento.innerHTML = svgQR(urlDeRastreio(codigo), opcoes);
  const svg = elemento.querySelector('svg');
  if (svg) {
    svg.setAttribute('role', 'img');
    svg.setAttribute('aria-label', `QR Code do código de rastreio ${codigo}`);
  }
}

/* ------------------------------------------------------------------ *
 * Interpretação do conteúdo lido
 * ------------------------------------------------------------------ */

const PADRAO_CODIGO = /MS-?[0-9A-Z]{4}-?[0-9A-Z]{4}/i;

/**
 * Extrai um código de rastreio válido do que quer que tenha sido lido:
 * o código puro, a URL completa da etiqueta ou um texto que o contenha.
 * Retorna o código canônico ou null.
 */
export function extrairCodigo(texto) {
  if (!texto) return null;

  const direto = normalizarCodigo(texto);
  if (direto) return direto;

  try {
    const url = new URL(texto);
    const doParametro = normalizarCodigo(url.searchParams.get('c'));
    if (doParametro) return doParametro;
  } catch {
    /* não era uma URL, segue para a busca por padrão */
  }

  const achado = texto.match(PADRAO_CODIGO);
  return achado ? normalizarCodigo(achado[0]) : null;
}

/* ------------------------------------------------------------------ *
 * Leitura pela câmera
 * ------------------------------------------------------------------ */

/**
 * Leitor de QR pela câmera.
 *
 * Usa a API nativa `BarcodeDetector` quando o navegador oferece (Chrome e Edge,
 * onde a decodificação roda em código nativo do sistema operacional, fora da
 * thread de JavaScript) e cai para a biblioteca jsQR quando não há suporte
 * (Firefox e Safari), decodificando quadro a quadro sobre um canvas.
 *
 * A permissão de câmera é concedida pelo usuário ao navegador, que a intermedeia
 * com o sistema operacional — o app nunca fala direto com o dispositivo.
 */
export class LeitorQR {
  constructor(video, { onLeitura, onErro, intervaloMs = 250 } = {}) {
    this.video = video;
    this.onLeitura = onLeitura ?? (() => {});
    this.onErro = onErro ?? (() => {});
    this.intervaloMs = intervaloMs;
    this.stream = null;
    this.detector = null;
    this.metodo = null;
    this.timer = null;
    this.ultimaLeitura = { texto: null, em: 0 };
    this.canvas = document.createElement('canvas');
    this.ctx = this.canvas.getContext('2d', { willReadFrequently: true });
  }

  get ativo() {
    return this.stream != null;
  }

  async iniciar() {
    if (this.ativo) return;

    if (!navigator.mediaDevices?.getUserMedia) {
      throw new Error(
        'Este navegador não expõe a câmera. Abra a página por http://localhost (a câmera é bloqueada em file://) ou use a digitação manual do código.'
      );
    }

    this.stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: 'environment' }, width: { ideal: 1280 } },
      audio: false,
    });
    this.video.srcObject = this.stream;
    this.video.setAttribute('playsinline', '');
    await this.video.play();

    if ('BarcodeDetector' in window) {
      try {
        const formatos = await window.BarcodeDetector.getSupportedFormats();
        if (formatos.includes('qr_code')) {
          this.detector = new window.BarcodeDetector({ formats: ['qr_code'] });
          this.metodo = 'BarcodeDetector (nativo do navegador)';
        }
      } catch {
        /* segue para o plano B */
      }
    }
    if (!this.detector) {
      if (typeof window.jsQR !== 'function') {
        throw new Error('vendor/jsqr.js não foi carregado e este navegador não tem BarcodeDetector.');
      }
      this.metodo = 'jsQR (decodificação em JavaScript)';
    }

    this.timer = setInterval(() => this.#analisarQuadro(), this.intervaloMs);
  }

  parar() {
    clearInterval(this.timer);
    this.timer = null;
    this.stream?.getTracks().forEach((t) => t.stop());
    this.stream = null;
    this.video.srcObject = null;
  }

  async #analisarQuadro() {
    if (!this.ativo || this.video.readyState < 2) return;
    try {
      const texto = this.detector ? await this.#lerNativo() : this.#lerJsQR();
      if (texto) this.#emitir(texto);
    } catch (erro) {
      this.onErro(erro);
    }
  }

  async #lerNativo() {
    const [primeiro] = await this.detector.detect(this.video);
    return primeiro?.rawValue ?? null;
  }

  #lerJsQR() {
    const { videoWidth: w, videoHeight: h } = this.video;
    if (!w || !h) return null;
    // Reduz a resolução antes de decodificar: sem isso, um quadro 1280x720
    // custa caro em JavaScript e a prévia trava em máquinas modestas.
    const escala = Math.min(1, 640 / w);
    this.canvas.width = Math.round(w * escala);
    this.canvas.height = Math.round(h * escala);
    this.ctx.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
    const imagem = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
    const resultado = window.jsQR(imagem.data, imagem.width, imagem.height, {
      inversionAttempts: 'dontInvert',
    });
    return resultado?.data ?? null;
  }

  /** Evita disparar dezenas de vezes enquanto o mesmo QR fica na frente da câmera. */
  #emitir(texto) {
    const agora = Date.now();
    if (texto === this.ultimaLeitura.texto && agora - this.ultimaLeitura.em < 3000) return;
    this.ultimaLeitura = { texto, em: agora };
    this.onLeitura(texto, extrairCodigo(texto));
  }
}
