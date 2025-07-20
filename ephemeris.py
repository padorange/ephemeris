#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__application__="ephemeris.py"
__appname__="Éphémérides"
__version__="0.4"
__author__="Pierre-Alain Dorange"
__copyright__=f"Copyright juillet 2025, {__author__}"
__license__="BSD-3-Clauses"			# voir https://en.wikipedia.org/wiki/BSD_licenses
__contact__="pdorange@mac.com"

"""
	Ephemeris
	-----------------------------------------------------------------------------------------
	Script Python 3.11, testé sur Debian 12 (bookworm)
	-----------------------------------------------------------------------------------------
	Permet de calculer les données astronomique de lever et coucher du soleil par rapport à un point sur terre
	grace à la bibliothéque Astral, inclus dans certaines distribution.
	Debian inclus la version Astral 1.6.1, un peu ancienne, mais c'est l'API utilisé par ce script (défaut de Python 3.11 pour Debian).
	-- Modules spécifiques à installer (licences : voir readme.md) ---------------------------
		MatPlotLib 3.3.x (https://matplotlib.org/)
			permet de réaliser de jolis graphiques
	-- Notions Astronomiques -----------------------------------------------------------------
		Coordonnées équatoriales (indépendant de l'observateur)
		Equinoxe : instant ou le soleil traverse le plan équatoral terreste (durée jour = durée nuit)
					équinoxe de printemps et équinoxe d'hiver
					référence : https://fr.wikipedia.org/wiki/%C3%89quinoxe
		Solstice : instant ou la position apparente solaire atteint sa plus grande inclinaison vers le Nord ou le Sud
					solstice d'hiver : jour le plus court (nuit la plus longue)
					solstice d'été : jour le plus long (nuit la plus courte)
					référence : https://fr.wikipedia.org/wiki/Solstice
	-- Paramètres CLI ------------------------------------------------------------------------
		-h : aide
		-dX : ajout X jours à la date actuelle
		-s : afficher l'image du diagramme solaire
		-w : affiche le HTML crée avec le navigateur
		-x : mode debug
	-----------------------------------------------------------------------------------------
	0.1 : janvier-février 2025 : première version
	0.2 : février-mars 2025 : résultat sous forme HTML5 + option CLI "-d"
	0.3 : mars-avril 2025 : intégration diagramme solaire en azimuth et hauteur + position solaire selon target_date + paramètre "-s"
	0.4 : juillet 2025 : debug calcul variation durée jour + ajout option CLI "-x", "-s" et "-w" + optimisation du code
	
	-- todo --------------------------------------------------------------------------
	ajouter la lecture d'un fichier de config pour les paramètres locaux
"""

# -- Bibliothèques  ---------------------------------------------------------------
# Bibliothèques par défaut de Python
import sys,getopt,os
import datetime, pytz					# gestion date et temps + timezone
import configparser						# gestion fichier.INI (paramètres et configuration)
import codecs
import math,numpy as np					# calculs scientifique
import astral							# Astral 1.6.1 (default version include in Debian 12
from xml.etree import ElementTree as ET	# gestion elementtree pour créer le résultat HTML
import webbrowser						# module pour ouvrir une URL dans le navigateur par défaut
# Bibliothèques supplémentaires à installer
import matplotlib.pyplot as plt			# matplot lib

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
default_font="Roboto Condensed"
default_fontsize=8
color_sun="gold"
color_hours='royalblue'
color_halfhours='gray'

# définit le répertoire par défaut comme celui du source (gestion du lancement hors dossier source)
path=os.path.dirname(os.path.abspath(__file__))
os.chdir(path)

# -- Classes -----------------------------------------------------------------------

class Config():
	"""	objet Config pour regrouper les paramètres utilisés, stockés dans le fichier INI de configuration
		certaines valeurs par défaut (__init__) sont surchargées par la lecture du fichier de configration (load)
		voir default.ini
	"""

	def __init__(self, filename=default_config):
		# chargement des paramètre depuis le fichier de configuration (hubeau.ini)
		# avec valeurs par défaut si erreur de chargement ou valeur non définie
		#	Paris, France
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
				self.longitude==float(config.get('observer','longitude'))
			except Exception as ex:
				print("error:",ex)
			try:
				self.elevation=float(config.get('observer','elevation'))
			except Exception as ex:
				print("error:",ex)
			try:
				self.tz=config.get('observer','tz',fallback=None)
			except Exception as ex:
				print("error:",ex)
		except Exception as ex:
			print("ERREUR : fichier de configuration introuvable:",default_config)
			print("error :",ex)
		if _debug: 
			print(self)
		return
	
	def __str__(self):
		value=f"Observateur : {self.location} ({self.region}) / tz = {self.tz}"
		value+=f"\n\tlat : {self.latitude:.4f}°, lon = {self.longitude:.4f}°, ele = {self.elevation:.1f} m"
		return value

