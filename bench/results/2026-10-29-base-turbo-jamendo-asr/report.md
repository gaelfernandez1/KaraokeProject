# Banco · base-turbo · jamendo · sin letra

- Fecha: 2026-10-29T09:07:31+01:00
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

Demucs + Whisper large-v3-turbo (language given) + default CTC aligner

- **separator**: `karaoke_bench.baseline.separation:DemucsSeparator` v2
- **transcriber**: `karaoke_bench.baseline.whisper:FasterWhisperTranscriber` v1 {'model': 'large-v3-turbo'}
- **segmenter**: `karaoke_bench.baseline.segment:SegmentPerLine` v1
- **aligner**: `karaoke_bench.baseline.ctc:CtcAligner` v1

## Resumen

| Grupo | Canciones | Fallos | WER | CER | Inicio mediana | Inicio media | ≤ 0,3 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| de | 20 | 0 | 27.2 % | 17.6 % | 0.032 | 0.874 | 92.6 % | 0.079 | -0.435 | 83.0 % | — | 0 | 40 |
| en | 20 | 0 | 37.5 % | 30.0 % | 0.051 | 0.627 | 92.0 % | 0.065 | -0.147 | 70.5 % | — | 0 | 41 |
| es | 20 | 0 | 28.7 % | 22.0 % | 0.029 | 0.413 | 95.7 % | 0.092 | -0.085 | 76.9 % | — | 0 | 41 |
| fr | 19 | 0 | 40.3 % | 28.0 % | 0.031 | 0.159 | 96.9 % | 0.077 | -0.101 | 64.3 % | — | 0 | 39 |
| total | 79 | 0 | 33.7 % | 24.5 % | 0.034 | 0.535 | 94.2 % | 0.078 | -0.199 | 73.5 % | — | 0 | 40 |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 3.1 | 804 | 3080 | 0.060 |
| transcriber | 5.5 | 1335 | 2068 | 0.052 |
| segmenter | — | 0 | 99 | 0.000 |
| aligner | — | 1559 | 4637 | 0.019 |

## Por canción

