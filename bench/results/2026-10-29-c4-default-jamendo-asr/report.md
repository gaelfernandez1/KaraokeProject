# Banco · c4-default · jamendo · sin letra

- Fecha: 2026-10-29T19:55:06+01:00
- Commit: 70c0da5
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

Mel-Band RoFormer (Kim, 8 s) + Whisper (HiTZ large-v3 for Galician, large-v3-turbo otherwise) + lyrics aligner (each language's default CTC model)

- **separator**: `karaoke_engine.separation:RoformerSeparator` v2 {'model': 'vocals_mel_band_roformer.ckpt', 'segment_size': 801}
- **transcriber**: `karaoke_engine.transcribe:WhisperTranscriber` v2
- **segmenter**: `karaoke_engine.transcribe:LineSegmenter` v1
- **aligner**: `karaoke_engine.align.aligner:LyricsAligner` v11

## Resumen

| Grupo | Canciones | Fallos | WER | CER | Inicio mediana | Inicio media | ≤ 0,3 s | ≤ 0,5 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) | Fuera de voz | Confianza < 0,3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| de | 20 | 0 | 13.9 % | 8.6 % | 0.029 | 0.112 | 98.3 % | 98.7 % | 0.073 | 0.035 | 86.0 % | — | 0 | 65 | 0.0 % | 17.1 % |
| en | 20 | 0 | 33.7 % | 27.7 % | 0.059 | 0.693 | 95.4 % | 95.6 % | 0.055 | 0.274 | 69.7 % | — | 0 | 65 | 0.0 % | 26.4 % |
| es | 20 | 0 | 15.0 % | 9.6 % | 0.028 | 0.173 | 98.2 % | 98.2 % | 0.092 | 0.120 | 87.4 % | — | 0 | 66 | 0.0 % | 16.9 % |
| fr | 19 | 0 | 26.7 % | 15.9 % | 0.030 | 0.056 | 98.7 % | 98.9 % | 0.080 | 0.001 | 74.7 % | — | 0 | 67 | 0.0 % | 27.5 % |
| total | 79 | 0 | 22.9 % | 15.7 % | 0.034 | 0.250 | 97.7 % | 97.9 % | 0.075 | 0.105 | 79.2 % | — | 0 | 66 | 0.0 % | 21.9 % |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 6.9 | 2867 | 2388 | 0.204 |
| transcriber | 0.1 | 1335 | 2119 | 0.026 |
| segmenter | — | 0 | 94 | 0.000 |
| aligner | 0.1 | 1559 | 3787 | 0.014 |

## Por canción

