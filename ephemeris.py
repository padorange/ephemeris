#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__application__="ephemeris.py"
__version__="0.3"
__copyright__="Copyright mars-avril 2025, Pierre-Alain Dorange"
__license__="BSD-3-Clauses"		# voir https://en.wikipedia.org/wiki/BSD_licenses
__author__="Pierre-Alain Dorange"
__contact__="pdorange@mac.com"

"""
	Ephemeris
	-----------------------------------------------------------------------------------------
	Script Python 3.11.x, testé sur Debian 12 (bookworm)
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
	-----------------------------------------------------------------------------------------
	0.1 : janvier-février 2025 : première version
	0.2 : février-mars 2025 : résultat sous forme HTML5 + paramètre "-d"
	0.3 : mars-avril 2025 : intégration diagramme solaire en azimuth et hauteur + position solaire selon target_date + paramètre "-s"
	"""

import sys,getopt,os
import datetime, pytz					# gestion date et temps + timezone
import math
from xml.etree import ElementTree as ET	# gestion elementtree pour créer le résultat HTML
import webbrowser						# module pour ouvrir une URL dans le navigateur par défaut
import astral							# Astral 1.6.1 (default version include in Debian 12
import matplotlib.pyplot as plt			# matplot lib
import numpy as np						# numpy

_debug=False

default_directory="html"						# répertoire local ou enregistrer les éléments HTML
default_diagsol_file="diagramme_solaire.png"	# nom du fichier avec le diagramme solaire
default_html_file="ephemeris.html"				# nom du fichier html généré
maxDeclinaison=23.436							# déclinaison maximale du soleil / terre

# Position par défaut : Paris, France (a surchager pendant l'init des objets)
default_latitude=48.859
default_longitude=2.347
default_tz="Europe/Paris"

# couleur de fond (html) pour le bloc info
color_bluehour='SteelBlue'
color_goldhour='Orange'
color_dayhour='SkyBlue'
color_nighthour='CornflowerBlue'

# personnalisation pour le diagramme solaire
default_font="Roboto Condensed"
default_fontsize=8
color_sun="gold"
color_hours='royalblue'
color_halfhours='gray'

# définit le répertoire par défaut comme celui du source (gestion du lancement hors dossier source)
path=os.path.dirname(os.path.abspath(__file__))
os.chdir(path)

def getPhaseName(phase):
	""" getPhaseName
		converti la phase lunaire (entier entre 0 et 28) en une dénomination et une image
		Phases de la lune (ref : https://fr.wikipedia.org/wiki/Phase_de_la_Lune)
		Images référence : https://starwalk.space/fr/moon-calendar
		Cycle : 29.5 jours
	"""
	prefix="./phases/lune_"
	if phase<2 or phase>=28:
		name="Nouvelle Lune"
		pictureName=prefix+"00.png"
	elif phase<6:
		name="Premier croissant"
		pictureName=prefix+"01.png"
	elif phase<9:
		name="Premier quartier"
		pictureName=prefix+"02.png"
	elif phase<14:
		name="Lune Gibeuse croissante"
		pictureName=prefix+"03.png"
	elif phase<17:
		name="Pleine Lune"
		pictureName=prefix+"04.png"
	elif phase<22:
		name="Lune Gibeuse décroissante"
		pictureName=prefix+"05.png"
	elif phase<25:
		name="Dernier quartier"
		pictureName=prefix+"06.png"
	elif phase<28:
		name="Dernier croissant"
		pictureName=prefix+"07.png"
	return (name,pictureName)

def sunColorName(elevation):
	if elevation<-4.0 and elevation>-6.0:
		color_name="Heure bleue"
		color_html=color_bluehour
	elif elevation<6.0 and elevation>-4.0:
		color_name="Heure dorée"
		color_html=color_goldhour
	elif elevation>6.0 :
		color_name="Jour"
		color_html=color_dayhour
	else:
		color_name="Nuit"
		color_html=color_nighthour
	return((color_name,color_html))

