# -*- coding: utf-8 -*-
"""
Created on Wed Aug  1 10:31:24 2018

@author: gelbj
"""

#############################################################################
# Import des packages
#############################################################################
import os

#Link = "C:/Users/GelbJ/Desktop/ANACONDA1/Library/share/gdal/"
#os.environ["GDAL_DATA"] = Link

import sys
sys.path.append("G:/Python/___JBasics")
from path import Path
from osgeo import ogr
from JQgis import JVectorLayer as JV
import JGeom
import JTopology
import copy
import numpy as np
import traceback

#############################################################################
# Parametres principaux
#############################################################################

Participants = ["ID1_SP"] #ID2_VJ ID3_MG ID4_DD ID1_SP
GlobChunk = 5
DistSplit = 200
TestDeep=3

def LineDistance(Line,Point) : 
    ShLine = JGeom.ToShapely(Line)
    ShPoint = JGeom.ToShapely(Point)
    Inter = ShLine.project(ShPoint)
    NewPoint = ShLine.interpolate(Inter)
    return NewPoint.distance(ShPoint)

def CountNones(Feat) : 
    Count = 0
    for key,value in Feat.items() : 
        if value=="NONE" or value=="None" : 
            Count+=1
    return Count

def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in xrange(0, len(l), n):
        yield l[i:i + n]

#def SplitOnLastPoint(Line,Points,Start,Tolerance=0.1) : 
#    A,B = JGeom.GetExtremites(Line)
#    if Start.Distance(A)>Tolerance : 
#        Line = JGeom.GeomReverse(Line)
#    ShPoints = [JGeom.ToShapely(Pt) for Pt in Points]
#    ShLine = JGeom.ToShapely(Line)
#    Distances = [(Pt,ShLine.project(Pt)) for Pt in ShPoints]
#    Distances.sort(key=lambda x : x[1])
#    LastPt = Distances[-1][0]
#    Pt = JGeom.ToOgr(LastPt)
#    Part1,Part2 = JGeom.SplitOnIntersectV3(Line,[Pt])
#    if Part1.Distance(Start)<=Part2.Distance(Start) : 
#        return Part1
#    else : 
#        return Part2
    
def SplitOnLastPoint(Line,LayerPoint,Start,Tolerance=0.1) : 
    ##Mettre la ligne dans le bon sens
    A,B = JGeom.GetExtremites(Line)
    if Start.Distance(A)>Tolerance : 
        Line = JGeom.GeomReverse(Line)
    ##chercher tous les points a moins de 15m
    Pts = LayerPoint.SpatialFilter(Line.Buffer(20))
    if Pts is None : 
        #NB : cette ligne ne fait pas vraiment partie de notre polyligne
        return JGeom.LineFromPoints([Start,Start])
    ShPoints = [JGeom.ToShapely(Pt) for Pt in Pts.Geoms.values()]
    ShLine = JGeom.ToShapely(Line)
    Distances = [(Pt,ShLine.project(Pt)) for Pt in ShPoints]
    Distances.sort(key=lambda x : x[1])
    LastPt = Distances[-1][0]
    Pt = JGeom.ToOgr(LastPt)
    Parts = JGeom.SplitOnIntersectV3(Line,[Pt])
    if len(Parts)==1 : 
        return Parts[0]
    elif len(Parts)==0 : 
        raise ValueError("there is an error with the splitting here !! (line 89)")
    elif len(Parts)>2 : 
        print((Pt.ExportToWkt(),Distances[-1][1]))
        for element in Parts : 
            print("Part : "+element.ExportToWkt())
        print(Line.ExportToWkt())
        raise ValueError("there is to many parts...")
    else : 
        Part1,Part2 = Parts
        if Part1.Distance(Start)<=Part2.Distance(Start) : 
            return Part1
        else : 
            return Part2
    
def DbInterCheck(ActualLine,ActualID,LayerLines,Tolerance = 0.1) : 
    Buff = ActualLine.Buffer(Tolerance)
    Inters = LayerLines.SpatialFilter(Buff)
    InterA = False
    InterB = False
    A,B = JGeom.GetExtremites(ActualLine)
    for Feat in Inters.Iterate(True) : 
        if Feat["OID"] != ActualID : 
            C,D = JGeom.GetExtremites(Feat["Geom"])
            if C.Distance(A)<Tolerance : 
                InterA = True
            if C.Distance(B)<Tolerance : 
                InterB = True
            if D.Distance(A)<Tolerance : 
                InterA = True
            if D.Distance(B)<Tolerance : 
                InterB = True
            if InterA and InterB : 
                return True
    else : 
        return False
    
