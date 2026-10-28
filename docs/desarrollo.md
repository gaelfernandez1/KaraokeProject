# Guía de desarrollo

Cómo preparar un equipo para trabajar en el karaoke v3 y qué comandos se usan cada día.
Referencia: el portátil del proyecto (Windows 11 + WSL2 con Ubuntu 26.04, RTX 3050 Laptop de
4 GB).

## Requisitos

- Windows con WSL2 y una distribución Ubuntu. En Linux nativo, lo mismo sin la parte de Windows.
- Driver de NVIDIA instalado **en Windows** (no dentro de WSL). Dentro de WSL, `nvidia-smi` debe
  mostrar la GPU.
- Node 22 o superior.

## Instalación paso a paso

1. **ffmpeg** (con libass para los subtítulos y NVENC para codificar con la GPU):
   ```bash
   sudo apt update && sudo apt install -y ffmpeg
   ```
2. **uv** (gestor de Python; no necesita sudo):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
3. **pnpm** (gestor de paquetes de la web), vía corepack, que viene con Node:
   ```bash
   corepack install -g pnpm@10.33.0
   ```
   El corepack de Ubuntu (0.24) no sabe instalar pnpm 11 o superior; por eso se fija la 10.
4. **Dependencias del proyecto**, desde la raíz del repo:
   ```bash
   make setup                 # Python (sin GPU), hooks de pre-commit y la web
   uv sync --extra ml         # además torch con CUDA (unos GB), solo en el equipo con GPU
   ```
   Ojo: un `uv sync` a mano sin `--extra ml` desinstala torch (`make setup` no, porque usa
   `--inexact`). En el equipo con GPU, sincroniza a mano siempre con `--extra ml`.
5. **Comprobar que todo está bien:**
   ```bash
   make check-env
   ```
   Todo lo obligatorio debe salir `OK`. NVENC y torch salen como `aviso` si faltan, porque el
   código también funciona sin GPU (más lento).

## Comandos de cada día

| Qué | Comando |
|---|---|
| Todas las comprobaciones de CI en local | `make ci` |
| Formatear Python | `make format` |
| Tests de Python | `make test` (o `uv run pytest packages/engine -q`) |
| Web en modo desarrollo | `pnpm --dir web dev` |
| Regenerar JSON Schema y tipos TS tras tocar un contrato | `make contracts` |
| Validar un paquete de karaoke | `uv run karaoke validate <carpeta>` |
| Audio sintético para el paquete de ejemplo | `uv run karaoke demo fixtures/packages/demo-sintetico` |

## Problemas conocidos

- **WSL ve menos RAM que Windows** (unos 7–8 GB de 16). Los modelos grandes se cargan de uno en
  uno.
- **4 GB de VRAM**: un modelo en la GPU a la vez, en int8 o float16, y liberarlo antes del
  siguiente.
- **Cachés de root** (`.mypy_cache/3.10`, `input/`, `output/`) que dejó el Docker de la versión
  anterior: están ignorados por git; si molestan, `sudo rm -rf` sobre ellos.
- **Aviso de NumPy al importar torch**: inofensivo; desaparece cuando el motor añada NumPy.
