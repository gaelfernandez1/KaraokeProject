# Banco · base-legacy · jamendo · sin letra

- Fecha: 2026-10-29T09:33:48+01:00
- Commit: 2244468
- Banco 0.1.0, normalización v1
- Referencias: de manual, en manual, es manual, fr manual

## Entorno

| Clave | Valor |
|---|---|
| ctranslate2 | 4.8.4 |
| demucs | 4.0.1 |
| driver | 617.42 |
| faster-whisper | 1.2.1 |
| gpu | NVIDIA GeForce RTX 3050 Laptop GPU |
| gpu_memory_mb | 4096 |
| jiwer | 4.0.0 |
| numpy | 2.5.4 |
| platform | Linux-6.6.114.1-microsoft-standard-WSL2-x86_64-with-glibc2.43 |
| python | 3.12.16 |
| torch | 2.14.1+cu130 |
| transformers | 5.21.0 |

## Pipeline

Demucs + Whisper small (language detected) + default CTC aligner, like v2

- **separator**: `karaoke_bench.baseline.separation:DemucsSeparator` v2
- **transcriber**: `karaoke_bench.baseline.whisper:FasterWhisperTranscriber` v1 {'model': 'small', 'detect_language': True}
- **segmenter**: `karaoke_bench.baseline.segment:SegmentPerLine` v1
- **aligner**: `karaoke_bench.baseline.ctc:CtcAligner` v1

## Resumen

| Grupo | Canciones | Fallos | WER | CER | Inicio mediana | Inicio media | ≤ 0,3 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| de | 20 | 4 | 33.3 % | 20.6 % | 0.030 | 0.096 | 97.9 % | 0.076 | 0.000 | 79.0 % | — | 4 | 36 |
| en | 20 | 3 | 40.4 % | 27.8 % | 0.052 | 0.459 | 93.0 % | 0.065 | 0.172 | 78.5 % | — | 3 | 32 |
| es | 20 | 3 | 37.8 % | 23.6 % | 0.029 | 0.490 | 96.3 % | 0.093 | 0.303 | 75.9 % | — | 5 | 41 |
| fr | 19 | 0 | 40.8 % | 23.4 % | 0.030 | 0.198 | 96.8 % | 0.083 | -0.016 | 64.4 % | — | 1 | 35 |
| total | 79 | 10 | 38.2 % | 23.9 % | 0.034 | 0.315 | 95.9 % | 0.078 | 0.116 | 74.1 % | — | 13 | 36 |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 3.1 | 804 | 3080 | 0.060 |
| transcriber | 3.6 | 823 | 1372 | 0.040 |
| segmenter | — | 0 | 137 | 0.000 |
| aligner | — | 1559 | 5871 | 0.022 |

## Por canción

