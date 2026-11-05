// Caixa do no sensor. Escolha a peca com -D 'peca="base"' (ver gerar.ps1).
include <medidas.scad>
include <comum.scad>
include <base.scad>
include <tampa.scad>
include <gancho.scad>
include <suporte.scad>

peca = "montagem";

if (peca == "base")             base();
if (peca == "tampa")            tampa_impressao();
if (peca == "gancho")           gancho_impressao();
if (peca == "parafuso")         parafuso_aperto();
if (peca == "suporte_presilha") presilha_impressao();
if (peca == "suporte_braco")    braco_impressao();

// Provas rapidas para conferir folgas antes das pecas grandes
if (peca == "prova_tampa")   intersection() { tampa_impressao(); translate([120, -10, -1]) cube([70, 60, 30]); }
if (peca == "prova_base")    intersection() { base(); translate([140, 80, -1]) cube([50, 50, 100]); }
if (peca == "prova_gancho")  gancho_impressao(0, 25, [12.5], false);
if (peca == "prova_suporte") intersection() { braco_impressao(); translate([-1, -1, -1]) cube([90, 12, 60]); }

vidro_esp = 6;   // so para a vista da montagem

if (peca == "montagem") rotate([90, 0, 0]) {
  color("SteelBlue") base();
  color("LightSteelBlue", 0.6) tampa();
  color("Orange") gancho();
  color("LightBlue", 0.3) translate([-20, 0, -5 - vidro_esp]) cube([300, gancho_topo, vidro_esp]);
  translate([200, gancho_topo, -5 - vidro_esp]) mirror([0, 0, 1]) {
    color("Orange") presilha_suporte();
    color("Gold") translate([suporte_largura / 2, -150, 8 + folga]) braco();
  }
}
