# Banco · sep-melkim-8s · jamendo · con letra

- Fecha: 2026-10-29T13:12:40+01:00
- Commit: 57a6d23
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

Mel-Band RoFormer vocals model (Kimberley Jensen, 8 s chunks) + Whisper large-v3-turbo + default CTC aligner

- **separator**: `karaoke_engine.separation:RoformerSeparator` v2 {'model': 'vocals_mel_band_roformer.ckpt', 'segment_size': 801}
- **transcriber**: `karaoke_bench.baseline.whisper:FasterWhisperTranscriber` v1 {'model': 'large-v3-turbo'}
- **segmenter**: `karaoke_bench.baseline.segment:SegmentPerLine` v1
- **aligner**: `karaoke_bench.baseline.ctc:CtcAligner` v1

## Resumen

| Grupo | Canciones | Fallos | WER | CER | Inicio mediana | Inicio media | ≤ 0,3 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| de | 20 | 0 | — | — | 0.029 | 0.058 | 99.5 % | 0.071 | 0.037 | 96.0 % | 0.029 | 0 | 61 |
| en | 20 | 0 | — | — | 0.050 | 0.229 | 94.4 % | 0.064 | 0.010 | 93.4 % | 0.048 | 0 | 58 |
| es | 20 | 0 | — | — | 0.028 | 0.131 | 98.9 % | 0.091 | 0.093 | 96.5 % | 0.031 | 0 | 61 |
| fr | 19 | 0 | — | — | 0.031 | 0.118 | 97.2 % | 0.081 | 0.037 | 88.5 % | 0.036 | 0 | 61 |
| total | 79 | 0 | — | — | 0.033 | 0.136 | 97.5 % | 0.076 | 0.044 | 93.6 % | 0.035 | 0 | 60 |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 6.9 | 2867 | 2388 | 0.204 |
| aligner | — | 1559 | 4770 | 0.019 |

## Por canción