| Canción | Idioma | Duración | WER | Inicio mediana | ≤ 0,3 s | Cobertura | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|
| 10._Disparan_-_criatura | es | 160 | 99.5 % | — | — | — | sv | 37.6 | aligner: ValueError: no default alignment model for language 'sv' |
| 1_Freak_-_Automatisch_Gekommen | de | 188 | 27.0 % | 0.043 | 100.0 % | 74.7 % | de | 34.0 |  |
| Avercage_-_Embers | en | 243 | 89.2 % | — | — | — | nn | 78.6 | aligner: ValueError: no default alignment model for language 'nn' |
| Baila_-_Alfonso_Lugo | es | 210 | 51.8 % | 0.024 | 86.1 % | 68.8 % | es | 34.4 |  |
| Besando_Sapos_-_Dream_Tabu | es | 251 | 31.1 % | 0.029 | 99.4 % | 78.9 % | es | 30.3 |  |
| Bitte_beweg_dich_nicht_-_Bukto | de | 273 | 24.1 % | 0.036 | 97.5 % | 79.0 % | de | 32.5 |  |
| Burn_Out_Man_-_Abendblau | de | 260 | 22.7 % | 0.045 | 95.9 % | 74.2 % | de | 27.3 |  |
| CHRISTMAS_AVEC_TOI_-_imfreshyourepretty | fr | 234 | 51.9 % | 0.036 | 100.0 % | 52.0 % | fr | 26.3 |  |
| CLUB_DESTINO__-_Pensando_en_ti_-_CLUB_DESTINO | es | 219 | 104.9 % | 0.481 | 0.0 % | 0.5 % | en | 28.0 |  |
| Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique | de | 248 | 96.8 % | — | — | — | nn | 61.6 | aligner: ValueError: no default alignment model for language 'nn' |
| Capotes_à_un_Franc_-_elmanu | fr | 188 | 18.0 % | 0.024 | 100.0 % | 84.1 % | fr | 20.5 |  |
| Caralibro_-_Vagos_Permanentes | es | 279 | 100.0 % | — | — | — | nn | 115.8 |  |
| Color_Out_-_Falling_Star | en | 222 | 28.9 % | 0.145 | 93.3 % | 86.6 % | en | 19.1 |  |
| Confession_-_Quesabe | fr | 148 | 34.9 % | 0.027 | 98.7 % | 68.2 % | fr | 24.7 |  |
| Cortez_-_Feel__Stripped_ | en | 241 | 16.3 % | 0.062 | 96.4 % | 86.2 % | en | 27.5 |  |
| Culture_&_Co._-_cool.cavemen | fr | 212 | 97.4 % | 0.038 | 75.0 % | 3.0 % | pt | 53.5 |  |
| DON_VALDES_-_Tu_sais_Man | fr | 209 | 41.3 % | 0.034 | 93.0 % | 62.6 % | fr | 30.7 |  |
| Da_wurdest_du_geboren_-_Alice_Tlustos_ | de | 207 | 20.9 % | 0.053 | 99.2 % | 83.1 % | de | 23.6 |  |
| Der_Baum_-_Dienstag_is_Damensauna_(2) | de | 209 | 15.3 % | 0.027 | 100.0 % | 90.5 % | de | 25.5 |  |
| Der_Musiker_-_d-music | de | 271 | 95.6 % | — | — | — | cy | 44.8 | aligner: ValueError: no default alignment model for language 'cy' |
| Die_Revolution_gehört_Dir!_-_partysahnen | de | 167 | 50.9 % | 0.030 | 88.8 % | 51.3 % | de | 15.5 |  |
| Diosa_de_la_noche_-_Brunela_Crochenci | es | 230 | 19.9 % | 0.030 | 99.4 % | 83.6 % | es | 28.7 |  |
| Drei_Nüsse_-_patrouille | de | 259 | 10.8 % | 0.026 | 100.0 % | 89.2 % | de | 32.4 |  |
| En_liberté_-_tom.leyak | fr | 234 | 38.0 % | 0.033 | 100.0 % | 73.7 % | fr | 27.2 |  |
| Esencia_-_NandoMalo_ | es | 262 | 28.7 % | 0.022 | 96.8 % | 74.6 % | es | 33.8 |  |
| Explosive_Ear_Candy_-_Like_The_Sun | en | 193 | 85.0 % | 0.048 | 97.6 % | 94.0 % | en | 41.7 |  |
| Fantasma_-_Los_Rombos | es | 166 | 50.0 % | 0.193 | 52.9 % | 79.5 % | es | 16.7 |  |
| Freifliegen_-_durch.dick.und.duenn | de | 250 | 30.4 % | 0.032 | 98.3 % | 87.4 % | de | 25.4 |  |
| Fußabdrücke_-_Andreas_Jachmann | de | 241 | 18.8 % | 0.025 | 97.8 % | 90.3 % | de | 22.8 |  |
| Guayeteo_-_JhoyKing | es | 158 | 46.7 % | 0.026 | 98.1 % | 62.6 % | es | 21.2 |  |
| HILA_-_Give_Me_the_Same | en | 234 | 12.5 % | 0.056 | 94.3 % | 86.6 % | en | 22.2 |  |
| Háblame_-_(Talk_to_me)_-_Brunela_Crochenci | es | 214 | 118.9 % | — | — | — | cy | 36.6 | aligner: ValueError: no default alignment model for language 'cy' |
| Ich_kann_dich_nicht_vergessen_-_Wingenbach_Frank | de | 258 | 6.6 % | 0.028 | 99.5 % | 94.4 % | de | 26.8 |  |
| Intentando_Destacar_-_Sundayers_ | es | 220 | 40.2 % | 0.023 | 97.3 % | 67.0 % | es | 33.5 |  |
| Intro_[Pulsschlag]_-_Zeugen_der_Leere_(2) | de | 157 | 84.1 % | — | — | — | nn | 65.9 | aligner: ValueError: no default alignment model for language 'nn' |
| JASON_MILLER_-_CROWD_PLEASER | en | 193 | 22.8 % | 0.040 | 99.6 % | 86.2 % | en | 28.5 |  |
| Keine_Lust_-_Jonny_M | de | 229 | 30.3 % | 0.018 | 92.3 % | 71.0 % | de | 68.4 |  |
| Kinematic_-_Peyote | en | 183 | 46.5 % | 0.052 | 89.7 % | 85.7 % | en | 16.5 |  |
| LUNABLIND_-_Vision__Radio_Edit_ | en | 221 | 26.5 % | 0.069 | 74.9 % | 76.0 % | en | 28.4 |  |
| La_rumba_del_coronavirus_-_Rich_Don_Jeri | es | 187 | 50.2 % | 0.036 | 95.5 % | 68.8 % | es | 27.0 |  |
| Le_musée_d'air_contemporain_-_KPTN | fr | 184 | 17.1 % | 0.024 | 100.0 % | 90.2 % | fr | 22.5 |  |
| Le_royaume_des_glous_glous_-_Raoul_de_QSM | fr | 163 | 63.9 % | 0.030 | 93.9 % | 56.9 % | fr | 22.3 |  |
| Les_files_d'attente_-_Law' | fr | 196 | 43.1 % | 0.033 | 96.6 % | 56.1 % | fr | 21.8 |  |
| Libre_by_CybeR_AttaCK_-_CyberAttacK | fr | 217 | 62.7 % | 0.028 | 91.5 % | 44.6 % | fr | 45.1 |  |
| Lower_Loveday_-_Is_It_Right_ | en | 180 | 18.1 % | 0.057 | 94.3 % | 90.6 % | en | 17.7 |  |
| Mes_Larmes_-_kobzx2z | fr | 159 | 66.8 % | 0.032 | 71.8 % | 32.0 % | fr | 21.2 |  |
| Moon_I_Mean_-_Wrong_Concept | en | 220 | 61.0 % | 0.052 | 91.6 % | 48.2 % | en | 21.7 |  |
| Musik_-_Heiko | de | 295 | 19.4 % | 0.024 | 99.5 % | 90.3 % | de | 31.0 |  |
| Mère_nature_-_Law' | fr | 225 | 41.1 % | 0.038 | 96.8 % | 74.4 % | fr | 25.4 |  |
| POIGNEE_DE_MAIN_-_Cabbac | fr | 209 | 43.2 % | 0.033 | 98.9 % | 60.3 % | fr | 19.9 |  |
| Palabras_-_Javier_Gomez_Bello | es | 216 | 6.1 % | 0.028 | 100.0 % | 96.2 % | es | 23.2 |  |
| Pas_que_tes_pas_-_AZUL | fr | 202 | 34.0 % | 0.039 | 100.0 % | 78.7 % | fr | 23.0 |  |
| Pluie_d'entre_deux_saisons_-_Midnight_Prefou | fr | 205 | 34.5 % | 0.045 | 89.1 % | 68.7 % | fr | 20.8 |  |
| Pure_Mids_-_The_Leader | en | 262 | 85.2 % | — | — | — | nn | 76.9 | aligner: ValueError: no default alignment model for language 'nn' |
| Quentin_Hannappe_-_Keep_On | en | 190 | 27.4 % | 0.044 | 97.8 % | 76.6 % | en | 17.3 |  |
| Quiero_y_Puedo_-_Nacidos_de_la_Tierra | es | 236 | 15.2 % | 0.026 | 98.7 % | 87.3 % | es | 47.4 |  |
| Ridgway_-_Fire_Inside | en | 284 | 100.0 % | — | — | — | nn | 120.2 | aligner: ValueError: no default alignment model for language 'nn' |
| Rxbyn_-_Bad_Side | en | 217 | 22.9 % | 0.052 | 97.3 % | 83.6 % | en | 29.9 |  |
| SHANEY_23_feat._G1NA_G._x_In_den_Strassen_-_Shaney_23 | de | 211 | 35.7 % | 0.042 | 99.3 % | 63.4 % | de | 28.0 |  |
| Schnodderdodder_-_Abendblau | de | 197 | 27.1 % | 0.023 | 97.4 % | 79.0 % | de | 22.9 |  |
| Sehnsucht-Unplugged_-_REH-TORTE | de | 233 | 100.0 % | — | — | — | nn | 58.7 | aligner: ValueError: no default alignment model for language 'nn' |
| Sin_miedo_-_Living_Camboya | es | 223 | 19.8 % | 0.029 | 94.3 % | 82.5 % | es | 22.5 |  |
| Slingshot_Miracle_-_Whistler | en | 229 | 24.5 % | 0.050 | 94.0 % | 82.1 % | en | 20.8 |  |
| Songwriterz_-_Back_In_Time | en | 209 | 40.2 % | 0.044 | 90.0 % | 71.4 % | en | 19.3 |  |
| Séculaire_feat._Nÿme_-_saru | fr | 159 | 33.3 % | 0.024 | 98.0 % | 71.0 % | fr | 22.8 |  |
| Te_Recuerdo_-_Wilson_Way | es | 194 | 19.0 % | 0.031 | 95.8 % | 88.9 % | es | 31.8 |  |
| The.madpix.project_-_One_Way_Street | en | 171 | 26.9 % | 0.045 | 98.6 % | 77.6 % | en | 16.7 |  |
| The_Rinn_-_Voices__2017_Version_ | en | 231 | 29.7 % | 0.056 | 91.3 % | 73.9 % | en | 21.5 |  |
| Tom_Orlando_-_The_One__feat._Tina_G_ | en | 240 | 38.0 % | 0.040 | 80.9 % | 80.9 % | en | 26.9 |  |
| Une_Vie_De_Roi_-_david | fr | 303 | 14.1 % | 0.029 | 100.0 % | 87.5 % | fr | 34.4 |  |
| Vente_-_Fafarulo_Calabaza | es | 336 | 17.5 % | 0.035 | 99.3 % | 84.4 % | es | 45.5 |  |
| Veränderung_-_doromusis | de | 194 | 27.0 % | 0.031 | 99.4 % | 74.9 % | de | 21.6 |  |
| Wordsmith_-_The_Statement | en | 171 | 38.0 % | 0.046 | 96.6 % | 59.9 % | en | 40.8 |  |
| Yuanan_-_Miedo_-_Yuanan | es | 169 | 25.7 % | 0.027 | 97.6 % | 77.6 % | es | 27.9 |  |
| de_bonne_humeur_-_Le_Nez_Tordu | fr | 161 | 23.1 % | 0.028 | 99.5 % | 81.6 % | fr | 20.0 |  |
| dich_gehen_zu_sehn._-_Wingenbach_Frank | de | 193 | 9.3 % | 0.029 | 98.8 % | 92.3 % | de | 22.0 |  |
| l'abandon_-_flo | fr | 210 | 29.9 % | 0.028 | 99.2 % | 71.8 % | fr | 24.9 |  |
| te_amo_-_fabios_la_nueva_expresion_de_la_cancion | es | 195 | 22.5 % | — | — | — | la | 26.1 | aligner: ValueError: no default alignment model for language 'la' |
| ¡Óyeme_tiburón!_-_Corrientes | es | 180 | 31.9 % | 0.029 | 98.8 % | 76.7 % | es | 20.5 |  |

