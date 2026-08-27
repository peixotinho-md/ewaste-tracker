/**
 * sw.js — Service Worker do e-Trilha MS.
 *
 * O service worker é um script que o navegador mantém registrado e executa
 * FORA da página, num processo próprio, mesmo quando nenhuma aba está aberta.
 * Ele intercepta as requisições da aplicação e decide se responde da rede ou do
 * cache — o que dá ao app a capacidade de abrir sem internet, situação real em
 * galpões de triagem e em pontos de coleta do interior do estado.
 *
 * Estratégia: REDE PRIMEIRO, CACHE COMO PLANO B.
 * Assim o time sempre vê a versão mais recente durante o desenvolvimento, e o
 * app continua abrindo quando a conexão cai.
 *
 * Com o back-end no ar, o que dá para fazer offline mudou:
 *
 *   CONSULTAR  funciona, com os últimos dados que passaram por aqui;
 *   GRAVAR     não funciona. Registrar um aparelho ou avançar uma etapa precisa
 *              do servidor, que é quem valida a transição e grava a cadeia de
 *              custódia. A tela mostra um erro claro em vez de fingir sucesso —
 *              uma fila de gravações offline está listada como melhoria futura
 *              no Relatório Técnico.
 */

const CACHE = 'etrilhams-v4';

// Só as páginas que abrem sem conta entram na instalação. As demais o servidor
// nem entrega sem sessão, e guardar a casca delas aqui só criaria uma tela que
// abre offline para não conseguir carregar dado nenhum.
const ARQUIVOS = [
  './',
  './rastrear',
  './css/app.css',
  './js/model.js',
  './js/store.js',
  './js/indicadores.js',
  './js/qr.js',
  './js/ui.js',
  './vendor/qrcode.js',
  './vendor/jsqr.js',
  './manifest.webmanifest',
  './icon.svg',
];

/**
 * Só respostas de leitura PÚBLICA da API entram no cache.
 *
 * `/api/sessao`, `/api/meus-itens` e `/api/painel` dependem de quem está
 * logado — o painel inclusive muda de forma conforme o papel, vindo anônimo
 * para conta comum e identificado para operador. Guardar qualquer uma delas
 * faria a resposta de uma pessoa aparecer para outra no mesmo navegador.
 * `/api/saude` é diagnóstico e precisa dizer a verdade sobre o servidor agora.
 * `/api/admin/*` nunca entra: é a lista de contas do sistema, e uma cópia
 * guardada no navegador continuaria legível depois que o papel de quem a
 * carregou fosse revogado.
 */
const API_CACHEAVEL = [
  /^\/api\/pontos$/,
  /^\/api\/itens\/[^/]+\/rastreio$/,
];

const podeGuardar = (url) =>
  !url.pathname.startsWith('/api/') || API_CACHEAVEL.some((re) => re.test(url.pathname));

self.addEventListener('install', (evento) => {
  evento.waitUntil(
    caches.open(CACHE)
      // addAll falha inteiro se um arquivo faltar; guardamos um a um para que
      // uma ausência isolada não impeça o app de ficar disponível offline.
      .then((cache) => Promise.allSettled(ARQUIVOS.map((a) => cache.add(a))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (evento) => {
  evento.waitUntil(
    caches.keys()
      .then((chaves) => Promise.all(chaves.filter((c) => c !== CACHE).map((c) => caches.delete(c))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (evento) => {
  const req = evento.request;
  const url = new URL(req.url);

  // POST e DELETE (registrar aparelho, avançar etapa, entrar) passam direto:
  // são gravações e precisam do servidor.
  if (req.method !== 'GET' || url.origin !== location.origin) return;

  evento.respondWith(
    fetch(req)
      .then((resposta) => {
        if (resposta.ok && podeGuardar(url)) {
          const copia = resposta.clone();
          caches.open(CACHE).then((cache) => cache.put(req, copia));
        }
        return resposta;
      })
      .catch(async () => {
        const doCache = await caches.match(req);
        if (doCache) return doCache;

        // Navegação sem rede e sem cópia da rota: cai na home já armazenada.
        if (req.mode === 'navigate') return caches.match('./');

        // Chamada de API sem rede e sem cópia: devolve um erro que a camada
        // de dados sabe exibir, em vez de uma falha genérica de rede.
        if (url.pathname.startsWith('/api/')) {
          return new Response(
            JSON.stringify({ erro: 'Sem conexão com o servidor e sem dados guardados para esta consulta.' }),
            { status: 503, headers: { 'Content-Type': 'application/json; charset=utf-8' } }
          );
        }

        return new Response('Sem conexão e sem cópia local deste recurso.', {
          status: 503,
          headers: { 'Content-Type': 'text/plain; charset=utf-8' },
        });
      })
  );
});
