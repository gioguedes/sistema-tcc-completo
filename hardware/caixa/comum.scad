module retangulo_arredondado(tam, r) offset(r) offset(-r) square(tam);

// Rosca grossa imprimivel: circulo excentrico torcido. A femea e o mesmo solido
// com folga, subtraido.
module rosca(d, h, passo = 3, excentrico = 0.75, folga = 0) {
  linear_extrude(height = h, twist = -360 * h / passo, slices = ceil(h / passo * 24), convexity = 4)
    translate([excentrico, 0]) circle(d = d - 2 * excentrico + 2 * folga, $fn = 40);
}

// Bloco com tunel ao longo de X para a abracadeira de nylon.
module ancora_abracadeira() {
  difference() {
    translate([-4, -3.5, 0]) cube([8, 7, 5]);
    translate([-5, -2.5, 1.2]) cube([10, 5, 2]);
  }
}

module parafuso_aperto(comprimento = 24) {
  difference() {
    cylinder(d = 20, h = 8);
    for (a = [0:30:359]) rotate(a) translate([10.5, 0, -1]) cylinder(d = 3, h = 10);
  }
  translate([0, 0, 8]) rosca(rosca_d, comprimento);
}
