# -*- coding: utf-8 -*-
"""
Created on Thu Jul  5 11:00:00 2018

@author: gelbj
"""

import os,sys
Link = "C:/Users/GelbJ/Desktop/ANACONDA1/Library/share/gdal/"
os.environ["GDAL_DATA"] = Link
from path import Path
import copy
from osgeo import osr


sys.path.append("L:/Python/___JBasics")
from JQgis import JVectorLayer as JV
import OsmData
import JGeom

#############################################
## Parametres generaux
#############################################

#Shapefiles = Path("I:/___Data These/Christchurch/Traces/frames/ID1_PA")
#MatchingFile = Path("I:/___Data These/Christchurch/Traces/adjusted/MatchingOSRM/ID1_PA")
#QgisBase = "H:/Programmation/Python/MapMatchingV3/Basic_qgisProj.qgs"
#Sortie = "I:/___Data These/Christchurch/Traces/adjusted/Qgs/ID1_PA"

#OSMFolder = "I:/___Data These/Christchurch/OSM"
#OSMName = "Christchurch_07_03_2018"

Root = Path(__file__).parent
print("This is Root : "+str(Root))

FrameFiles = Root.parent.joinpath("__Frames")
MatchingFile = Root.parent.joinpath("__OsrmMatched")
Sortie = Root.parent.joinpath("__QgisFiles")
QgisBase = Root.joinpath("Basic_qgisProj.qgs")
OSMFolder = Root.joinpath("OSMData")
OSMName = list(OSMFolder.files("*.osm"))[0].name.split("_Data")[0]

#############################################
## Execution
#############################################
XMLBase = open(QgisBase,"r")
StringBase = XMLBase.read()

##recuperation des participants
#IDParts = [str(element.name) for element in FrameFiles.listdir()]
IDParts = ["ID4_DD"] #"ID1_SP" "ID2_VJ","ID3_MG","ID4_DD"
#,

##creation des fichiers de sortie
for element in IDParts : 
    Folder = Sortie.joinpath(element)
    try :
        os.mkdir(Folder)
    except : 
        print("The folder seems to exist : "+Folder)

## A remplacer :
#--UNAME-- : nom du fichier avec les - rempalces par des _
#--NAME-- : nom du fichier
#--SOURCE-- : source du fichier shp
#--XMIN--
#--YMIN--
#--XMAX--
#--YMAX--


source = osr.SpatialReference()
source.ImportFromEPSG(4326)

target = osr.SpatialReference()
target.ImportFromEPSG(3857)

transform1 = osr.CoordinateTransformation(source, target)
transform2 = osr.CoordinateTransformation(target, source)

for IDPart in IDParts : 
    Folder = FrameFiles.joinpath(IDPart)
    MatchingFolder = MatchingFile.joinpath(IDPart)
    for Shp in Folder.files("*.shp") :
        print("___Working on :"+Shp)
        OutFile = Sortie.joinpath(IDPart).joinpath(str(Shp.name).split(".")[0]+".qgs")
        if os.path.isfile(OutFile)==False :
            ## Rajout d'un petit Buffer de 800m
            Layer = JV.JFastLayer(str(Shp))
            Layer.Initialize(ID="OID",GeomIndex=False)
            ExtentGeom = JGeom.Extent_geom(Layer.Extent)
            ExtentGeom.Transform(transform1)
            BUFFER = ExtentGeom.Buffer(800)
            BUFFER.Transform(transform2)
            Extent = BUFFER.GetEnvelope()
            print(Extent)
            #Preparation de l'extraction OSM
            OutputOSM = str(MatchingFolder+'/'+Shp.name.split(".")[0]+"_Data.osm")
            print("Extracting OSMFIle")
            OSMDB = OsmData.OSMDb(OSMFolder,OSMName)
            OSMDB.Extract(Extent,OutputOSM)
            OSMDB = OsmData.OSMDb(MatchingFolder,Shp.name.split('.')[0])
            print("Building osm file...")
            OSMDB.Build()
            print("Calculating cycling fields")
            OSMDB.BuildOSMFields("lines",[("cycleway","cycleway"),("cyclewayLeft","cycleway:left"),("cyclewayRight","cycleway:right")])
            
            ## Preparation du fichier Qgs
            #(MinX,MaxX,MinY,MaxY)
            Dico = {"--SOURCESHP--" : str(Shp),
                    "--SOURCEMATCHINGOSM--":str(MatchingFolder)+"/"+str(Shp.name).split(".")[0]+"_Layers.sdb",
                    "--SOURCEMATCHINGSHP--":str(MatchingFolder)+"/Matching_"+str(Shp.name),
                    "--XMIN--" :str(Extent[0]),
                    "--YMIN--":str(Extent[2]),
                    "--XMAX--":str(Extent[1]),
                    "--YMAX--":str(Extent[3]),
                    "--NAME--":str(Shp.name).split(".")[0],
                    "--UNAME--":str(Shp.name).split(".")[0].replace("-","_")
                    }
            ThisString = copy.deepcopy(StringBase)
            for key,value in Dico.items() : 
                ThisString=ThisString.replace(key,value)
            Output = open(OutFile,"w")
            Output.write(ThisString)
            Output.close()