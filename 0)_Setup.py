# -*- coding: utf-8 -*-
"""
Created on Thu Aug 16 11:56:23 2018

@author: GelbJ
"""

import os
from path import Path


##################################
## Parametres generaux
##################################

## Aucun parametres a modifier ici !!


##################################
## Creating Folders
##################################

Folders = ["__OsrmMatched","__Frames","__QgisFiles","__ExportedLines","__PolyLines","__MatchedPoints"]
ActualFolder = Path(os.path.dirname(__file__)).parent

for element in Folders : 
    NewFolder = ActualFolder.joinpath(element)
    os.mkdir(str(NewFolder))


