#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__application__="ephemeris.py"
__appname__="Éphémérides"
__version__="0.5.2"
__author__="Pierre-Alain Dorange (MadDog)"
__copyright__=f"Copyright septembre 2025, {__author__}"
__license__="BSD-3-Clauses"			# voir https://en.wikipedia.org/wiki/BSD_licenses
__contact__="pdorange@mac.com"
__source__="https://github.com/padorange/ephemeris"

"""
	Ephemeris
	-----------------------------------------------------------------------------------------
	Script Python 3.13, testé sur Debian 13 (trixie)
	-----------------------------------------------------------------------------------------
	Permet de calculer les données astronomique du soleil et de la lune par rapport à un point (observateur)sur terre
		grâce à la bibliothèque Astral, inclus dans la plupart des distributions Python.
	Debian 13 inclus la version Astral 3.2, rien à installer.
	
	-- Modules astral (installé par défaut pour Python3 / Debian 13)------------------------------------------------------------------------
		Astral 3.2 (https://sffjunkie.github.io/astral/index.html)
	-- Modules spécifiques à installer (licences : voir readme.md) ---------------------------
		MatPlotLib 3.10 (https://matplotlib.org/)
			permet de réaliser de jolis graphiques
			
	-- Notions Astronomiques -----------------------------------------------------------------
		Voir le fichier readme.md		
		Heure dorée			instant ou le disque solaire est 4° sous l'horizon
		Heure bleu			instant ou le disque solaire est 4 et 6° sous l'horizon
	-- Paramètres CLI ------------------------------------------------------------------------
		-h  : aide
		-dX : ajout X jours à la date actuelle
		-s  : afficher l'image du diagramme solaire
		-w  : affiche le HTML crée avec le navigateur
		-x  : mode debug
	-- Historique ------------------------------------------------------------------------------
	0.1 : janvier-février 2025 : première version
	0.2 : février-mars 2025 : résultat sous forme HTML5 + option CLI "-d"
	0.3 : mars-avril 2025 : intégration diagramme solaire en azimuth et hauteur + position solaire selon target_date + paramètre "-s"
	0.4 : juillet 2025 : debug calcul variation durée jour + ajout option CLI "-x", "-s" et "-w" + optimisation du code
	0.5 : septembre 2025 : adaptation pour astral 3.2 (par défaut avec Debian trixie)
						gestion exception ValueError pour le calcul lunaire (pas de lever)
						retour à la police de caractères par défaut de MatPlotLib : default_font="DejaVu Sans" pour éviter l'erreur de font non disponible
						correction lecture longitude dans default.ini
						utilisation des heures locales partout (datetime aware)
						correction calcul de l'élévation solaire (heure local au lieu de UTC+0)
						amélioration rédaction du readme.md
						afficher timedelta sous forme HH:MM:SS
	
	-- A Faire (to do) --------------------------------------------------------------------------
	Bug cosmétique : Police 'Roboto Condensed' absente, géré l'erreur
		voir : <https://matplotlib.org/stable/users/explain/text/fonts.html>
		En attendant retour à "DejaVu Sans"
	Affichage (txt et HTML) : mieux présenter en séparant Soleil et Lune et instant présent (élévation solaire par exemple)
	Ajouter les paramètres locaux et les globales pour MatPlotLib dans default.ini (font, fontsize) ?
	Ajouter la personnalisation des couleurs des courbes solaire dans default.ini ?
	Proposer une option pour l'heure locale et l'heure UTC ?
	Proposer une option pour l'aube et crépuscule (civile, nautique, astronomique)
	Améliorer pour Astral 3 : utiliser Location() ?
	HTML avec une présentation graphique par icone
	
	Vérification des calculs avec : https://www.ephemeride.com/, https://www.ephemeride-jour.fr/ et https://heuresolaire.com/ephem_day
"""

# -- Bibliothèques  ---------------------------------------------------------------

# Bibliothèques par défaut de Python
import sys,getopt,os
from datetime import datetime,timedelta	# gestion date et heure standard
from zoneinfo import ZoneInfo			# gestion des timezones (python 3.9+)
import configparser						# gestion fichier.INI (paramètres et configuration)
import codecs							# gestion utf des chaines
import math,numpy as np					# calculs scientifique
import astral							# Astral 3.2 (version incluse pour Debian 13)
import astral.sun,astral.moon
from xml.etree import ElementTree as ET	# gestion elementtree pour créer le résultat HTML
import webbrowser						# module pour ouvrir une URL dans le navigateur par défaut

# Bibliothèques supplémentaires à installer (voir readme.md)
import matplotlib.pyplot as plt			# matplotlib 3.3

# définir le répertoire par défaut du script comme celui du source (gestion du lancement hors dossier source)
path=os.path.dirname(os.path.abspath(__file__))
os.chdir(path)

# -- Constantes et globales ------------------------------------------------------
_verbose=True
_debug=False

default_shift=0
default_solar=False
default_window=True

default_config="default.ini"					# fichier de cong par défaut : définir la position par défaut de l'observateur
default_directory="html"						# répertoire local ou enregistrer les éléments HTML
default_diagsol_file="diagramme_solaire.png"	# nom du fichier pour sauvegarder le diagramme solaire
default_html_file="ephemeris.html"				# nom du fichier html généré
maxDeclinaison=23.436							# déclinaison maximale du soleil / terre

