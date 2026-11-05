// Fila circular FIFO de leituras em RAM -- CT03 / RNF04 do TC1.
// Cheia, descarta a MAIS ANTIGA (janela deslizante): perder a leitura mais velha
// e melhor que perder a mais nova, que e a que descreve a agua agora.
// BUFFER_CAPACIDADE x sizeof(Leitura) = 120 x 20 = 2,4 kB de RAM estatica,
// desprezivel nos ~320 kB do ESP32 (o firmware inteiro usa 7%).
#ifndef BUFFER_LEITURAS_H
#define BUFFER_LEITURAS_H

#include "config.h"
#include "sensores.h"

static Leitura bufItens[BUFFER_CAPACIDADE];
static int bufInicio = 0;            // indice da leitura mais antiga
static int bufTamanho = 0;
static int bufPico = 0;              // maior ocupacao ja atingida (evidencia do CT03)
static uint32_t bufDescartadas = 0;  // leituras perdidas por buffer cheio

inline int  bufferTamanho() { return bufTamanho; }
inline bool bufferVazio()   { return bufTamanho == 0; }
inline bool bufferCheio()   { return bufTamanho == BUFFER_CAPACIDADE; }
inline int  bufferPico()    { return bufPico; }
inline uint32_t bufferDescartadas() { return bufDescartadas; }

inline void bufferGuardar(const Leitura& l) {
  int fim = (bufInicio + bufTamanho) % BUFFER_CAPACIDADE;
  bufItens[fim] = l;
  if (bufTamanho < BUFFER_CAPACIDADE) {
    bufTamanho++;
    if (bufTamanho > bufPico) bufPico = bufTamanho;
  } else {
    // Acabamos de sobrescrever a mais antiga: o inicio anda para a seguinte,
    // senao a fila passaria a entregar a leitura nova como se fosse a velha.
    bufInicio = (bufInicio + 1) % BUFFER_CAPACIDADE;
    bufDescartadas++;
  }
}

inline Leitura bufferProxima() { return bufItens[bufInicio]; }

inline void bufferRemover() {
  if (bufTamanho == 0) return;
  bufInicio = (bufInicio + 1) % BUFFER_CAPACIDADE;
  bufTamanho--;
}

#endif
