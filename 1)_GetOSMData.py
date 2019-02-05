# -*- coding: utf-8 -*-
"""
Created on Mon Jun 11 10:16:43 2018

@author: GelbJ
"""


######################################
# import de librairies en autres fonctions
######################################

import os,sys
Link = "C:/Users/GelbJ/Desktop/ANACONDA1/Library/share/gdal/"
os.environ["GDAL_DATA"] = Link

sys.path.append("J:/__Collecte reseau cyclable Montreal 05-2018/Python/DataCollectionTool/___JBasics")
from osgeo import osr

import OsmData
from JQgis import JVectorLayer as JV
from JQgis import JGeom
import numpy as np
import copy
from path import Path


######################################
# Parametres du script
######################################

##### Donnees pour Paris
#Root = "H:/__These/Base de donnees/Paris/Traces Fabrices/Version 16-03-2018/original"
#Sortie = "H:/Programmation/Python/MapMatchingV2/Data/OSMData"
#BDName = "Paris_11_06"

####Donnees pour Auckland
Root = str(Path(__file__).parent.parent.parent.joinpath("B)_VideoStructured")).replace("\\","/") #"J:/___NewZealand/__Auckland/B)_VideoStructured"
BDName = "Montreal_2018"
SpatialLiteFiles = "C:/Users/GelbJ/Desktop/SpatialLiteExes"


######################################
# Fonction utilitaire
######################################
def CheckDistances(Geoms) : 
    ## preparation de la transformation
    inSpatialRef = osr.SpatialReference()
    inSpatialRef.ImportFromEPSG(4326)
    outSpatialRef = osr.SpatialReference()
    outSpatialRef.ImportFromEPSG(3857)
    coordTransform = osr.CoordinateTransformation(inSpatialRef, outSpatialRef)
    OkPts = []
    #Application de la transformation
    Xs= []
    Ys = []
    Projs = copy.deepcopy(Geoms)
    for element in Projs :
        element.Transform(coordTransform)
        Xs.append(element.GetX())
        Ys.append(element.GetY())
        
    #Verification des distances
    Center = JGeom.OgrPoint((np.mean(Xs),np.mean(Ys)))
    for e,Pt in enumerate(Projs) : 
        if Pt.Distance(Center)<200000 : 
            OkPts.append(Geoms[e])
#   
#    #Verification des distances
#for e,Pt1 in enumerate(Projs) : 
#    Dists = [Pt1.Distance(Pt2) for Pt2 in Projs]
#    M = np.mean(Dists)
#    if M < 50000 : 
#        OkPts.append(Geoms[e])
    
    return OkPts
        



######################################
# Execution
######################################

## Recuperation de l'entendue de tous les shapefiles
Extents = []
print("Reading shapefiles ...")

Sortie = Path(__file__).parent.joinpath("OSMData")

for root, dirnames, Files in os.walk(Root) :
    if len(Files)>0 :
        for File in Files :
            Ext = File.split(".")[-1]
            if Ext == "shp" : 
                Layer = JV.JFastLayer(root+"/"+File)
                Layer.Initialize(ID="OID",GeomIndex=False)
                OkPts = CheckDistances(Layer.Geoms.values())
                if len(OkPts)==0:
                    print(root+"/"+File)
                    raise ValueError("No geometries ok")
                Extents.append(JGeom.Extent_geom(JGeom.GetExtent(OkPts)))
        
print("Calculating total extent ...")
TotalExtent = JGeom.GetExtent(Extents)

print("Downloading OSM data ...")
TraceBD = OsmData.OSMDb(Sortie,BDName)
TraceBD.DownloadData(TotalExtent)
TraceBD.BuildHard(ExeFile=SpatialLiteFiles)