# Banco · base-legacy · jamendo · con letra

- Fecha: 2026-10-29T09:07:33+01:00
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
| de | 20 | 0 | — | — | 0.029 | 0.068 | 99.1 % | 0.071 | 0.005 | 96.0 % | 0.030 | 0 | 22 |
| en | 20 | 0 | — | — | 0.051 | 0.205 | 93.8 % | 0.064 | 0.021 | 93.4 % | 0.049 | 0 | 20 |
| es | 20 | 0 | — | — | 0.028 | 0.181 | 98.3 % | 0.091 | 0.123 | 96.5 % | 0.031 | 0 | 23 |
| fr | 19 | 0 | — | — | 0.032 | 0.106 | 97.0 % | 0.081 | -0.009 | 88.5 % | 0.037 | 0 | 23 |
| total | 79 | 0 | — | — | 0.034 | 0.142 | 97.0 % | 0.076 | 0.036 | 93.6 % | 0.036 | 0 | 22 |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 3.1 | 804 | 3080 | 0.060 |
| aligner | — | 1559 | 4558 | 0.018 |

## Por canción

| Canción | Idioma | Duración | WER | Inicio mediana | ≤ 0,3 s | Cobertura | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|
| 10._Disparan_-_criatura | es | 160 | — | 0.021 | 100.0 % | 100.0 % | — | 18.6 (caché) |  |
| 1_Freak_-_Automatisch_Gekommen | de | 188 | — | 0.043 | 100.0 % | 97.8 % | — | 15.4 (caché) |  |
| Avercage_-_Embers | en | 243 | — | 0.152 | 73.5 % | 100.0 % | — | 16.1 (caché) |  |
| Baila_-_Alfonso_Lugo | es | 210 | — | 0.020 | 98.9 % | 98.2 % | — | 17.1 (caché) |  |
| Besando_Sapos_-_Dream_Tabu | es | 251 | — | 0.032 | 100.0 % | 100.0 % | — | 18.0 (caché) |  |
| Bitte_beweg_dich_nicht_-_Bukto | de | 273 | — | 0.037 | 99.1 % | 98.9 % | — | 22.7 (caché) |  |
| Burn_Out_Man_-_Abendblau | de | 260 | — | 0.041 | 100.0 % | 86.7 % | — | 19.9 (caché) |  |
| CHRISTMAS_AVEC_TOI_-_imfreshyourepretty | fr | 234 | — | 0.038 | 93.8 % | 64.3 % | — | 19.1 (caché) |  |
| CLUB_DESTINO__-_Pensando_en_ti_-_CLUB_DESTINO | es | 219 | — | 0.040 | 97.5 % | 100.0 % | — | 17.9 (caché) |  |
| Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique | de | 248 | — | 0.046 | 97.7 % | 94.6 % | — | 18.4 (caché) |  |
| Capotes_à_un_Franc_-_elmanu | fr | 188 | — | 0.024 | 99.2 % | 97.6 % | — | 15.3 (caché) |  |
| Caralibro_-_Vagos_Permanentes | es | 279 | — | 0.034 | 90.5 % | 99.5 % | — | 21.0 (caché) |  |
| Color_Out_-_Falling_Star | en | 222 | — | 0.148 | 89.3 % | 96.0 % | — | 15.3 (caché) |  |
| Confession_-_Quesabe | fr | 148 | — | 0.029 | 97.4 % | 91.7 % | — | 12.7 (caché) |  |
| Cortez_-_Feel__Stripped_ | en | 241 | — | 0.058 | 97.7 % | 98.9 % | — | 18.1 (caché) |  |
| Culture_&_Co._-_cool.cavemen | fr | 212 | — | 0.039 | 89.5 % | 93.9 % | — | 17.9 (caché) |  |
| DON_VALDES_-_Tu_sais_Man | fr | 209 | — | 0.037 | 91.3 % | 86.7 % | — | 17.9 (caché) |  |
| Da_wurdest_du_geboren_-_Alice_Tlustos_ | de | 207 | — | 0.051 | 100.0 % | 100.0 % | — | 17.4 (caché) |  |
| Der_Baum_-_Dienstag_is_Damensauna_(2) | de | 209 | — | 0.027 | 100.0 % | 97.7 % | — | 15.6 (caché) |  |
| Der_Musiker_-_d-music | de | 271 | — | 0.021 | 96.8 % | 98.0 % | — | 21.3 (caché) |  |
| Die_Revolution_gehört_Dir!_-_partysahnen | de | 167 | — | 0.037 | 95.5 % | 98.7 % | — | 12.7 (caché) |  |
| Diosa_de_la_noche_-_Brunela_Crochenci | es | 230 | — | 0.030 | 98.9 % | 91.0 % | — | 18.4 (caché) |  |
| Drei_Nüsse_-_patrouille | de | 259 | — | 0.027 | 100.0 % | 98.5 % | — | 22.3 (caché) |  |
| En_liberté_-_tom.leyak | fr | 234 | — | 0.036 | 99.6 % | 94.0 % | — | 19.9 (caché) |  |
| Esencia_-_NandoMalo_ | es | 262 | — | 0.023 | 100.0 % | 98.2 % | — | 21.6 (caché) |  |
| Explosive_Ear_Candy_-_Like_The_Sun | en | 193 | — | 0.046 | 100.0 % | 99.6 % | — | 14.8 (caché) |  |
| Fantasma_-_Los_Rombos | es | 166 | — | 0.054 | 85.9 % | 88.6 % | — | 13.4 (caché) |  |
| Freifliegen_-_durch.dick.und.duenn | de | 250 | — | 0.032 | 100.0 % | 97.8 % | — | 19.5 (caché) |  |
| Fußabdrücke_-_Andreas_Jachmann | de | 241 | — | 0.025 | 100.0 % | 100.0 % | — | 18.2 (caché) |  |
| Guayeteo_-_JhoyKing | es | 158 | — | 0.026 | 97.2 % | 84.7 % | — | 13.7 (caché) |  |
| HILA_-_Give_Me_the_Same | en | 234 | — | 0.059 | 90.8 % | 98.1 % | — | 16.5 (caché) |  |
| Háblame_-_(Talk_to_me)_-_Brunela_Crochenci | es | 214 | — | 0.029 | 100.0 % | 99.1 % | — | 16.8 (caché) |  |
| Ich_kann_dich_nicht_vergessen_-_Wingenbach_Frank | de | 258 | — | 0.028 | 99.5 % | 95.5 % | — | 20.7 (caché) |  |
| Intentando_Destacar_-_Sundayers_ | es | 220 | — | 0.024 | 97.3 % | 81.2 % | — | 17.5 (caché) |  |
| Intro_[Pulsschlag]_-_Zeugen_der_Leere_(2) | de | 157 | — | 0.041 | 91.5 % | 100.0 % | — | 12.3 (caché) |  |
| JASON_MILLER_-_CROWD_PLEASER | en | 193 | — | 0.041 | 99.8 % | 83.1 % | — | 14.1 (caché) |  |
| Keine_Lust_-_Jonny_M | de | 229 | — | 0.017 | 99.8 % | 95.8 % | — | 19.5 (caché) |  |
| Kinematic_-_Peyote | en | 183 | — | 0.049 | 94.2 % | 93.9 % | — | 12.5 (caché) |  |
| LUNABLIND_-_Vision__Radio_Edit_ | en | 221 | — | 0.047 | 99.3 % | 99.7 % | — | 14.6 (caché) |  |
| La_rumba_del_coronavirus_-_Rich_Don_Jeri | es | 187 | — | 0.024 | 100.0 % | 100.0 % | — | 15.1 (caché) |  |
| Le_musée_d'air_contemporain_-_KPTN | fr | 184 | — | 0.023 | 100.0 % | 94.1 % | — | 15.5 (caché) |  |
| Le_royaume_des_glous_glous_-_Raoul_de_QSM | fr | 163 | — | 0.032 | 100.0 % | 96.5 % | — | 12.4 (caché) |  |
| Les_files_d'attente_-_Law' | fr | 196 | — | 0.037 | 91.9 % | 69.6 % | — | 15.2 (caché) |  |
| Libre_by_CybeR_AttaCK_-_CyberAttacK | fr | 217 | — | 0.029 | 99.7 % | 98.5 % | — | 17.6 (caché) |  |
| Lower_Loveday_-_Is_It_Right_ | en | 180 | — | 0.056 | 95.7 % | 98.6 % | — | 12.7 (caché) |  |
| Mes_Larmes_-_kobzx2z | fr | 159 | — | 0.025 | 95.1 % | 78.6 % | — | 13.8 (caché) |  |
| Moon_I_Mean_-_Wrong_Concept | en | 220 | — | 0.041 | 99.2 % | 95.2 % | — | 14.9 (caché) |  |
| Musik_-_Heiko | de | 295 | — | 0.026 | 100.0 % | 94.1 % | — | 23.0 (caché) |  |
| Mère_nature_-_Law' | fr | 225 | — | 0.037 | 100.0 % | 96.5 % | — | 17.9 (caché) |  |
| POIGNEE_DE_MAIN_-_Cabbac | fr | 209 | — | 0.033 | 98.5 % | 90.4 % | — | 14.9 (caché) |  |
| Palabras_-_Javier_Gomez_Bello | es | 216 | — | 0.028 | 100.0 % | 99.5 % | — | 17.0 (caché) |  |
| Pas_que_tes_pas_-_AZUL | fr | 202 | — | 0.039 | 98.7 % | 88.1 % | — | 16.1 (caché) |  |
| Pluie_d'entre_deux_saisons_-_Midnight_Prefou | fr | 205 | — | 0.050 | 84.0 % | 93.3 % | — | 14.8 (caché) |  |
| Pure_Mids_-_The_Leader | en | 262 | — | 0.077 | 81.7 % | 71.9 % | — | 17.2 (caché) |  |
| Quentin_Hannappe_-_Keep_On | en | 190 | — | 0.038 | 97.6 % | 96.0 % | — | 12.5 (caché) |  |
| Quiero_y_Puedo_-_Nacidos_de_la_Tierra | es | 236 | — | 0.026 | 100.0 % | 99.8 % | — | 20.5 (caché) |  |
| Ridgway_-_Fire_Inside | en | 284 | — | 0.047 | 91.5 % | 77.0 % | — | 19.4 (caché) |  |
| Rxbyn_-_Bad_Side | en | 217 | — | 0.057 | 92.2 % | 98.6 % | — | 14.9 (caché) |  |
| SHANEY_23_feat._G1NA_G._x_In_den_Strassen_-_Shaney_23 | de | 211 | — | 0.042 | 98.3 % | 92.6 % | — | 18.2 (caché) |  |
| Schnodderdodder_-_Abendblau | de | 197 | — | 0.022 | 99.6 % | 95.9 % | — | 15.0 (caché) |  |
| Sehnsucht-Unplugged_-_REH-TORTE | de | 233 | — | 0.030 | 98.6 % | 96.0 % | — | 16.8 (caché) |  |
| Sin_miedo_-_Living_Camboya | es | 223 | — | 0.027 | 100.0 % | 100.0 % | — | 17.6 (caché) |  |
| Slingshot_Miracle_-_Whistler | en | 229 | — | 0.049 | 96.9 % | 98.8 % | — | 15.5 (caché) |  |
| Songwriterz_-_Back_In_Time | en | 209 | — | 0.042 | 91.8 % | 92.0 % | — | 14.0 (caché) |  |
| Séculaire_feat._Nÿme_-_saru | fr | 159 | — | 0.025 | 98.7 % | 89.3 % | — | 14.4 (caché) |  |
| Te_Recuerdo_-_Wilson_Way | es | 194 | — | 0.030 | 95.6 % | 98.3 % | — | 17.4 (caché) |  |
| The.madpix.project_-_One_Way_Street | en | 171 | — | 0.047 | 90.8 % | 95.1 % | — | 12.7 (caché) |  |
| The_Rinn_-_Voices__2017_Version_ | en | 231 | — | 0.047 | 90.9 % | 97.5 % | — | 15.7 (caché) |  |
| Tom_Orlando_-_The_One__feat._Tina_G_ | en | 240 | — | 0.039 | 85.5 % | 93.0 % | — | 17.5 (caché) |  |
| Une_Vie_De_Roi_-_david | fr | 303 | — | 0.029 | 100.0 % | 96.1 % | — | 24.2 (caché) |  |
| Vente_-_Fafarulo_Calabaza | es | 336 | — | 0.035 | 98.8 % | 97.8 % | — | 29.0 (caché) |  |
| Veränderung_-_doromusis | de | 194 | — | 0.030 | 99.0 % | 90.5 % | — | 16.7 (caché) |  |
| Wordsmith_-_The_Statement | en | 171 | — | 0.043 | 100.0 % | 90.7 % | — | 12.9 (caché) |  |
| Yuanan_-_Miedo_-_Yuanan | es | 169 | — | 0.027 | 100.0 % | 91.0 % | — | 13.8 (caché) |  |
| de_bonne_humeur_-_Le_Nez_Tordu | fr | 161 | — | 0.029 | 98.8 % | 97.0 % | — | 13.9 (caché) |  |
| dich_gehen_zu_sehn._-_Wingenbach_Frank | de | 193 | — | 0.029 | 98.3 % | 97.8 % | — | 15.8 (caché) |  |
| l'abandon_-_flo | fr | 210 | — | 0.031 | 99.7 % | 86.2 % | — | 18.0 (caché) |  |
| te_amo_-_fabios_la_nueva_expresion_de_la_cancion | es | 195 | — | 0.034 | 98.8 % | 99.4 % | — | 15.7 (caché) |  |
| ¡Óyeme_tiburón!_-_Corrientes | es | 180 | — | 0.032 | 99.0 % | 98.1 % | — | 13.1 (caché) |  |

## Peores casos

Mayor mediana de error de inicio:
- Avercage_-_Embers: 0.152 s
- Color_Out_-_Falling_Star: 0.148 s
- Pure_Mids_-_The_Leader: 0.077 s
- HILA_-_Give_Me_the_Same: 0.059 s
- Cortez_-_Feel__Stripped_: 0.058 s

## Notas

- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