| Canción | Idioma | Duración | WER | Inicio mediana | ≤ 0,3 s | Cobertura | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|
| 10._Disparan_-_criatura | es | 160 | 51.5 % | 0.024 | 100.0 % | 50.0 % | es | 42.4 |  |
| 1_Freak_-_Automatisch_Gekommen | de | 188 | 40.4 % | 0.050 | 81.8 % | 88.3 % | de | 28.2 |  |
| Avercage_-_Embers | en | 243 | 100.0 % | — | — | — | en | 20.3 |  |
| Baila_-_Alfonso_Lugo | es | 210 | 20.1 % | 0.019 | 100.0 % | 85.1 % | es | 30.9 |  |
| Besando_Sapos_-_Dream_Tabu | es | 251 | 100.0 % | — | — | — | es | 22.1 |  |
| Bitte_beweg_dich_nicht_-_Bukto | de | 273 | 12.7 % | 0.037 | 96.5 % | 88.4 % | de | 33.0 |  |
| Burn_Out_Man_-_Abendblau | de | 260 | 11.5 % | 0.042 | 99.0 % | 86.7 % | de | 32.2 |  |
| CHRISTMAS_AVEC_TOI_-_imfreshyourepretty | fr | 234 | 47.3 % | 0.036 | 97.3 % | 53.4 % | fr | 27.4 |  |
| CLUB_DESTINO__-_Pensando_en_ti_-_CLUB_DESTINO | es | 219 | 11.7 % | 0.038 | 98.9 % | 91.7 % | es | 27.7 |  |
| Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique | de | 248 | 100.0 % | — | — | — | de | 29.0 |  |
| Capotes_à_un_Franc_-_elmanu | fr | 188 | 70.6 % | 0.025 | 100.0 % | 29.8 % | fr | 20.8 |  |
| Caralibro_-_Vagos_Permanentes | es | 279 | 100.0 % | — | — | — | es | 25.6 |  |
| Color_Out_-_Falling_Star | en | 222 | 39.6 % | 0.150 | 83.1 % | 89.7 % | en | 31.0 |  |
| Confession_-_Quesabe | fr | 148 | 30.7 % | 0.029 | 90.8 % | 78.0 % | fr | 25.6 |  |
| Cortez_-_Feel__Stripped_ | en | 241 | 13.5 % | 0.061 | 93.5 % | 90.7 % | en | 29.7 |  |
| Culture_&_Co._-_cool.cavemen | fr | 212 | 100.0 % | — | — | — | fr | 26.2 |  |
| DON_VALDES_-_Tu_sais_Man | fr | 209 | 33.6 % | 0.035 | 93.2 % | 72.5 % | fr | 32.7 |  |
| Da_wurdest_du_geboren_-_Alice_Tlustos_ | de | 207 | 11.5 % | 0.057 | 93.8 % | 98.0 % | de | 24.1 |  |
| Der_Baum_-_Dienstag_is_Damensauna_(2) | de | 209 | 13.1 % | 0.027 | 100.0 % | 89.2 % | de | 30.6 |  |
| Der_Musiker_-_d-music | de | 271 | 49.5 % | 0.023 | 95.0 % | 56.2 % | de | 34.3 |  |
| Die_Revolution_gehört_Dir!_-_partysahnen | de | 167 | 33.3 % | 0.043 | 74.3 % | 69.9 % | de | 20.7 |  |
| Diosa_de_la_noche_-_Brunela_Crochenci | es | 230 | 23.3 % | 0.030 | 98.9 % | 90.0 % | es | 31.7 |  |
| Drei_Nüsse_-_patrouille | de | 259 | 5.2 % | 0.026 | 97.8 % | 96.0 % | de | 37.5 |  |
| En_liberté_-_tom.leyak | fr | 234 | 65.7 % | 0.041 | 84.7 % | 54.1 % | fr | 32.9 |  |
| Esencia_-_NandoMalo_ | es | 262 | 17.7 % | 0.023 | 98.4 % | 93.1 % | es | 35.1 |  |
| Explosive_Ear_Candy_-_Like_The_Sun | en | 193 | 39.0 % | 0.047 | 96.9 % | 97.7 % | en | 31.2 |  |
| Fantasma_-_Los_Rombos | es | 166 | 57.1 % | 0.054 | 83.3 % | 81.8 % | es | 21.7 |  |
| Freifliegen_-_durch.dick.und.duenn | de | 250 | 19.3 % | 0.034 | 96.0 % | 91.9 % | de | 34.8 |  |
| Fußabdrücke_-_Andreas_Jachmann | de | 241 | 18.2 % | 0.025 | 97.9 % | 94.8 % | de | 29.4 |  |
| Guayeteo_-_JhoyKing | es | 158 | 35.2 % | 0.025 | 99.6 % | 72.1 % | es | 26.1 |  |
| HILA_-_Give_Me_the_Same | en | 234 | 36.7 % | 0.064 | 85.0 % | 62.1 % | en | 25.0 |  |
| Háblame_-_(Talk_to_me)_-_Brunela_Crochenci | es | 214 | 100.0 % | — | — | — | es | 20.9 |  |
| Ich_kann_dich_nicht_vergessen_-_Wingenbach_Frank | de | 258 | 24.7 % | 0.033 | 88.5 % | 92.4 % | de | 34.5 |  |
| Intentando_Destacar_-_Sundayers_ | es | 220 | 44.2 % | 0.023 | 94.8 % | 68.8 % | es | 32.1 |  |
| Intro_[Pulsschlag]_-_Zeugen_der_Leere_(2) | de | 157 | 84.1 % | 18.534 | 0.0 % | 58.5 % | de | 17.6 |  |
| JASON_MILLER_-_CROWD_PLEASER | en | 193 | 11.6 % | 0.041 | 100.0 % | 83.1 % | en | 32.4 |  |
| Keine_Lust_-_Jonny_M | de | 229 | 15.1 % | 0.018 | 94.6 % | 84.1 % | de | 43.8 |  |
| Kinematic_-_Peyote | en | 183 | 45.9 % | 0.058 | 84.3 % | 86.4 % | en | 26.1 |  |
| LUNABLIND_-_Vision__Radio_Edit_ | en | 221 | 15.6 % | 0.051 | 97.3 % | 88.9 % | en | 25.5 |  |
| La_rumba_del_coronavirus_-_Rich_Don_Jeri | es | 187 | 32.0 % | 0.042 | 85.5 % | 71.0 % | es | 27.6 |  |
| Le_musée_d'air_contemporain_-_KPTN | fr | 184 | 14.3 % | 0.023 | 98.7 % | 92.6 % | fr | 24.1 |  |
| Le_royaume_des_glous_glous_-_Raoul_de_QSM | fr | 163 | 36.1 % | 0.032 | 100.0 % | 71.8 % | fr | 24.3 |  |
| Les_files_d'attente_-_Law' | fr | 196 | 34.6 % | 0.033 | 98.0 % | 61.8 % | fr | 22.1 |  |
| Libre_by_CybeR_AttaCK_-_CyberAttacK | fr | 217 | 36.0 % | 0.028 | 100.0 % | 71.3 % | fr | 30.0 |  |
| Lower_Loveday_-_Is_It_Right_ | en | 180 | 17.1 % | 0.056 | 97.2 % | 84.0 % | en | 25.3 |  |
| Mes_Larmes_-_kobzx2z | fr | 159 | 30.3 % | 0.024 | 97.5 % | 61.1 % | fr | 21.0 |  |
| Moon_I_Mean_-_Wrong_Concept | en | 220 | 50.7 % | 0.048 | 94.4 % | 71.7 % | en | 26.6 |  |
| Musik_-_Heiko | de | 295 | 14.8 % | 0.024 | 100.0 % | 94.9 % | de | 35.3 |  |
| Mère_nature_-_Law' | fr | 225 | 24.1 % | 0.040 | 95.0 % | 86.2 % | fr | 31.8 |  |
| POIGNEE_DE_MAIN_-_Cabbac | fr | 209 | 56.8 % | 0.040 | 98.4 % | 43.8 % | fr | 21.0 |  |
| Palabras_-_Javier_Gomez_Bello | es | 216 | 4.7 % | 0.028 | 100.0 % | 95.3 % | es | 25.6 |  |
| Pas_que_tes_pas_-_AZUL | fr | 202 | 25.0 % | 0.038 | 99.5 % | 81.7 % | fr | 24.4 |  |
| Pluie_d'entre_deux_saisons_-_Midnight_Prefou | fr | 205 | 35.9 % | 0.044 | 100.0 % | 67.2 % | fr | 29.4 |  |
| Pure_Mids_-_The_Leader | en | 262 | 93.3 % | 36.279 | 0.0 % | 9.6 % | en | 24.9 |  |
| Quentin_Hannappe_-_Keep_On | en | 190 | 32.1 % | 0.042 | 93.0 % | 81.1 % | en | 26.0 |  |
| Quiero_y_Puedo_-_Nacidos_de_la_Tierra | es | 236 | 4.2 % | 0.027 | 99.8 % | 96.7 % | es | 32.8 |  |
| Ridgway_-_Fire_Inside | en | 284 | 98.0 % | 96.845 | 0.0 % | 1.3 % | en | 29.2 |  |
| Rxbyn_-_Bad_Side | en | 217 | 24.0 % | 0.055 | 91.6 % | 84.3 % | en | 29.2 |  |
| SHANEY_23_feat._G1NA_G._x_In_den_Strassen_-_Shaney_23 | de | 211 | 69.2 % | 0.049 | 85.3 % | 75.7 % | de | 36.9 |  |
| Schnodderdodder_-_Abendblau | de | 197 | 14.7 % | 0.022 | 100.0 % | 88.7 % | de | 22.3 |  |
| Sehnsucht-Unplugged_-_REH-TORTE | de | 233 | 27.2 % | 0.031 | 98.4 % | 85.4 % | de | 24.4 |  |
| Sin_miedo_-_Living_Camboya | es | 223 | 5.8 % | 0.027 | 100.0 % | 95.9 % | es | 24.9 |  |
| Slingshot_Miracle_-_Whistler | en | 229 | 26.4 % | 0.050 | 94.0 % | 92.6 % | en | 29.5 |  |
| Songwriterz_-_Back_In_Time | en | 209 | 19.6 % | 0.046 | 89.5 % | 79.8 % | en | 28.7 |  |
| Séculaire_feat._Nÿme_-_saru | fr | 159 | 27.1 % | 0.025 | 98.5 % | 79.4 % | fr | 25.8 |  |
| Te_Recuerdo_-_Wilson_Way | es | 194 | 12.8 % | 0.034 | 88.5 % | 91.3 % | es | 28.7 |  |
| The.madpix.project_-_One_Way_Street | en | 171 | 33.0 % | 0.047 | 92.3 % | 84.7 % | en | 27.8 |  |
| The_Rinn_-_Voices__2017_Version_ | en | 231 | 100.0 % | — | — | — | en | 19.7 |  |
| Tom_Orlando_-_The_One__feat._Tina_G_ | en | 240 | 31.2 % | 0.041 | 80.8 % | 83.5 % | en | 36.9 |  |
| Une_Vie_De_Roi_-_david | fr | 303 | 15.4 % | 0.030 | 99.0 % | 93.2 % | fr | 37.9 |  |
| Vente_-_Fafarulo_Calabaza | es | 336 | 17.5 % | 0.036 | 92.3 % | 87.1 % | es | 46.1 |  |
| Veränderung_-_doromusis | de | 194 | 23.2 % | 0.032 | 93.6 % | 82.0 % | de | 27.1 |  |
| Wordsmith_-_The_Statement | en | 171 | 29.8 % | 0.044 | 97.5 % | 69.4 % | en | 38.4 |  |
| Yuanan_-_Miedo_-_Yuanan | es | 169 | 32.1 % | 0.030 | 89.2 % | 79.5 % | es | 27.6 |  |
| de_bonne_humeur_-_Le_Nez_Tordu | fr | 161 | 19.8 % | 0.028 | 99.6 % | 83.8 % | fr | 19.2 |  |
| dich_gehen_zu_sehn._-_Wingenbach_Frank | de | 193 | 24.2 % | 0.036 | 84.2 % | 76.8 % | de | 28.6 |  |
| l'abandon_-_flo | fr | 210 | 100.0 % | — | — | — | fr | 21.5 |  |
| te_amo_-_fabios_la_nueva_expresion_de_la_cancion | es | 195 | 14.8 % | 0.035 | 93.7 % | 94.1 % | es | 23.5 |  |
| ¡Óyeme_tiburón!_-_Corrientes | es | 180 | 12.9 % | 0.033 | 96.8 % | 90.0 % | es | 24.5 |  |

## Peores casos

Mayor mediana de error de inicio:
- Ridgway_-_Fire_Inside: 96.845 s
- Pure_Mids_-_The_Leader: 36.279 s
- Intro_[Pulsschlag]_-_Zeugen_der_Leere_(2): 18.534 s
- Color_Out_-_Falling_Star: 0.150 s
- HILA_-_Give_Me_the_Same: 0.064 s

Mayor WER:
- Avercage_-_Embers: 100.0 %
- Besando_Sapos_-_Dream_Tabu: 100.0 %
- Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique: 100.0 %
- Caralibro_-_Vagos_Permanentes: 100.0 %
- Culture_&_Co._-_cool.cavemen: 100.0 %

## Notas

- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