# personnalisation pour le diagramme solaire
# default_font="Roboto Condensed"
default_font="DejaVu Sans"					# back to default matplotlib font
default_fontsize=8							# smallest readable for DejaVu Sans
diagram_width=6.0							# taille du diagram en pouces (2.54 cm)
diagram_height=5.0
diagram_sun_halo=48							# diamètre du halo solaire (pixels)
diagram_sun_disk=6							# diamètre du disque solaire (pixels)
color_sun="gold"							# couleur du soleil sur le diagramme
color_sun_halo="OrangeRed"					# couleur du halo solaire sur le diagramme
color_coordinates="Red"						# couleur des coordonnées sur le diagramme
color_hours='royalblue'						# couleurs pour la grille des heures
color_halfhours='gray'						# couleur pour la grille des demi-heures
color_decl_solstice_winter='IndianRed'		# couleurs pour les courbes des parcours solaire
color_decl_equinox='BlueViolet'
color_decl_solstice_summer='Teal'
color_decl_current='OrangeRed'

# -- Classes -----------------------------------------------------------------------

class Config():
	"""	objet Config pour regrouper les paramètres utilisés, stockés dans le fichier INI de configuration
		certaines valeurs par défaut (__init__) sont surchargées par la lecture du fichier de configration (load)
		voir default.ini
	"""

	def __init__(self, filename=default_config):
		# chargement des paramètre depuis le fichier de configuration (default.ini)
		# avec valeurs par défaut si erreur de chargement ou valeur non définie
		#	Location : Paris, France
		self.location="Paris"
		self.region="France"
		self.latitude=48.859
		self.longitude=2.347
		self.elevation=10
		self.tz="Europe/Paris"
		try:
			config=configparser.RawConfigParser()
			with codecs.open(filename,'r',encoding='utf-8') as f:
				config.read_file(f)
			try:
				self.location=config.get('observer','location')
			except Exception as ex:
				print("error:",ex)
			try:
				self.region=config.get('observer','region')
			except Exception as ex:
				print("error:",ex)
			try:
				self.latitude=float(config.get('observer','latitude'))
			except Exception as ex:
				print("error:",ex)
			try:
				self.longitude=float(config.get('observer','longitude'))
			except Exception as ex:
				print("error:",ex)
			try:
				self.elevation=float(config.get('observer','elevation'))
			except Exception as ex:
				print("error:",ex)
			try:
				self.tz=config.get('observer','timezone',fallback=None)
			except Exception as ex:
				print("error:",ex)
		except Exception as ex:
			print("ERREUR : fichier de configuration introuvable:",default_config)
			print("error :",ex)
		if _debug: 
			print(self)
		return
	
	def __str__(self):
		value=f"Observateur : {self.location} ({self.region}) / timezone = {self.tz}"
		value+=f"\n\tlatitude : {self.latitude:.4f}°, longitude = {self.longitude:.4f}°, altitude = {self.elevation:.1f} m"
		return value

class MoonPhase():
	""" Gère les phases de la lune comme des désignations, des émoticones et des images d'illustration
		converti depuis la phase lunaire calculé par Astral (flottant entre 0.0 et 27.99) en une dénomination et une image
		Phases de la lune (ref : https://fr.wikipedia.org/wiki/Phase_de_la_Lune)
		Emoticones : 
		Images référence : https://starwalk.space/fr/moon-calendar
			Les images doivent être dans le sous-dossier : self.prefix
		Cycle Lunaire : 29.5 jours
	"""
	def __init__(self, phase):
		prefix="./phases/lune_"
		self.phase=phase
		if phase<2.0 or phase>=28.0: 	
			self.name="Nouvelle Lune"
			self.emoticon="\U0001F311"
			self.image="f{prefix}00.png"
		elif phase<6.0:					
			self.name="Premier croissant"
			self.emoticon="\U0001F313"
			self.image="f{prefix}01.png"
		elif phase<9.0:					
			self.name="Premier quartier"
			self.emoticon="\U0001F314"
			self.image="f{prefix}02.png"
		elif phase<14.0:					
			self.name="Lune Gibeuse croissante"
			self.emoticon="\U0001F315"
			self.image="f{prefix}03.png"
		elif phase<17.0:					
			self.name="Pleine Lune"
			self.emoticon="\U0001F316"
			self.image="f{prefix}04.png"
		elif phase<22.0:					
			self.name="Lune Gibeuse décroissante"
			self.emoticon="\U0001F317"
			self.image="f{prefix}05.png"
		elif phase<25.0:					
			self.name="Dernier quartier"
			self.emoticon="\U0001F318"
			self.image="f{prefix}06.png"
		elif phase<28.0:					
			self.name="Dernier croissant"
			self.emoticon="\U0001F319"
			self.image="f{prefix}07.png"
		else:									
			self.name=f"Erreur phase non géré : {phase}"
			self.emoticon="\U0001FA90"
			self.image="error.png"
	
	def getName(self):
		return self.name

	def getEmoticon(self):
		return self.emoticon

	def getPicture(self):
		return self.image

