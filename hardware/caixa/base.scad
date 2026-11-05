module contorno_externo(h) {
  linear_extrude(h) {
    retangulo_arredondado([ext[0], ext[1]], raio);
    for (o = orelhas) hull() {
      translate(o) circle(d = 9);
      translate([o[0] - 4.5, o[1] < 0 ? 0 : ext[1] - 1]) square([9, 1]);
    }
  }
}

module recorte_fenda(f) {
  w = f[2]; z0 = f[3]; h = ext[2] - z0 + 1;
  if (f[0] == "esq")   translate([-1, f[1] - w / 2, z0]) cube([parede + 2, w, h]);
  if (f[0] == "dir")   translate([ext[0] - parede - 1, f[1] - w / 2, z0]) cube([parede + 2, w, h]);
  if (f[0] == "baixo") translate([f[1] - w / 2, -1, z0]) cube([w, parede + 2, h]);
}

// lados = [esquerda, direita, baixo, cima]
module berco(pos, tam, lados = [1, 1, 1, 1], h = 4, t = 1.2) {
  x0 = pos[0] - folga - t; y0 = pos[1] - folga - t;
  x1 = pos[0] + tam[0] + folga; y1 = pos[1] + tam[1] + folga;
  translate([0, 0, fundo]) {
    if (lados[0]) translate([x0, y0, 0]) cube([t, y1 - y0 + t, h]);
    if (lados[1]) translate([x1, y0, 0]) cube([t, y1 - y0 + t, h]);
    if (lados[2]) translate([x0, y0, 0]) cube([x1 - x0 + t, t, h]);
    if (lados[3]) translate([x0, y1, 0]) cube([x1 - x0 + t, t, h]);
  }
}

module internos_base() {
  // aba onde a protoboard descansa com a caixa pendurada
  translate([20, pb_pos[1] - folga - 1.6, fundo]) cube([130, 1.6, 6]);
  berco(rele_pos, rele);
  berco(turb_pos, turb_placa);
  // plataforma para o plugue BNC nao raspar no fundo; sem parede a direita, onde passa o plugue
  translate([ph_pos[0], ph_pos[1], fundo]) cube([ph_placa[0], ph_placa[1], ph_plataforma]);
  translate([0, 0, ph_plataforma]) berco(ph_pos, ph_placa, lados = [1, 0, 1, 1]);
  translate([14, 32, fundo]) rotate(90) ancora_abracadeira();   // cabo da temperatura
  translate([57, 12, fundo]) ancora_abracadeira();              // cabo da turbidez
}

module base() {
  difference() {
    union() {
      difference() {
        contorno_externo(ext[2]);
        translate([parede, parede, fundo]) cube([interno[0], interno[1], ext[2]]);
      }
      internos_base();
      // ancora externa: segura o cabo USB para o puxao nao chegar ao ESP32
      translate([-6, 58, 0]) difference() {
        cube([6.5, 8, 14]);
        translate([-1, -1, 7]) cube([5.5, 10, 2]);
      }
    }
    for (f = fendas) recorte_fenda(f);
    for (o = orelhas) translate([o[0], o[1], ext[2] - 14]) cylinder(d = m3_piloto, h = 15);
    for (p = furos_gancho) translate([p[0], p[1], -1]) cylinder(d = m3_passante, h = fundo + 2);
  }
}
