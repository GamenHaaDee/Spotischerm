// SpotiScherm: behuizing voor aan de muur
// ------------------------------------------
// Twee delen: een voorkant (rand om het scherm) en een achterbak (Pi, ventilator,
// USB-C-ingang). Ze worden met 4 schroeven M3x10 van achteren aan elkaar gezet.
// Daarnaast 4 voetjes die de bak 8 mm van de muur houden, zodat de ventilator
// zijn warme lucht kwijt kan.
//
// Optioneel (aan/uit in de Customizer): keystone-poorten onderin voor USB of netwerk,
// een volumeknop (draaiknop EC11) in de rechterzijkant en een bewegingssensor (mini-PIR)
// in de onderkant, die schuin naar voren de kamer in kijkt.
//
// Alle maten in mm. Pas in OpenSCAD de waarden aan via Window > Customizer.
// MEET JE EIGEN SCHERM OP: de standaardwaarden zijn voor een gangbaar 7"-HDMI-scherm
// (zoals het Waveshare 7inch HDMI LCD (C)), maar elk merk is net anders.
//
// Printen: de achterbak met de achterkant op het bed, de voorkant met de voorkant
// op het bed. Geen support nodig. PETG is beter dan PLA als het scherm warm wordt.
//
// Onderdelen:
//  - 4x M3x10 schroef (cilinderkop) om voor en achter te verbinden
//  - 4x M2.5x6 schroef voor de Pi (of zelftappend)
//  - Noctua NF-A4x10 5V (40x40x10 mm) + 4x M3x16 met moer, of de schroeven van Noctua
//  - Adafruit 4056: USB-C (female) naar micro-B (male), met de 2 M3-schroefjes die erbij zitten
//  - dun schuimtape om het scherm stevig in de voorkant te klemmen
//  - optioneel: keystone-modules (USB-A en/of RJ45) met een kort kabeltje naar de Pi,
//    een EC11-draaiknop met drukknop, en een mini-PIR (bijv. AM312)

/* [Wat laten zien] */
// printen = alle delen naast elkaar, samen = in elkaar gezet, test_* = proefstukjes
deel = "samen"; // [samen, printen, voor, achter, voetjes, test_usbc, test_keystone, test_knop]

/* [Scherm] */
// Breedte van de schermmodule (het grootste: glas of printplaat)
scherm_b = 164.9;
// Hoogte van de schermmodule
scherm_h = 100.0;
// Dikte van de module aan de rand (glas + paneel); dit deel valt in de voorkant
scherm_d = 6.0;
// Zichtbaar beeld: het actieve gebied plus ~1 mm
zicht_b = 156.0;
zicht_h = 88.0;
// Ligt het beeld niet in het midden van de module? Verschuif het venster hiermee
zicht_dx = 0;
zicht_dy = 0;

/* [Behuizing] */
wand = 2.4;
// Ruimte tussen scherm en buitenwand, voor de schroeven
rand = 7;
// Speling rondom het scherm
speling = 0.4;
// Dikte van de voorplaat over de rand van het scherm
voorplaat = 2.0;
// Binnenruimte achter het scherm (Pi + stekkers: minstens 30)
diepte_achter = 32;
// Hoeveel de achterbak over de rand van het scherm valt om het vast te klemmen
klem = 3;
hoekstraal = 3;
// Afstand tot de muur (hoogte van de voetjes), nodig voor de ventilator
afstand_muur = 8;

/* [Raspberry Pi] */
// Plek van de printplaat (linksonder), gemeten vanaf de binnenkant van de wanden.
// De Pi ligt met de kant met HDMI en voeding naar onderen.
pi_x = 14;
pi_y = 28;
// Gaten van de Pi 2B, 3B, 3B+, 4 en 1B+ (58 x 49 mm). De allereerste Pi 1 Model B heeft
// een ander gatenpatroon: meet dat zelf op en vul het hier in.
pi_gaten = [[3.5, 3.5], [61.5, 3.5], [3.5, 52.5], [61.5, 52.5]];
pi_hoogte = 5;

/* [Ventilator] */
ventilator = true;
fan_maat = 40;
fan_gaten = 32;
// Afstand van de ventilator tot de binnenkant van de rechter- en bovenwand
fan_marge = 8;

/* [USB-C-ingang (onderkant)] */
usbc_b = 11;
usbc_h = 5;
// Afstand tussen de twee schroefoortjes
usbc_oor = 20;
// Plek van het midden, gemeten vanaf de linker buitenkant
usbc_x = 40;