class SunPhase():
	""" Gère les dénominations et couleurs du ciel suivant son élévation dans le ciel (degrés décimaux)
		Les dénominations proviennent de Wikipédia :
			https://fr.wikipedia.org/wiki/Couleur_du_ciel
			https://fr.wikipedia.org/wiki/Heure_dorée
			https://fr.wikipedia.org/wiki/Heure_bleue
		Les couleurs sont des dénominations de la norme X11, utilisés par SVG, CSS et HTML :
			https://htmlcolorcodes.com/fr/noms-de-couleur/
	"""
	def __init__(self,elevation,target_date):
		self.elevation=elevation
		self.target_date=target_date
		if target_date.hour<12:
			prefix="Aube"
		else:
			prefix="Crépuscule"
		if elevation>=6.0 :
			self.name="Jour"
			self.textcolor="Black"
			self.backcolor="SkyBlue"
		elif elevation<0.0 and elevation>=-6.0:
			self.name=f"{prefix} civil"
			self.textcolor="Black"
			self.backcolor="DeepSkyBlue"
		elif elevation<-0.5 and elevation>=4.0:	
			self.name=f"{prefix} civil (heure dorée)"
			self.textcolor="Black"
			self.backcolor="Orange"
		elif elevation<-4.0 and elevation>=-6.0:	
			self.name=f"{prefix} ivil (Heure bleue)"
			self.textcolor="Black"
			self.backcolor="SteelBlue"
		elif elevation<-6.0 and elevation>=-12.0:
			self.name=f"{prefix} nautique"
			self.textcolor="White"
			self.backcolor="RoyalBlue"
		elif elevation<-12.0 and elevation>=-18.0:
			self.name=f"{prefix} astronomique"
			self.textcolor="White"
			self.backcolor="DarkBlue"
		else:												
			self.name="Nuit"
			self.textcolor="White"
			self.backcolor="MidnightBlue"
	
	def getName(self):
		return(self.name)

	def getColors(self):
		return(self.textcolor,self.backcolor)

