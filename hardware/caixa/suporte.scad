// Suporte das sondas, do lado de dentro do aquario. Coordenadas proprias: face
// interna do vidro em Z = 0, agua em Z > 0, borda do vidro em Y = 0.
suporte_largura = 40;
guia_y = [-75, -25];
braco_secao = [12, 6];

module presilha_suporte() {
  l = suporte_largura;
  difference() {
    union() {
      translate([0, -75, 0]) cube([l, 75, 6]);                            // placa dentro d'agua
      translate([0, 0, -vidro_max - 1 - 6]) cube([l, 6, vidro_max + 13]); // ponte sobre a borda
      translate([0, -30, -vidro_max - 1 - 6]) cube([l, 30, 6]);           // perna por fora
      translate([0, guia_y[0], 6]) cube([l, guia_y[1] - guia_y[0], 16.6]); // guia do braco
    }
    translate([l / 2, -15, -vidro_max - 8]) rosca(rosca_d, 8, folga = 0.35);
    translate([l / 2 - braco_secao[0] / 2 - folga, guia_y[0] - 1, 8])
      cube([braco_secao[0] + 2 * folga, guia_y[1] - guia_y[0] + 2, braco_secao[1] + 2 * folga]);
    translate([l / 2, (guia_y[0] + guia_y[1]) / 2, 14]) rosca(rosca_d, 10, folga = 0.35);
  }
}

// Braco com a cabeca das sondas. Cabeca horizontal com o aquario montado.
module braco(comprimento = 160) {
  translate([-braco_secao[0] / 2, 0, 0]) cube([braco_secao[0], comprimento, braco_secao[1]]);
  difference() {
    translate([-40, 0, 0]) cube([80, 5, 50]);
    // pH: o tubo passa, a parte grossa (17 mm) apoia por cima
    translate([-26, -1, 25]) rotate([-90, 0, 0]) cylinder(d = ph_eletrodo_d + 0.4, h = 7);
    // temperatura: furo justo com fenda, funciona como presilha
    translate([-10, -1, 42]) rotate([-90, 0, 0]) cylinder(d = temp_d + 0.1, h = 7);
    translate([-10.5, -1, 42]) cube([1, 7, 10]);
    // turbidez: o corpo passa e a tampa azul apoia por cima
    translate([18 - (turb_corpo[0] + 0.6) / 2, -1, 25 - (turb_corpo[1] + 0.6) / 2])
      cube([turb_corpo[0] + 0.6, 7, turb_corpo[1] + 0.6]);
  }
}

module braco_impressao(comprimento = 160) translate([40, 0, 0]) braco(comprimento);

module presilha_impressao() rotate([0, -90, 0]) presilha_suporte();
