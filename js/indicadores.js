/**
 * indicadores.js — Cálculo dos indicadores do painel.
 *
 * Funções puras: recebem itens, eventos e pontos, devolvem números.
 * Nada de armazenamento nem de DOM aqui, para que os cálculos possam ser
 * conferidos à mão e reaproveitados no back-end.
 */

import {
  ETAPAS,
  ETAPA_FINAL,
  etapa as definicaoEtapa,
  estaPendente,
  materiaisRecuperaveis,
  co2eEvitado,
  categoria,
} from './model.js';

/**
 * Tempo que cada item passou em cada etapa, em horas.
 * Só conta etapas ENCERRADAS (as que já têm um evento seguinte); a etapa em
 * que o item está agora ainda não terminou e distorceria a média.
 */
export function duracoesPorEtapa(eventos) {
  const porItem = new Map();
  for (const ev of eventos) {
    if (!porItem.has(ev.itemCodigo)) porItem.set(ev.itemCodigo, []);
    porItem.get(ev.itemCodigo).push(ev);
  }

  const duracoes = {}; // etapaId -> [horas, horas, ...]
  for (const lista of porItem.values()) {
    lista.sort((a, b) => new Date(a.em) - new Date(b.em));
    for (let i = 0; i < lista.length - 1; i++) {
      const horas = (new Date(lista[i + 1].em) - new Date(lista[i].em)) / 36e5;
      (duracoes[lista[i].etapa] ??= []).push(horas);
    }
  }
  return duracoes;
}

const media = (lista) => (lista.length ? lista.reduce((a, b) => a + b, 0) / lista.length : null);

/**
 * Indicadores completos do painel.
 *
 * @param {Array} itens   itens cadastrados
 * @param {Array} eventos todos os eventos de rastreio
 * @param {Array} pontos  pontos de coleta (para agrupar por município)
 */
export function calcularIndicadores(itens, eventos, pontos, agora = new Date()) {
  const pontoPorId = new Map(pontos.map((p) => [p.id, p]));
  const processados = itens.filter((i) => i.etapaAtual === ETAPA_FINAL);
  const emCurso = itens.filter((i) => i.etapaAtual !== ETAPA_FINAL);

  /* --- massa --------------------------------------------------------- */
  const somaPeso = (lista) => lista.reduce((t, i) => t + (Number(i.pesoKg) || 0), 0);
  const massaTotalKg = somaPeso(itens);
  const massaDesviadaKg = somaPeso(processados);
  const massaEmCursoKg = somaPeso(emCurso);

  /* --- distribuição por etapa ---------------------------------------- */
  const porEtapa = ETAPAS.map((e) => {
    const doGrupo = itens.filter((i) => i.etapaAtual === e.id);
    return {
      id: e.id,
      rotulo: e.rotulo,
      quantidade: doGrupo.length,
      pesoKg: somaPeso(doGrupo),
    };
  });

  /* --- materiais recuperados e CO2e ---------------------------------- */
  // Contabilizados apenas nos itens PROCESSADOS: só aí a recuperação de fato
  // aconteceu. Contar o que ainda está em trânsito inflaria o resultado.
  const materiais = {};
  let co2eKg = 0;
  for (const item of processados) {
    for (const [material, kg] of Object.entries(materiaisRecuperaveis(item))) {
      materiais[material] = (materiais[material] ?? 0) + kg;
    }
    co2eKg += co2eEvitado(item);
  }

  /* --- tempo por etapa e gargalo ------------------------------------- */
  const duracoes = duracoesPorEtapa(eventos);
  const tempos = ETAPAS.filter((e) => e.slaHoras != null).map((e) => {
    const horas = media(duracoes[e.id] ?? []);
    return {
      id: e.id,
      rotulo: e.rotulo,
      mediaHoras: horas,
      slaHoras: e.slaHoras,
      // Acima de 1 significa que, em média, a etapa estoura o prazo previsto.
      razaoSla: horas == null ? null : horas / e.slaHoras,
      amostras: (duracoes[e.id] ?? []).length,
    };
  });

  const comMedia = tempos.filter((t) => t.razaoSla != null);
  const gargalo = comMedia.length
    ? comMedia.reduce((pior, t) => (t.razaoSla > pior.razaoSla ? t : pior))
    : null;

  /* --- pendências ----------------------------------------------------- */
  const pendentes = emCurso
    .filter((i) => estaPendente(i, agora))
    .map((i) => ({
      ...i,
      horasParado: (agora - new Date(i.atualizadoEm)) / 36e5,
      slaHoras: definicaoEtapa(i.etapaAtual)?.slaHoras ?? null,
    }))
    .sort((a, b) => b.horasParado - a.horasParado);

  /* --- recortes por município e por categoria ------------------------- */
  const porMunicipio = agrupar(itens, (i) => pontoPorId.get(i.pontoOrigemId)?.municipio ?? 'Não informado');
  const porCategoria = agrupar(itens, (i) => categoria(i.categoria)?.rotulo ?? i.categoria);

  /* --- tempo médio de ponta a ponta ----------------------------------- */
  const ciclos = processados
    .map((i) => (new Date(i.atualizadoEm) - new Date(i.criadoEm)) / 36e5)
    .filter((h) => h >= 0);

  return {
    totalItens: itens.length,
    totalProcessados: processados.length,
    totalEmCurso: emCurso.length,
    taxaConclusao: itens.length ? processados.length / itens.length : 0,
    massaTotalKg,
    massaDesviadaKg,
    massaEmCursoKg,
    porEtapa,
    materiais,
    co2eKg,
    tempos,
    gargalo,
    pendentes,
    porMunicipio,
    porCategoria,
    cicloMedioHoras: media(ciclos),
    municipiosAtendidos: new Set(pontos.map((p) => p.municipio)).size,
    totalPontos: pontos.length,
  };
}

/** Agrupa itens por uma chave, somando quantidade e peso. Ordena por peso. */
function agrupar(itens, chaveDe) {
  const mapa = new Map();
  for (const item of itens) {
    const chave = chaveDe(item);
    const atual = mapa.get(chave) ?? { chave, quantidade: 0, pesoKg: 0, processados: 0 };
    atual.quantidade++;
    atual.pesoKg += Number(item.pesoKg) || 0;
    if (item.etapaAtual === ETAPA_FINAL) atual.processados++;
    mapa.set(chave, atual);
  }
  return [...mapa.values()].sort((a, b) => b.pesoKg - a.pesoKg);
}

/**
 * Fatores usados para traduzir o CO2e em algo imaginável.
 *
 * Ficam exportados para que a tela que exibe o número possa exibir também de
 * onde ele saiu — um total sem a conta atrás dele é um número que ninguém
 * consegue conferir.
 */
export const EQUIVALENCIAS = {
  //: kg de CO2e por km rodado por um carro de passeio a combustão.
  kgPorKmDeCarro: 0.12,
  //: kg de CO2 que uma árvore nativa absorve em um ano.
  kgPorArvoreAno: 22,
};

/** Equivalências para tornar o CO2e compreensível na apresentação. */
export function equivalencias(co2eKg) {
  return {
    kmDeCarro: co2eKg / EQUIVALENCIAS.kgPorKmDeCarro,
    arvoresPorAno: co2eKg / EQUIVALENCIAS.kgPorArvoreAno,
  };
}