class SolarDiagram():
	"""
		Calcul et rendu du diagramme solaire pour une latitude
		adapté du script de David Alberto
		source : https://www.astrolabe-science.fr/diagramme-solaire-azimut-hauteur/
		Utilise la librairie matplotlib.pyplot
	"""
	def __init__(self, title, latitude):
		self.title=title
		self.phi_degrees=latitude
		self.phi_radians=np.radians(latitude)
	
	def calc(self,target_date=None):
		"""	target_date doit être défini avec tzinfo (not naive)
		"""
		if target_date==None :	# si pas de datetime alors prendre l'instant présent (now)
			print("SolarDiagram targetdate is not defined : back to now in UTC")
			target_date=datetime.now(ZoneInfo('UTC'))
		else:
			if target_date.tzinfo==None:
				print("SolarDiagram targetdate has no timezone : back to UTC")
			else:
				target_date=target_date.astimezone(ZoneInfo('Europe/Paris'))
		dt=datetime.utcoffset(target_date)
		dhours=dt.seconds/3600
		if _debug:
			print("TimeZone décalage : {dhours:%.1f} heure(s)")
			
		# Paramètres à personnaliser
		plt.rcParams["font.family"]=default_font
		plt.rcParams["font.size"]=default_fontsize
		lat_str=str(self.phi_degrees)
		
		# min/max pour définir la taille du graphique
		hauteurmax=90+maxDeclinaison-self.phi_degrees	# hauteur méridienne au 21 juin, pour l'échelle de hauteur
		maxH=np.degrees(math.acos(-math.tan(self.phi_radians)*math.tan(np.radians(maxDeclinaison))))	# angle horaire maxi au 21 juin, pour les heures de lever/coucher
		maxH=int(maxH/15)*15
		maxAz=np.degrees(math.acos(-math.sin(np.radians(maxDeclinaison)/math.cos(self.phi_radians))))	# azimut maximal au lever/coucher (axe X)
		maxAz=int((maxAz/20)+1)*20
		
		# vectorisation des fonctions hauteur et azimut, pour qu'elles puissent être appliquées à une liste de valeurs
		liste_hauteur=np.vectorize(self.calcul_hauteur)
		liste_azimut=np.vectorize(self.calcul_azimut)
		
		# paramètres et axes du graphique
		fig=plt.figure(figsize=(diagram_width,diagram_height), tight_layout=True)
		ax=plt.subplot()
		plt.xticks(np.arange(-150, 200, 50))	# graduations chiffrées en azimut
		plt.xlim(-maxAz, +maxAz)	# fixer les min/max
		plt.title("Diagramme solaire azimut / hauteur")
		plt.text(0.005, 0.993, f"{self.title} : {self.phi_degrees:.1f}°", color=color_coordinates, va='top', fontsize=9, transform=ax.transAxes, bbox=dict(facecolor='white', edgecolor='black'))
		plt.ylim(0, int(hauteurmax+5))
		plt.xlabel("Azimut (°)")
		plt.ylabel("Hauteur (°)")
		
		# échelle X des points cardinaux (azimuts)
		cardinaux={'N-E':-135,'E':-90,'S-E':-45,'S-O':+45,'O':+90,'N-O':+135}
		for direction in cardinaux:
			plt.text(cardinaux[direction], -3.5, direction, va='top', ha='center', rotation=90)
			
		# Tracé de la grille azimut (axe X)
		minor_xticks = np.arange(-maxAz, maxAz, 10)	# espaces de la grille
		ax.set_xticks(minor_xticks, minor=True)
		minor_yticks = np.arange(0, int(hauteurmax+5), 5)	# espaces de la grille
		ax.set_yticks(minor_yticks, minor=True)
		ax.grid(which='minor', alpha=0.5)
		plt.grid()
		
		# Tracé des lignes horaires et des heures sur le diagramme (axe Y)
		decl=np.arange(-maxDeclinaison, +maxDeclinaison, 0.05)
		for H in np.arange(-maxH, maxH+7.5, 7.5):
			if H.is_integer()==False:	# demi-heures
				props=dict(color=color_halfhours, alpha=0.5, lw=1)	# ligne fine et grise
			else :	# heures pleines
				props=dict(color=color_hours, alpha=1.0, lw=1)	# ligne fine, en couleur
			X=liste_azimut(decl,H)
			Y=liste_hauteur(decl,H)
			plt.plot(X,Y, **props)
			if H.is_integer():
				if H==0.0 :	# chiffres des heures
					prop_chiffres=dict(ha='center')
					X=1.01*max(X)
				elif H>0.0 :	# chiffres des heures
					prop_chiffres=dict(ha='left')
					X=1.01*max(X)
				elif H<0.0 :
					prop_chiffres=dict(ha='right')
					X=1.01*min(X)
				hour=(H/15)+12+dhours
				plt.text(X, 1.01*max(Y), '%ih' % hour, fontweight='normal',**prop_chiffres)
				
		# courbes de déclinaison (solstices, équinoxes et aujourd'hui avec le décalage optionnel)
		couleursdecl=[color_decl_solstice_winter, color_decl_equinox, color_decl_solstice_summer,color_decl_current]
		datesdecl=["Solstice d'hiver","Équinoxes","Solstice d'été","Aujourd'hui (+décalage)"]
		widthdecl=[1,1,1,2]
		s=SolarPosition(target_date)
		declinaison=s.getDeclinaison()
		H = np.arange(-maxH-15, maxH+15, 1.0)	# liste des angles horaires
		for i, D in enumerate([-maxDeclinaison, 0.0, +maxDeclinaison, declinaison]):
			X=liste_azimut(D,H)
			Y=liste_hauteur(D,H)
			plt.plot(X, Y, color=couleursdecl[i], label=datesdecl[i], lw=widthdecl[i])
			
		# ajout de la position solaire (cercle jaune) pour l'heure de target_date en UTC
		# convertir en heure décimale
		hd=target_date.hour+target_date.minute/60.0+target_date.second/3600.0-dhours
		if _debug:
			print("date :",target_date)
			print("hour (local):",hd)
		h=(hd-12.0)*15.0	# (heure décimale-12 UTC) * 15
		x=self.calcul_azimut(declinaison,h)
		y=self.calcul_hauteur(declinaison,h)
		plt.plot(x,y,color=color_sun,marker='o',markersize=diagram_sun_halo,alpha=0.75)
		plt.plot(x,y,color=color_sun_halo,marker='o',markersize=diagram_sun_disk,alpha=1.0)
		
		# enregistre le diagramme final (image PNG)
		plt.legend()
		path=os.path.join(".",default_directory)	# chemin pour la sauvegarde des résultats (images et html)
		url=os.path.join(path,default_diagsol_file)
		fig.savefig(url, dpi=72)
	
	def calcul_hauteur(self,D,H):
		# renvoie la hauteur du Soleil (degré), d'après la déclinaison D et l'angle horaire H
		return np.degrees(math.asin(math.sin(np.radians(D))*math.sin(self.phi_radians)+math.cos(np.radians(D))*math.cos(self.phi_radians)*math.cos(np.radians(H))))
	
	def calcul_azimut(self,D, H) :
		# renvoie l'azimut corrigé (degré), d'après la déclinaison D et l'angle horaire H
		Az=np.degrees(math.atan(math.sin(np.radians(H))/(math.sin(self.phi_radians)*math.cos(np.radians(H))-math.cos(self.phi_radians)*math.tan(np.radians(D)))))
		if Az<0 and H>0:
			Az=Az+180
		elif Az>0 and H<0:
			Az=Az-180
		return Az
	
