# Ephémérides
Permet de calculer les éphémérides du soleil et de la lune pour un observateur précis : lieu (latitude, longitude) et un moment précis (date, heure). 
Affiche le résultat dans la terminal (CLI) mais aussi sous forme d'une page HTML (via la navigateur) accompagné du diagramme solaire de la journée (azimut et hauteur solaire selon l'heure de la journée) ainsi que la phase de la lune.

* Plateforme de test : Debian 13 (Trixie)
* Language : Python 3.9+
* Bibliothèque interne Python principale : numpy, elementtree, astral
* Bibliothèque externe (à installer) : 
	* [Astral](https://pypi.org/project/astral/) 3
		* Ce module est installé d'origine avec Debian 13 (Trixie)
		* Installation (Debian) : apt install python3-astral
	* [MatPlotLib](https://matplotlib.org/) 3.3
		* Installation (Debian) : `apt install python3-matplotlib`
* Affichage : HTML5+CSS
* Gestion de l'horodatage suivant la timezone locale ("datetime aware")

## Utilisation
ephemeris.py est utilisable sous la forme d'un script python et peut être exécuté depuis le terminal avec la commande :
`python3 ephemeris.py`

Les données locales de l'utilisateur sont définies dans le fichier default.ini et sont à personnaliser. Si le fichier default.ini est absent ou erroné, le script se rabat sur les paramètres par défaut dans le scipt, soit : Paris (France) ; latitude=48.859 ; longitude=2.347 ; elevation=10 ; timezone = "Europe/Paris"

### fichier default.ini
Ce fichier permet de configurer les paramètres de calcul de l'éphéméride, soit :

- location : le nom du lieu
- region : le pays ou région du lieu
- latitude : la latitude géographique du lieu en degré décimaux
- longitude : la longitude géographique du lieu en degré décimaux
- elevation : l'altitude du lieu d'observation en mètres
- timezone : la "timezone" locale pour exprimé les heures, se reporter à [wikipédia](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) par exemple, pour une liste complète

### options
Le script accepte plusieurs options depuis le terminal

- -h (ou --help), affiche l'aide
- -d (ou --day), préciser le décalage en jour pour le calcul, sous forme d'un entier (par défaut : 0, soit maintenant)
- -s (ou --sol), inverse le mode diagramme solaire dans une fenêtre (par défaut : Faux)
- -w (ou --html), inverse le mode afficher résulats dans la navigateur (par défaut : Vrai)
- -x (ou --debug), inverse le mode debug (par défaut : Faux)

#### exemples
* `python3 ephemeris.py -d+2` : calcul pour dans 2 jours
* `python3 ephemeris.py -d-10` : calcul pour il y a 10 jours

## Vocabulaire
### Coordonnées géographique ([wikipédia](https://fr.wikipedia.org/wiki/Coordonn%C3%A9es_g%C3%A9ographiques))
Système de trois coordonnées qui décrivent un point ou une position sur le globe terrestre. Qui sont le plus souvent : la latitude, la longitude et l'altitude :

- **Latitude** : angle horaire, expression de la position du nord (positif) vers le sud (négatif). Les points d'une même latitude, constituent une parallèle (à l'équateur).
- **Longitude** : angle horaire, expression de la position de l'est (positif) vers l'ouest (négatif). Les points d'une même longitude, constitent un demi-arc : un méridien. Contrairement à la latitude, il n'existe aucune référence naturelle pour son origine, qui est historiquement défino par le mérifien de Greenwich.
- **Altitude** ou élévation par rapport au niveau moyen de la mer.

### Systèmes de coordonnées céleste ([wikipédia](https://fr.wikipedia.org/wiki/Syst%C3%A8me_de_coordonn%C3%A9es_c%C3%A9lestes))
En astronomie, un système de coordonnées céleste est un système de coordonnées permettant de déterminer une position dans le ciel, généralement exprimée en notation décimale ou pseudo-sexagésimale (l'unité de base de l'ascension droite étant cependant l'heure sidérale, équivalente à 15°).

Il existe plusieurs systèmes, utilisant une grille de coordonnées projetée sur la sphère céleste, de manière analogue aux systèmes de coordonnées géographiques utilisés à la surface de la Terre. Les systèmes de coordonnées célestes différent seulement dans le choix du plan de référence, qui divise le ciel en deux hémisphères le long d'un grand cercle (le plan de référence du système de coordonnées géographiques est l'équateur terrestre). Chaque système est nommé d'après son plan de référence : 

#### Coordonnées horizontales ([wikipédia](https://fr.wikipedia.org/wiki/Syst%C3%A8me_de_coordonn%C3%A9es_horizontales))
Plan de référence : l'horizon de l'observeteur

Système de coordonnées célestes (local) utilisé en astronomie par un observateur au sol. Le système sépare le ciel en deux hémisphères : l'un situé au-dessus de l'observateur et l'autre situé au-dessous, caché par le sol. Le grand cercle séparant les deux hémisphères situe le plan horizontal, à partir duquel sont établis une altitude et un azimut, qui constituent les deux principales coordonnées de ce système.

- La **hauteur** (h), angle vertical entre le plan horizontal et l'objet visé. Il varie entre 0° (horizon) et 90° (zénith). Il est cependant possible d'obtenir des valeurs négatives lors d'une observation à partir d'un lieu élevé. Le point situé aux pieds de l'observateur (-90°) est appelé le nadir.
- L'**azimut** (A), angle entre le nord ou le sud cardinal et la projection de la direction de l'objet observé sur le plan horizontal. Les azimuts sont généralement numérotés de 0° à 360° dans le sens horaire à partir du point cardinal (le sud pour le soleil)

#### Coordonnées équatoriales ([wikipédia](https://fr.wikipedia.org/wiki/Syst%C3%A8me_de_coordonn%C3%A9es_%C3%A9quatoriales))
Plan de référence : l'équateur du globe terrestre

Système de coordonnées célestes dont les valeurs sont indépendantes de la position de l'observateur. Ce système utilise un plan de référence (projection sur la sphère céleste de l'équateur céleste, qui divise le ciel en deux hémisphères ayant pour pôles la projection des pôles terrestres. La direction de référence est le point vernal : la direction du soleil lorsqu'il passe par la déclinaison nulle, dans le sens des déclinaisons croissantes, ce qui correspond à l'équinoxe de printemps dans l'hémisphère nord.

À partir de ces références, le système permet d'établir deux coordonnées angulaires :

- l'**ascension droite** (α, positif vers l'ouest) c'est l'angle mesuré sur l'axe de référence par rapport à l'angle de référence. Parfois exprimé de manière horaire (1 heure = 15°)
- la **déclinaison** (δ, positif pour le nord), c'est l'angle mesuré perpendiculaire àau plan de référence.

