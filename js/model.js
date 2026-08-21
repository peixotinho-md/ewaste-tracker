/**
 * model.js — Regras de negócio e tabelas de referência do e-Trilha MS.
 *
 * Este arquivo não acessa armazenamento nem DOM: só define o que as coisas são
 * e as funções puras que operam sobre elas. Isso permite testar as regras
 * isoladamente e reaproveitá-las quando o back-end for implementado.
 */

/* ------------------------------------------------------------------ *
 * 1. Etapas da cadeia de custódia (máquina de estados)
 * ------------------------------------------------------------------ */

/**
 * O fluxo é linear e só avança. Cada etapa tem um SLA em horas: se o item
 * ficar parado além disso, o painel o marca como pendência — é assim que a
 * plataforma detecta gargalos na logística reversa em vez de só arquivar dados.
 */
export const ETAPAS = [
  {
    id: 'REGISTRADO',
    rotulo: 'Registrado',
    descricao: 'Dispositivo cadastrado pelo dono e etiqueta QR gerada.',
    ator: 'Cidadão ou empresa',
    slaHoras: 168,
  },
  {
    id: 'COLETADO',
    rotulo: 'Coletado',
    descricao: 'Aparelho recebido no ponto de coleta e QR lido na entrada.',
    ator: 'Ponto de coleta',
    slaHoras: 72,
  },
  {
    id: 'EM_TRIAGEM',
    rotulo: 'Em triagem',
    descricao: 'Item classificado, pesado e separado por tipo de material.',
    ator: 'Cooperativa de reciclagem',
    slaHoras: 96,
  },
  {
    id: 'EM_TRANSPORTE',
    rotulo: 'Em transporte',
    descricao: 'Lote a caminho da unidade de reciclagem credenciada.',
    ator: 'Transportadora / logística reversa',
    slaHoras: 120,
  },
  {
    id: 'EM_RECICLAGEM',
    rotulo: 'Em reciclagem',
    descricao: 'Desmontagem e recuperação dos materiais na recicladora.',
    ator: 'Recicladora credenciada',
    slaHoras: 168,
  },
  {
    id: 'PROCESSADO',
    rotulo: 'Processado',
    descricao: 'Destinação concluída. Certificado de destinação final emitido.',
    ator: 'Recicladora credenciada',
    slaHoras: null,
  },
];

export const PRIMEIRA_ETAPA = ETAPAS[0].id;
export const ETAPA_FINAL = ETAPAS[ETAPAS.length - 1].id;

export function etapa(id) {
  return ETAPAS.find((e) => e.id === id) ?? null;
}

export function indiceEtapa(id) {
  return ETAPAS.findIndex((e) => e.id === id);
}

/** Próxima etapa do fluxo, ou null se o item já está processado. */
export function proximaEtapa(id) {
  const i = indiceEtapa(id);
  if (i < 0 || i >= ETAPAS.length - 1) return null;
  return ETAPAS[i + 1];
}

/**
 * Valida a transição. Retorna { ok: true } ou { ok: false, motivo }.
 * Só o passo imediatamente seguinte é aceito: pular etapa quebraria a cadeia
 * de custódia (não haveria prova de que o item passou pela triagem) e voltar
 * permitiria mascarar um extravio.
 */
export function validarTransicao(etapaAtual, etapaDestino) {
  const atual = indiceEtapa(etapaAtual);
  const destino = indiceEtapa(etapaDestino);

  if (destino < 0) return { ok: false, motivo: 'Etapa desconhecida.' };
  if (atual < 0) return { ok: false, motivo: 'Item sem etapa atual válida.' };
  if (destino === atual) {
    return { ok: false, motivo: `O item já está em "${etapa(etapaAtual).rotulo}".` };
  }
  if (destino < atual) {
    return {
      ok: false,
      motivo: `Não é possível retroceder de "${etapa(etapaAtual).rotulo}" para "${etapa(etapaDestino).rotulo}". O histórico é somente de acréscimo.`,
    };
  }
  if (destino > atual + 1) {
    return {
      ok: false,
      motivo: `Não é possível pular etapas: depois de "${etapa(etapaAtual).rotulo}" vem "${ETAPAS[atual + 1].rotulo}".`,
    };
  }
  return { ok: true };
}

/**
 * Um item está pendente quando estourou o SLA da etapa em que se encontra.
 * É estado derivado (calculado da data do último evento), nunca digitado.
 */
export function estaPendente(item, agora = new Date()) {
  const def = etapa(item.etapaAtual);
  if (!def || def.slaHoras == null) return false;
  const horas = (agora - new Date(item.atualizadoEm)) / 36e5;
  return horas > def.slaHoras;
}

/* ------------------------------------------------------------------ *
 * 2. Categorias de dispositivo e composição material
 * ------------------------------------------------------------------ */

