// Medidas da bancada tiradas em 17/10/2026, em mm. "estimado" = ainda nao medido.
$fn = 48;

protoboard    = [163, 54, 10];
usb_plugue    = [12.4, 6.3];
ph_placa      = [43, 32, 14];
ph_plugue_ate = 70;        // do inicio da placa ate o fim do plugue metalico do BNC
ph_plugue_d   = 15;        // estimado
turb_placa    = [37, 33, 35];
rele          = [45, 17, 20];
oled_placa    = [26, 24];
oled_tela     = [24, 13];
ph_eletrodo_d = 12.1;
temp_d        = 5.8;
temp_cabo_d   = 4;         // estimado
turb_corpo    = [32, 27];  // estimado: secao do corpo transparente, abaixo da tampa azul
turb_cabo     = [8, 2];    // estimado: cabo achatado

parede = 2.4; fundo = 2.4; tampa_esp = 3; folga = 0.3; raio = 3;
interno = [165, 100, 48];
ext = [interno[0] + 2 * parede, interno[1] + 2 * parede, interno[2] + fundo];
m3_piloto = 2.5; m3_passante = 3.4;

// Arranjo, em coordenadas da base: origem no canto externo, Y para cima com a
// caixa pendurada, Z saindo do vidro para a tampa.
pb_pos   = [parede + 1, parede + interno[1] - protoboard[1] - 1];
rele_pos = [6, parede + 2];
turb_pos = [64, parede + 2];
ph_pos   = [parede + interno[0] - (ph_plugue_ate - 8), parede + 2];
ph_plataforma = 2;
ph_bnc_z = fundo + ph_plataforma + 7;

// [parede, posicao ao longo dela, largura, z do fundo da fenda, z da ponta da lingueta]
fendas = [
  ["esq",   12,   7,                   fundo + 1, fundo + 7],     // aerador (reserva)
  ["esq",   32,   temp_cabo_d + 1.5,   fundo + 1, fundo + 1.5 + temp_cabo_d],
  ["esq",   74.4, usb_plugue[0] + 3.5, 13.5,      22],            // USB, posicao estimada
  ["baixo", 57,   turb_cabo[0] + 1.5,  fundo + 1, fundo + 1.5 + turb_cabo[1]],
  ["dir",   ph_pos[1] + ph_placa[1] / 2, ph_plugue_d + 2,
            ph_bnc_z - ph_plugue_d / 2 - 0.5, ph_bnc_z + ph_plugue_d / 2 + 0.5],
];

orelhas      = [[14, -3.5], [156, -3.5], [14, ext[1] + 3.5], [156, ext[1] + 3.5]];
furos_gancho = [[40, 42], [130, 42]];

led_pos    = [123, 88];   // estimado: medir na bancada
buzzer_pos = [84, 77];    // estimado
oled_pos   = [150, 74];
silica_pos = [35, 74];
silica_tam = [40, 30];

vidro_max = 15;
rosca_d   = 10;
