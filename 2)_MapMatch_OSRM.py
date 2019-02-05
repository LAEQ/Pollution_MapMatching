# -*- coding: utf-8 -*-
"""
Created on Thu Jul  5 12:05:50 2018

@author: gelbj
"""
import os,sys
Link = "C:/Users/GelbJ/Desktop/ANACONDA1/Library/share/gdal/"
os.environ["GDAL_DATA"] = Link

sys.path.append("L:/Python/___JBasics")
import os
from __OSRMobj import *
from JQgis import JVectorLayer as JV
from path import Path
import json
import JDate

## Demarer le server : 
## backend>osrm-routed.exe "H:\Programmation\Python\MapMatchingV3\OSMData\Paris_11_06_Data.osrm" --max-matching-size 10000

#etape 1 preparer le fichier osm
#backend>osrm-extract.exe Data/Montreal_2018_Data.osm -p profiles/bicycle.lua
#etape 2 comprimer le fichier osrm
#backend>osrm-contract.exe Data/Montreal_2018_Data.osrm
#etape 3 demarrer le server osrm
#backend>osrm-routed.exe Data/Montreal_2018_Data.osrm --max-matching-size 100000

## autre option
##I:\___Data These\Christchurch\OSM>C:\Users\gelbj\Desktop\osrm_backend\osrm-routed.exe Christchurch_07_03_2018_Data.osrm --max-matching-size 10000

#####################
## Parametres generaux
#####################

Participants = ["ID4_DD"]# "ID1_SP" "ID2_VJ","ID3_MG","ID4_DD"]

Root = Path(__file__).parent.parent.parent.joinpath("B)_VideoStructured")
InputFolderShpPts = Root


#####################
## Execution
#####################
OutPutFolderShpPts = Path(__file__).parent.parent.joinpath("__OsrmMatched")


def TimeLaps(Start,End) :
    AYear,AMonth,ADay = Start.split(" ")[0].split("-")
    AHour,AMinute,ASecond = Start.split(" ")[1].split(":")
    A = JDate.Jdatetime(Year=AYear,Month=AMonth,Day=ADay,Hour=AHour,Minute=AMinute,Second=ASecond)
    BYear,BMonth,BDay = End.split(" ")[0].split("-")
    BHour,BMinute,BSecond = End.split(" ")[1].split(":")
    B = JDate.Jdatetime(Year=BYear,Month=BMonth,Day=BDay,Hour=BHour,Minute=BMinute,Second=BSecond)
    Diff = abs((A.DateTime-B.DateTime).total_seconds())
    return Diff/60.0
    
ToShort = []
for IDPart in Participants :
    FolderPart = InputFolderShpPts.joinpath(IDPart).joinpath("SHP")
    OutPutFolder = OutPutFolderShpPts.joinpath(IDPart)
    try :
        os.mkdir(OutPutFolder)
    except : 
        pass
    for Shp in FolderPart.files("*.shp") :
        print("Working on : "+str(Shp))
        if os.path.isfile(OutPutFolder+"/Matching_"+str(Shp.name))==False :
            Layer = JV.JFastLayer(Shp)
            Layer.Initialize(ID ="OID",GeomIndex=False)
            Start = Layer.GetRow(0)
            End = Layer.GetRow(Layer.FeatureCount-1)
            Duree = TimeLaps(Start["DATETIME"],End["DATETIME"])
            if Duree < 5 :
                ToShort.append((Shp.name,Duree))
            else :
                Stops,Movings = SplitAtStops(Layer)
                
                #Test naif
                Server = OSRM("http://localhost:5000")
                Coords = []
                Dates = []
                for e,Move in enumerate(Movings) :
                    Coord,Date = GetCoordsAnTime(Move)
                    Coords+=Coord
                    Dates+=Date
                    if e<len(Stops)-1 and len(Stops)>0 : 
                        Stopped = Stops[e]
                        CoordStop,TimeStop = GetCenterTime(Stopped)
                        Coords+=CoordStop
                        Dates+=TimeStop
                    
                
                Rep = Server.MapMatch(Coords,Dates)
                JS = json.loads(Rep)
                Points,Lines = Server.StructureRep(JS,Coords)
                
                ## creation du layer de point
                NewLayer = JV.JFastLayer("")
                NewLayer.MakeItEmpty(Params={"SpatialRef":Layer.SpatialRef})
                for e,Pt in enumerate(Points) : 
                    Feat = {"OID":e}
                    NewLayer.AppendFeat(Feat,Pt)
                    
            #    ##creation du layer de ligne
            #    LayerLine = JV.JFastLayer('')
            #    LayerLine.MakeItEmpty(Params={"SpatialRef":Layer.SpatialRef,"GeomType":"LINESTRING"})
            #    
            #    for e,Line in enumerate(Lines) :
            #        Feat = {"OID":e}
            #        LayerLine.AppendFeat(Feat,Line)
            #        
            #    LayerLine.Save(OutPutFolderShpLines+"/"+str(Shp.name))
                NewLayer.Save(OutPutFolder.joinpath("Matching_"+str(Shp.name)))
                
print("Files that are too short for the next steps : ")
for File,Duree in ToShort : 
    print("   "+File+" ; "+str(Duree)+"min")