#############################################################################
# Fonction principales
#############################################################################
def CleanLines(LayerLine) :     
    #Etape 0 : decouper les saloperies de rings
    Lines = [Feat["Geom"] for Feat in LayerLine.Iterate(True)]
    NewLines = JTopology.SplitRings(Lines,0.1)
    NewLayer0 = LayerLine.CreateEmptyLayer()
    e=0
    print("How many lines after splitting rings : "+str(len(NewLines)))
    for Feat,Lines in zip(LayerLine.Iterate(True),NewLines) : 
        for Line in Lines : 
            Feat["OID"] = e
            e+=1
            NewLayer0.AppendFeat(Feat,Line)
    NewLayer0.Save(str(TempFile.replace("\\","/")+"CleaningStep0.shp"))
    #Etape1 : splitter en section de 100m
    NewLayer1 = NewLayer0.CreateEmptyLayer()
    e=0
    for Feat in NewLayer0.Iterate(True) : 
        Lines = JGeom.SplitLineByDist(Feat["Geom"],DistSplit,Min=5)
        for Line in Lines : 
            Feat["OID"] = e
            NewLayer1.AppendFeat(Feat,Line)
            e+=1
    NewLayer1.Save(str(TempFile.replace("\\","/")+"CleaningStep1.shp"))
    
    #Etape 2 : nettoyer les intersections franches
    Lines2 = [Feat["Geom"] for Feat in NewLayer1.Iterate(True)]
    NewLines = JTopology.CorrectCrossedLine(Lines2)
    NewLayer2 = LayerLine.CreateEmptyLayer()
    e=0
    for Feat,Lines in zip(NewLayer1.Iterate(True),NewLines) : 
        for Line in Lines : 
            Feat["OID"] = e
            e+=1
            NewLayer2.AppendFeat(Feat,Line)
    
    #print(NewLayer.FeatureCount)
    #Etape 3 : nettoyer les intersections touchees
    NewLayer2.Save(str(TempFile.replace("\\","/")+"CleaningStep2.shp"))
    Lines = NewLayer2.Geoms.values()
#    for element in Lines : 
#        print(element.ExportToWkt())
    NewLines = JTopology.CorrectTouchedLine(Lines)
    NewLayer3 = LayerLine.CreateEmptyLayer()
    e=0
    for Feat,Lines in zip(NewLayer2.Iterate(True),NewLines) : 
        for Line in Lines : 
            Feat["OID"] = e
            e+=1
            NewLayer3.AppendFeat(Feat,Line)
    NewLayer3.Save(str(TempFile.replace("\\","/")+"CleaningStep3.shp"))
    #Etape complementaire, ajuster la coordonnees
    NewLayer3.RoundCoordinates(3)
    
    #Etape 4 reconnecter les lignes tres proches
    NewLines2 = [Feat["Geom"] for Feat in NewLayer3.Iterate(True)]
    print("Number of Feature Before correction : "+str(len(NewLines2)))
    NewLines3 = JTopology.ConnectVeryCloseLines(NewLines2,Tolerance=1)
    print("Number of Feature After correction : "+str(len(NewLines3)))
    NewLayer4 = LayerLine.CreateEmptyLayer()
    e=0
    for Feat,Line in zip(NewLayer3.Iterate(True),NewLines3) : 
        if type(Line)==list : 
            for SubLine in Line : 
                Feat["OID"] = e
                e+=1
                NewLayer4.AppendFeat(Feat,SubLine)
        else :
            Feat["OID"] = e
            e+=1
            NewLayer4.AppendFeat(Feat,Line)
    NewLayer4.Save(str(TempFile.replace("\\","/")+"CleaningStep4.shp"))
    
    
    #Etape finale : retirer les lignes identiques
    Lines = [Feat["Geom"] for Feat in NewLayer4.Iterate(True)]
    Feats =  [Feat for Feat in NewLayer4.Iterate(True)]
    Problems = JTopology.FindSimilarLines(Lines,Tolerance=0.1)
    if len(Problems) == 0 :
        NextLayer = NewLayer4
    else : 
        print("Hell we have a problem with identical geometries !!")
        print(Problems)
        ToDelete = []
        for A,B in Problems : 
            FeatA = Feats[A]
            FeatB = Feats[B]
            if CountNones(FeatA)>CountNones(FeatB) : 
               ToDelete.append(FeatA["OID"])
            else : 
                ToDelete.append(FeatB["OID"])
        print("Features to delete for duplication : "+str(ToDelete))
        NextLayer = NewLayer4.RemoveFeats(ToDelete)
        
    print("deleting the covered features")
    Lines = [Feat["Geom"] for Feat in NextLayer.Iterate(True)]
    Feats =  [Feat for Feat in NextLayer.Iterate(True)]
    Problems2 = JTopology.FindCoveredGeoms(Lines)
    if len(Problems2)>0 : 
        print("We have a problem with covered Features !!!!!!!!")
    ToDelete = []
    for ID in Problems2 : 
        Feat = Feats[ID]
        ToDelete.append(Feat["OID"])
    NewLayer5 = NextLayer.RemoveFeats(ToDelete)
    NewLayer5.Save(str(TempFile.replace("\\","/")+"CleaningStep5.shp"))
    return NewLayer5
    