/**
 * Percentuais médios de massa por material e teor de ouro em mg por kg.
 * São valores de referência da literatura de e-waste (Global E-waste Monitor,
 * relatórios de logística reversa) usados para estimar o material recuperado
 * a partir do peso e da categoria — o protótipo não pesa material real.
 *
 * A composição é o que conecta o projeto a Arquitetura de Computadores: o ouro
 * está nos contatos e no encapsulamento dos circuitos integrados, o cobre nas
 * trilhas da placa e nos enrolamentos, o alumínio nos dissipadores e chassis,
 * e as terras raras (neodímio, disprósio) nos ímãs de discos rígidos e alto-falantes.
 */
export const CATEGORIAS = [
  {
    id: 'celular',
    rotulo: 'Celular / smartphone',
    pesoMedioKg: 0.19,
    composicao: { cobre: 0.15, aluminio: 0.06, aco: 0.08, plastico: 0.4, vidro: 0.16, terrasRaras: 0.003 },
    ouroMgPorKg: 300,
    contaminantes: ['lítio', 'cobalto', 'chumbo'],
  },
  {
    id: 'notebook',
    rotulo: 'Notebook',
    pesoMedioKg: 2.0,
    composicao: { cobre: 0.09, aluminio: 0.21, aco: 0.12, plastico: 0.31, vidro: 0.1, terrasRaras: 0.002 },
    ouroMgPorKg: 90,
    contaminantes: ['lítio', 'chumbo', 'mercúrio'],
  },
  {
    id: 'desktop',
    rotulo: 'Desktop / gabinete',
    pesoMedioKg: 8.5,
    composicao: { cobre: 0.07, aluminio: 0.06, aco: 0.45, plastico: 0.23, vidro: 0.01, terrasRaras: 0.001 },
    ouroMgPorKg: 45,
    contaminantes: ['chumbo', 'berílio'],
  },
  {
    id: 'monitor',
    rotulo: 'Monitor / TV',
    pesoMedioKg: 7.5,
    composicao: { cobre: 0.04, aluminio: 0.07, aco: 0.11, plastico: 0.45, vidro: 0.28, terrasRaras: 0 },
    ouroMgPorKg: 15,
    contaminantes: ['mercúrio', 'chumbo', 'cádmio'],
  },
  {
    id: 'impressora',
    rotulo: 'Impressora / multifuncional',
    pesoMedioKg: 6.5,
    composicao: { cobre: 0.05, aluminio: 0.04, aco: 0.26, plastico: 0.54, vidro: 0.01, terrasRaras: 0.001 },
    ouroMgPorKg: 12,
    contaminantes: ['resíduo de toner', 'chumbo'],
  },
  {
    id: 'servidor',
    rotulo: 'Servidor / no-break',
    pesoMedioKg: 16.0,
    composicao: { cobre: 0.11, aluminio: 0.11, aco: 0.48, plastico: 0.16, vidro: 0.01, terrasRaras: 0.002 },
    ouroMgPorKg: 70,
    contaminantes: ['chumbo', 'ácido de bateria'],
  },
  {
    id: 'hd',
    rotulo: 'HD / SSD / mídia de armazenamento',
    pesoMedioKg: 0.55,
    composicao: { cobre: 0.05, aluminio: 0.45, aco: 0.26, plastico: 0.1, vidro: 0.01, terrasRaras: 0.05 },
    ouroMgPorKg: 35,
    contaminantes: ['chumbo'],
  },
  {
    id: 'cabos',
    rotulo: 'Cabos e carregadores',
    pesoMedioKg: 0.3,
    composicao: { cobre: 0.3, aluminio: 0.02, aco: 0.05, plastico: 0.6, vidro: 0, terrasRaras: 0 },
    ouroMgPorKg: 3,
    contaminantes: ['PVC', 'chumbo'],
  },
  {
    id: 'bateria',
    rotulo: 'Baterias e pilhas',
    pesoMedioKg: 0.12,
    composicao: { cobre: 0.1, aluminio: 0.08, aco: 0.24, plastico: 0.06, vidro: 0, terrasRaras: 0.01 },
    ouroMgPorKg: 0,
    contaminantes: ['lítio', 'cádmio', 'mercúrio', 'níquel'],
  },
  {
    id: 'eletrodomestico',
    rotulo: 'Eletrodoméstico',
    pesoMedioKg: 12.0,
    composicao: { cobre: 0.06, aluminio: 0.05, aco: 0.52, plastico: 0.28, vidro: 0.04, terrasRaras: 0.001 },
    ouroMgPorKg: 4,
    contaminantes: ['gás refrigerante', 'óleo'],
  },
];

export function categoria(id) {
  return CATEGORIAS.find((c) => c.id === id) ?? null;
}

