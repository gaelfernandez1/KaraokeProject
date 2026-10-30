# Fonts for the lyrics themes

Built by `scripts/build_fonts.py` from [google/fonts](https://github.com/google/fonts) at commit
`6157dfaa640ca5738b4d1a7070fe389c3036d7fc`. Each one is the variable font fixed at one instance,
renamed to a single-face family, and cut down to Latin, Greek, Cyrillic, combining marks and
general punctuation. All are under the SIL Open Font License 1.1 (none reserves its name); the
licence of each family sits next to it.

| File | Family | Source | Instance |
|---|---|---|---|
| `Nunito-Black.*` | Nunito Black | `ofl/nunito/Nunito[wght].ttf` | wght 900 |
| `Inter-ExtraBold.*` | Inter ExtraBold | `ofl/inter/Inter[opsz,wght].ttf` | wght 800, opsz 32 |
| `AtkinsonHyperlegibleNext-ExtraBold.*` | Atkinson Hyperlegible Next ExtraBold | `ofl/atkinsonhyperlegiblenext/AtkinsonHyperlegibleNext[wght].ttf` | wght 800 |

`.ttf` is for libass (video export), `.woff2` for browsers, and `.metrics.json` holds every
character's advance width so both break lines in the same places.