def IdentifyPath(LayerLines,LayerPoints,Tolerance = 0.1) : 
    """
    Objectif retirer les elements superflus des lignes structurees
    Element superflus : ont une densite de ligne inferieure a X pt par m
    """
    ###Etape 0 : touver la ligne de depart et d'arrivee
    ## Etape 1 : Trouver la ligne de depart
    AllPts = [Feat["Geom"] for Feat in LayerPoints.Iterate(True)]
    PtsStart = JGeom.MeanPoint(AllPts[0:5])
    PtsEnds = JGeom.MeanPoint(AllPts[len(AllPts)-6:len(AllPts)-1])
    
    DistancesStart = [(Feat,Feat["Geom"].Distance(PtsStart)) for Feat in LayerLines.Iterate(True)]
    DistancesEnd = [(Feat,Feat["Geom"].Distance(PtsEnds)) for Feat in LayerLines.Iterate(True)]
    
    DistancesStart.sort(key = lambda x : x[1])
    DistancesEnd.sort(key = lambda x : x[1])
    
    StartFeat,Dist = DistancesStart[0]
    EndFeat,Dist = DistancesEnd[0] 
    print("First Line is : "+str(StartFeat["OID"]))
    print("Last Line is : "+str(EndFeat["OID"]))
    
    def KeepMe(Feat) : 
        if Feat["OID"] == StartFeat["OID"] or Feat["OID"] == EndFeat["OID"] : 
            return 1
        else : 
            return 0
        
    LayerLines.AttrTable.AddField("Start_End","int32",0)
    LayerLines.CalculateFieldWithGeom("Start_End",KeepMe)
    ###Etape 1 : calculer la densite de pts
    LayerLines.AttrTable.AddField("DensPts","float32",-999)
    def Func(Feat,LayerPts) : 
        Pts = LayerPts.SpatialFilter(Feat["Geom"].Buffer(5))
        if Pts is None : 
            return 0
        else :
            return float(Pts.FeatureCount) / Feat["Geom"].Length()
    LayerLines.CalculateFieldWithGeom("DensPts",Func,LayerPts = LayerPoints)
    #calculer si les lignes sont doubles intersectees
    def DoubleInter(Feat,LinesLayer) : 
        A,B = JGeom.GetExtremites(Feat["Geom"])
        Ai = False
        Bi = False
        for NeighboursID in LinesLayer.Contiguity[Feat[LinesLayer.ID]] : 
            F2 = LinesLayer.NiceFeat(LinesLayer[NeighboursID])
            G = F2["Geom"]
            if G.Distance(A)<=Tolerance : 
                Ai=True
            if G.Distance(B)<=Tolerance : 
                Bi = True
        Values = [Ai,Bi]
        #print(Values)
        return Values.count(True)
    
    ###calculer la matrice de contiguite
    LayerLines.BuildContiguity(Tolerance = Tolerance)
    LayerLines.AttrTable.AddField("DbInter","int",0)
    LayerLines.CalculateFieldWithGeom("DbInter",DoubleInter, LinesLayer = LayerLines)
    #ne garder les lignes que si la densite est superieure a : 0.1 pt/m et qui ne sont pas double intersectees
    Keeped = LayerLines.AttributeFilter("(DensPts >= 0.1) OR (DbInter>=2) OR (Start_End==1)")
    return Keeped