/* [Extra poorten onderin (keystone)] */
// Aantal keystone-gaten in de onderkant (0 = geen). Er past elke keystone-module in:
// USB-A, RJ45 (netwerk), HDMI... Binnenin een kort kabeltje naar de Pi.
keystones = 2; // [0:1:3]
// Afstand van het eerste gat tot de rechter binnenwand
keystone_rechts = 10;
// Hoogte van het midden, gemeten vanaf de achterkant (buitenkant)
keystone_z = 15;
// Standaard keystone-uitsparing (breedte x hoogte); bij een te strakke klik 0,2 mm groter maken
keystone_b = 14.9;
keystone_h = 16.3;
// Keystones klikken in een plaat van ~1,5-2,2 mm: de wand wordt rond het gat zo dun
keystone_wand = 1.8;

/* [Volumeknop (zijkant)] */
volumeknop = true;
// Gat voor de as/schroefbus van een EC11-draaiknop (M7)
knop_gat = 7.2;
// Plek op de rechterzijkant: hoogte vanaf de onderkant (buitenkant) en vanaf de achterkant
knop_y = 48;
knop_z = 17;
// Gaatje voor het nokje dat de knop tegen draaien zet (0 = geen)
knop_nok = 2.6;
// Kommetje aan de buitenkant waar de moer in wegvalt, zodat alleen het knopje uitsteekt
knop_kom = 12.5;
knop_kom_diepte = 2;
// Ring aan de binnenkant, zodat de wand rond het gat sterk genoeg blijft
knop_ring = 18;

/* [Bewegingssensor (onderkant)] */
// Gat in de onderkant voor een mini-PIR (bijv. AM312); de kegel van ~100 graden ziet de kamer in
bewegingssensor = true;
// Gat voor de lens
pir_gat = 10;
// Plek: vanaf de linker buitenkant, en hoogte vanaf de achterkant (hoe hoger, hoe dichter bij de voorkant)
pir_x = 62;
pir_z = 18;
// Kraag aan de binnenkant waar het printplaatje tegenaan komt (0 = geen)
pir_kraag = 14;

$fn = 48;

// ---- afgeleide maten ----
binnen_b = scherm_b + 2 * speling + 2 * rand;
binnen_h = scherm_h + 2 * speling + 2 * rand;
B = binnen_b + 2 * wand;
H = binnen_h + 2 * wand;
voor_d = scherm_d + voorplaat;
achter_d = wand + diepte_achter;
scherm_y = wand + rand;                        // onderkant van het schermvak
scherm_cy = scherm_y + speling + scherm_h / 2; // midden van het scherm

// Schroeven in het midden van de rand, iets van de hoeken af (de hoeken zijn rond)
c = (wand + rand) / 2;
schroeven = [[c, c + 10], [B - c, c + 10], [c, H - c - 10], [B - c, H - c - 10]];
voetjes = [[8, 8], [B - 8, 8], [8, H - 8], [B - 8, H - 8]];
fan_c = [B - wand - fan_marge - fan_maat / 2, H - wand - fan_marge - fan_maat / 2];
sleutelgaten = [[B / 2 - 35, H - wand - 22], [B / 2 + 35, H - wand - 22]];
// Keystones van rechts naar links in de onderkant
keystone_xs = keystones > 0
    ? [for (i = [0:keystones - 1]) B - wand - keystone_rechts - keystone_b / 2 - i * (keystone_b + 8)] : [];
keystone_links = keystones > 0 ? keystone_xs[keystones - 1] - keystone_b / 2 - 6 : B - 30;
// ventilatiesleuven onderin pas na de USB-C-ingang en de bewegingssensor
sleuf_start = bewegingssensor ? pir_x + pir_gat / 2 + 6 : 62;

module rrect(b, h, r) {
    translate([r, r]) offset(r = r) square([b - 2 * r, h - 2 * r]);
}

// ================= voorkant =================
module voor() {
    difference() {
        linear_extrude(voor_d) rrect(B, H, hoekstraal);
        // vak voor het scherm, open naar achteren
        translate([wand + rand, scherm_y, -1])
            cube([scherm_b + 2 * speling, scherm_h + 2 * speling, scherm_d + 1]);
        // venster, schuin naar voren zodat de rand niet in beeld valt
        hull() {
            translate([B / 2 + zicht_dx - zicht_b / 2, scherm_cy + zicht_dy - zicht_h / 2, scherm_d - 0.01])
                cube([zicht_b, zicht_h, 0.01]);
            translate([B / 2 + zicht_dx - zicht_b / 2 - voorplaat, scherm_cy + zicht_dy - zicht_h / 2 - voorplaat, voor_d])
                cube([zicht_b + 2 * voorplaat, zicht_h + 2 * voorplaat, 0.01]);
        }
        // voorgaten voor M3 (niet door de voorkant heen)
        for (p = schroeven) translate([p[0], p[1], -1]) cylinder(d = 2.5, h = voor_d - 0.8 + 1);
    }
}

