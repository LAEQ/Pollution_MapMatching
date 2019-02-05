# -*- coding: utf-8 -*-
"""
Created on Thu Aug  9 09:48:33 2018

@author: gelbj
"""

#############################################################################
# Import des packages
#############################################################################

import sys
sys.path.append("H:/Python/___JBasics")
from path import Path

from ..Pollution_StructurationTools.JG_Structuring_BD import PollutionBD 
from ..Pollution_StructurationTools.Config import Config

import JDate

from JQgis import JVectorLayer as JV
import JGeom
import JDate
import os


#############################################################################
# Parametres principaux
#############################################################################

## Participant
Participants = ["ID4_DD"] #ID2_VJ ID3_MG ID4_DD ID1_SP

FieldsToComplete =["NO2","RH","TEMP_C","LAEQ","LCPEAK","LACS","BreathRt","HeartRt","Ventil","Cadence","Activity"]

Root = Path(__file__).parent.parent


#############################################################################
# Fonctions principales
#############################################################################

def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in xrange(0, len(l), n):
        yield l[i:i + n]


def GetDateTime(Str) : 
    Year,Month,Day = Str.split(" ")[0].split("-")
    Hour,Minute,Second = Str.split(" ")[1].split(":")
    return JDate.Jdatetime(Year = Year, Month=Month, Day=Day, Hour=Hour, Minute=Minute, Second=Second)

def SplitAtStops(Layer,Limit=2) : 
    Parts=[]
    ActualPts=[]
    P1 = Layer.GetRow(0)
    if P1["Speed"]<Limit :
        InStopPart=True
    else :
        InStopPart = False
    for Feat in Layer.Iterate(True) :
        #si on est pas dans une phase d'arret et que l'on roule
        if Feat["Speed"]>Limit and InStopPart==False or len(ActualPts)<2 :
            ActualPts.append(Feat)
        #si on est pas dans une phase d'arret  mais qu'on s'arrete, on ouvre une phase d'arret
        elif Feat["Speed"]<Limit and InStopPart==False and len(ActualPts)>1 :
            Parts.append({"Type":"Moving","Pts":ActualPts})
            ActualPts=[]
            InStopPart = True
            ActualPts.append(Feat)
        #si on est dans une phase d'arret  et qu'on est toujours arrete
        elif Feat["Speed"]<Limit and InStopPart==True :
            ActualPts.append(Feat)
        #si on est dans une phase d'arret  et que l'on redemarre
        elif Feat["Speed"]>Limit and InStopPart==True :
            Parts.append({"Type":"Stopped","Pts":ActualPts})
            ActualPts=[]
            InStopPart = False
            ActualPts.append(Feat)
    #sortie de la boucle, enregistrement du dernier layer
    if InStopPart : 
        Parts.append({"Type":"Stopped","Pts":ActualPts})
    else : 
        Parts.append({"Type":"Moving","Pts":ActualPts})
        
    return Parts