def WalkingMan(LayerLines,LayerPoints,Chunck=5,Tolerance=0.1,TestDeep=3) : 
    """
    Objectif : Ordonner les lignes selon les points pour former la polyligne
    finale
    """
    TolerateDist=100
    #Etape 0 : resetter les OID des lignes
    global Count
    Count = 0
    def RefineOID(Feat) : 
        global Count
        Value = Count
        Count+=1
        return Value
    LayerLines.AttrTable.CalculateField("OID",RefineOID)
    LayerLines.AttrTable.UpdateID()
    LayerLines.UpdateTree()
    LayerLines.BuildContiguity(Tolerance = Tolerance)
    LayerLines.Save(str(TempFile.replace("\\","/")+"CleanLines3.shp"))
    
    
    AllPts = [Feat["Geom"] for Feat in LayerPoints.Iterate(True)]
    PtsStart = JGeom.MeanPoint(AllPts[0:5])
    print(PtsStart.ExportToWkt())
    PtsEnds = JGeom.MeanPoint(AllPts[len(AllPts)-6:len(AllPts)-1])
    print(PtsEnds.ExportToWkt())
    
    DistancesStart = [(Feat,Feat["Geom"].Distance(PtsStart)) for Feat in LayerLines.Iterate(True)]
    DistancesEnd = [(Feat,Feat["Geom"].Distance(PtsEnds)) for Feat in LayerLines.Iterate(True)]
    
    DistancesStart.sort(key = lambda x : x[1])
    DistancesEnd.sort(key = lambda x : x[1])
    print(DistancesStart[0:5])
    print(DistancesEnd[0:5])
    
    StartFeat,Dist = DistancesStart[0]
    EndFeat,Dist = DistancesEnd[0] 
    print("First Line is : "+str(StartFeat["OID"]))
    print(StartFeat["Geom"].ExportToWkt())
    print("Last Line is : "+str(EndFeat["OID"]))
    print(EndFeat["Geom"].ExportToWkt())

    ActualLine = StartFeat["Geom"]
    ActualID = StartFeat["OID"]
    
    def CheckNeighbours(Pts,ThisID) :
        Possibles = {ID : LayerLines.Geoms[ID] for ID in LayerLines.Contiguity[ThisID]}
        Possibles[ThisID] = LayerLines.Geoms[ThisID]
        Distances = [(key,np.sum([G.Distance(Pt) for Pt in Pts])) for key,G in Possibles.items()]
        Distances.sort(key=lambda x : x[1])
        #ne renvoyer que les elements probables
        return Distances
    
    #Algorithme d'analyse des possibilites
    #fonctionnement : test d'hypothese : a chaque intersection, verfier que le chemin peut se poursuivre
    #Iterer sur les points par chunk et verifier nos hypotheses
    PtsChunks = list(chunks(AllPts,Chunck))
    NewHypothesis = [{"Path":[(ActualID,ActualLine)],"i":0,"Cost":0}]
    ValidHypothesis = []
    Continue = True
    MaxHypothesis = 10
        
    
    while len(NewHypothesis)>0 : 
        #Step1 : se preparer a recevoir les prochaines hypotheses
        OldHypothesis = NewHypothesis
        NewHypothesis = []
        KeepedPath = []
        #garder seulement les X hypotheses les plus pertinentes
        if len(OldHypothesis)>MaxHypothesis :
            Costs = sorted(OldHypothesis, key = lambda x: (x["Cost"], len(x["Path"])))
            OldHypothesis = Costs[0:MaxHypothesis]
        print("Hypothesis to test : "+str(len(OldHypothesis)))
        for Hypothesis in OldHypothesis : 
            print("This is an hypothesis : "+str([El[0] for El in Hypothesis["Path"]]))
            #recuperer les points !
            Pts = PtsChunks[Hypothesis["i"]]
            LastID = Hypothesis["Path"][-1][0]
            #recuperer les voisins !
            Neihgbours = CheckNeighbours(Pts,LastID)
            #garder un nombre raisonnable d'hypothese
            if len(Neihgbours)>TestDeep : 
                Neihgbours = Neihgbours[0:TestDeep]
            #valider les hypotheses
            for ID,Dist in Neihgbours : 
                #si la distance est valide, on garde l'hypothese
                ToKeep =  Dist <= TolerateDist*len(Pts)
                ThisHypothesis = copy.deepcopy(Hypothesis)
                if ToKeep : 
                    ThisHypothesis["i"]+=1
                    ThisHypothesis["Cost"]+=Dist
                    #on verifie qu'il ne s'agit pas de la meme ligne
                    if ID != LastID : 
                        #c'est une nouvelle ligne ! proceder a la mise a jour
                        ThisHypothesis["Path"].append((ID,LayerLines.Geoms[ID]))
                    #On a encore du chemin a faire !
                    if ThisHypothesis["i"]<len(PtsChunks) :
                        StringPath = str([El[0] for El in ThisHypothesis["Path"]])
                        if StringPath not in KeepedPath : 
                            NewHypothesis.append(ThisHypothesis)
                            KeepedPath.append(StringPath)
                    #cette hypothese a abouti ! on la garde
                    elif ID == EndFeat["OID"] and  abs(ThisHypothesis["i"]-len(PtsChunks))<=2 : 
                        ValidHypothesis.append(ThisHypothesis)
            
    #le tour des hypotheses est termine, il faut garder la meilleure
    Costs = []
    if len(ValidHypothesis)==0 : 
        for element in OldHypothesis : 
            print("Shit ! No valid hypothesis found....")
            print("This is one of the last hypothesis : "+str([El[0] for El in element["Path"]]))
        raise ValueError("No valid hypothesis at the end of the process.....")
    for Hypothesis in ValidHypothesis : 
        MultiLine = JGeom.MultiGeom([El[1] for El in Hypothesis["Path"]])
        Distances = np.sum([MultiLine.Distance(Pt) for Pt in AllPts])
        Costs.append((Hypothesis,Distances,len(Hypothesis["Path"])))
    Costs = sorted(Costs, key = lambda x: (x[1], x[2]))
    Best = Costs[0][0]
    print("This is the best Hypothesis : "+str([El[0] for El in Best["Path"]]))
    return Best["Path"]
        
    