class Ephemeris():
	""" Classe Ephemeris, principe général :
		__init__ :initialise l'objet avec un lieu
		calc : calcul les éphémérides du lieu pour la date donnée
	"""
	def __init__(self, name, region, latitude, longitude, tzname, elevation):
		"""
		Prepare l'objet Ephemeris en l'initialisant avec une localisation sur terre
			name :		nom de la position (ville)
			country :	nom du pays ou de la région
			latitude :	latitude du lieu (en degré)
			longitude :	longitude du lieu (en degré)
			time-zone :	nom de la zone horaire (suivant des dénominations standard : {Région}/{Ville}, voir https://utctime.info/timezone/)
			elevation :	hauteur du lieu (en mètres)
		"""
		self.location=astral.LocationInfo()
		self.location.name=name
		self.location.region=region
		self.location.latitude=latitude
		self.location.longitude=longitude
		self.location.timezone=tzname
		self.elevation=elevation
		self.solar_depression=6
		self.dawn=None
		self.sunrise=None
		self.solar_moon=None
		self.solar_elevation=None
		self.sunset=None
		self.dusk=None
		self.daylight=None
		self.night=None
		
	def calc(self,target_date=None):
		""" Calcule les données pour le lieu (location) et le moment (target_date), via la bibliothèque 'astral'
				target_date : date/heure du calcul (si None = date/heure temps réel), Aware mode (timezone))
				dawn : aube (soleil de 6 à 0 degrés sous l'horizon, le matin)
				sunrise : lever du soleil (quand le soleil est à 0.833 degrés sous l'horizon, le matin)
				noon : midi solaire (quand le soleil est le plus haut dans le ciel)
				solar_elevation : elevation solaire (degrés)
				solar_elevation-noon : élevation solaire à midi (degrés)
				sunset : coucher du soleil (quand le soleil est à 0.833 degrés sous l'horizon, le matin)
				dusk : crépuscule (soleil entre 0 et 6 degrés sous l'horizon, le soir)
				moon_phase : phase de lune entier : [0..28[
				daylength : durée du jour (entre le lever et le coucher du soleil)
				nightlength : durée de la nuit (entre le coucher et le lever du soleil)
		"""
		if target_date==None :	# si pas de datetime alors prendre l'instant présent (now)
			print("Ephemeris targetdate is not defined : back to now in UTC")
			target_date=datetime.now(ZoneInfo('UTC'))
		else:
			if target_date.tzinfo==None:
				print("Ephemeris targetdate has no timezone : back to UTC")
				target_date=target_date.astimezone(ZoneInfo('Europe/Paris'))
		self.target_date=target_date
		
		# calcul données du soleil (sun)
		sun=astral.sun.sun(self.location.observer,date=target_date,tzinfo=self.location.timezone,dawn_dusk_depression=self.solar_depression)
		self.sun_dawn=sun['dawn']
		self.sun_rise=sun['sunrise']
		self.sun_noon=sun['noon']
		self.sun_set=sun['sunset']
		self.sun_dusk=sun['dusk']
		self.solar_elevation=astral.sun.elevation(self.location.observer,dateandtime=target_date)
		self.solar_elevation_noon=astral.sun.elevation(self.location.observer,dateandtime=self.sun_noon)
		
		# calcule données de la Lune (moon)
		try:
			self.moon_rise=astral.moon.moonrise(self.location.observer,date=target_date,tzinfo=self.location.timezone)
			self.moon_set=astral.moon.moonset(self.location.observer,date=target_date,tzinfo=self.location.timezone)
			self.moon_phase=astral.moon.phase(date=target_date)
			phase=MoonPhase(self.moon_phase)
			self.moon_phase_name=phase.getName()
			self.moon_phase_pict=phase.getPicture()
			self.moon_emoji=phase.getEmoticon()
		except ValueError:
			print(">>> Erreur : Pas de lever de lune à cet endroit.")
			self.moon_phase=None
			self.moon_rise=None
			self.moon_set=None
			self.moon_phase_name=None
			self.moon_phase_pict=None
			self.moon_emoji=None
			
		# calcul des durées à partir des horaires de base
		daylight=astral.sun.daylight(self.location.observer,date=target_date,tzinfo=self.location.timezone)
		self.daylength=daylight[1]-daylight[0]
		night=astral.sun.night(self.location.observer,date=target_date,tzinfo=self.location.timezone)
		self.nightlength=night[1]-night[0]
		
		# calcul de la veille pour déterminer la variation de durée du jour
		target_date_previous=target_date+timedelta(days=-1)
		daylight=astral.sun.daylight(self.location.observer,date=target_date_previous,tzinfo=self.location.timezone)
		daylength=daylight[1]-daylight[0]
		variation=self.daylength-daylength
		self.day_increase_minutes=variation.total_seconds()/60.0
	
	def __str__(self):
		if self.location==None:
			r="location non definie"
		elif self.target_date==None:
			r="date non définie (fonction Ephemeris.calc)"
		else:
			sun=SunPhase(self.solar_elevation,self.target_date)
			colorname=sun.getName()
			r=f"Éphéméride {self.location.name} ({self.location.region}) pour {self.target_date:%d/%m/%Y @ %H:%M}"
			r=r+f"\n\tÉlévation        : {self.solar_elevation:.1f}° ({colorname})"
			r=r+f"\n\tJour:Aube        : {self.sun_dawn:%H:%M}"
			r=r+f"\n\tJour:Lever       : {self.sun_rise:%H:%M}"
			r=r+f"\n\tJour:Culmination : {self.sun_noon:%H:%M} (hauteur : {self.solar_elevation_noon:.1f}°)"
			r=r+f"\n\tJour:Coucher     : {self.sun_set:%H:%M}"
			r=r+f"\n\tJour:Crépuscule  : {self.sun_dusk:%H:%M}"
			dl=fmtTimeDelta2HM(self.daylength)
			r=r+f"\n\tJour:Durée       : {dl} ({self.day_increase_minutes:+.1f} minute(s))"
			nl=fmtTimeDelta2HM(self.nightlength)
			r=r+f"\n\tNuit:Durée       : {nl}"
			if self.moon_phase :
				r=r+f"\n\tLune:Phase       : {self.moon_phase_name} ({self.moon_phase:.1f}/28) [{self.moon_emoji}]"
				r=r+f"\n\tLune:Lever       : {self.moon_set:%H:%M}"
				r=r+f"\n\tLune:Coucher     : {self.moon_rise:%H:%M}"		
			else:
				r=r+"\n\tLune:Phase       : Pas de lune visible cette nuit"
		return(r)
	
	def toHTML(self,diagram=None):
		""" toHTML
			Create and save to disk, a HTML5 object with results
		"""
		default_css="""
			body { background-color: lightgrey; }
			.clearfix { overflow: auto; }
			#diag { float: right; padding: 5px; margin: auto;}
			"""
		# création de l'entête
		html=ET.Element('html')
		head=ET.SubElement(html,'header')
		meta=ET.SubElement(head,'meta',attrib={'charset':'utf-8'})
		meta.text=""
		title=ET.SubElement(head,'title')
		title.text=f"{__appname__}"
		style=ET.SubElement(head,'style')
		style.text=default_css
		
		# création du corps, de la structure de base et ajout flottant de l'image du diagramme solaire
		body=ET.SubElement(html,'body')
		div=ET.SubElement(body,'div',attrib={'id':'diag'})
		img=ET.SubElement(div,'img',attrib={'src':f"{default_diagsol_file}"})
		div=ET.SubElement(body,'div',attrib={'id':'tab'})
		h=ET.SubElement(div,'h1')
		h.text=f"{__appname__}"
		h=ET.SubElement(div,'h2')
		h.text=f"Localisation : {self.location.name} ({self.location.region})"
		h=ET.SubElement(div,'h3')
		h.text=f"Date : {self.target_date:%d/%m/%Y @ %H:%M}"
		
		# création du tableau de données
		table=ET.SubElement(div,'table')
		# ligne 1 : Hauteur solaire
		sun=SunPhase(self.solar_elevation,self.target_date)
		colorname=sun.getName()
		(textcolor,backcolor)=sun.getColors()
		line=ET.SubElement(table,'tr')
		cell=ET.SubElement(line,'td')
		cell.text=f"Hauteur du soleil"
		cell=ET.SubElement(line,'td',attrib={'style':f'color: {textcolor}; background-color: {backcolor};'})
		cell.text=f"{self.solar_elevation:.1f}° ({colorname})"
		# ligne 2 : Aube
		line=ET.SubElement(table,'tr')
		cell=ET.SubElement(line,'td')
		cell.text=f"Aube"
		cell=ET.SubElement(line,'td')
		cell.text=f"{self.sun_dawn:%H:%M}"
		# ligne 3 : Lever du soleil
		line=ET.SubElement(table,'tr')
		cell=ET.SubElement(line,'td')
		cell.text=f"Lever du soleil"
		cell=ET.SubElement(line,'td')
		cell.text=f"{self.sun_rise:%H:%M}"
		# ligne 4 : Zénith solaire
		line=ET.SubElement(table,'tr')
		cell=ET.SubElement(line,'td')
		cell.text=f"Culmination (Zenith solaire)"
		cell=ET.SubElement(line,'td')
		cell.text=f"{self.sun_noon:%H:%M}"
		# ligne 5 : Coucher du soleil
		line=ET.SubElement(table,'tr')
		cell=ET.SubElement(line,'td')
		cell.text=f"Coucher du soleil"
		cell=ET.SubElement(line,'td')
		cell.text=f"{self.sun_set:%H:%M}"
		# ligne 6 : Crépuscule
		line=ET.SubElement(table,'tr')
		cell=ET.SubElement(line,'td')
		cell.text=f"Crépuscule"
		cell=ET.SubElement(line,'td')
		cell.text=f"{self.sun_dusk:%H:%M}"
		# ligne 7 : Durée du jour
		line=ET.SubElement(table,'tr')
		cell=ET.SubElement(line,'td')
		cell.text=f"Durée du jour"
		cell=ET.SubElement(line,'td')
		dl=fmtTimeDelta2HM(self.daylength)
		cell.text=f"{dl} {self.day_increase_minutes:+.1f} minute(s)"
		# ligne 8 : Durée de la nuit
		line=ET.SubElement(table,'tr')
		cell=ET.SubElement(line,'td')
		cell.text=f"Durée de la nuit"
		cell=ET.SubElement(line,'td')
		nl=fmtTimeDelta2HM(self.nightlength)
		cell.text=f"{nl}"
		# ligne 9, 10 et 11 : Phase lunaire et heure lever/coucher
		line=ET.SubElement(table,'tr')
		cell=ET.SubElement(line,'td')
		cell.text=f"Phase de la lune"
		cell=ET.SubElement(line,'td')
		if self.moon_phase:
			cell.text=f"{self.moon_phase_name} ({self.moon_phase:.1f}/28) [{self.moon_emoji}]"
			# img=ET.SubElement(cell,'img',attrib={'src':f"{self.moon_phase_pict}",'width':'30','height':'30'})
			line=ET.SubElement(table,'tr')
			cell=ET.SubElement(line,'td')
			cell.text=f"Lever de la lune"
			cell=ET.SubElement(line,'td')	
			cell.text=f"{self.moon_set:%H:%M}"
			# ligne 11 : Coucher de lune
			line=ET.SubElement(table,'tr')
			cell=ET.SubElement(line,'td')
			cell.text=f"Coucher de la lune"	
			cell=ET.SubElement(line,'td')
			cell.text=f"{self.moon_rise:%H:%M}"
		else:
			cell.text="Pas de lune visible cette nuit"

		# Finalisation et enregistrement du fichier HTML complet
		path=os.path.join(".",default_directory)	# chemin pour la sauvegarde des résultats (images et html)
		url=os.path.join(path,default_html_file)
		with open(url, 'w') as f:
			f.write("<!DOCTYPE html>\n")	# ajout du doctype en première ligne
			ET.ElementTree(html).write(f, encoding='unicode',method='html')
		webbrowser.open(url,autoraise=True)

