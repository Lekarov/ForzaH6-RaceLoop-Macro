# ForzaH6 — Race Loop Macro

<div align="center">

**Boucle de courses automatisée pour Forza Horizon 6 — overlay live, phases visuelles, compteur de tours.**

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D4?style=flat-square&logo=windows&logoColor=white)
![pynput](https://img.shields.io/badge/pynput-keyboard%20automation-FF6B35?style=flat-square)

</div>

---

## Description

Macro de boucle de courses pour **Forza Horizon 6**.  
Lance et relance automatiquement une course en séquençant les phases (départ, course, fin, menus)  
avec un overlay Tkinter flottant indiquant la phase en cours, le temps restant et le nombre de tours.

---

## Fonctionnalités

- **Boucle automatique** — enchaîne les courses sans intervention manuelle
- **Overlay live** — affiche la phase, le timer et le compteur de tours en temps réel
- **Phases visuelles** — chaque phase a sa propre couleur (départ · course · menus · chargement)
- **Touche Z maintenue** — maintien optionnel d'une touche pendant la course (configurable)
- **Toggle clavier** — activation / désactivation instantanée (F2 par défaut, remappable)
- **Durées personnalisables** — délais, durée de course, timings des menus
- **Config persistante** — sauvegarde dans `%APPDATA%\Pestovich\forza6_config.json`
- **Overlay draggable** — repositionnable librement sur l'écran
- **Opacité réglable** — de 10% à 100%

---

## Phases

| Phase | Couleur | Description |
|---|---|---|
| `DEPART` | 🟡 Orange | Délai initial avant le début de la course |
| `COURSE` | 🟢 Vert | Course en cours (touche Z maintenue si activé) |
| `FIN COURSE` | 🟡 Orange | Frappe X pour valider la fin |
| `TOUCHE X` | 🟡 Orange | Confirmation fin de course |
| `ATTENTE →↵` | 🔵 Bleu | Navigation dans les menus |
| `ENTREE 1` | 🔵 Bleu | Premier Enter pour relancer |
| `CHARGEMENT` | 🟣 Violet | Attente du chargement |
| `ENTREE 2` | 🟣 Violet | Second Enter au départ |
| `EN ATTENTE` | ⬛ Gris | Macro en pause |

---

## Architecture

```
ForzaH6-RaceLoop-Macro/
├── forza_race_loop.py    Moteur + overlay Tkinter (fichier unique)
└── launch.bat            Lanceur Windows
```

### Composants internes (`forza_race_loop.py`)

```
Engine          Moteur de boucle — phases · timers · threading
  └── _run()   Séquence complète d'une boucle de course
  └── _sleep_phase()  Timer par phase avec interruption propre

Overlay (Tkinter)
  ├── Header   Titre + toggle actif/inactif
  ├── Phase    Nom coloré + barre de progression
  ├── Timer    Temps restant en secondes
  ├── Counter  Nombre de tours effectués
  └── Config   Panneau réglages (durées · touche · opacité)
```

---

## Installation

**Prérequis** — Python 3.11+ · Windows 10/11

```bash
pip install pynput
```

**Lancement**

```
double-clic sur launch.bat
```

ou

```bash
python forza_race_loop.py
```

---

## Raccourcis

| Touche | Action |
|---|---|
| `F2` | Activer / Désactiver la boucle (remappable) |
| `Glisser l'overlay` | Repositionner la fenêtre |

---

## Configuration

Panneau de configuration intégré dans l'overlay :

| Paramètre | Défaut | Description |
|---|---|---|
| Délai départ | 3.0 s | Pause avant le début de la course |
| Durée course | 56.0 s | Durée de la phase de course |
| Délai X | 0.3 s | Délai avant frappe X |
| Entrée 1 | 2.0 s | Délai premier Enter |
| Chargement → Entrée 2 | 13.0 s | Attente chargement |
| Touche maintenue | Z | Touche maintenue pendant la course |
| Durée frappe | 80 ms | Durée des frappes clavier |
| Opacité | 92% | Transparence de l'overlay |

La configuration est sauvegardée automatiquement dans :
```
%APPDATA%\Pestovich\forza6_config.json
```

---

<div align="center">

Développé par **Pestovich**

</div>