/* ------------------------------------------------------------------ *
 * 2b. Apagamento seguro de mídias de dados
 *
 * Um aparelho descartado não carrega só metal: carrega dados. Apagar um
 * arquivo ou formatar não destrói o conteúdo — só marca o espaço como livre.
 * E a forma correta de destruir depende de COMO a mídia guarda o bit, o que é
 * arquitetura do hardware, não software:
 *
 *   DISCO MAGNÉTICO (HDD) — o bit é a orientação magnética de uma região do
 *   prato, e o endereço lógico corresponde a uma posição física estável.
 *   Sobrescrever o setor destrói o dado; um campo magnético forte
 *   (desmagnetização) apaga o disco inteiro.
 *
 *   MEMÓRIA FLASH (SSD, NVMe, eMMC) — o bit é carga presa numa célula, e o
 *   endereço lógico NÃO corresponde a uma célula fixa: a flash translation
 *   layer do controlador remapeia blocos para distribuir o desgaste (wear
 *   leveling) e mantém uma reserva invisível ao sistema (over-provisioning).
 *   Logo, sobrescrever pelo endereço lógico deixa cópias intactas em blocos
 *   que o sistema operacional nem consegue endereçar, e desmagnetizar não faz
 *   nada, porque não há magnetismo guardando o dado.
 *
 * Estas tabelas espelham `backend/modelo.py` e servem para a tela oferecer
 * apenas o que funciona. A recusa que vale continua sendo a do servidor.
 * ------------------------------------------------------------------ */

/** Categorias que carregam memória não volátil. */
export const CATEGORIAS_COM_MIDIA = new Set([
  'celular', 'notebook', 'desktop', 'servidor', 'hd', 'impressora',
]);

export const MIDIAS = {
  magnetica: { rotulo: 'Disco magnético (HDD)' },
  flash: { rotulo: 'Memória flash (SSD, NVMe, eMMC, cartão)' },
  sem_midia: { rotulo: 'Sem mídia de dados, ou já removida' },
};

export const METODOS_APAGAMENTO = {
  SOBRESCRITA: {
    rotulo: 'Sobrescrita de todos os setores',
    midias: ['magnetica'],
    porqueNao: 'Não alcança os blocos remapeados pelo wear leveling nem a área de over-provisioning: em flash, restam cópias legíveis.',
  },
  DESMAGNETIZACAO: {
    rotulo: 'Desmagnetização (degausser)',
    midias: ['magnetica'],
    porqueNao: 'Em flash o bit é carga elétrica, não orientação magnética. O degausser não tem efeito nenhum.',
  },
  SECURE_ERASE: {
    rotulo: 'ATA Secure Erase / NVMe Format',
    midias: ['magnetica', 'flash'],
    porqueNao: 'Aplicável apenas a mídias de dados.',
  },
  CRIPTO_ERASE: {
    rotulo: 'Destruição da chave de criptografia',
    midias: ['magnetica', 'flash'],
    porqueNao: 'Aplicável apenas a mídias de dados.',
  },
  DESTRUICAO_FISICA: {
    rotulo: 'Destruição física (trituração da mídia)',
    midias: ['magnetica', 'flash'],
    porqueNao: 'Aplicável apenas a mídias de dados.',
  },
  NAO_APLICAVEL: {
    rotulo: 'Não aplicável — sem mídia de dados',
    midias: ['sem_midia'],
    porqueNao: 'O aparelho tem mídia de dados: informe como ela foi destruída.',
  },
};

export function exigeApagamento(categoriaId) {
  return CATEGORIAS_COM_MIDIA.has(categoriaId);
}

/** Métodos que realmente destroem o dado no tipo de mídia informado. */
export function metodosParaMidia(midia) {
  return Object.entries(METODOS_APAGAMENTO)
    .filter(([, def]) => def.midias.includes(midia))
    .map(([id, def]) => ({ id, ...def }));
}

/* ------------------------------------------------------------------ *
 * 3. Materiais e fator de CO2e evitado
 * ------------------------------------------------------------------ */

/**
 * kg de CO2e evitado por kg de material recuperado, comparando a reciclagem
 * com a produção primária (mineração + refino). O ouro tem fator altíssimo
 * porque extrair 1 kg de ouro primário move toneladas de minério — é por isso
 * que poucos miligramas por aparelho ainda pesam no resultado final.
 */
export const MATERIAIS = {
  cobre: { rotulo: 'Cobre', co2ePorKg: 3.5 },
  aluminio: { rotulo: 'Alumínio', co2ePorKg: 9.0 },
  aco: { rotulo: 'Aço', co2ePorKg: 1.8 },
  plastico: { rotulo: 'Plástico', co2ePorKg: 1.7 },
  vidro: { rotulo: 'Vidro', co2ePorKg: 0.6 },
  terrasRaras: { rotulo: 'Terras raras', co2ePorKg: 25.0 },
  ouro: { rotulo: 'Ouro', co2ePorKg: 12500 },
};