class MoonPhase():
	""" Gère les phases de la lune comme des désignation et des images d'illustration
		converti la phase lunaire (entier entre 0 et 28) en une dénomination et une image
		Phases de la lune (ref : https://fr.wikipedia.org/wiki/Phase_de_la_Lune)
		Images référence : https://starwalk.space/fr/moon-calendar
		Les images doivent être dans le sous-dossier : ./html/phases
		Cycle : 29.5 jours
	"""
	def __init__(self, phase):
		self.phase=phase
		self.prefix="./phases/lune_"
	
	def getName(self):
		if self.phase<2 or self.phase>=28: 	name="Nouvelle Lune"
		elif self.phase<6:					name="Premier croissant"
		elif self.phase<9:					name="Premier quartier"
		elif self.phase<14:					name="Lune Gibeuse croissante"
		elif self.phase<17:					name="Pleine Lune"
		elif self.phase<22:					name="Lune Gibeuse décroissante"
		elif self.phase<25:					name="Dernier quartier"
		elif self.phase<28:					name="Dernier croissant"
		else:								name=f"Erreur phase non géré : {self.phase}"
		return name

	def getPicture(self):
		if self.phase<2 or self.phase>=28:	image="00.png"
		elif self.phase<6:					image="01.png"
		elif self.phase<9:					image="02.png"
		elif self.phase<14:					image="03.png"
		elif self.phase<17:					image="04.png"
		elif self.phase<22:					image="05.png"
		elif self.phase<25:					image="06.png"
		elif self.phase<28:					image="07.png"
		else:								image="error.png"
		pictureName=self.prefix+image
		return pictureName

class SunPhase():
	""" Gère les dénomnations et couleurs du ciel suivant son élévation dans le ciel (degrés décimaux)
		Les dénominations proviennent de Wikipédia :
			https://fr.wikipedia.org/wiki/Couleur_du_ciel
			https://fr.wikipedia.org/wiki/Heure_dorée
			https://fr.wikipedia.org/wiki/Heure_bleue
		Les couleurs sont des dénominations de la norme X11, utilisés par SVG, CSS et HTML :
			https://htmlcolorcodes.com/fr/noms-de-couleur/
	"""
	def __init__(self,elevation):
		self.elevation=elevation
	
	def getName(self):
		if self.elevation<-4.0 and self.elevation>-6.0:		color_name="Heure bleue"
		elif self.elevation<6.0 and self.elevation>-4.0:	color_name="Heure dorée"
		elif self.elevation>6.0 :							color_name="Jour"
		else:												color_name="Nuit"
		return(color_name)

	def getColor(self):
		if self.elevation<-4.0 and self.elevation>-6.0:		color_html="SteelBlue"
		elif self.elevation<6.0 and self.elevation>-4.0:	color_html="Orange"
		elif self.elevation>6.0 :							color_html="SkyBlue"
		else:												color_html="CornflowerBlue"
		return(color_html)