class SolarDiagram():
	"""
		Calcul du diagramme solaire pour une latitude
		adapté du script de David Alberto
		source : https://www.astrolabe-science.fr/diagramme-solaire-azimut-hauteur/
	"""
	def __init__(self, latitude=default_latitude, timezone=default_tz):
		self.phi_degrees=latitude
		self.phi_radians=np.radians(latitude)
	
	def calc(self,target_date=None,tz_str=default_tz):
		if target_date==None :	# si pas de datetime alors prendre l'instant présent (now)
			self.target_date=datetime.datetime.now()
		else:
			self.target_date=target_date
		# Paramètres à personnaliser
		plt.rcParams["font.family"] = default_font
		plt.rcParams["font.size"] = default_fontsize
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
		plt.text(0.005, 0.993, 'Latitude %.1f°' % (self.phi_degrees), color='red', va='top', fontsize=9, transform=ax.transAxes, bbox=dict(facecolor='white', edgecolor='black'))
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
		tz=pytz.timezone(tz_str)
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
	def __init__(self, name="Paris", region="France", latitude=default_latitude, longitude=default_longitude, timezone=default_tz, elevation=35):
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
		(self.moon_phase_name,self.moon_phase_pict)=getPhaseName(self.moon_phase)
		# calcul des durées à partir des horaires de base
		daylight=self.location.daylight(date=target_date)
		self.daylength=daylight[1]-daylight[0]
		night=self.location.night(date=target_date)
		self.nightlength=night[1]-night[0]
		# calcul de la veille pour déterminer la variation de durée du jour
		target_date_previous=target_date+datetime.timedelta(days=-1)
		daylight=self.location.daylight(date=target_date_previous)
		daylength=daylight[1]-daylight[0]
		self.day_increase_minutes=(self.daylength-daylength).seconds/60
	
	def __str__(self):
		if self.location==None:
			r="location non definie"
		elif self.target_date==None:
			r="date non définie (fonction Ephemeris.calc"
		else:
			r=f"Éphéméride {self.location.name} ({self.location.region}) pour {self.target_date:%d/%m/%Y}"
			(colorname,colorhtml)=sunColorName(self.solar_elevation)
			r=r+f"\n\tÉlévation        : {self.solar_elevation:.1f}° ({self.target_date:%H:%M}) {colorname}"
			r=r+f"\n\tJour:Aube        : {self.dawn:%H:%M}"
			r=r+f"\n\tJour:Lever       : {self.sunrise:%H:%M}"
			r=r+f"\n\tJour:Culmination : {self.noon:%H:%M} (hauteur : {self.solar_elevation_noon:.1f}°)"
			r=r+f"\n\tJour:Coucher     : {self.sunset:%H:%M}"
			r=r+f"\n\tJour:Crépuscule  : {self.dusk:%H:%M}"
			r=r+f"\n\tJour:Durée       : {self.daylength} (+{self.day_increase_minutes:.1f} minute(s))"
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
		html=ET.Element('html')
		head=ET.SubElement(html,'header')
		meta=ET.SubElement(head,'meta',attrib={'charset':'utf-8'})
		meta.text=""
		title=ET.SubElement(head,'title')
		title.text="Éphémérides"
		style=ET.SubElement(head,'style')
		style.text=default_css
		body=ET.SubElement(html,'body')
		div=ET.SubElement(body,'div',attrib={'id':'diag'})
		img=ET.SubElement(div,'img',attrib={'src':f"diagramme_solaire.png"})
		div=ET.SubElement(body,'div',attrib={'id':'tab'})
		h=ET.SubElement(div,'h1')
		h.text=f"Éphémérides"
		h=ET.SubElement(div,'h2')
		h.text=f"Localisation : {self.location.name} ({self.location.region})"
		h=ET.SubElement(div,'h3')
		h.text=f"Date : {self.target_date:%d/%m/%Y}"

		table=ET.SubElement(div,'table')

		line=ET.SubElement(table,'tr')
		cell=ET.SubElement(line,'td')
		cell.text=f"Hauteur du soleil"
		(colorname,colorhtml)=sunColorName(self.solar_elevation)
		cell=ET.SubElement(line,'td',attrib={'style':f'background-color: {colorhtml}'})
		cell.text=f"{self.solar_elevation:.1f}° ({self.target_date:%H:%M}) {colorname}"

		line=ET.SubElement(table,'tr')
		cell=ET.SubElement(line,'td')
		cell.text=f"Aube"
		cell=ET.SubElement(line,'td')
		cell.text=f"{self.dawn:%H:%M}"

		line=ET.SubElement(table,'tr')
		cell=ET.SubElement(line,'td')
		cell.text=f"Lever"
		cell=ET.SubElement(line,'td')
		cell.text=f"{self.sunrise:%H:%M}"

		line=ET.SubElement(table,'tr')
		cell=ET.SubElement(line,'td')
		cell.text=f"Culmination (Zenith)"
		cell=ET.SubElement(line,'td')
		cell.text=f"{self.noon:%H:%M}"

		line=ET.SubElement(table,'tr')
		cell=ET.SubElement(line,'td')
		cell.text=f"Coucher"
		cell=ET.SubElement(line,'td')
		cell.text=f"{self.sunset:%H:%M}"

		line=ET.SubElement(table,'tr')
		cell=ET.SubElement(line,'td')
		cell.text=f"Crépuscule"
		cell=ET.SubElement(line,'td')
		cell.text=f"{self.dusk:%H:%M}"

		line=ET.SubElement(table,'tr')
		cell=ET.SubElement(line,'td')
		cell.text=f"Durée du jour"
		cell=ET.SubElement(line,'td')
		cell.text=f"{self.daylength} (+{self.day_increase_minutes:.1f} minute(s))"

		line=ET.SubElement(table,'tr')
		cell=ET.SubElement(line,'td')
		cell.text=f"Durée de la nuit"
		cell=ET.SubElement(line,'td')
		cell.text=f"{self.nightlength}"

		line=ET.SubElement(table,'tr')
		cell=ET.SubElement(line,'td')
		cell.text=f"Phase de la lune"
		cell=ET.SubElement(line,'td')
		cell.text=f"{self.moon_phase_name} ({self.moon_phase:}/28)"
		img=ET.SubElement(cell,'img',attrib={'src':f"{self.moon_phase_pict}",'width':'30','height':'30'})
		
		path=os.path.join(".",default_directory)	# chemin pour la sauvegarde des résultats (images et html)
		url=os.path.join(path,default_html_file)

		with open(url, 'w') as f:
			f.write("<!DOCTYPE html>\n")	# ajout du doctype en première ligne
			ET.ElementTree(html).write(f, encoding='unicode',method='html')
		webbrowser.open(url,autoraise=True)