/**
 * Estima os materiais recuperáveis de um item.
 * Retorna massas em kg (o ouro também em kg, para o cálculo de CO2e ficar homogêneo).
 */
export function materiaisRecuperaveis(item) {
  const cat = categoria(item.categoria);
  if (!cat) return {};
  const peso = Number(item.pesoKg) || cat.pesoMedioKg;
  const saida = {};
  for (const [material, fracao] of Object.entries(cat.composicao)) {
    if (fracao > 0) saida[material] = peso * fracao;
  }
  if (cat.ouroMgPorKg > 0) saida.ouro = (peso * cat.ouroMgPorKg) / 1e6; // mg -> kg
  return saida;
}

/** CO2e evitado (kg) pela reciclagem correta de um item. */
export function co2eEvitado(item) {
  let total = 0;
  for (const [material, kg] of Object.entries(materiaisRecuperaveis(item))) {
    total += kg * (MATERIAIS[material]?.co2ePorKg ?? 0);
  }
  return total;
}

/* ------------------------------------------------------------------ *
 * 4. Código de rastreio com dígito verificador
 * ------------------------------------------------------------------ */

/**
 * Alfabeto base32 sem os caracteres que as pessoas confundem ao ler uma
 * etiqueta suja ou riscada: I, L, O e U ficaram de fora.
 */
const ALFABETO = '0123456789ABCDEFGHJKMNPQRSTVWXYZ';

/** Corrige as confusões mais comuns na digitação manual do código. */
const CORRECOES = { O: '0', I: '1', L: '1', U: 'V' };

/**
 * Dígito verificador por soma ponderada módulo 32 (mesma ideia do CPF e do
 * ISBN). Detecta todos os erros de um caractere e a maioria das transposições.
 */
export function digitoVerificador(corpo) {
  let soma = 0;
  for (let i = 0; i < corpo.length; i++) {
    const valor = ALFABETO.indexOf(corpo[i]);
    if (valor < 0) return null;
    soma += valor * (corpo.length + 1 - i);
  }
  return ALFABETO[soma % ALFABETO.length];
}

/** Gera um código novo no formato MS-XXXX-XXXX (7 aleatórios + 1 verificador). */
export function gerarCodigo() {
  const bytes = new Uint8Array(7);
  crypto.getRandomValues(bytes);
  const corpo = Array.from(bytes, (b) => ALFABETO[b % ALFABETO.length]).join('');
  return formatarCodigo(corpo + digitoVerificador(corpo));
}

/** MS7K3F2QX9 -> MS-7K3F-2QX9 */
export function formatarCodigo(corpo) {
  const limpo = corpo.replace(/^MS/, '');
  return `MS-${limpo.slice(0, 4)}-${limpo.slice(4, 8)}`;
}

/**
 * Aceita o que o usuário digitar (minúsculas, sem hífen, com O no lugar de 0)
 * e devolve o código canônico, ou null se for inválido.
 */
export function normalizarCodigo(entrada) {
  if (!entrada) return null;
  let bruto = String(entrada).toUpperCase().replace(/[^0-9A-Z]/g, '');
  if (bruto.startsWith('MS')) bruto = bruto.slice(2);
  bruto = Array.from(bruto, (c) => CORRECOES[c] ?? c).join('');
  if (bruto.length !== 8) return null;
  const corpo = bruto.slice(0, 7);
  if (digitoVerificador(corpo) !== bruto[7]) return null;
  return formatarCodigo(bruto);
}

/* ------------------------------------------------------------------ *
 * 5. Geolocalização
 * ------------------------------------------------------------------ */

/** Distância em km entre duas coordenadas pela fórmula de Haversine. */
export function distanciaKm(lat1, lon1, lat2, lon2) {
  const R = 6371;
  const rad = (g) => (g * Math.PI) / 180;
  const dLat = rad(lat2 - lat1);
  const dLon = rad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(rad(lat1)) * Math.cos(rad(lat2)) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(a));
}

/* ------------------------------------------------------------------ *
 * 6. Tipos de ponto de coleta
 * ------------------------------------------------------------------ */

export const TIPOS_PONTO = {
  ecoponto: { rotulo: 'Ecoponto municipal', cor: '#2f8f5b' },
  cooperativa: { rotulo: 'Cooperativa de reciclagem', cor: '#b8792b' },
  fabricante: { rotulo: 'Loja / fabricante', cor: '#2f6fb8' },
  pev: { rotulo: 'Ponto de entrega voluntária', cor: '#7a4fb5' },
  recicladora: { rotulo: 'Recicladora credenciada', cor: '#525a68' },
};
