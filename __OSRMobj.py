# -*- coding: utf-8 -*-
"""
Created on Mon Jul  2 08:13:17 2018

@author: gelbj
"""

import urllib2,json
import JDate,JGeom
import numpy as np


## Demarer le server : 
## backend>osrm-routed.exe "H:\Programmation\Python\MapMatchingV3\OSMData\Paris_11_06_Data.osrm" --max-matching-size 10000

## autre option
##I:\___Data These\Christchurch\OSM>C:\Users\gelbj\Desktop\osrm_backend\osrm-routed.exe Christchurch_07_03_2018_Data.osrm --max-matching-size 10000

class OSRM(object) : 
    
    def __init__(self,Root) : 
        self.Root = Root
        
    def MapMatch(self,Coordinates,Times) : 
        """
        Coordinates ==> coordonnees en 4326 des points
        Times ==> TimeStemps des points (dans l'ordre bien sur)
        """
        #rajouter un point au debut et a la fin pour avoir le bon nombre de point
        Coordinates = [Coordinates[0]]+Coordinates+[Coordinates[-1]]
        Times = [Times[0]-1]+Times+[Times[-1]+1]
        Coords = ";".join([str(e) for e in Coordinates]).replace(")","").replace("(","").replace(" ","")
        TimeStamps = ";".join([str(e) for e in Times])
        Request = self.Root+"/match/v1/bike/"+Coords+"?geometries=geojson&overview=full&annotations=true&timestamps="+TimeStamps
        try :
            Json = urllib2.urlopen(Request).read()
        except urllib2.HTTPError :
            print(Request)
            raise urllib2.HTTPError("The request failed")
        return Json
    
    def StructureRep(self,JS,Coordinates) : 
        """
        Prend une reponse de OSRM pour retourner : 
            un ensemble de linestring format le trajet
            une liste de points matches
        """
        ##Step1 : generer les lignes
        LineStrings=[]
        for Match in JS["matchings"] :
            Pts = [JGeom.OgrPoint(Coord) for Coord in Match["geometry"]['coordinates']]
            Line = JGeom.LineFromPoints(Pts)
            LineStrings.append(Line)
            
        ##Step2 : Generer les points avec leur osmid
        Points=[]
        print("Total Matched Points : "+str(len(JS["tracepoints"])))
        for e,Record in enumerate(JS["tracepoints"]) : 
            if Record is None :
                #Pt = JGeom.OgrPoint(Coordinates[e])
                pass
            else :
                Pt = JGeom.OgrPoint(Record["location"])
                Points.append(Pt)
        return(Points,LineStrings)
        
            
    
    
    
def GetCoordsAnTime(Layer) :
    Coords = []
    Dates = []
    for Feat in Layer.Iterate(True) :
        Coords.append((Feat["Geom"].GetX(),Feat["Geom"].GetY()))
        Date = Feat["DATETIME"].split(" ")[0].split("-")
        Time = Feat["DATETIME"].split(" ")[1].split(":")
        ThisDate = JDate.Jdatetime(Year=Date[0],Month=Date[1],Day = Date[2],Hour=Time[0],Minute=Time[1],Second=Time[2])
        Dates.append(int(ThisDate.TimeStamp))
    return (Coords,Dates)

def SplitAtStops(Layer,Limit=2) : 
    MovingParts=[]
    StopParts=[]
    NewLayer = Layer.CreateEmptyLayer()
    InStopPart = False
    for Feat in Layer.Iterate(True) :
        #si on est pas dans une phase d'arret et que l'on roule
        if Feat["Speed"]>Limit and InStopPart==False :
            NewLayer.AppendFeat(Feat,Feat["Geom"])
        #si on est pas dans une phase d'arret  mais qu'on s'arrete, on ouvre une phase d'arret
        elif Feat["Speed"]<Limit and InStopPart==False :
            MovingParts.append(NewLayer)
            NewLayer = Layer.CreateEmptyLayer()
            InStopPart = True
            NewLayer.AppendFeat(Feat,Feat["Geom"])
        #si on est dans une phase d'arret  et qu'on est toujours arrete
        elif Feat["Speed"]<Limit and InStopPart==True :
            NewLayer.AppendFeat(Feat,Feat["Geom"])
        #si on est dans une phase d'arret  et que l'on redemarre
        elif Feat["Speed"]>Limit and InStopPart==True :
            StopParts.append(NewLayer)
            NewLayer = Layer.CreateEmptyLayer()
            InStopPart = False
            NewLayer.AppendFeat(Feat,Feat["Geom"])
    #sortie de la boucle, enregistrement du dernier layer
    if InStopPart : 
        StopParts.append(NewLayer)
    else : 
        MovingParts.append(NewLayer)
        
    return (StopParts,MovingParts)

def GetCenterTime(Layer) : 
    X=[]
    Y=[]
    Times=[]
    for Feat in Layer.Iterate(True) : 
        X.append(Feat["Geom"].GetX())
        Y.append(Feat["Geom"].GetY())
        Date = Feat["DATETIME"].split(" ")[0].split("-")
        Time = Feat["DATETIME"].split(" ")[1].split(":")
        ThisDate = JDate.Jdatetime(Year=Date[0],Month=Date[1],Day = Date[2],Hour=Time[0],Minute=Time[1],Second=Time[2])
        Times.append(int(ThisDate.TimeStamp))
    MX = np.mean(X)
    MY = np.mean(Y)
    return ([(MX,MY) for T in Times],Times)
            