## Peores casos

Mayor mediana de error de inicio:
- CLUB_DESTINO__-_Pensando_en_ti_-_CLUB_DESTINO: 0.481 s
- Fantasma_-_Los_Rombos: 0.193 s
- Color_Out_-_Falling_Star: 0.145 s
- LUNABLIND_-_Vision__Radio_Edit_: 0.069 s
- Cortez_-_Feel__Stripped_: 0.062 s

Mayor WER:
- Háblame_-_(Talk_to_me)_-_Brunela_Crochenci: 118.9 %
- CLUB_DESTINO__-_Pensando_en_ti_-_CLUB_DESTINO: 104.9 %
- Caralibro_-_Vagos_Permanentes: 100.0 %
- Ridgway_-_Fire_Inside: 100.0 %
- Sehnsucht-Unplugged_-_REH-TORTE: 100.0 %

## Notas

- Falló 10._Disparan_-_criatura: aligner: ValueError: no default alignment model for language 'sv'
- Falló Avercage_-_Embers: aligner: ValueError: no default alignment model for language 'nn'
- Falló Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique: aligner: ValueError: no default alignment model for language 'nn'
- Falló Der_Musiker_-_d-music: aligner: ValueError: no default alignment model for language 'cy'
- Falló Háblame_-_(Talk_to_me)_-_Brunela_Crochenci: aligner: ValueError: no default alignment model for language 'cy'
- Falló Intro_[Pulsschlag]_-_Zeugen_der_Leere_(2): aligner: ValueError: no default alignment model for language 'nn'
- Falló Pure_Mids_-_The_Leader: aligner: ValueError: no default alignment model for language 'nn'
- Falló Ridgway_-_Fire_Inside: aligner: ValueError: no default alignment model for language 'nn'
- Falló Sehnsucht-Unplugged_-_REH-TORTE: aligner: ValueError: no default alignment model for language 'nn'
- Falló te_amo_-_fabios_la_nueva_expresion_de_la_cancion: aligner: ValueError: no default alignment model for language 'la'
- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