class SolarDiagram():
	"""
		Calcul et rendu du diagramme solaire pour une latitude
		adapté du script de David Alberto
		source : https://www.astrolabe-science.fr/diagramme-solaire-azimut-hauteur/
		Utilise la librairie matplotlib.pyplot
	"""
	def __init__(self, latitude, timezone):
		self.phi_degrees=latitude
		self.phi_radians=np.radians(latitude)
	
	def calc(self,target_date=None,tz_identifier="Europe/Paris"):
		if target_date==None :	# si pas de datetime alors prendre l'instant présent (now)
			self.target_date=datetime.datetime.now()
		else:
			self.target_date=target_date
		# Paramètres à personnaliser
		plt.rcParams["font.family"]=default_font
		plt.rcParams["font.size"]=default_fontsize
		lat_str=str(self.phi_degrees)
		# min/max pour définir la taille du graphique
		hauteurmax=90+maxDeclinaison-self.phi_degrees	# hauteur méridienne au 21 juin, pour l'échelle de hauteur
		maxH=np.degrees(math.acos(-math.tan(self.phi_radians)*math.tan(np.radians(maxDeclinaison))))	# angle horaire maxi au 21 juin, pour les heures de lever/coucher
		maxH=int(maxH/15)*15
		maxAz=np.degrees(math.acos(-math.sin(np.radians(maxDeclinaison)/math.cos(self.phi_radians))))	# azimut maximal au lever/coucher, pour l'axe x
		maxAz=int(maxAz/20+1)*20
		# vectorisation des fonctions hauteur et azimut, pour qu'elles puissent être appliquées à une liste de valeurs
		liste_hauteur=np.vectorize(self.calcul_hauteur)
		liste_azimut=np.vectorize(self.calcul_azimut)
		# paramètres et axes du graphique
		fig=plt.figure(figsize=(5.0,5.0), tight_layout=True)	# taille en inch (2.54 cm)
		ax=plt.subplot()
		plt.xticks(np.arange(-150, 200, 50))	# graduations chiffrées en azimut
		plt.xlim(-maxAz, +maxAz)	# fixer les min/max
		plt.title("Diagramme solaire azimut / hauteur")
		plt.text(0.005, 0.993, f"Latitude {self.phi_degrees:.1f}°", color='red', va='top', fontsize=9, transform=ax.transAxes, bbox=dict(facecolor='white', edgecolor='black'))
		plt.ylim(0, int(hauteurmax+5))
		plt.xlabel("Azimut (°)")
		plt.ylabel("Hauteur (°)")
		# points cardinaux (azimuts)
		cardinaux={'N-E':-135,'Est': -90,'S-E': -45,'S-O': +45,'Ouest': +90,'N-O': +135}
		for direction in cardinaux:
			plt.text(cardinaux[direction], -2.5, direction, va='top', ha='center', rotation=90)
		# Tracé de la grille azimut (axe X)
		minor_xticks = np.arange(-maxAz, maxAz, 10)	# espaces de la grille
		ax.set_xticks(minor_xticks, minor=True)
		minor_yticks = np.arange(0, int(hauteurmax+5), 5)	# espaces de la grille
		ax.set_yticks(minor_yticks, minor=True)
		ax.grid(which='minor', alpha=0.5)
		plt.grid()
		# Tracé des lignes horaires (axe Y)
		decl=np.arange(-maxDeclinaison, +maxDeclinaison, 0.05)
		for H in np.arange(-maxH, maxH+7.5, 7.5):
			if H.is_integer()==False:	# demi-heures
				props=dict(color=color_halfhours, alpha=0.5, lw=1)	# ligne fine et grise
			else :	# heures pleines
				props=dict(color=color_hours, alpha=1.0)	# ligne épaisse, en couleur (non grise)
			X=liste_azimut(decl,H)
			Y=liste_hauteur(decl,H)
			plt.plot(X,Y, **props)
			if H.is_integer():
				if H>=0 :	# chiffres des heures
					prop_chiffres=dict(ha='left')
					X=1.01*max(X)
				elif H<0 :
					prop_chiffres=dict(ha='right')
					X=1.01*min(X)
				plt.text(X, 1.01*max(Y), '%ih'%(12+H/15), fontweight='bold',**prop_chiffres)
		# courbes de déclinaison (équinoxes, solstices et aujourd'hui)
		couleursdecl=['IndianRed', 'BlueViolet', 'Teal','OrangeRed']
		datesdecl=["Solstice d'hiver", "Equinoxes","Solstice d'été","Aujourd'hui"]
		s=SolarPosition(target_date)
		declinaison=s.getDeclinaison()
		H = np.arange(-maxH-15, maxH+15, 1.0)	# liste des angles horaires
		for i, D in enumerate([-maxDeclinaison, 0.0, +maxDeclinaison, declinaison]):
			X=liste_azimut(D,H)
			Y=liste_hauteur(D,H)
			plt.plot(X, Y, color=couleursdecl[i], label=datesdecl[i])
		# ajout de la position solaire (cercle jaune) pour l'heure de target_date en UTC
		# convert local time to UTC time
		tz=pytz.timezone(tz_identifier)
		target_date_local=tz.localize(target_date)
		target_date_utc=target_date_local.astimezone(pytz.utc)
		hd=target_date_utc.hour+target_date_utc.minute/60+target_date_utc.second/3600
		if _debug:
			print("date :",target_date)
			print("date (local) :",target_date_local)
			print("date (UTC):",target_date_utc)
			print("hour (UTC):",hd)
		h=(hd-12.0)*15	# (heure décimale-12UTC) * 15
		x=self.calcul_azimut(declinaison,h)
		y=self.calcul_hauteur(declinaison,h)
		plt.plot(x,y,color=color_sun,marker='o',markersize=20,alpha=0.75)
		plt.plot(x,y,color='OrangeRed',marker='o',markersize=6,alpha=1.0)
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
	def __init__(self, name, region, latitude, longitude, timezone, elevation):
		"""
		Prepare l'objet Ephemeris en l'initialisant avec une localisation sur terre
			name :		nom de la position (ville)
			country :	nom du pays ou de la région
			latitude :	latitude du lieu (en degré)
			longitude :	longitude du lieu (en degré)
			time-zone :	nom de la zone horaire (suivant des dénominations standard : {Région}/{Ville}, voir https://utctime.info/timezone/)
			elevation :	hauteur du lieu (en mètres)
		"""
		self.location=astral.Location()
		self.location.name=name
		self.location.region=region
		self.location.latitude=latitude
		self.location.longitude=longitude
		self.location.timezone=timezone
		self.location.elevation=elevation
		self.location.solar_depression=6
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
				target_date : date/heure du calcul (si None = date/heure temps réel)
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
		# si pas de date, prendre la date courante
		if target_date==None :
			self.target_date=datetime.datetime.now()
		else:
			self.target_date=target_date
		# calcul données de base (Astral 1.6.1)
		self.dawn=self.location.dawn(date=target_date)
		self.sunrise=self.location.sunrise(date=target_date)
		self.noon=self.location.solar_noon(date=target_date)
		self.solar_elevation=self.location.solar_elevation(dateandtime=self.target_date)
		self.solar_elevation_noon=self.location.solar_elevation(dateandtime=self.noon)
		self.sunset=self.location.sunset(date=target_date)
		self.dusk=self.location.dusk(date=target_date)
		self.moon_phase=self.location.moon_phase(date=target_date)
		phase=MoonPhase(self.moon_phase)
		self.moon_phase_name=phase.getName()
		self.moon_phase_pict=phase.getPicture()
		# calcul des durées à partir des horaires de base
		daylight=self.location.daylight(date=target_date)
		self.daylength=daylight[1]-daylight[0]
		night=self.location.night(date=target_date)
		self.nightlength=night[1]-night[0]
		# calcul de la veille pour déterminer la variation de durée du jour
		target_date_previous=target_date+datetime.timedelta(days=-1)
		daylight=self.location.daylight(date=target_date_previous)
		daylength=daylight[1]-daylight[0]
		variation=self.daylength-daylength
		self.day_increase_minutes=variation.total_seconds()/60.0
	
	def __str__(self):
		if self.location==None:
			r="location non definie"
		elif self.target_date==None:
			r="date non définie (fonction Ephemeris.calc)"
		else:
			sun=SunPhase(self.solar_elevation)
			colorname=sun.getName()
			colorhtml=sun.getColor()
			r=f"Éphéméride {self.location.name} ({self.location.region}) pour {self.target_date:%d/%m/%Y @ %H:%M}"
			r=r+f"\n\tÉlévation        : {self.solar_elevation:.1f}° ({colorname})"
			r=r+f"\n\tJour:Aube        : {self.dawn:%H:%M}"
			r=r+f"\n\tJour:Lever       : {self.sunrise:%H:%M}"
			r=r+f"\n\tJour:Culmination : {self.noon:%H:%M} (hauteur : {self.solar_elevation_noon:.1f}°)"
			r=r+f"\n\tJour:Coucher     : {self.sunset:%H:%M}"
			r=r+f"\n\tJour:Crépuscule  : {self.dusk:%H:%M}"
			r=r+f"\n\tJour:Durée       : {self.daylength} ({self.day_increase_minutes:+.1f} minute(s))"
			r=r+f"\n\tNuit:Phase       : {self.moon_phase_name} ({self.moon_phase:}/28)"
			r=r+f"\n\tNuit:Durée       : {self.nightlength}"
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
		sun=SunPhase(self.solar_elevation)
		colorname=sun.getName()
		colorhtml=sun.getColor()
		line=ET.SubElement(table,'tr')
		cell=ET.SubElement(line,'td')
		cell.text=f"Hauteur du soleil"
		cell=ET.SubElement(line,'td',attrib={'style':f'background-color: {colorhtml}'})
		cell.text=f"{self.solar_elevation:.1f}° ({self.target_date:%H:%M}) {colorname}"
		# ligne 2 : Aube
		line=ET.SubElement(table,'tr')
		cell=ET.SubElement(line,'td')
		cell.text=f"Aube"
		cell=ET.SubElement(line,'td')
		cell.text=f"{self.dawn:%H:%M}"
		# ligne 3 : Lever du soleil
		line=ET.SubElement(table,'tr')
		cell=ET.SubElement(line,'td')
		cell.text=f"Lever"
		cell=ET.SubElement(line,'td')
		cell.text=f"{self.sunrise:%H:%M}"
		# ligne 4 : Zénith solaire
		line=ET.SubElement(table,'tr')
		cell=ET.SubElement(line,'td')
		cell.text=f"Culmination (Zenith)"
		cell=ET.SubElement(line,'td')
		cell.text=f"{self.noon:%H:%M}"
		# ligne 5 : Coucher du soleil
		line=ET.SubElement(table,'tr')
		cell=ET.SubElement(line,'td')
		cell.text=f"Coucher"
		cell=ET.SubElement(line,'td')
		cell.text=f"{self.sunset:%H:%M}"
		# ligne 6 : Crépuscule
		line=ET.SubElement(table,'tr')
		cell=ET.SubElement(line,'td')
		cell.text=f"Crépuscule"
		cell=ET.SubElement(line,'td')
		cell.text=f"{self.dusk:%H:%M}"
		# ligne 7 : Durée du jour
		line=ET.SubElement(table,'tr')
		cell=ET.SubElement(line,'td')
		cell.text=f"Durée du jour"
		cell=ET.SubElement(line,'td')
		cell.text=f"{self.daylength} {self.day_increase_minutes:+.1f} minute(s)"
		# ligne 8 : Durée de la nuit
		line=ET.SubElement(table,'tr')
		cell=ET.SubElement(line,'td')
		cell.text=f"Durée de la nuit"
		cell=ET.SubElement(line,'td')
		cell.text=f"{self.nightlength}"
		# ligne 9 : Phase lunaire (avec illustration)
		line=ET.SubElement(table,'tr')
		cell=ET.SubElement(line,'td')
		cell.text=f"Phase de la lune"
		cell=ET.SubElement(line,'td')
		cell.text=f"{self.moon_phase_name} ({self.moon_phase:}/28)"
		img=ET.SubElement(cell,'img',attrib={'src':f"{self.moon_phase_pict}",'width':'30','height':'30'})
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
		Coordonnées indépendantes de la position de l'observateur est compsé de 2 angles :
			Ascension droite
			Déclinaison
		Ces coordonnées sont repérés dans la plan quatoriale (le plan qui passe par l'équateur de la Terre
		soit l'équivalent spaciale des latitude et longitude terrestre projetées.
	"""
	def __init__(self,date=None):
		if date==None:
			self.date=datetime.datetime.now()
		else:
			self.date=date
	
	def getDeclinaison(self):
		# numéro du jour de l'année
		date0 = datetime.datetime(self.date.year, 1, 1)
		dd=self.date-date0
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
			J2000.0 : référence au jour Junien du 1/01/2000 12h
			Aussi nommé "Epoque standard depuis 1984
			En savoir plus : https://fr.wikipedia.org/wiki/J2000.0
		"""
		return((self.JJ-2415020.0)/36525)
	
	def __str__(self):
		""" affiche le jour julien lisible (sous forme calendaire) """
		d=self.getDate()
		return(f"Julien={self.JJ} : {d}")

# -- Fonctions -----------------------------------------------------------------------

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
	# date du calcul (aujourd'hui + décalage)
	date=datetime.datetime.now()
	targetDate=date+datetime.timedelta(days=shiftday)
	if _debug:
		print("aujourd'hui",date)
		print("offset",shiftday)
		print("target",targetDate)
	# 4. Calcul jour julien
	jj=JulianDay()
	jj.setDate(targetDate)
	if _verbose:
		print(f"Date :            {targetDate}")
		print(f"Jour Julien :     {jj.JJ:.2f} TT")
		print(f"Epoque standard : {jj.getT():.6f} J2000.0")
	# 5. Calcul position solaire
	# déclinaison solaire
	s=SolarPosition(targetDate)
	sunDeclinaison=s.getDeclinaison()
	if _verbose:
		print(f"Déclinaison :     {sunDeclinaison:.2f}°")
	# diagramme solaire
	sd=SolarDiagram(config.latitude,sunDeclinaison)
	sd.calc(targetDate,config.tz)
	if default_solar: plt.show()
	# 6. Calcul éphéméride
	e=Ephemeris(config.location, config.region, config.latitude, config.longitude, config.tz, config.elevation)
	e.calc(targetDate)
	if _verbose: print(e)
	if default_window: e.toHTML()

if __name__ == '__main__' :
	main(sys.argv[1:])