def BuildPolyLine2(LayerLines,LayerPoints,Chunk = 5,Tolerance=0.1,TestDeep=4) : 
    """
    Objectif : Ordonner les lignes selon les points pour former la polyligne
    finale
    Version utilisant le WalkingMan
    """   
    AllPts = [Feat["Geom"] for Feat in LayerPoints.Iterate(True)]
    PtsStart = AllPts[0]
    PtsEnds = AllPts[-1]
    BestPath = WalkingMan(LayerLines=LayerLines,LayerPoints=LayerPoints,Chunck=Chunk,Tolerance=Tolerance,TestDeep=TestDeep)
    ##trouver le point d'entree et la sortie du premier segment
    Id1,Seg1 = BestPath[0]
    A,B = JGeom.GetExtremites(Seg1)
    Id2,Seg2 = BestPath[1]
    C,D = JGeom.GetExtremites(Seg2)
    if min([A.Distance(C),A.Distance(D)])>min([B.Distance(C),B.Distance(D)]) : 
        Entrance = A
        Out = B
    else : 
        Entrance = B
        Out = A
        Seg1 = JGeom.GeomReverse(Seg1)
    
    FinalLines = [Seg1]
    IDList = [Id1]
    BestPath.pop(0)
    PrevID = None
    e=0
    for ID,Line in BestPath : 
        #check if it is connected to Out
        A,B = JGeom.GetExtremites(Line)
        if min([A.Distance(Entrance),B.Distance(Entrance)])>min([A.Distance(Out),B.Distance(Out)]) :
            #on est bon, cette ligne est bien connectee a la sortie de la precedente
            #il faut maintenant trouver quel bout est connecte
            if A.Distance(Out)<B.Distance(Out) : 
                #on est dans le bon sens, il suffit d'ajouter cette ligne au paquet
                IDList.append(ID)
                FinalLines.append(Line)
            else : 
                #la ligne est dans le mauvais sens... il faut l'inverser
                Line = JGeom.GeomReverse(Line)
                IDList.append(ID)
                FinalLines.append(Line)
        else : 
            #Ah ! il semblerait que l<on soit connecte a l'entree de la ligne, il s'agit donc d'un demi tour
            IDList.append(IDList[-1])
            PrevLine = FinalLines.pop(-1)
            Part = SplitOnLastPoint(PrevLine,LayerPoints,Entrance)
            #verifions si la longueur de se demi tour depasse 15m
            Reversed = JGeom.GeomReverse(Part)
            if Part.Length()>15 :
                FinalLines.append(Part)
                FinalLines.append(Reversed)
            Entrance,Out = JGeom.GetExtremites(Reversed)
            #il faut maintenant trouver quel bout est connecte
            if A.Distance(Out)<B.Distance(Out) : 
                #on est dans le bon sens, il suffit d'ajouter cette ligne au paquet
                IDList.append(ID)
                FinalLines.append(Line)
            else : 
                #la ligne est dans le mauvais sens... il faut l'inverser
                Line = JGeom.GeomReverse(Line)
                IDList.append(ID)
                FinalLines.append(Line)
        Entrance,Out = JGeom.GetExtremites(FinalLines[-1])
            
    print("This is the list to make the polyline : "+str(IDList))
    print("Number of element in IDList : "+str(len(IDList)))
    print("Number of element in LineList : "+str(len(FinalLines)))
    PolyLine = JGeom.MergeLinesOrdered(FinalLines)
	#OkPolyLine = JGeom.PartOfLine(PtsStart,PtsEnds,PolyLine)
    return PolyLine,FinalLines        
        

    
