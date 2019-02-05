# -*- coding: utf-8 -*-
"""
Created on Tue Nov 20 15:15:05 2018

@author: GelbJ
"""

################################################
## Import des packages
################################################

import cv2
from path import Path

import sys
sys.path.append("L:/Python/___JBasics")
import os,shutil

from JQgis import JVectorLayer as JV
import JDate

################################################
## Parametres principaux
################################################

Participant = "ID3_MG" #"ID1_SP" "ID2_VJ","ID3_MG","ID4_DD"

Root = str(Path(__file__).parent.parent).replace("\\","/")


ShpPath = Path(Root+"/__Frames/"+Participant)
QgisPaths = Path(Root+"/__QgisFiles/"+Participant)

OldPath = Root
#NewPath = r"C:/Temp/Mapmatching"
NewPath = r"C:/Temp/Mapmatching"


def ReplacePath(Feat) : 
    #return Feat["PictPath"].replace(OldPath,NewPath)
    return NewPath+"/__Frames/"+Participant+Feat["PictPath"]

def MoveShp(Shp,Dest) : 
    Name = str(Shp.name).split(".")[0]
    FilesToMove = Shp.parent.files(Name+"*")
    for File in FilesToMove : 
        Origin = str(File)
        Destination = str(Dest)+"/"+str(File.name)
        shutil.move(Origin,Destination)

try : 
    os.makedirs(str(ShpPath)+"/SaveShp")
    
except : 
    print("The folder "+str(ShpPath)+"/SaveShp"+"seems to exist")
    
    
try : 
    os.makedirs(str(QgisPaths)+"/SavedQgs")
    
except : 
    print("The folder "+str(QgisPaths)+"/SavedQgs"+" seems to exist")
    
SavedShp = str(ShpPath)+"/SaveShp"
SavedQgs = str(QgisPaths)+"/SavedQgs"

    
    
for Shp in ShpPath.files("*.shp") : 
    #modifing the SHP
    print("Working on : "+Shp)
    ## initialisation du layer
    Layer = JV.JFastLayer(Shp)
    Layer.Initialize(ID="OID",GeomIndex=False)
    ## deplacement de l'ancien Layer
    MoveShp(Shp,SavedShp)
    Layer.CalculateFieldWithGeom("PictPath",ReplacePath,Cores=1)
    Layer.Save(Shp)
    #modifing the .qgs
    QgsFilePath = str(QgisPaths.joinpath(Shp.name)).replace("\\","/").replace(".shp",".qgs")
    File = open(QgsFilePath,"r")
    Txt = File.read()
    #moving the old .qgs
    File.close()
    FinaleName = str(Shp.name).replace(".shp",".qgs")
    shutil.move(QgsFilePath,SavedQgs+"/"+FinaleName)
    #modifying the text and save the new .qgs
    txt = Txt.replace(OldPath,NewPath)
    Sortie = open(QgsFilePath,"w")
    Sortie.write(txt)
    Sortie.close()