| Canción | Idioma | Duración | WER | Inicio mediana | ≤ 0,3 s | ≤ 0,5 s | Cobertura | Referencia | Fuera de voz | Confianza < 0,3 | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 10._Disparan_-_criatura | es | 160 | 11.3 % | 0.024 | 99.4 % | 99.4 % | 89.2 % | manual | 0.0 % | 22.7 % | es | 45.3 |  |
| 1_Freak_-_Automatisch_Gekommen | de | 188 | 9.0 % | 0.045 | 97.6 % | 97.6 % | 90.5 % | manual | 0.0 % | 32.0 % | de | 55.3 |  |
| Avercage_-_Embers | en | 243 | 82.6 % | 2.493 | 44.1 % | 44.1 % | 18.0 % | manual | 0.0 % | 78.1 % | en | 57.0 |  |
| Baila_-_Alfonso_Lugo | es | 210 | 9.2 % | 0.019 | 100.0 % | 100.0 % | 91.1 % | manual | 0.0 % | 27.9 % | es | 51.6 |  |
| Besando_Sapos_-_Dream_Tabu | es | 251 | 7.9 % | 0.033 | 97.7 % | 97.7 % | 94.7 % | manual | 0.0 % | 27.5 % | es | 62.3 |  |
| Bitte_beweg_dich_nicht_-_Bukto | de | 273 | 13.9 % | 0.038 | 97.4 % | 97.7 % | 87.0 % | manual | 0.0 % | 22.5 % | de | 77.8 |  |
| Burn_Out_Man_-_Abendblau | de | 260 | 8.1 % | 0.039 | 98.6 % | 99.0 % | 87.0 % | manual | 0.0 % | 10.9 % | de | 64.3 |  |
| CHRISTMAS_AVEC_TOI_-_imfreshyourepretty | fr | 234 | 53.3 % | 0.033 | 96.4 % | 96.4 % | 47.4 % | manual | 0.0 % | 41.5 % | fr | 58.1 |  |
| CLUB_DESTINO__-_Pensando_en_ti_-_CLUB_DESTINO | es | 219 | 12.1 % | 0.042 | 94.0 % | 94.0 % | 89.7 % | manual | 0.0 % | 13.7 % | es | 52.1 |  |
| Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique | de | 248 | 15.1 % | 0.051 | 97.4 % | 98.7 % | 82.6 % | manual | 0.0 % | 11.0 % | de | 56.6 |  |
| Capotes_à_un_Franc_-_elmanu | fr | 188 | 10.2 % | 0.025 | 99.5 % | 99.5 % | 89.4 % | manual | 0.0 % | 7.3 % | fr | 48.1 |  |
| Caralibro_-_Vagos_Permanentes | es | 279 | 21.2 % | 0.030 | 96.4 % | 96.4 % | 78.2 % | manual | 0.0 % | 22.0 % | es | 65.1 |  |
| Color_Out_-_Falling_Star | en | 222 | 32.2 % | 0.147 | 93.7 % | 94.3 % | 78.1 % | manual | 0.0 % | 33.8 % | en | 53.2 |  |
| Confession_-_Quesabe | fr | 148 | 40.0 % | 0.030 | 100.0 % | 100.0 % | 59.8 % | manual | 0.0 % | 35.9 % | fr | 36.7 |  |
| Cortez_-_Feel__Stripped_ | en | 241 | 9.6 % | 0.072 | 96.9 % | 96.9 % | 89.9 % | manual | 0.0 % | 11.2 % | en | 60.8 |  |
| Culture_&_Co._-_cool.cavemen | fr | 212 | 43.0 % | 0.024 | 98.8 % | 100.0 % | 63.6 % | manual | 0.0 % | 58.7 % | fr | 49.7 |  |
| DON_VALDES_-_Tu_sais_Man | fr | 209 | 32.7 % | 0.032 | 94.1 % | 94.9 % | 74.1 % | manual | 0.0 % | 41.8 % | fr | 53.7 |  |
| Da_wurdest_du_geboren_-_Alice_Tlustos_ | de | 207 | 2.7 % | 0.048 | 100.0 % | 100.0 % | 98.0 % | manual | 0.0 % | 11.5 % | de | 49.6 |  |
| Der_Baum_-_Dienstag_is_Damensauna_(2) | de | 209 | 9.5 % | 0.027 | 100.0 % | 100.0 % | 91.0 % | manual | 0.0 % | 12.6 % | de | 50.5 |  |
| Der_Musiker_-_d-music | de | 271 | 19.1 % | 0.020 | 100.0 % | 100.0 % | 83.9 % | manual | 0.0 % | 9.1 % | de | 66.1 |  |
| Die_Revolution_gehört_Dir!_-_partysahnen | de | 167 | 18.2 % | 0.027 | 97.0 % | 97.0 % | 85.3 % | manual | 0.0 % | 36.6 % | de | 39.7 |  |
| Diosa_de_la_noche_-_Brunela_Crochenci | es | 230 | 24.2 % | 0.030 | 100.0 % | 100.0 % | 89.1 % | manual | 0.0 % | 18.9 % | es | 55.0 |  |
| Drei_Nüsse_-_patrouille | de | 259 | 4.6 % | 0.026 | 99.0 % | 99.2 % | 94.4 % | manual | 0.0 % | 7.3 % | de | 65.6 |  |
| En_liberté_-_tom.leyak | fr | 234 | 17.7 % | 0.033 | 100.0 % | 100.0 % | 87.2 % | manual | 0.0 % | 25.1 % | fr | 58.0 |  |
| Esencia_-_NandoMalo_ | es | 262 | 15.6 % | 0.023 | 99.7 % | 99.7 % | 88.0 % | manual | 0.0 % | 12.7 % | es | 64.2 |  |
| Explosive_Ear_Candy_-_Like_The_Sun | en | 193 | 39.9 % | 0.049 | 100.0 % | 100.0 % | 96.2 % | manual | 0.2 % | 14.3 % | en | 51.9 |  |
| Fantasma_-_Los_Rombos | es | 166 | 56.4 % | 0.036 | 98.4 % | 98.4 % | 69.3 % | manual | 0.0 % | 0.0 % | es | 37.7 |  |
| Freifliegen_-_durch.dick.und.duenn | de | 250 | 11.1 % | 0.030 | 100.0 % | 100.0 % | 89.6 % | manual | 0.0 % | 16.4 % | de | 59.2 |  |
| Fußabdrücke_-_Andreas_Jachmann | de | 241 | 15.6 % | 0.022 | 100.0 % | 100.0 % | 85.1 % | manual | 0.1 % | 3.6 % | de | 57.9 |  |
| Guayeteo_-_JhoyKing | es | 158 | 32.5 % | 0.025 | 99.2 % | 99.6 % | 73.8 % | manual | 0.0 % | 29.3 % | es | 41.6 |  |
| HILA_-_Give_Me_the_Same | en | 234 | 28.2 % | 0.065 | 95.2 % | 95.2 % | 70.8 % | manual | 0.0 % | 24.3 % | en | 56.1 |  |
| Háblame_-_(Talk_to_me)_-_Brunela_Crochenci | es | 214 | 16.0 % | 0.030 | 97.8 % | 97.8 % | 84.0 % | manual | 0.0 % | 34.4 % | es | 49.7 |  |
| Ich_kann_dich_nicht_vergessen_-_Wingenbach_Frank | de | 258 | 10.6 % | 0.032 | 100.0 % | 100.0 % | 89.9 % | manual | 0.0 % | 11.8 % | de | 61.2 |  |
| Intentando_Destacar_-_Sundayers_ | es | 220 | 20.1 % | 0.023 | 100.0 % | 100.0 % | 78.1 % | manual | 0.0 % | 13.1 % | es | 53.1 |  |
| Intro_[Pulsschlag]_-_Zeugen_der_Leere_(2) | de | 157 | 28.0 % | 0.038 | 95.2 % | 100.0 % | 76.8 % | manual | 0.0 % | 51.2 % | de | 36.9 |  |
| JASON_MILLER_-_CROWD_PLEASER | en | 193 | 14.0 % | 0.050 | 100.0 % | 100.0 % | 87.1 % | manual | 0.0 % | 10.0 % | en | 59.8 |  |
| Keine_Lust_-_Jonny_M | de | 229 | 28.4 % | 0.016 | 93.0 % | 93.8 % | 69.9 % | manual | 0.0 % | 7.8 % | de | 66.6 |  |
| Kinematic_-_Peyote | en | 183 | 25.2 % | 0.055 | 96.7 % | 97.5 % | 81.6 % | manual | 0.0 % | 29.5 % | en | 44.8 |  |
| LUNABLIND_-_Vision__Radio_Edit_ | en | 221 | 36.1 % | 0.070 | 88.2 % | 88.2 % | 64.6 % | manual | 0.0 % | 16.5 % | en | 56.4 |  |
| La_rumba_del_coronavirus_-_Rich_Don_Jeri | es | 187 | 9.8 % | 0.031 | 96.0 % | 96.0 % | 90.2 % | manual | 0.1 % | 12.3 % | es | 49.6 |  |
| Le_musée_d'air_contemporain_-_KPTN | fr | 184 | 10.3 % | 0.022 | 99.6 % | 99.6 % | 94.9 % | manual | 0.0 % | 13.0 % | fr | 46.8 |  |
| Le_royaume_des_glous_glous_-_Raoul_de_QSM | fr | 163 | 25.7 % | 0.035 | 99.3 % | 99.3 % | 75.7 % | manual | 0.0 % | 25.8 % | fr | 40.3 |  |
| Les_files_d'attente_-_Law' | fr | 196 | 39.6 % | 0.032 | 97.2 % | 97.8 % | 56.1 % | manual | 0.0 % | 27.2 % | fr | 48.0 |  |
| Libre_by_CybeR_AttaCK_-_CyberAttacK | fr | 217 | 25.0 % | 0.028 | 100.0 % | 100.0 % | 79.3 % | manual | 0.0 % | 31.4 % | fr | 55.2 |  |
| Lower_Loveday_-_Is_It_Right_ | en | 180 | 10.6 % | 0.057 | 100.0 % | 100.0 % | 88.7 % | manual | 0.0 % | 18.5 % | en | 44.2 |  |
| Mes_Larmes_-_kobzx2z | fr | 159 | 41.0 % | 0.024 | 95.2 % | 96.2 % | 54.1 % | manual | 0.0 % | 47.0 % | fr | 41.1 |  |
| Moon_I_Mean_-_Wrong_Concept | en | 220 | 73.9 % | 0.085 | 82.9 % | 82.9 % | 25.7 % | manual | 0.0 % | 35.6 % | en | 53.7 |  |
| Musik_-_Heiko | de | 295 | 6.3 % | 0.024 | 100.0 % | 100.0 % | 95.4 % | manual | 0.1 % | 10.5 % | de | 70.7 |  |
| Mère_nature_-_Law' | fr | 225 | 15.4 % | 0.037 | 100.0 % | 100.0 % | 89.0 % | manual | 0.0 % | 20.5 % | fr | 55.5 |  |
| POIGNEE_DE_MAIN_-_Cabbac | fr | 209 | 17.1 % | 0.031 | 99.1 % | 99.1 % | 77.4 % | manual | 0.2 % | 21.0 % | fr | 50.1 |  |
| Palabras_-_Javier_Gomez_Bello | es | 216 | 9.4 % | 0.033 | 93.8 % | 93.8 % | 91.0 % | manual | 0.0 % | 6.5 % | es | 53.2 |  |
| Pas_que_tes_pas_-_AZUL | fr | 202 | 14.7 % | 0.037 | 100.0 % | 100.0 % | 85.8 % | manual | 0.0 % | 41.5 % | fr | 51.2 |  |
| Pluie_d'entre_deux_saisons_-_Midnight_Prefou | fr | 205 | 31.7 % | 0.037 | 100.0 % | 100.0 % | 71.6 % | manual | 0.2 % | 23.8 % | fr | 48.6 |  |
| Pure_Mids_-_The_Leader | en | 262 | 96.0 % | 2.714 | 33.3 % | 33.3 % | 5.3 % | manual | 0.0 % | 28.6 % | en | 57.9 |  |
| Quentin_Hannappe_-_Keep_On | en | 190 | 12.6 % | 0.045 | 100.0 % | 100.0 % | 92.0 % | manual | 0.0 % | 20.0 % | en | 45.3 |  |
| Quiero_y_Puedo_-_Nacidos_de_la_Tierra | es | 236 | 5.9 % | 0.027 | 100.0 % | 100.0 % | 95.2 % | manual | 0.0 % | 15.8 % | es | 68.8 |  |
| Ridgway_-_Fire_Inside | en | 284 | 29.7 % | 0.047 | 97.7 % | 97.7 % | 56.9 % | manual | 0.0 % | 25.1 % | en | 67.0 |  |
| Rxbyn_-_Bad_Side | en | 217 | 16.6 % | 0.056 | 99.0 % | 99.0 % | 89.5 % | manual | 0.0 % | 22.5 % | en | 56.7 |  |
| SHANEY_23_feat._G1NA_G._x_In_den_Strassen_-_Shaney_23 | de | 211 | 16.4 % | 0.042 | 98.9 % | 100.0 % | 79.5 % | manual | 0.0 % | 33.3 % | de | 55.1 |  |
| Schnodderdodder_-_Abendblau | de | 197 | 14.7 % | 0.022 | 99.6 % | 99.6 % | 88.7 % | manual | 0.0 % | 14.1 % | de | 50.1 |  |
| Sehnsucht-Unplugged_-_REH-TORTE | de | 233 | 25.2 % | 0.033 | 99.1 % | 99.1 % | 76.2 % | manual | 0.1 % | 13.1 % | de | 54.7 |  |
| Sin_miedo_-_Living_Camboya | es | 223 | 5.8 % | 0.027 | 97.5 % | 97.5 % | 94.7 % | manual | 0.0 % | 13.0 % | es | 54.4 |  |
| Slingshot_Miracle_-_Whistler | en | 229 | 14.1 % | 0.063 | 96.4 % | 98.6 % | 85.2 % | manual | 0.0 % | 29.5 % | en | 55.3 |  |
| Songwriterz_-_Back_In_Time | en | 209 | 25.6 % | 0.062 | 91.7 % | 91.7 % | 71.0 % | manual | 0.1 % | 32.9 % | en | 52.1 |  |
| Séculaire_feat._Nÿme_-_saru | fr | 159 | 23.3 % | 0.023 | 99.6 % | 100.0 % | 79.4 % | manual | 0.1 % | 24.0 % | fr | 41.0 |  |
| Te_Recuerdo_-_Wilson_Way | es | 194 | 8.5 % | 0.028 | 97.9 % | 98.1 % | 92.6 % | manual | 0.0 % | 15.4 % | es | 50.4 |  |
| The.madpix.project_-_One_Way_Street | en | 171 | 28.8 % | 0.063 | 97.1 % | 97.1 % | 74.9 % | manual | 0.1 % | 14.3 % | en | 40.2 |  |
| The_Rinn_-_Voices__2017_Version_ | en | 231 | 58.4 % | 0.078 | 78.8 % | 81.2 % | 41.9 % | manual | 0.0 % | 30.5 % | en | 52.9 |  |
| Tom_Orlando_-_The_One__feat._Tina_G_ | en | 240 | 53.2 % | 0.043 | 97.9 % | 97.9 % | 57.4 % | manual | 0.0 % | 22.2 % | en | 58.7 |  |
| Une_Vie_De_Roi_-_david | fr | 303 | 10.3 % | 0.030 | 100.0 % | 100.0 % | 89.4 % | manual | 0.0 % | 5.1 % | fr | 74.0 |  |
| Vente_-_Fafarulo_Calabaza | es | 336 | 12.9 % | 0.033 | 99.5 % | 99.5 % | 86.7 % | manual | 0.0 % | 9.5 % | es | 84.6 |  |
| Veränderung_-_doromusis | de | 194 | 13.7 % | 0.029 | 98.4 % | 98.4 % | 86.3 % | manual | 0.0 % | 17.2 % | de | 47.4 |  |
| Wordsmith_-_The_Statement | en | 171 | 28.8 % | 0.057 | 91.3 % | 91.3 % | 67.3 % | manual | 0.0 % | 31.1 % | en | 64.7 |  |
| Yuanan_-_Miedo_-_Yuanan | es | 169 | 24.6 % | 0.027 | 96.6 % | 96.6 % | 76.9 % | manual | 0.0 % | 21.2 % | es | 49.4 |  |
| de_bonne_humeur_-_Le_Nez_Tordu | fr | 161 | 21.3 % | 0.029 | 100.0 % | 100.0 % | 82.3 % | manual | 0.0 % | 14.6 % | fr | 41.3 |  |
| dich_gehen_zu_sehn._-_Wingenbach_Frank | de | 193 | 8.2 % | 0.030 | 96.4 % | 97.6 % | 91.7 % | manual | 0.0 % | 9.6 % | de | 46.7 |  |
| l'abandon_-_flo | fr | 210 | 19.5 % | 0.029 | 97.8 % | 98.1 % | 78.6 % | manual | 0.0 % | 18.2 % | fr | 52.1 |  |
| te_amo_-_fabios_la_nueva_expresion_de_la_cancion | es | 195 | 6.5 % | 0.033 | 98.1 % | 98.7 % | 92.9 % | manual | 0.1 % | 8.2 % | es | 46.7 |  |
| ¡Óyeme_tiburón!_-_Corrientes | es | 180 | 17.6 % | 0.036 | 93.6 % | 93.6 % | 81.4 % | manual | 0.0 % | 14.1 % | es | 44.4 |  |

## Peores casos

Mayor mediana de error de inicio:
- Pure_Mids_-_The_Leader: 2.714 s
- Avercage_-_Embers: 2.493 s
- Color_Out_-_Falling_Star: 0.147 s
- Moon_I_Mean_-_Wrong_Concept: 0.085 s
- The_Rinn_-_Voices__2017_Version_: 0.078 s

Mayor WER:
- Pure_Mids_-_The_Leader: 96.0 %
- Avercage_-_Embers: 82.6 %
- Moon_I_Mean_-_Wrong_Concept: 73.9 %
- The_Rinn_-_Voices__2017_Version_: 58.4 %
- Fantasma_-_Los_Rombos: 56.4 %

## Notas

- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
- Sin referencia: «Fuera de voz» es la parte del tiempo de las palabras en la que la voz (separada) calla; «Confianza < 0,3», la parte de las palabras con confianza baja.
