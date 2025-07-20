# Ephémérides
Permet de calculer les éphémérides du soleil pour un lieu donné (latitude, longitude) et un moment précis (date, heure). 
Affiche le résultat dans la terminal mais aussi sous forme d'une page HTML (via la navigateur) accompagné du diagramme solaire de la journée (azimut et hauteur solaire selon l'heure de la journée) ainsi que la phase de la lune.

* Plateforme de test : Debian 12 (Bookworm)
* Language : Python 3
* Bibliothèque interne Python principale : numpy, astral 1.6, pytz, elementtree
* Bibliothèque externe (à installer) : MatPlotLib 3.3
* Affichage : HTML5+CSS

## Données calculées et affichées
### Jour
* Dawn (Aube) : période avant le lever du soleil, entre le nuit et le jour (6 à 0° sous l'horizon)
* Sunrise (Lever du soleil) : moment ou le soleil apparaît à l'horizon (Aurore)
* Noon (Midi) : moment ou le soleil est au plus haut (zénith)
* Midnight (Minuit) : moment ou le soleil est plus bas sous l'horizon
* Sunset (Coucher du soleil) : moment ou le soleil disparaît derrière l'horizon
* Dusk (Crépuscule) : moment après le coucher du soleil ou la nuit prend place (0 à 6° sous l'horizon)
* Daylight (Journée) : période du lever au coucher du soleil
* Night (Nuit) : période entre le fin du crépuscule et le début de l'aube, qui laisse apparaitre les astres
### Jour (information complémentaires)
* Golden hour (Heure dorée) : courte période suivant le lever du soleil ou précédent le coucher du soleil.
* Blue hour (Heure bleue) : période entre le jour et la nuit ou le ciel est totalement bleue foncé (crépuscule nautique et l'aube nautique).
* Equinoxe : Moment de l'année ou le jour est égal à la nuit, c'est aussi l'instant ou le solail traverse le plan équatorial terrestre. Marque le changement de saison.
* Solstice : Moment de l'année ou la position apparente du soleil atteint sa plus grand inclinaison. Marque le changement de saison. C'est aussi le moment de l'année pour la durée du jour est la plus longue ou la plus courte.
### Nuit
* Moonrise (Lever de lune)
* Moonset (Coucher de lune)
* Moon phase
#### Moon phase (Phase de la Lune) : 
Définition phases de Astral

* Nouvelle lune : Astral [0;3[
* Premier croissant : Astral [3;7[
* Premier quartier : Astral [7;10[
* Gibeuse croissante Astral [10;14[
* Pleine lune : Astral [14;17[
* Gibeuse décroissante : Astral [17;21[
* Dernier quartier : Astral [21;24[
* Dernier croissant : Astral [24;28[

## Diagramme solaire
Calcul du diagramme solaire pour une latitude,	adapté du script de David Alberto
source : https://www.astrolabe-science.fr/diagramme-solaire-azimut-hauteur/

Ce diagramme permet de visualiser le parcours du soleil dans le ciel du lieu tout au long de la journée.