C'est un peu l'équivalent des coordonnées géographie (latitude, longitude) mais pour une position dans le ciel.

### Équinoxes ([wikipédia](https://fr.wikipedia.org/wiki/%C3%89quinoxe))
Un équinoxe est un instant de l'année où le Soleil traverse le plan équatorial terrestre, changeant ainsi d'hémisphère céleste. Cette définition astronomique précise la conception préscientifique selon laquelle l'équinoxe est le jour de l'année où la présence et l'absence du soleil dans le ciel sont d'égale en durée (sur toute la surface de la Terre, la durée du jour est alors égale à celle de la nuit si l'on inclut dans celle-ci l'aube et le crépuscule).

On appelle équinoxe de printemps (ou vernal) l'**équinoxe de mars** dans l'hémisphère nord et l'**équinoxe de septembre** dans l'hémisphère sud. On appelle équinoxe d'automne celui de septembre dans l'hémisphère nord et de mars dans l'hémisphère sud. 

Marque le changement de saison (printemps, automne).

### Solstices ([wikipédia](https://fr.wikipedia.org/wiki/Solstice))
Le solstice est un événement astronomique qui se produit deux fois par an, lorsque la position apparente du soleil atteint sa plus grande inclinaison vers le nord ou vers le sud, par rapport à l'équateur céleste. Cela entraîne la durée du jour la plus longue ou la plus courte de l'année.

Il s'oppose ainsi à l'équinoxe. Les solstices correspondent à une durée de jour et de nuit maximales, alternativement et de façon opposée entre les hémisphères nord et sud.

Une année connaît deux solstices : dans le calendrier grégorien, le premier est proche du 21 juin (**solstice d'été**), le second est proche du 21 décembre (**solstice d'hiver**). Ces dates changent légèrement au cours des années. Elles évoluent aussi sur les grandes périodes de temps en fonction des légers mouvements de l'axe de rotation terrestre. 

Marque le changement de saison (été, hiver).

### Moments du soleil dans le ciel

