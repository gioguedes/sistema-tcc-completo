module lingueta(f) {
  w = f[2] - 2 * folga; z0 = f[4]; h = ext[2] - z0;
  if (f[0] == "esq")   translate([0, f[1] - w / 2, z0]) cube([parede, w, h]);
  if (f[0] == "dir")   translate([ext[0] - parede, f[1] - w / 2, z0]) cube([parede, w, h]);
  if (f[0] == "baixo") translate([f[1] - w / 2, 0, z0]) cube([w, parede, h]);
}

module moldura(centro, tam, h, t = 1.2) {
  translate([centro[0] - tam[0] / 2 - t, centro[1] - tam[1] / 2 - t, ext[2] - h])
    difference() {
      cube([tam[0] + 2 * t, tam[1] + 2 * t, h]);
      translate([t, t, -1]) cube([tam[0], tam[1], h + 2]);
    }
}

// Modelada na posicao montada; tampa_impressao() vira para a face externa ficar na mesa.
module tampa() {
  difference() {
    union() {
      translate([0, 0, ext[2]]) contorno_externo(tampa_esp);
      // aba que entra por dentro das paredes contra respingo
      translate([parede + folga, parede + folga, ext[2] - 3]) difference() {
        cube([interno[0] - 2 * folga, interno[1] - 2 * folga, 3]);
        translate([1.2, 1.2, -1]) cube([interno[0] - 2 * folga - 2.4, interno[1] - 2 * folga - 2.4, 5]);
      }
      for (f = fendas) lingueta(f);
      moldura(oled_pos, oled_placa + [2 * folga, 2 * folga], 3);
      moldura(silica_pos, silica_tam, 6);
      // abas que seguram o sache de silica
      for (s = [-1, 1])
        translate([silica_pos[0] - silica_tam[0] / 2, silica_pos[1] + s * (silica_tam[1] / 2 - 0.75) - 0.75, ext[2] - 6])
          cube([silica_tam[0], 1.5, 1.2]);
    }
    for (o = orelhas) translate([o[0], o[1], ext[2] - 1]) cylinder(d = m3_passante, h = tampa_esp + 2);
    translate([oled_pos[0] - (oled_tela[0] + 1) / 2, oled_pos[1] - (oled_tela[1] + 1) / 2, ext[2] - 1])
      cube([oled_tela[0] + 1, oled_tela[1] + 1, tampa_esp + 2]);
    translate([led_pos[0], led_pos[1], ext[2] - 1]) cylinder(d = 8, h = tampa_esp + 2);
    for (p = concat([[0, 0]], [for (a = [0:60:359]) [5 * cos(a), 5 * sin(a)]]))
      translate([buzzer_pos[0] + p[0], buzzer_pos[1] + p[1], ext[2] - 1]) cylinder(d = 2, h = tampa_esp + 2);
  }
}

module tampa_impressao() translate([0, ext[1], ext[2] + tampa_esp]) rotate([180, 0, 0]) tampa();
