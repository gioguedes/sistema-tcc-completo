// "J" invertido sobre o vidro. Coordenadas da caixa: a placa encosta nas costas
// da caixa (Z = 0) e o vidro fica entre a placa e a perna interna.
gancho_topo = ext[1] + 12;   // altura da borda do vidro
gancho_vao  = vidro_max + 1;

module gancho(x0 = 30, largura = 110, parafusos = [25, 85], furos_caixa = true) {
  difference() {
    translate([x0, 0, 0]) union() {
      translate([0, furos_caixa ? 30 : gancho_topo - 40, -5]) cube([largura, gancho_topo - (furos_caixa ? 30 : gancho_topo - 40), 5]);
      translate([0, gancho_topo, -5 - gancho_vao - 6]) cube([largura, 6, 11 + gancho_vao]);
      translate([0, gancho_topo - 38, -5 - gancho_vao - 6]) cube([largura, 38, 6]);
    }
    for (p = parafusos) translate([x0 + p, gancho_topo - 20, -5 - gancho_vao - 7]) rosca(rosca_d, 8, folga = 0.35);
    if (furos_caixa) for (p = furos_gancho) translate([p[0], p[1], -6]) cylinder(d = m3_piloto, h = 7);
  }
}

module gancho_impressao(x0 = 30, largura = 110, parafusos = [25, 85], furos_caixa = true)
  rotate([0, -90, 0]) translate([-x0, 0, 0]) gancho(x0, largura, parafusos, furos_caixa);