- L'**aube** (dawn) est le moment de la journée avant l'aurore et le lever du soleil. On distingue plusieurs type (voir plus bas)
- L'**aurore** est le bref moment ou le bord supérieur du disque solaire pointe à l'horizon
- Le **lever du soleil** (sunrise) du soleil est le moment ou le centre du disque solaire franchit l'horizon en y apparaissant
- Le **zénith** (zenith), point d'intersection de la varticale d'un lieu et la sphère céleste, c'est la verticale au-dessus de notre tête. Souvent confondu, dans le vocabulaire courant avec le point de culmination.
- **point du culmination** (noon), le point le plus élevé de la trajectoire d'un astre dans le ciel (12h en heure locale vrai).
- Le **crépuscule** (dusk) est le moment de la journée entre le coucher du soleil et la nuit. Comme pour l'aube on distingue plusieurs types.
- Le **coucher du soleil** (sunset) est le moment ou le centre du disque solaire franchit la ligne d'horizon pour y disparaitre
- Minuit (midnight)
- Journée (daylight) est la durée du jour, calculé comme de l'instant du lever ou coucher du soleil
- Nuit (night) est la durée de la nuit, calculé comme de l'instant du crépuscule astronomique à l'aube astronomique du jour suivant. La durée jour + nuit (suivant ces définitions) n'est pas courte que les 24 heures d'un jour, puisque l'aube et le crépuscule sont exclus.

Aube et crépuscule ont plusieurs définitions suivant le domaine d'application) :

- **civil** : période ou le centre du disque solaire est situé 6° sous l'horizon. Les planètes et les étoiles les plus brillantes deviennent visibles, la plupart des activités ne nécessitent pas de lumières artificielles.
- **nautique** : période ou le centre du disque solaire est situé entre 6° et 12° sous l'horizon. En mer la ligne d'horizon est encore visible (on la distingue visuellement de la mer).
- **astronomique** : période ou le centre du disque solaire est situé entre 12° et 18° sous l'horizon. Pour un observateur c'est le moment ou le maximum d'étoiles sont visibles (par ciel clair).

### Phase de la lune ([wikipédia](https://fr.wikipedia.org/wiki/Phase_de_la_Lune))
C'est la portion de la lune illuminée par le soleil et vue depuis la terre. Cette dernière correspond à la partie de la Lune orientée à la fois vers la Terre et vers le Soleil. Puisque la Lune se déplace en orbite autour de la Terre, les phases lunaires changent d'une journée à l'autre, complétant un cycle au bout d'une lunaison, d'une durée d'environ 29,5 jours.

### Couleurs du ciel
La couleur du ciel varie suivant les périodes de la journée et les conditions métérologiques, toutefois on distingue quelques périodes particulières :

* **Heure dorée** (golden hour) : courte période suivant le lever du soleil ou précédent le coucher du soleil. Disque solaire vers 4° sous l'horizon. Suivant le condition météorologique le ciel a des couleurs dorées, variant du bleu au jaune, orange, rouge en passant par le rose. Couleur particulièrement prisée des photographes.
* **Heure bleue** (blue hour) : période entre le jour et la nuit ou le ciel est totalement bleue foncé (crépuscule nautique et l'aube nautique). Disque solaire entre 4 et 6° sous l'horizon. Le ciel est alors d'une couleur presque entièrement bleu, plus foncé que le bleu ciel de la journée. Couleur particulièrement prisée des photographes.
* **Nuit noire** (noir) : période comprise entre le crépuscule et l'aube astronomique. Le ciel nocturne est caractérisé par l'absence du lumière solaire
* Ciel bleu de jour : période comprise entre le lever et le coucher du soleil. Sans nuage le ciel a des teintes bleu insaturé variant du bleu ciel, azur au bleu très pale (presque blanc).

## Données calculées et affichées
Toutes ces données sont calculées par le module Astral pour un moment et un observateur sur terre.
L'observateur est défini par ses coordonnées géographiques, le moment est calcul en heure locale.

### Jour (information complémentaires)

#### Phase de la lune (moon phase) : 
Définition des phases de la Lune selon Astral (valeur de 0 à 28) :

* Nouvelle lune : Astral [0;3[
* Premier croissant : Astral [3;7[
* Premier quartier : Astral [7;10[
* Gibeuse croissante Astral [10;14[
* Pleine lune : Astral [14;17[
* Gibeuse décroissante : Astral [17;21[
* Dernier quartier : Astral [21;24[
* Dernier croissant : Astral [24;28[

Ephemeris représente les phases lunaire graphique avec les caractères emoji du l'UTF-16 (de \U0001F311 à \U0001F318). 

## Diagramme solaire
Le diagramme solaire est une représentation de la position de l'astre solaire dans le ciel pour une journé, dans le système de coordonénes horizontales pour un lieu donné.
Calcul du diagramme solaire pour une latitude : adapté du script de _David Alberto_
source : [diagramme-solaire-azimut-hauteur](https://www.astrolabe-science.fr/diagramme-solaire-azimut-hauteur/)

Ce diagramme permet de visualiser le parcours du soleil dans le ciel du lieu tout au long de la journée.