# -*- coding: utf-8 -*-
"""
Created on Tue Jul  3 14:59:46 2018

@author: gelbj
"""

################################################
## Import des packages
################################################

import cv2
from path import Path

import os,sys
Link = "C:/Users/GelbJ/Desktop/ANACONDA1/Library/share/gdal/"
os.environ["GDAL_DATA"] = Link
sys.path.append("L:/Python/___JBasics")

from JQgis import JVectorLayer as JV
import JDate

################################################
## definition des variables globales
################################################


Root = Path(__file__).parent
print("This is Root : "+str(Root))


MainPath = Root.parent.parent.joinpath("B)_VideoStructured")
#Participants = [str(F.name) for F in MainPath.listdir()]

Participants = ["ID3_MG"]# "ID1_SP" "ID2_VJ","ID3_MG","ID4_DD"]

Jump = 5
FieldDate = "DATETIME"
Skip = []


################################################
## definition des fonctions utilitaires
################################################

## fonction struturee pour la NZ
def ConvertDate(Txt) : 
    """
    Pour les cas : 2018-02-26 13:46:20
    """
    Date = Txt.split(" ")[0].split("-")
    Time = Txt.split(" ")[1].split(":")
    return JDate.Jdatetime(Year = Date[0], Month = Date[1], Day = Date[2], Hour=Time[0], Minute=Time[1], Second=Time[2])

def TimeLaps(Start,End) :
    A = ConvertDate(Start)
    B = ConvertDate(End)
    Diff = abs((A.DateTime-B.DateTime).total_seconds())
    return Diff/60.0

SortieShp = Path(__file__).parent.parent.joinpath("__Frames")


################################################
## execution du script
################################################

for IDPart in Participants : 
    ShpPath = MainPath.joinpath(IDPart).joinpath("SHP")
    VideoPath = MainPath.joinpath(IDPart).joinpath("VIDEO")
    FolderPart = SortieShp.joinpath(IDPart)
    try :
        os.mkdir(FolderPart)
    except : 
        print("This Folder exist : "+FolderPart)
    for Shp in ShpPath.files("*.shp") : 
        if Shp.name.split(".")[0] not in Skip : 
            ##creation du dossier qui comprendra les images
            FolderName = Shp.name.split(".")[0]
            Folder = FolderPart.joinpath(FolderName)
            if os.path.isdir(Folder) : 
                print(Shp.name+" is already done")
            else : 
                os.mkdir(Folder)
                print("Working on : "+Shp.name)
                ##ouverture du layer
                Layer = JV.JFastLayer(Shp)
                Layer.Initialize(ID="OID",GeomIndex=False)
                Start = Layer.GetRow(0)
                End = Layer.GetRow(Layer.FeatureCount-1)
                Duree = TimeLaps(Start["DATETIME"],End["DATETIME"])
                if Duree > 5 :
                    ## Ajout du champs avec le path de l'image
                    Layer.AttrTable.AddField("PictPath","|S500","NONE")
                    ## Setting du point de depart
                    StartDTime = ConvertDate(Layer.GetRow(0)[FieldDate])
                    Start = int(StartDTime.TimeStamp)
                    ##ouverture de la video
                    vidcap = cv2.VideoCapture(str(VideoPath)+"/"+Shp.name.split(".")[0]+".mp4")
                    ## Debut des iterations
                    for Feat in Layer.Iterate(True) : 
                        DTime = ConvertDate(Feat[FieldDate])
                        Time = int(DTime.TimeStamp)
                        Ecart = abs(Start-Time)
                        #avancement dans la video
                        if Feat["OID"]%Jump == 0  :
                            vidcap.set(cv2.CAP_PROP_POS_MSEC,Ecart*1000)
                            #recuperation de l'image
                            success,image = vidcap.read()
                            PicPath = Folder+"/Pict_"+str(Feat["OID"])+".jpg"
                            PicPathField = "/"+FolderName+"/Pict_"+str(Feat["OID"])+".jpg"
                            if success:
                                image = cv2.resize(image, (0,0), fx = 0.5, fy = 0.5)
                                cv2.imwrite(PicPath, image)    # save frame as JPEG file
                                Layer.AttrTable.SetValue(Feat["OID"],"PictPath",PicPathField)
                            else : 
                                #si on est dans les 30 derniere secondes, pas important
                                if Feat["OID"]>=Layer.FeatureCount-30 :
                                    Layer.AttrTable.SetValue(Feat["OID"],"PictPath",PicPathField)
                                else :
                                    raise ValueError("The video failed to read the image...")
                        else : 
                            Layer.AttrTable.SetValue(Feat["OID"],"PictPath",PicPathField)
                            
                    Layer.Save(FolderPart+"/"+str(Shp.name))
                
        
        
 