| Canción | Idioma | Duración | WER | Inicio mediana | ≤ 0,3 s | Cobertura | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|
| 10._Disparan_-_criatura | es | 160 | — | 0.024 | 100.0 % | 100.0 % | — | 36.3 (caché) |  |
| 1_Freak_-_Automatisch_Gekommen | de | 188 | — | 0.045 | 100.0 % | 97.8 % | — | 43.7 (caché) |  |
| Avercage_-_Embers | en | 243 | — | 0.169 | 67.2 % | 100.0 % | — | 63.6 |  |
| Baila_-_Alfonso_Lugo | es | 210 | — | 0.019 | 100.0 % | 98.2 % | — | 46.2 (caché) |  |
| Besando_Sapos_-_Dream_Tabu | es | 251 | — | 0.032 | 100.0 % | 100.0 % | — | 57.2 |  |
| Bitte_beweg_dich_nicht_-_Bukto | de | 273 | — | 0.038 | 99.7 % | 98.9 % | — | 62.7 |  |
| Burn_Out_Man_-_Abendblau | de | 260 | — | 0.039 | 100.0 % | 86.7 % | — | 57.2 |  |
| CHRISTMAS_AVEC_TOI_-_imfreshyourepretty | fr | 234 | — | 0.036 | 96.9 % | 64.3 % | — | 54.3 |  |
| CLUB_DESTINO__-_Pensando_en_ti_-_CLUB_DESTINO | es | 219 | — | 0.036 | 100.0 % | 100.0 % | — | 49.4 |  |
| Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique | de | 248 | — | 0.046 | 97.7 % | 94.6 % | — | 53.7 (caché) |  |
| Capotes_à_un_Franc_-_elmanu | fr | 188 | — | 0.025 | 100.0 % | 97.6 % | — | 43.0 (caché) |  |
| Caralibro_-_Vagos_Permanentes | es | 279 | — | 0.033 | 92.4 % | 99.5 % | — | 61.1 |  |
| Color_Out_-_Falling_Star | en | 222 | — | 0.142 | 91.6 % | 96.0 % | — | 47.8 |  |
| Confession_-_Quesabe | fr | 148 | — | 0.031 | 97.1 % | 91.7 % | — | 32.5 (caché) |  |
| Cortez_-_Feel__Stripped_ | en | 241 | — | 0.057 | 98.3 % | 98.9 % | — | 51.0 (caché) |  |
| Culture_&_Co._-_cool.cavemen | fr | 212 | — | 0.048 | 82.3 % | 93.9 % | — | 49.1 |  |
| DON_VALDES_-_Tu_sais_Man | fr | 209 | — | 0.036 | 90.2 % | 86.7 % | — | 48.2 |  |
| Da_wurdest_du_geboren_-_Alice_Tlustos_ | de | 207 | — | 0.049 | 100.0 % | 100.0 % | — | 46.8 |  |
| Der_Baum_-_Dienstag_is_Damensauna_(2) | de | 209 | — | 0.027 | 100.0 % | 97.7 % | — | 45.9 |  |
| Der_Musiker_-_d-music | de | 271 | — | 0.021 | 99.4 % | 98.0 % | — | 60.5 (caché) |  |
| Die_Revolution_gehört_Dir!_-_partysahnen | de | 167 | — | 0.031 | 97.4 % | 98.7 % | — | 36.1 |  |
| Diosa_de_la_noche_-_Brunela_Crochenci | es | 230 | — | 0.030 | 99.5 % | 91.0 % | — | 51.5 |  |
| Drei_Nüsse_-_patrouille | de | 259 | — | 0.026 | 100.0 % | 98.5 % | — | 59.8 |  |
| En_liberté_-_tom.leyak | fr | 234 | — | 0.034 | 100.0 % | 94.0 % | — | 52.8 |  |
| Esencia_-_NandoMalo_ | es | 262 | — | 0.023 | 100.0 % | 98.2 % | — | 58.0 (caché) |  |
| Explosive_Ear_Candy_-_Like_The_Sun | en | 193 | — | 0.045 | 100.0 % | 99.6 % | — | 41.8 |  |
| Fantasma_-_Los_Rombos | es | 166 | — | 0.045 | 96.2 % | 88.6 % | — | 37.3 |  |
| Freifliegen_-_durch.dick.und.duenn | de | 250 | — | 0.031 | 99.2 % | 97.8 % | — | 55.6 |  |
| Fußabdrücke_-_Andreas_Jachmann | de | 241 | — | 0.023 | 100.0 % | 100.0 % | — | 53.0 |  |
| Guayeteo_-_JhoyKing | es | 158 | — | 0.027 | 97.9 % | 84.7 % | — | 36.4 |  |
| HILA_-_Give_Me_the_Same | en | 234 | — | 0.054 | 94.0 % | 98.1 % | — | 50.2 |  |
| Háblame_-_(Talk_to_me)_-_Brunela_Crochenci | es | 214 | — | 0.026 | 100.0 % | 99.1 % | — | 46.0 (caché) |  |
| Ich_kann_dich_nicht_vergessen_-_Wingenbach_Frank | de | 258 | — | 0.031 | 100.0 % | 95.5 % | — | 57.5 |  |
| Intentando_Destacar_-_Sundayers_ | es | 220 | — | 0.023 | 97.3 % | 81.2 % | — | 49.9 |  |
| Intro_[Pulsschlag]_-_Zeugen_der_Leere_(2) | de | 157 | — | 0.040 | 93.9 % | 100.0 % | — | 35.4 |  |
| JASON_MILLER_-_CROWD_PLEASER | en | 193 | — | 0.042 | 99.8 % | 83.1 % | — | 42.3 |  |
| Keine_Lust_-_Jonny_M | de | 229 | — | 0.016 | 99.8 % | 95.8 % | — | 51.7 (caché) |  |
| Kinematic_-_Peyote | en | 183 | — | 0.050 | 95.7 % | 93.9 % | — | 46.8 (caché) |  |
| LUNABLIND_-_Vision__Radio_Edit_ | en | 221 | — | 0.049 | 99.0 % | 99.7 % | — | 47.1 |  |
| La_rumba_del_coronavirus_-_Rich_Don_Jeri | es | 187 | — | 0.028 | 100.0 % | 100.0 % | — | 42.3 |  |
| Le_musée_d'air_contemporain_-_KPTN | fr | 184 | — | 0.022 | 100.0 % | 94.1 % | — | 40.9 (caché) |  |
| Le_royaume_des_glous_glous_-_Raoul_de_QSM | fr | 163 | — | 0.035 | 100.0 % | 96.5 % | — | 37.5 |  |
| Les_files_d'attente_-_Law' | fr | 196 | — | 0.035 | 92.8 % | 69.6 % | — | 43.4 |  |
| Libre_by_CybeR_AttaCK_-_CyberAttacK | fr | 217 | — | 0.029 | 100.0 % | 98.5 % | — | 48.5 |  |
| Lower_Loveday_-_Is_It_Right_ | en | 180 | — | 0.051 | 96.7 % | 98.6 % | — | 39.0 |  |
| Mes_Larmes_-_kobzx2z | fr | 159 | — | 0.024 | 96.1 % | 78.6 % | — | 36.1 |  |
| Moon_I_Mean_-_Wrong_Concept | en | 220 | — | 0.044 | 98.8 % | 95.2 % | — | 46.9 |  |
| Musik_-_Heiko | de | 295 | — | 0.026 | 100.0 % | 94.1 % | — | 66.3 |  |
| Mère_nature_-_Law' | fr | 225 | — | 0.037 | 100.0 % | 96.5 % | — | 49.8 (caché) |  |
| POIGNEE_DE_MAIN_-_Cabbac | fr | 209 | — | 0.032 | 99.2 % | 90.4 % | — | 46.6 |  |
| Palabras_-_Javier_Gomez_Bello | es | 216 | — | 0.030 | 100.0 % | 99.5 % | — | 48.8 |  |
| Pas_que_tes_pas_-_AZUL | fr | 202 | — | 0.037 | 100.0 % | 88.1 % | — | 44.7 (caché) |  |
| Pluie_d'entre_deux_saisons_-_Midnight_Prefou | fr | 205 | — | 0.046 | 88.8 % | 93.3 % | — | 45.4 |  |
| Pure_Mids_-_The_Leader | en | 262 | — | 0.063 | 93.9 % | 71.9 % | — | 55.3 |  |
| Quentin_Hannappe_-_Keep_On | en | 190 | — | 0.040 | 97.6 % | 96.0 % | — | 40.2 |  |
| Quiero_y_Puedo_-_Nacidos_de_la_Tierra | es | 236 | — | 0.027 | 100.0 % | 99.8 % | — | 56.1 |  |
| Ridgway_-_Fire_Inside | en | 284 | — | 0.044 | 92.3 % | 77.0 % | — | 59.2 (caché) |  |
| Rxbyn_-_Bad_Side | en | 217 | — | 0.053 | 94.0 % | 98.6 % | — | 47.5 |  |
| SHANEY_23_feat._G1NA_G._x_In_den_Strassen_-_Shaney_23 | de | 211 | — | 0.042 | 98.6 % | 92.6 % | — | 49.1 |  |
| Schnodderdodder_-_Abendblau | de | 197 | — | 0.022 | 99.6 % | 95.9 % | — | 44.0 |  |
| Sehnsucht-Unplugged_-_REH-TORTE | de | 233 | — | 0.031 | 100.0 % | 96.0 % | — | 51.0 (caché) |  |
| Sin_miedo_-_Living_Camboya | es | 223 | — | 0.027 | 100.0 % | 100.0 % | — | 50.1 |  |
| Slingshot_Miracle_-_Whistler | en | 229 | — | 0.051 | 94.4 % | 98.8 % | — | 49.1 |  |
| Songwriterz_-_Back_In_Time | en | 209 | — | 0.041 | 95.0 % | 92.0 % | — | 44.4 |  |
| Séculaire_feat._Nÿme_-_saru | fr | 159 | — | 0.024 | 97.4 % | 89.3 % | — | 36.9 |  |
| Te_Recuerdo_-_Wilson_Way | es | 194 | — | 0.030 | 95.3 % | 98.3 % | — | 43.3 (caché) |  |
| The.madpix.project_-_One_Way_Street | en | 171 | — | 0.045 | 92.0 % | 95.1 % | — | 36.6 |  |
| The_Rinn_-_Voices__2017_Version_ | en | 231 | — | 0.048 | 91.4 % | 97.5 % | — | 48.1 (caché) |  |
| Tom_Orlando_-_The_One__feat._Tina_G_ | en | 240 | — | 0.038 | 85.5 % | 93.0 % | — | 53.3 |  |
| Une_Vie_De_Roi_-_david | fr | 303 | — | 0.029 | 100.0 % | 96.1 % | — | 69.0 |  |
| Vente_-_Fafarulo_Calabaza | es | 336 | — | 0.035 | 99.6 % | 97.8 % | — | 77.3 |  |
| Veränderung_-_doromusis | de | 194 | — | 0.030 | 99.5 % | 90.5 % | — | 44.5 |  |
| Wordsmith_-_The_Statement | en | 171 | — | 0.043 | 99.8 % | 90.7 % | — | 36.4 (caché) |  |
| Yuanan_-_Miedo_-_Yuanan | es | 169 | — | 0.027 | 100.0 % | 91.0 % | — | 38.4 |  |
| de_bonne_humeur_-_Le_Nez_Tordu | fr | 161 | — | 0.029 | 99.6 % | 97.0 % | — | 37.5 |  |
| dich_gehen_zu_sehn._-_Wingenbach_Frank | de | 193 | — | 0.029 | 98.9 % | 97.8 % | — | 43.3 |  |
| l'abandon_-_flo | fr | 210 | — | 0.030 | 99.7 % | 86.2 % | — | 47.4 |  |
| te_amo_-_fabios_la_nueva_expresion_de_la_cancion | es | 195 | — | 0.032 | 99.4 % | 99.4 % | — | 43.9 |  |
| ¡Óyeme_tiburón!_-_Corrientes | es | 180 | — | 0.033 | 99.0 % | 98.1 % | — | 39.5 |  |

## Peores casos

Mayor mediana de error de inicio:
- Avercage_-_Embers: 0.169 s
- Color_Out_-_Falling_Star: 0.142 s
- Pure_Mids_-_The_Leader: 0.063 s
- Cortez_-_Feel__Stripped_: 0.057 s
- HILA_-_Give_Me_the_Same: 0.054 s

## Notas

- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
