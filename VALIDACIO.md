# Validació de la versió integrada

Proves efectuades amb un adaptador Pillow de les funcions gràfiques de Pygame, sense dispositiu SDL ni navegador.

- PASS: compilació de tots els fitxers Python.
- PASS: renderització dels 42 exemples de tutorial abans, durant i després de la revelació.
- PASS: configuració de so, volum i moviment, persistència en fitxer temporal i compatibilitat amb un desament sense preferències v7.
- PASS: dibuix inicial i actualització aïllada dels set jocs.
- PASS: inicialització dels 20 parells joc/dificultat de les IA i cinc modes locals. No equival a completar les partides ni a provar exhaustivament la IA.
- PASS: inicialització de tres modes Dino i sis modes Buscamines.
- PASS: desament i restauració de set jocs en fitxer temporal, amb migració Dino.
- PASS (versió anterior al retoc final): compra i reequipament dels sis packs nous sense doble cobrament. Aquestes categories ja no estan disponibles.
- PASS: les classes dels jocs són idèntiques per AST a la versió refinada de la fase 6.
- PASS: vuit fitxers WAV llegibles, no s'ha verificat la reproducció real.
- PASS: GIF del tutorial de 4 en ratlla generat amb les funcions de dibuix.

Pendent: Pygame real, reproducció d'àudio, FPS i memòria en dispositius reals, Pygbag, GitHub Pages, Firebase, prova de cada mode en partida completa, revisió de totes les resolucions. El mode online del menú original estava desactivat. No s'ha alterat l'URL de Firebase. Queden també animacions específiques per a captures i peces d'Escacs, Go i Shogi, i alguns acabats gràfics de les fases anteriors.

Retoc final: PASS navegació i renderització de les cinc categories, bloqueig de compra de Packs i Extres, compra ordinària, conservació dels articles i consumibles adquirits en desar i recarregar, i compilació Python. Proves aïllades amb l’adaptador Pillow, no amb Pygame real.

PASS: càrrega i renderització de l’emblema celestial amb transparència al menú, i repetició de les proves aïllades de la botiga de cinc categories.