def Matching(PointsLayer,PolyLine) : 
    """
    Fonction pour adapter les points le long des lignes
    """
    #File = open(TempFile+"/Logger.txt","w")
    PointsLayer.AttrTable.AddField("ProjDist","float32",-999)
    ###Etape 0 : verifier si la ligne est dans le bon sens
    P1 = PointsLayer.GetRow(0)
   # print("StartPoint : "+P1["Geom"].ExportToWkt())
    A,B = JGeom.GetExtremites(PolyLine)
    if A.Distance(P1["Geom"]) > B.Distance(P1["Geom"]) : 
        PolyLine = JGeom.GeomReverse(PolyLine)
    ###Etape 0.5 : ne garder que le morceau qui nous concerne
    P2 = PointsLayer.GetRow(PointsLayer.FeatureCount-1)
    PolyLine = JGeom.PartOfLine(P1["Geom"],P2["Geom"],PolyLine)
    #print("EndPoint : "+P2["Geom"].ExportToWkt())
    #print("CuttedLine : "+PolyLine.ExportToWkt())
    ###Etape 1 : Segmenter les points en fonction des arrets
    OutputLayer = PointsLayer.CreateEmptyLayer()
    Parts = SplitAtStops(PointsLayer)
    #Etape 2 : specifier les points et leurs coordonnnees
    Points = []
    for Part in Parts : 
        Pts = Part["Pts"]
        if Part["Type"]=="Stopped" : 
            Geom = JGeom.MeanPoint([Feat["Geom"] for Feat in Pts])
            for Feat in Pts : 
                Feat["Geom"] = Geom
                Points.append(Feat)
        else : 
            Points+=Pts
    #Etape 3 : calculer les projections
    ActualProj = 0
    
    PtChunks = chunks(Points,60)
    for ThisChunck in PtChunks : 
        #trouver le 1er point d'ancrage
        P1 = ThisChunck[0]["Geom"]
        Proj1A = JGeom.RevInterpolate(PolyLine,P1)
        Proj1B = JGeom.RevInterpolate(JGeom.GeomReverse(PolyLine),P1)
        if abs(ActualProj-Proj1A)<=abs(ActualProj-(PolyLine.Length()-Proj1B)):
            D1 = Proj1A
        else : 
            D1 = PolyLine.Length()-Proj1B
        ProjP1 = JGeom.Interpolate(PolyLine,D1)
        
        RealLine = JGeom.LineFromPoints([Pt["Geom"] for Pt in ThisChunck])
        RealDist = RealLine.Length()
        if RealDist==0 :
            for Pt in ThisChunck : 
                Pt["ProjDist"] = D1
                OutputLayer.AppendFeat(Pt,ProjP1)
            ActualProj = D1
        else :
            #print("Hey, see me ?")
            #trouver le 2e point d'ancrage
            P2 = ThisChunck[-1]["Geom"]
            Proj2A = JGeom.RevInterpolate(PolyLine,P2)
            Proj2B = PolyLine.Length()-JGeom.RevInterpolate(JGeom.GeomReverse(PolyLine),P2)
            if abs(RealDist-abs(D1-Proj2A))<=abs(RealDist-abs(D1-Proj2B)) : 
                D2 = Proj2A
            else : 
                D2 = Proj2B
            #print("This is D1 : "+str(D1))
            #print("This is D2 : "+str(D2))
            ProjP2 = JGeom.Interpolate(PolyLine,D2)
            ProjLenght = D2-D1
            #print("this is RealDist : "+str(RealDist))
            #print("this is projlength : "+str(ProjLenght))
            PrecPt = ThisChunck[0]["Geom"]
            TotBonus = 0
            for Pt in ThisChunck : 
                Dist = Pt["Geom"].Distance(PrecPt)
                ProjDist = Dist*ProjLenght/RealDist
                #print("    real distance between points :"+str(Dist))
                #print("    Modified distance between points :"+str(ProjDist))
                NewPt = JGeom.Interpolate(PolyLine,D1+ProjDist+TotBonus)
                Pt["ProjDist"] = D1+ProjDist+TotBonus
                #print("   This is a distance :"+str(D1+ProjDist+TotBonus))
                OutputLayer.AppendFeat(Pt,NewPt)
                PrecPt = Pt["Geom"]
                TotBonus+=ProjDist
            
            ActualProj = D2
            #print("Actual Proj :"+str(D2))
                
    #Tout a ete ajoute, on retourner le OutputLayer gentiment
    return OutputLayer



 
def GetLineOID(LayerLine,LayerPt,Tolerance=0.1) : 
    ## fonction d'execution
    def GetOID(Feat,ThisLayer) : 
        ThisLayer = LineLayer.SpatialFilter(Feat["Geom"].Buffer(Tolerance))
        Distances = [(Line["Geom"].Distance(Feat["Geom"]),Line["OID"]) for Line in Lines.Iterate(True)]
        Distances.sort(key = lambda x : x[0] )
        return Distances[0][1]
    LayerPt.AttrTable.AddField("LineID","int32",-999)
    LayerPt.CalculateFieldWithGeom("LineID",GetOID,ThisLayer = LayerLine)
    return LayerPt
            

def BuildSegment(PolyLine,LayerPoint) : 
    AllPts = [Pt for Pt in LayerPoint.Iterate(True)]
    StartPt = AllPts[0]
    PrevTime = GetDateTime(StartPt["DATETIME"])
    LastOID = AllPts[-1]["OID"]
    Segments=[]
    Count = 0
    PrevPt = AllPts[0]
    ## Generation des segments
    for Pt in AllPts : 
        Time2 = GetDateTime(Pt["DATETIME"])
        Ecart = Time2.TimeStamp - PrevTime.TimeStamp
#        CorrectedP1 = JGeom.Interpolate(PolyLine,PrevPt["ProjDist"])
#        CorrectedP2 = JGeom.Interpolate(PolyLine,Pt["ProjDist"])
#        Seg = JGeom.PartOfLine(CorrectedP1,CorrectedP2,PolyLine)
#        Parts.append(Seg)
        if Ecart >= 60 or Pt["OID"]==LastOID : 
            CorrectedP1 = JGeom.Interpolate(PolyLine,PrevPt["ProjDist"])
            CorrectedP2 = JGeom.Interpolate(PolyLine,Pt["ProjDist"])
            Seg = JGeom.PartOfLine(CorrectedP1,CorrectedP2,PolyLine)
            #print("    Building segment : "+str(Count))
            #TotalSeg = JGeom.MergeLinesOrdered(Parts)
            Feat = {"OID":Count,"Start":PrevPt["DATETIME"],"End":Pt["DATETIME"],"StartOID":StartPt["OID"],"EndOID":Pt["OID"],"Geom":Seg}
            Segments.append(Feat)
            Count+=1
            PrevTime = GetDateTime(Pt["DATETIME"])
            PrevPt = Pt
            
    ## Construction des segments
    SegmentsLayer = LayerPoint.CreateEmptyLayer()
    SegmentsLayer.MakeItEmpty()
    SegmentsLayer.AttrTable.AddField("Start","|S50","NONE")
    SegmentsLayer.AttrTable.AddField("StartOID","int32",-999)
    SegmentsLayer.AttrTable.AddField("End","|S50","NONE")
    SegmentsLayer.AttrTable.AddField("EndOID","int32",-999)
    for Seg in Segments : 
        SegmentsLayer.AppendFeat(Seg,Seg["Geom"])
    return SegmentsLayer