class SolarPosition():
	""" Calcul des coordonnées équatoriales solaire, celle-ci dépend d'une date
		Référence : https://fr.wikipedia.org/wiki/Syst%C3%A8me_de_coordonn%C3%A9es_%C3%A9quatoriales
		Coordonnées indépendantes de la position de l'observateur est composé de 2 angles :
			Ascension droite
			Déclinaison
		Ces coordonnées sont repérés dans la plan équatoriale (le plan qui passe par l'équateur de la Terre
		soit l'équivalent céleste des latitude et longitude terrestre projetées.
	"""
	def __init__(self,date=None,tzname="Europe/Paris"):
		self.tzname=tzname
		if date==None:
			self.date=datetime.datetime.now(tz=ZoneInfo(tzname))
		else:
			self.date=date
	
	def getDeclinaison(self):
		# numéro du jour de l'année
		dt0 = datetime(self.date.year, 1, 1,tzinfo=ZoneInfo(self.tzname))
		dd=self.date-dt0
		j=dd.days
		# déclinaison solaire pour j
		declinaison=maxDeclinaison*math.sin(2.0*math.pi*(j+284.0)/365.0)
		return declinaison

class JulianDay():
	"""	Le jour julien est un système de datation consistant à compter le nombre de jours et fraction de jour écoulés
		depuis une date conventionnelle fixée au 1er janvier de l'an 4713 av. J.-C. (= -4712) à 12 heures temps universel.
		Permet de simplifier les calculs des dates puisque indépendant des dates calendaires.
		Ici est implanté l'algorythme issut du livre :
			"Calculs astronomiques à l'usage des amateurs" de Jean MEEUS (1986,Société Astronomique)
		En savoir plus : <https://fr.wikipedia.org/wiki/Jour_julien>
	"""
	def __init__(self,JJ=0):
		""" initialise objet JulianDay avec un jour Julien """
		self.setJulianDay(JJ)
	
	def setJulianDay(self,JJ):
		""" calcul de conversion Jour Julien vers jour calendaire """
		self.JJ=JJ
		JJ=JJ+0.5
		Z=math.trunc(JJ)	# partie entière
		F=JJ-Z				# partie décimale
		if Z<2299161:
			A=Z
		else:
			a=math.trunc((Z-1867216.25)/36524.25)
			A=Z+1+a-math.trunc(a/4)
		B=A+1524
		C=math.trunc((B-122.1)/365.25)
		D=math.trunc(365.25*C)
		E=math.trunc((B-D)/30.6001)
		# calcul date
		self.decimalDay=B-D-math.trunc(30.6001*E)+F
		self.day=math.trunc(self.decimalDay)
		if E<13.5:
			self.month=E-1
		else:
			self.month=E-13
		if self.month>2.5:
			self.year=C-4716
		else:
			self.year=C-4715
		# calcul horaire
		dh=24.0*(self.decimalDay-self.day)
		self.hour=int(dh)
		self.minute=int(60*(dh-self.hour))
		self.second=int(((dh-self.hour)*60-self.minute)*60)
	
	def setDate(self,date):
		""" Affecte l'objet JulianDay avec une date calendaire (datetime) et calcul le jour julien correspondant """
		# cas des dates du calendrier grégorien
		if date.year<1582:	# calendrier Julien
			B=0
		else:	# calendrier Grégorien
			A=math.trunc(date.year/100)
			B=2-A+math.trunc(A/4)
		# 
		if date.month>2:
			y=date.year
			m=date.month
		else:
			y=date.year-1
			m=date.month+12
		JJ=1720994.5+math.trunc(365.25*y)+math.trunc(30.6001*(m+1))+date.day+B
		# converti l'horaire en jour décimal
		dd=(date.hour+(date.minute/60.0)+(date.second/3600.0))/24.0
		self.setJulianDay(JJ+dd)
	
	def getDate(self):
		""" retourne la date calendaire (datetime) du Jour julien """
		d=datetime.datetime(year=self.year,month=self.month,day=self.day,hour=self.hour,minute=self.minute,second=self.second)
		return(d)
	
	def getT(self):
		"""	
			J2000.0 : référence au jour Julien du 1/01/2000 à midi
			Aussi nommé "Epoque standard depuis 1984
			En savoir plus : https://fr.wikipedia.org/wiki/J2000.0
		"""
		return((self.JJ-2415020.0)/36525)
	
	def __str__(self):
		""" affiche le jour julien lisible (sous forme calendaire) """
		d=self.getDate()
		return(f"Julien={self.JJ} : {d}")