#def BuildPolyLine2(LayerLines,LayerPoints,Chunk = 5,Tolerance=0.1) : 
#    """
#    Objectif : Ordonner les lignes selon les points pour former la polyligne
#    finale
#    """
#    #Etape 0 : resetter les OID des lignes
#    global Count
#    Count = 0
#    def RefineOID(Feat) : 
#        global Count
#        Value = Count
#        Count+=1
#        return Value
#    LayerLines.AttrTable.CalculateField("OID",RefineOID)
#    LayerLines.AttrTable.UpdateID()
#    LayerLine.UpdateTree()
#    
#    LayerLines.BuildContiguity(Tolerance = Tolerance)
#    LayerLines.Save(str(TempFile.replace("\\","/")+"CleanLines3.shp"))
#    
#    AllPts = [Feat["Geom"] for Feat in LayerPoints.Iterate(True)]
#    PtsStart = JGeom.MeanPoint(AllPts[0:5])
#    PtsEnds = JGeom.MeanPoint(AllPts[len(AllPts)-6:len(AllPts)-1])
#    
#    DistancesStart = [(Feat,Feat["Geom"].Distance(PtsStart)) for Feat in LayerLines.Iterate(True)]
#    DistancesEnd = [(Feat,Feat["Geom"].Distance(PtsEnds)) for Feat in LayerLines.Iterate(True)]
#    
#    DistancesStart.sort(key = lambda x : x[1])
#    DistancesEnd.sort(key = lambda x : x[1])
#    
#    StartFeat,Dist = DistancesStart[0]
#    EndFeat,Dist = DistancesEnd[0] 
#    print("First Line is : "+str(StartFeat["OID"]))
#    print("Last Line is : "+str(EndFeat["OID"]))
#
#
#    #LayerPoints = LayerPoints.AttributeFilter("SPEED > 2")
#    ActualLine = StartFeat["Geom"]
#    ActualID = StartFeat["OID"]
#    Entrance = JGeom.OgrPoint((0,0))
#    Out = JGeom.OgrPoint((0,0))
#    #print(Possibles)
#    ### Etape 2 : iterer sur les points par batch de 5
#    FinalLines = [ActualLine]
#    IDList = [ActualID]
#    e = 0
#    Continue=True
#    while Continue : 
#        ## A : realiser un Chunk de X points (attention a sortir de la boucle a la fin)
#        if e+Chunk < LayerPoints.FeatureCount : 
#            Pts = [AllPts[e+i] for i in range(Chunk)]
#        else : 
#            Pts=[]
#            for i in range(Chunk) : 
#                if e+i<LayerPoints.FeatureCount :
#                    P = AllPts[e+i]
#
#                    Pts.append(P)
#                else : 
#                    break
#            Continue=False
#        e+=Chunk
#        ## B trouver lequel des possibles est le plus proche de nos points
#        Possibles = {ID : LayerLines.Geoms[ID] for ID in LayerLines.Contiguity[ActualID]}
#        Possibles[ActualID] = ActualLine
#        Distances = [(key,np.sum([G.Distance(Pt) for Pt in Pts])) for key,G in Possibles.items()]
#        Distances.sort(key=lambda x : x[1])
#        Nearest = Distances[0][0]
#        ## C.a : c'est toujours la meme ligne, on ne se pose pas de question
#        if Nearest==ActualID : 
#            pass
#        else : 
#        ## C.b on a change de ligne
#        ## il faut trouver le out et verifier qu'il est different de Entrance
#            P1,P2 = JGeom.GetExtremites(ActualLine)
#            #Sum1 = np.sum([P1.Distance(Pt) for Pt in Pts])
#            #Sum2 = np.sum([P2.Distance(Pt) for Pt in Pts])
#            Sum1 = P1.Distance(Pts[-1])
#            Sum2 = P2.Distance(Pts[-1])
#            if Sum1>Sum2 : 
#                Out = P2
#                NA = P1
#            else :
#                Out = P1
#                NA = P2
#            #si la sortie est differente de l'entree, tout va bien
#            if Out.Distance(Entrance)>Tolerance : 
#                ActualID = Nearest
#                ActualLine = LayerLines.Geoms[Nearest]
#                FinalLines.append(ActualLine)
#                IDList.append(ActualID)
#                Entrance = Out
#            #si la sortie est identique a l'entree, il faut faire quelque chose
#            else :
#                print("Alert ! we have a come back : "+str(ActualID))
#                A,B = JGeom.GetExtremites(LayerLines.Geoms[Nearest])
#                if A.Distance(Entrance)>B.Distance(Entrance) : 
#                    NewEntrance = B
#                else : 
#                    NewEntrance = A
#                if NewEntrance.Distance(NA)<Tolerance :
#                #just check if the connexion is right with the next line
#                    ActualID = Nearest
#                    ActualLine = LayerLines.Geoms[Nearest]
#                    FinalLines.append(ActualLine)
#                    IDList.append(ActualID)
#                    Entrance = NewEntrance
#                    
#                else :
#                    #second check : does the 3 next points have the same tendance ?
#                    print("We have to do another check")
#                    MorePoints = [AllPts[e-(2*Chunk)+y] for y in range(3)]
#                    print("Entrance : "+Entrance.ExportToWkt())
#                    print('Other Points : ')
#                    for titi in MorePoints : 
#                        print('   '+titi.ExportToWkt())
#                    Sum1 = np.mean([P1.Distance(pp) for pp in MorePoints])
#                    Sum2 = np.mean([P2.Distance(pp) for pp in MorePoints])
#                    if Sum1>Sum2 : 
#                        Out = P2
#                    else :
#                        Out = P1
#                    print("Out : "+Out.ExportToWkt())
#                    if Out.Distance(Entrance)>Tolerance : 
#                        print("The Other check was good !")
#                        ActualID = Nearest
#                        ActualLine = LayerLines.Geoms[Nearest]
#                        FinalLines.append(ActualLine)
#                        IDList.append(ActualID)
#                        Entrance = Out
#                    else :
#                        #NB 1) il faut retirer la ligne d'avant
#                        PrevLine = FinalLines.pop(-1)
#                        #NB 2) il faut couper cette ligne la ou est le dernier point
#                        #Part = SplitOnLastPoint(PrevLine,Pts,Entrance,Tolerance=Tolerance)
#                        Part = SplitOnLastPoint(PrevLine,LayerPoints,Entrance,Tolerance=Tolerance)
#                        #NB 3) il faut la rajouter au FinalLines
#                        FinalLines.append(Part)
#                        ActualLine = Part
#                        #NB 4) il faut l'inverser et l'ajouter une deuxieme fois
#                        FinalLines.append(JGeom.GeomReverse(ActualLine))
#                        ActualID = Nearest
#                        ActualLine = LayerLines.Geoms[Nearest]
#                        FinalLines.append(ActualLine)
#                        IDList.append(ActualID)
#                        Entrance = Out
#            #enfin, si on a atteint la derniere ligne, il faut s'arreter
#            if EndFeat["OID"] == ActualID : 
#                Continue = False
#    
#    if IDList[-1]!= EndFeat["OID"] :
#        FinalLines.append(EndFeat["Geom"])
#        IDList.append(EndFeat["OID"])
#    print("This is the list to make the polyline : "+str(IDList))
#    print("Number of element in IDList : "+str(len(IDList)))
#    print("Number of element in LineList : "+str(len(FinalLines)))
#    PolyLine = JGeom.MergeLinesOrdered(FinalLines)
#    return PolyLine,FinalLines
        
    