// ================= achterbak =================
module klemrand() {
    // Een schuine rand bovenin die het scherm in de voorkant drukt. 45 graden: print zonder support.
    L = rand + speling + klem;
    z0 = achter_d - L;
    difference() {
        translate([wand, wand, z0]) cube([binnen_b, binnen_h, L]);
        hull() {
            translate([wand + rand + speling + klem, scherm_y + speling + klem, achter_d - 0.01])
                cube([scherm_b - 2 * klem, scherm_h - 2 * klem, 0.02]);
            translate([wand - 0.01, wand - 0.01, z0 - 0.01]) cube([binnen_b + 0.02, binnen_h + 0.02, 0.02]);
        }
    }
}

module sleutelgat() {
    // Rond gat voor de schroefkop, daarboven de sleuf waar de bak in zakt.
    cylinder(d = 8.5, h = wand + 2);
    translate([-2.1, 0, 0]) cube([4.2, 9, wand + 2]);
    translate([0, 9, 0]) cylinder(d = 4.2, h = wand + 2);
}

module keystone_gat() {
    // Uitsparing door de onderwand, met van binnen een dunner stuk wand waar de module in klikt.
    translate([-keystone_b / 2, -1, -keystone_h / 2]) cube([keystone_b, wand + 2, keystone_h]);
    translate([-keystone_b / 2 - 4, keystone_wand, -keystone_h / 2 - 4]) cube([keystone_b + 8, wand, keystone_h + 8]);
}

module knop_gat_vorm() {
    // EC11: gat voor de schroefbus (door wand + ring), een gaatje voor het nokje, en
    // aan de buitenkant een kommetje voor de moer.
    rotate([0, 90, 0]) {
        translate([0, 0, -knop_kom_diepte - 1]) cylinder(d = knop_gat, h = wand + knop_kom_diepte + 3);
        if (knop_nok > 0) translate([0, 7.8, -knop_kom_diepte]) cylinder(d = knop_nok, h = wand + 1);
        translate([0, 0, wand + 1 - knop_kom_diepte]) cylinder(d = knop_kom, h = knop_kom_diepte + 1);
    }
}

module achter() {
    difference() {
        union() {
            difference() {
                linear_extrude(achter_d) rrect(B, H, hoekstraal);
                translate([wand, wand, wand]) linear_extrude(achter_d)
                    rrect(binnen_b, binnen_h, max(hoekstraal - wand, 0.5));
            }
            klemrand();
            // kolommen voor de schroeven naar de voorkant
            for (p = schroeven) translate([p[0], p[1], 0]) cylinder(d = 8.4, h = achter_d);
            // kraag rond de bewegingssensor, binnenin tegen de onderwand
            if (bewegingssensor && pir_kraag > 0) translate([pir_x, wand - 0.01, pir_z]) rotate([-90, 0, 0])
                difference() { cylinder(d = pir_kraag + 3, h = 3); translate([0, 0, -1]) cylinder(d = pir_kraag, h = 5); }
            // ring rond de volumeknop, binnen tegen de rechterwand
            if (volumeknop) translate([B - wand - knop_kom_diepte + 0.01, knop_y, knop_z]) rotate([0, 90, 0])
                cylinder(d = knop_ring, h = knop_kom_diepte);
            // afstandhouders voor de Pi
            for (g = pi_gaten) translate([wand + pi_x + g[0], wand + pi_y + g[1], wand - 0.01])
                cylinder(d = 6, h = pi_hoogte);
        }
        // schroefgaten: van achteren een diepe koker voor de kop, bovenin 4 mm vloer
        for (p = schroeven) translate([p[0], p[1], 0]) {
            translate([0, 0, -1]) cylinder(d = 6.2, h = achter_d - 4 + 1);
            translate([0, 0, -1]) cylinder(d = 3.4, h = achter_d + 2);
        }
        // gaatjes voor M2.5 in de afstandhouders (niet door de achterwand)
        for (g = pi_gaten) translate([wand + pi_x + g[0], wand + pi_y + g[1], wand + 0.6])
            cylinder(d = 2.3, h = pi_hoogte + 1);
        // ventilator: rooster en schroefgaten
        if (ventilator) translate([fan_c[0], fan_c[1], -1]) {
            for (i = [-3:3], j = [-3:3])
                if (norm([i, j]) * 6.2 < fan_maat / 2 - 4)
                    translate([i * 6.2, j * 6.2, 0]) cylinder(d = 5, h = wand + 2, $fn = 6);
            for (sx = [-1, 1], sy = [-1, 1])
                translate([sx * fan_gaten / 2, sy * fan_gaten / 2, 0]) cylinder(d = 3.3, h = wand + 2);
        }
        // ophangen
        for (k = sleutelgaten) translate([k[0], k[1], -1]) sleutelgat();
        // gaatjes voor de voetjes
        for (v = voetjes) translate([v[0], v[1], -1]) cylinder(d = 3.3, h = wand + 2);
        // ventilatiesleuven: onder lucht erin (niet bij de keystones), boven eruit
        for (x = [sleuf_start:6:keystone_links - 3]) translate([x, -1, wand + 4]) cube([2.5, wand + 2, 14]);
        for (x = [30:6:B - 30]) translate([x, H - wand - 1, wand + 4]) cube([2.5, wand + 2, 14]);
        // USB-C-ingang in de onderkant
        translate([usbc_x, -1, wand + 12]) usbc_gat();
        // extra poorten onderin
        for (x = keystone_xs) translate([x, 0, keystone_z]) keystone_gat();
        // bewegingssensor in de onderkant
        if (bewegingssensor) translate([pir_x, -1, pir_z]) rotate([-90, 0, 0]) cylinder(d = pir_gat, h = wand + 2);
        // volumeknop in de rechterzijkant
        if (volumeknop) translate([B - wand - 1, knop_y, knop_z]) knop_gat_vorm();  // binnenkant wand op x = -1
    }
}