# -- Fonctions -----------------------------------------------------------------------

def fmtTimeDelta2HM(tdelta):
	seconds=tdelta.total_seconds()
	hours,seconds=divmod(seconds,3600)
	minutes,seconds=divmod(seconds,60)
	return f"{int(hours)}:{int(minutes):02}:{int(seconds):02}"
	
# Aide CLI : lettre-code : {nom-long, type de valeur, valeur par défaut, aide}
arguments={	'h':("help",None,None,"aide"),
			'd':("day","<int>",default_shift,"Décalage (en jours) par rapport à aujourd'hui"),
			's':("sol",None,default_solar,"Affiche le diagramme solaire annuel dans une fenêtre séparée"),
			'w':("",None,default_window,"Affiche le HTML crée"),
			'x':("debug",None,_debug,"Active le mode debug"),
		}

def show_usage():
	print("--------------------------------------------")
	print(f"{__appname__} {__version__}, {__file__}")
	print(f"  {__copyright__}")
	print(f"  Licence : {__license__}")
	print("Calcul l'éphéméride à une date.")
	print("--------------------------------------------")
	print("options :")
	for a in arguments:
		(arg,attrb,default,help)=arguments[a]
		if attrb:
			arg+=f":{attrb}"
		if default:
			help+=" (défaut={default})"
		print("  -{a} (--{arg})\t{help}")
	print("--------------------------------------------")
	print()