class SolarPosition():
	"""
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
		J=dd.days
		# déclinaison solaire pour J
		decl=maxDeclinaison*math.sin(2.0*math.pi*(J+284.0)/365.0)
		return decl

class JulianDay():
	"""
		Le jour julien est un système de datation consistant à compter le nombre de jours et fraction de jour écoulés
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
		""" Affecte l'objet JulianDay avec une date (datetime) et calcul de jour julien """
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
		""" retourne la date calendaire du Jour julien """
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

# --  Aide  --------------------------------------------------------------------------------
#			lettre-code : {nom-long, type de valeur, valeur par défaut, aide}
arguments={	'h':("help",None,None,"aide"),
			'd':("day","<int>",0,"Décalage (en jours) par rapport à aujourd'hui"),
			's':("",None,None,"Affiche le diagramme solaire annuel")
		}

def show_usage():
	print("--------------------------------------------")
	print("%s %s" %(__file__,__version__))
	print("  %s" % __copyright__)
	print("  Licence : %s" % __license__)
	print("Calcul l'éphéméride à une date.")
	print("--------------------------------------------")
	print("options :")
	for a in arguments:
		(arg,attrb,default,help)=arguments[a]
		if attrb:
			arg+=":%s" % attrb
		if default:
			help+=" (défaut=%s)" % default
		print("  -%s (--%s)\t%s" % (a,arg,help))
	print("--------------------------------------------")
	print()

# -- Démarrage --------------------------------------------------------------------------------

def main(argv):
	print("--",__file__,__version__,"-----------------")
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
		if _debug:
			print(opt,":",arg)
		option=None
		for a in arguments:
			(ida,attrb,default,help)=arguments[a]
			if opt in (a,ida):
				option=a
		if option=="h":
			show_usage()
			exit()
		elif option=="d":
			if _debug:
				print("shift",arg)
			shiftday=int(arg)
		elif option=="s":
			solarDiag=True
		else:
			print("ERREUR : paramètre",opt,"non géré")
	# 3. Paramètres du lieu et moment d'observation
	city = "Cognac"
	country = "France"
	latitude = 45.68708
	longitude = -0.31587
	tz = "Europe/Paris"
	elevation = 24
	# date du calcul (aujourd'hui + décalage)
	date = datetime.datetime.now()
	targetDate = date + datetime.timedelta(days=shiftday)
	if _debug:
		print("aujourd'hui",date)
		print("offset",shiftday)
		print("target",targetDate)
	# 4. Calcul jour julien
	jj=JulianDay()
	jj.setDate(targetDate)
	print(f"Date : {targetDate}")
	print(f"Jour Julien : {jj.JJ:.2f}")
	print(f"T : {jj.getT()}")
	# 5. Calcul position solaire
	# déclinaison solaire
	s=SolarPosition(targetDate)
	declinaison=s.getDeclinaison()
	print(f"Déclinaison solaire : {declinaison:.2f}")
	# diagramme solaire
	sd=SolarDiagram(latitude,declinaison)
	sd.calc(targetDate,tz)
	if solarDiag:
		plt.show()
	# 6. Calcul éphéméride
	e=Ephemeris(city, country, latitude, longitude, tz, elevation)
	e.calc(targetDate)
	print(e)
	e.toHTML()

if __name__ == '__main__' :
	main(sys.argv[1:])