#############################################################################
# Execution
#############################################################################

Avoid = []
TODO = ["ID1_SP_2018-06-08_TRAJET08"]

Root = Path(__file__).parent.parent
TempFile = Root.joinpath("TEMP/")
if os.path.isdir(str(TempFile))==False : 
    os.mkdir(str(TempFile))

## dans l'ideal les points matches par OSRM

for Participant in Participants :
    TempFile = Root.joinpath("TEMP/"+Participant+"/")
    if os.path.isdir(str(TempFile))==False : 
        os.mkdir(str(TempFile))
    #create participant folder if not existing
    PartFile = Root.joinpath("__PolyLines/"+Participant)
    if os.path.isdir(str(PartFile))==False : 
        os.mkdir(str(PartFile))
    FolderPts = Root.joinpath("__Frames/"+Participant)
    
    ## Le dossier avec les lignes extraites manuellement
    FolderLine = Root.joinpath("__ExportedLines/"+Participant)
    Sortie = Root.joinpath("__PolyLines/"+Participant)
    ValidateFile = Root.joinpath("__PolyLines/"+Participant+"/Validate.csv")
    
    
    CSV = open(ValidateFile,"w")
    CSV.write("FileName;FirstPoint;LastPoint;MeanPoint\n")
    for ShpLine in FolderLine.files("*.shp") : 
        #####
        # Ouverture, reprojection et applatissement des layers
        #####
        Name = ShpLine.name.split(".")[0]
        #if Name not in Avoid :
        if Name in TODO :
            print("Working on : "+Name)
            ShpPt  = FolderPts.joinpath(ShpLine.name)
            LayerLine = JV.JFastLayer(ShpLine)
            LayerLine.Initialize(ID="OID",GeomIndex=True,Params={"Decode":'ISO-8859-1'})
            LayerLine.Reproj(3857)
            LayerLine.Flatten()
            ##faisons un petit filtre pour supprimer d'eventuelle saloperie !!
            LayerLine = LayerLine.AttributeFilter("(np.char.count(other_tags,'cables')==0)")
            
            
            LayerPt = JV.JFastLayer(ShpPt)
            LayerPt.Initialize(ID="OID",GeomIndex=True)
            LayerPt.Reproj(3857)
            LayerPt.Flatten()
            
            #####
            #Applicationd des algorithmes
            #####
            print("____Operation 1")
            CleanedLine = CleanLines(LayerLine)
            print("____Operation 3")
            CleanedLine.Flatten()
            print("____Operation 4")
            CleanedLine.AttrTable.UpdateID()
            CleanedLine.UpdateTree()
            CleanedLine.Save(str(TempFile.replace("\\","/")+"CleanLines.shp"))
            ReloadedLines = JV.JFastLayer(str(TempFile.replace("\\","/")+"CleanLines.shp"))
            ReloadedLines.Initialize(ID="OID",GeomIndex=True,Params={"Decode":"utf-8"})
            print("____Operation 5")
            CleanedLine2=IdentifyPath(ReloadedLines,LayerPt,Tolerance = 0.2)
            CleanedLine2.Save(str(TempFile.replace("\\","/")+"CleanLines2.shp"))
            ReloadedLines2 = JV.JFastLayer(str(TempFile.replace("\\","/")+"CleanLines2.shp"))
            ReloadedLines2.Initialize(ID="OID",GeomIndex=True,Params={"Decode":"utf-8"})
            try :
                print("____Operation 6")
                Poly = BuildPolyLine2(ReloadedLines2,LayerPt,Chunk = GlobChunk,Tolerance=0.1,TestDeep=4)
                #####
                #Creation des layers de sortie
                #####
                L1 = LayerLine.CreateEmptyLayer()
                L1.MakeItEmpty()
                L1.AppendFeat({"OID":1},Poly[0])
                L1.Save(Sortie+"/"+Name+"_Polyline.shp")
                CleanedLine.Save(Sortie+"/"+ShpPt.name)
                L2 = LayerLine.CreateEmptyLayer()
                L2.MakeItEmpty()
                for e,Line in enumerate(Poly[1]) : 
                    L2.AppendFeat({"OID":e},Line)
                L2.Save(str(TempFile.replace("\\","/")+Name+"_Selection.shp"))
                
                e+=1
                ################
                #Etape de Validation
                ################
                ## Tester la distance avec le premier point
                AllDistances=[Feat["Geom"].Distance(Poly[0]) for Feat in LayerPt.Iterate(True)]
                DistFirst = AllDistances[0]
                DistLast = AllDistances[-1]
                if DistFirst> 12 : 
                    Txt1 = "Probably Wrong"
                else : 
                    Txt1 = "RAS"
                if DistLast> 12 : 
                    Txt2 = "Probably Wrong"
                else : 
                    Txt2 = "RAS"
                if np.mean(AllDistances)>8 : 
                    Txt3 = "Probably Wrong"
                else : 
                    Txt3 = "RAS"
            except Exception as e  : 
                print("Error when building the polyline !!")
                print(str(e))
                print(traceback.format_exc())
                Txt1 = "Error"
                Txt2 = "Error"
                Txt3 = "Error"
            CSV.write(";".join([ShpPt.name,Txt1,Txt2,Txt3])+"\n")
    
    CSV.close()

