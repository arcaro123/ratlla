# RATLLA — Premium Strategy Collection

Versió integrada de les fases 1–8. Projecte Pygame amb interfície en català.

## Executar en local
1. Fes una còpia de seguretat del repositori i del fitxer de desament existent (`~/.jocs_de_taula.json`).
2. Copia el contingut d'aquesta carpeta al projecte original, conservant els recursos i la configuració de publicació que ja tenia. No eliminis les dades desades.
3. Instal·la les dependències: `python -m pip install -r requirements.txt`.
4. Executa `python main.py` des de la carpeta del projecte.

## Web: Pygbag i GitHub Pages
Conserva el mateix domini i la mateixa URL per mantenir l'accés al localStorage original. Conserva també el workflow i configuració originals. Instal·la Pygbag (`python -m pip install pygbag`) i prova en local amb `python -m pygbag .`. Si el joc funciona, utilitza el procés de publicació del teu repositori. Inclou main.py, els quatre mòduls ratlla_*.py i assets/. No s'ha executat el build web en aquest entorn. El mode online ja apareixia desactivat en el menú original; no s'ha habilitat ni s'ha provat Firebase.

## Canvis
- Fases 1–3: biblioteca rectangular, portades, menús de selecció, dificultats.
- Fases 4–5: materials, taulers, fitxes, revisions de 4 en ratlla i Dino Run.
- Fase 6: assoliments, estadístiques derivades de dades reals i partides desades.
- Fase 7: 42 lliçons existents amb presentació premium, exemples interactius, animació de caiguda i salt, transicions i efectes sonors originals; preferències de so, volum i moviment.
- Fase 8: desament local amb fitxer temporal i substitució, memòria cau de sprites amb límit, reutilització de la textura de cova, límit de delta de temps després de suspendre, revisió de la sintaxi i regressions aïllades.

## Proves i limitacions
Consulta VALIDACIO.md. Aquesta versió és candidata a validació, no una versió certificada en Pygame o GitHub Pages. No s'ha pogut instal·lar Pygame en l'entorn de treball. Les previsualitzacions s'han fet amb un adaptador Pillow. Les animacions de moviment de Morris i 4 en ratlla ja existien; els altres jocs no tenen totes les animacions específiques de captura i moviment descrites a la proposta inicial. Les imatges de portades són decoratives i no s'han de prendre com a posicions legals de joc.

## Recursos
Portades, materials i art nou creats per al projecte. Sons WAV sintetitzats originalment per al projecte; no s'hi incorpora música de tercers. Les fonts són de sistema i no es redistribueixen. La llicència dels recursos incrustats en el codi original no consta en els arxius rebuts; cal verificar-la abans d'una distribució comercial.

## Retoc final de la botiga
Només hi ha Fons, Taulers, Fitxes, Marques i Victòria. Packs i Extres no es poden comprar ni equipar des de la botiga. Es conserva el catàleg intern per compatibilitat amb el codi antic, els articles adquirits i l’inventari de consumibles existent; no s’elimina cap dada desada.

## Emblema final
El menú principal incorpora l’emblema celestial facilitat pel jugador, amb fons transparent i sense modificar el nom RATLLA.

## Revisió 2 — correccions posteriors a la primera prova real
- Dino Run: cos i dues cames separats amb 12 fotogrames de carrera i postures a l’aire, sis aparences, terra nou, fons diferenciats, indicadors dels obstacles. El personatge es manté a l’esquerra perquè és un corredor automàtic; el terreny i els obstacles es desplacen. Alguns obstacles especials conserven art estilitzat.
- So: efectes WAV estèreo amb envolupant suau, un canal, volum reduït i límit de repetició. El comptador de fotogrames de Dino ja no dispara sons de moviment.
- Botiga: 21 fons, 22 taulers, 18 estils de fitxes, 14 marques i 11 efectes de victòria. Afegits 7 fons, 4 taulers, 4 estils de fitxes, 3 marques i 3 efectes. Els preus nous són una proposta; es conserven els preus i identificadors antics. Packs i extres continuen desactivats.
- Biblioteca: emblema més gran, estadístiques al peu de la barra lateral, recuperació de les portades originals d’Escacs, Go, Shogi i Dino; 4 en ratlla conserva la portada millorada. Morris i Buscamines mantenen les portades de la versió premium, perquè no hi ha imatges originals independents incrustades per a aquests dos jocs.
- Resultats: estil diferenciat segons victòria, derrota o resultat neutre, mantenint les dades i botons originals.
- Conserva el domini i la ruta de publicació, i fes còpia de seguretat de les dades. No s’inclouen fitxers de desament nous.