def ExtractField(LayerLine,LayerPt,Fields,Tolerance = 0.1) : 
    """
    Fonction permettant d'extraire les valeurs des champs des points depuis la couche osm
    Fields = [(Name,Type,Default)]
    """
    ## fonction d'execution
    def GetValues(Feat,FieldName,LineLayer) : 
        Buff = Feat["Geom"].Buffer(Tolerance)
        Inter = LineLayer.SpatialFilter(Buff)
        if Inter is None :
            raise ValueError("The point must be on a line ...")
        elif Inter.FeatureCount == 1 : 
            LineFeat = Inter.GetRow(0)
            return LineFeat[FieldName]            
        elif Inter.FeatureCount > 1 :
            Dists = [(Line,Line["Geom"].Distance(Feat["Geom"])) for Line in Inter.Iterate(True)]
            Dists.sort(key = lambda x : x[1])
            LineFeat = Dists[0][0]
            return LineFeat[FieldName]
        
    ## Creation des champs
    for Field,Type,Defaut in Fields:
        LayerPt.AttrTable.AddField(Field,Type,Defaut)
        LayerPt.CalculateFieldWithGeom(Field,GetValues,FieldName=Field,LineLayer = LayerLine)
    return LayerPt


def CompleteColumns(LayerPoint,BDPath,Fields) : 
    """
    Fonction permettant d'aller retrouver des donnees dans la BD si jamais elles se seraient perdues en route
    Fields : liste de champs presentees ainsi : []
    """        
    def GetValue(Feat,BD,Field) : 
        Time = JDate.DateTimeFromText(Feat["DATETIME"],Format=1)
        TimeStamp = Time.timestamp()
        Values = BD.Request(TimeStamp)
        return Values[Field]


    BD = PollutionBD(BDPath,Config)
    for Field in Fields : 
        LayerPoint.AttrTable.CalculateField(Field,GetValue,BD=BD,Field=Field)
    return LayerPoint

#############################################################################
# Execution
#############################################################################

Avoid = []
TODO = []

for Participant in Participants : 
    TempFile = Root.joinpath("TEMP/"+Participant+"/")
    ## dans l'ideal les points matches par OSRM
    FolderPts = Root.joinpath("__Frames/"+Participant+"/")
    
    ## Le dossier avec les lignes extraites manuellement
    FolderLine = Root.joinpath("__PolyLines/"+Participant+"/")
    FolderSelectedLines = Root.joinpath("__ExportedLines/"+Participant+"/")
    SortiePt = Root.joinpath("__MatchedPoints/"+Participant+"/")
    if os.path.isdir(str(SortiePt))==False :
        os.mkdir(str(SortiePt))
    SortieSeg = Root.joinpath("__Segments/"+Participant+"/")
    if os.path.isdir(str(SortieSeg))==False :
        os.mkdir(str(SortieSeg))

    for ShpPts in FolderPts.files("*.shp") : 
        Name = ShpPts.name.split(".")[0]
        if Name not in Avoid :
        #if Name in TODO :
            print("___Working on "+Name)
            ##Chargement des differents Layer
            ShpLine = FolderLine.joinpath(Name+"_Polyline.shp")
            PointsLayer = JV.JFastLayer(ShpPts)
            PointsLayer.Initialize(ID="OID",GeomIndex=True)
            PointsLayer.AttrTable.Sort("OID")
            PointsLayer.Reproj(3857)
            LineLayer = JV.JFastLayer(ShpLine)
            LineLayer.Initialize(ID="OID",GeomIndex=False)
            PolyLine = LineLayer.Geoms.values()[0]
            SelectedLines = JV.JFastLayer(FolderSelectedLines.joinpath(Name+".shp"))
            SelectedLines.Initialize(ID="OID",GeomIndex=True,Params={"Decode":"ISO-8859-1"})
            SelectedLines.Reproj(3857)
            print("        matching the points")
            ##realisation du matching
            Matched = Matching(PointsLayer,PolyLine)
            Matched.AttrTable.UpdateID()
            Matched.UpdateTree()
            
            #rajout des valeurs qui auraient pu etre manquante
            print("        completing the fields that could miss")
            BDPath = str(Root.parent).replace("\\","/")+"/A)_FieldData/"+Participant+"/Pollution.jdb"
            Matched2 = CompleteColumns(Matched,BDPath,FieldsToComplete)
            
            Matched.Save(str(TempFile)+"LastMatched.shp")
            Matched.Save(str(SortiePt)+Name+'.shp')
            ##calcul des champs lines OID
    #        Matched2 = GetLineOID(SelectedLines,Matched,Tolerance=20)
    #        Matched2.Save(str(SortiePt)+Name+'.shp')
            ##creation des segments
            print("        building the segments")
            Segments = BuildSegment(PolyLine,Matched)
            Segments.Save(str(SortieSeg)+Name+'.shp')