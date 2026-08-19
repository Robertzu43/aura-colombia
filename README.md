# Aura Colombia 🇨🇴

Página para votar quién es la persona con más aura de Colombia, al estilo de
[aura-argentina.placeground.site](https://aura-argentina.placeground.site) pero con
colores y personajes colombianos.

## Cómo funciona

- **Ranking Elo**: las 100 personas más conocidas de Colombia arrancan con 1000 de aura.
- **Batallas 1v1**: la página te muestra dos personajes y eliges quién tiene más aura
  (clic o flechas `←` / `→`). El ganador roba aura al perdedor según la fórmula Elo (K=32).
- **Ranking en vivo**: pestaña 🏆 con el top 100, medallas, corona para el líder y barras de aura.
- Los votos se guardan en `localStorage` del navegador.

## Stack

Un solo `index.html` estático — HTML + CSS + JS vanilla, sin build ni dependencias.
Listo para deployar directo en Placeground o cualquier hosting estático.

## Correr local

```sh
python3 -m http.server 8000
# abrir http://localhost:8000
```