#LayerLine = JV.JFastLayer(LinesShp)
#LayerLine.Initialize(ID="OID",GeomIndex=True,Params={"Decode":'ISO-8859-1'})
#LayerLine.Reproj(3857)
#LayerLine.Flatten()
#
#LayerPt = JV.JFastLayer(PtsShp)
#LayerPt.Initialize(ID="OID",GeomIndex=True)
#LayerPt.Reproj(3857)
#LayerPt.Flatten()
#
#CleanedLine = CleanLines(LayerLine)
#CleanedLine.RoundCoordinates(3)
#CleanedLine.Flatten()
#CleanedLine.UpdateTree()
#CleanedLine2=IdentifyPath(CleanedLine,LayerPt,Tolerance = 0.2)
#CleanedLine2.Save("G:/TEMP/TestTopo/Lines/ID3_DD_2018-06-19_TRAJET01_cleaned.shp")
#Poly = BuildPolyLine(CleanedLine2,LayerPt,Chunk = 5,Tolerance=0.1)
#L1 = LayerLine.CreateEmptyLayer()
#L1.MakeItEmpty()
#L2 = LayerLine.CreateEmptyLayer()
#L2.MakeItEmpty()
#L1.AppendFeat({"OID":1},Poly[0][0])
#for e,Geom in enumerate(Poly[1]) : 
#    L2.AppendFeat({"OID":e},Poly[1][e])
#L1.Save("G:/TEMP/TestTopo/Lines/ID3_DD_2018-06-19_TRAJET01_Merged.shp")
#L2.Save("G:/TEMP/TestTopo/Lines/ID3_DD_2018-06-19_TRAJET01_Ordered.shp")