# -- Démarrage --------------------------------------------------------------------------------

def main(argv):
	global _debug,default_solar,default_window
	
	print(f"-- {__appname__} {__version__} -----------------")
	# 2. charger les paramètres de la CLI (command line interface)
	shortList=""	# chaine avec les arguments courts (1 lettre, suivi de : si valeur a passer)
	longList=[]		# les des noms d'arguments long (suivi de = si valeur à passer)
	for a in arguments:
		(arg,attrb,default,help)=arguments[a]
		if attrb:
			a+=':'
			arg+='='
		shortList+=a
		longList.append(arg)
	shiftday=0
	solarDiag=False
	if _debug:
		print("arguments",argv)
		print("shortList",shortList)
		print("longList",longList)
	try: 
		opts,args=getopt.getopt(argv,shortList,longList)
	except Exception as ex:
		print("error get.opt",ex)
		sys.exit(2)
	for opt,arg in opts:	# parcourir les arguments pour mettre à jour la configuration par défaut
		opt=opt.replace('-','')
		if _debug: print(opt,":",arg)
		option=None
		for a in arguments:
			(ida,attrb,default,help)=arguments[a]
			if opt in (a,ida):
				option=a
		if option=='h':
			show_usage()
			exit()
		elif option=='d':
			if _debug: print("shift",arg)
			shiftday=int(arg)
		elif option=='s':
			default_solar=not(default_solar)
		elif option=='w':
			default_window=not(default_window)
		elif option=='x':
			_debug=not(_debug)
		else:
			print("ERREUR : paramètre",opt,"non géré")

	# 3. Paramètres du lieu et moment d'observation (charger config)
	config=Config()
	if _verbose:
		print(f"Observateur :     {config.location} ({config.region}) / timezone = {config.tz}")
		print(f"                  lat : {config.latitude:.4f}°, lon = {config.longitude:.4f}°, ele = {config.elevation:.1f} m")
	
	# date du calcul (aujourd'hui + décalage, en heure locale)
	dt_local=datetime.now(tz=ZoneInfo(config.tz))
	targetDate=dt_local+timedelta(days=shiftday)
	if _verbose:
		print(f"Date :            {targetDate:%d/%m/%Y @ %H:%M}")
	if _debug:
		print("aujourd'hui",date_local)
		print("offset",shiftday)
		print("target",targetDate)

	# 4. Calcul jour julien
	jj=JulianDay()
	jj.setDate(targetDate)
	if _verbose:
		print(f"Jour Julien :     {jj.JJ:.2f} TT")
		print(f"Epoque standard : {jj.getT():.6f} J2000.0")

	# 5. Calcul position solaire
	# déclinaison solaire
	s=SolarPosition(targetDate)
	sunDeclinaison=s.getDeclinaison()
	if _verbose:
		print(f"Déclinaison :     {sunDeclinaison:.2f}°")
	# diagramme solaire
	sd=SolarDiagram(f"{config.location} ({config.region})",config.latitude)
	sd.calc(targetDate)
	if default_solar: plt.show()

	# 6. Calcul éphéméride
	e=Ephemeris(config.location, config.region, config.latitude, config.longitude, config.tz, config.elevation)
	e.calc(targetDate)
	if _verbose: 
		print(e)
	if default_window: 
		e.toHTML()

if __name__ == '__main__' :
	main(sys.argv[1:])