module usbc_gat() {
    rotate([-90, 0, 0]) {
        linear_extrude(wand + 2) offset(r = 1) square([usbc_b - 2, usbc_h - 2], center = true);
        for (s = [-1, 1]) translate([s * usbc_oor / 2, 0, 0]) cylinder(d = 3.3, h = wand + 2);
    }
}

// ================= kleine delen =================
module voetje() {
    // Wordt in een gaatje in de achterwand gedrukt (eventueel met een druppel lijm).
    cylinder(d = 12, h = afstand_muur);
    translate([0, 0, afstand_muur - 0.01]) cylinder(d = 3.0, h = wand);
}

module test_usbc() {
    // Proefstukje: print dit eerst en kijk of de USB-C-bus er goed in past.
    difference() {
        translate([-20, 0, -8]) cube([40, wand, 16]);
        translate([0, -1, 0]) usbc_gat();
    }
}

module test_keystone() {
    // Proefstukje: klikt je keystone-module er goed in?
    difference() {
        translate([-15, 0, -15]) cube([30, wand, 30]);
        keystone_gat();
    }
}

module test_knop() {
    // Proefstukje: past de draaiknop, en zit het nokje goed?
    difference() {
        translate([0, -12, -12]) cube([wand, 30, 24]);
        translate([-1, 0, 0]) knop_gat_vorm();
    }
}

// ================= tonen =================
if (deel == "voor") {
    translate([0, 0, voor_d]) mirror([0, 0, 1]) voor();     // voorkant op het bed
} else if (deel == "achter") {
    achter();
} else if (deel == "voetjes") {
    for (i = [0:3]) translate([i * 16, 0, 0]) voetje();
} else if (deel == "test_usbc") {
    rotate([90, 0, 0]) test_usbc();
} else if (deel == "test_keystone") {
    rotate([90, 0, 0]) test_keystone();
} else if (deel == "test_knop") {
    rotate([0, -90, 0]) test_knop();
} else if (deel == "printen") {
    achter();
    translate([0, H + 10, voor_d]) mirror([0, 0, 1]) voor();
    for (i = [0:3]) translate([B + 15, 10 + i * 16, 0]) voetje();
} else {  // samen
    color("dimgray") achter();
    color("gray") translate([0, 0, achter_d]) voor();
    color("black", 0.8) translate([wand + rand + speling, scherm_y + speling, achter_d])
        cube([scherm_b, scherm_h, scherm_d]);
    color("green") translate([wand + pi_x, wand + pi_y, wand + pi_hoogte]) cube([85, 56, 1.6]);
    if (ventilator) color("sienna")
        translate([fan_c[0] - fan_maat / 2, fan_c[1] - fan_maat / 2, wand]) cube([fan_maat, fan_maat, 10]);
    for (x = keystone_xs) color("white") translate([x - 7.5, wand, keystone_z - 9]) cube([15, 30, 18]);
    // een laag knopje van 12 mm (bijv. aluminium, 6 mm hoog)
    if (volumeknop) color("silver") translate([B + 0.5, knop_y, knop_z]) rotate([0, 90, 0]) cylinder(d = 12, h = 6);
    if (bewegingssensor) color("white") translate([pir_x, 0, pir_z]) sphere(d = pir_gat - 1);
    for (v = voetjes) color("white") translate([v[0], v[1], 0]) mirror([0, 0, 1]) cylinder(d = 12, h = afstand_muur);
}
