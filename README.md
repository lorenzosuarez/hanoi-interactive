# Hanoi Interactive Pro

**Author:** Lorenzo Suarez — September 9, 2025  
**License:** MIT

A professional, human-in-the-loop Tower of Hanoi visual analytics tool. Drag top disks, step optimally,
play/pause with a precise interval, undo, reset, and *resume* from any state with a shortest-path planner.

## Features
- Minimal UI: Play/Pause, Step, Undo, Reset + interval slider
- Manual drag & drop with legal-target highlighting
- Optimal continuation from any state via BFS in the legal state graph
- Full-visibility rendering (no clipping) with rounded disks and anti-aliased edges
- Keyboard shortcuts: Space (Play/Pause), Enter (Step), U/Backspace (Undo), R (Reset), Esc (Pause)

## Quickstart
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
hanoi --disks 5
# macOS if you need a GUI backend:
# pip install PyQt5
# MPLBACKEND=QtAgg hanoi --disks 5
```

## Development
- Install in editable mode and run:
```bash
pip install -e .
python -c "import hanoi_pro.ui as ui; print(ui.__doc__[:60])"  # smoke import
```
- Run the app in headless CI safely (no window) by forcing the `Agg` backend for tests.

## How it works
The app models configurations as vectors in `{0,1,2}^n`. Legal moves alter exactly one coordinate of the vector
consistent with the stack order. The shortest completion plan to the goal is computed by BFS.

## Español

**Autor:** Lorenzo Suarez — September 9, 2025  
**Licencia:** MIT

Herramienta profesional e interactiva para la Torre de Hanói. Podés arrastrar discos, avanzar paso a paso,
ejecutar automáticamente respetando el intervalo, deshacer y reiniciar, y **continuar** desde cualquier estado
con el camino **mínimo** hasta la meta.

### Características
- UI mínima: Play/Pause, Step, Undo, Reset + slider de intervalo
- Drag & drop con resaltado de destinos legales
- Continuación óptima vía BFS
- Render sin recortes con discos redondeados
- Atajos: Espacio (Play/Pause), Enter (Step), U/Backspace (Undo), R (Reset), Esc (Pause)

### Inicio rápido
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
hanoi --disks 5
# En macOS si falta backend:
# pip install PyQt5
# MPLBACKEND=QtAgg hanoi --disks 5
```
