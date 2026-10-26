/** Gera e baixa um CSV no padrão do Excel em português (";" e vírgula decimal). */
export function baixarCsv(nomeArquivo: string, cabecalho: string[], linhas: (string | number)[][]) {
  const celula = (valor: string | number) => {
    const texto = typeof valor === 'number' ? String(valor).replace('.', ',') : valor
    return /[";\n]/.test(texto) ? `"${texto.replace(/"/g, '""')}"` : texto
  }
  const conteudo = [cabecalho, ...linhas].map((linha) => linha.map(celula).join(';')).join('\r\n')
  // BOM para o Excel reconhecer UTF-8 (acentos).
  const arquivo = new Blob(['﻿', conteudo], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(arquivo)
  const link = document.createElement('a')
  link.href = url
  link.download = nomeArquivo
  link.click()
  URL.revokeObjectURL(url)
}

export function nomeDeArquivo(texto: string): string {
  return texto
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
}
