import wx
import numpy as np
import cv2 as cv

labelDict = {
    'conv':['input','canny','gauss','sobel','rand','','',''],
    'mark':['circle','point','cross','rectangle','max','min','others'],
    'filter':['input','med','mean','sobel','edge'],
    'trans':['input'],
    'noise':['input']
}


def genFilter(flag='input',paras=[],pane=None):
    a,b,c,d = paras
    a,b = int(a),int(b)
    
    filterDict = {
        'input':lambda img : cv.filter2D(img,-1,pane),
        'mean': lambda img : cv.blur(img,(a,b)),
        'med': lambda img : cv.medianBlur(img,(a,b)),
        'canny': lambda img : cv.Canny(img,c,d)}
    
    return filterDict[flag]


class FilterPanel(wx.Panel):
    def __init__(self,parent,size=-1,call=None):
        wx.Panel.__init__(self,parent,size)
        self.doFilter = False
        self.call = call
        self.history = lambda img : img
        self.Init()

    def Init(self):
        filters = list(labelDict.keys())
        subfilters = labelDict[filters[0]]

        mainBox = wx.BoxSizer(wx.VERTICAL)

        upBox = wx.BoxSizer()
        self.mode = wx.ComboBox(self,value='general',size=(60,30),
            choices=['general','continus','overlay'])
        self.mainFilter = wx.ComboBox(self,
            value=filters[0],size=(60,30),choices=filters)
        self.subFilter = wx.ComboBox(self,
            value=subfilters[0],size=(60,30),choices=subfilters)
        btnSetFilter = wx.Button(self,label='filter',size=(55,25))
        btnSetFilter.Bind(wx.EVT_BUTTON, self.convFilter)
        self.mainFilter.Bind(wx.EVT_COMBOBOX,self.OnMainFilter)

        upBox.Add(self.mode,1,
            flag=wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_HORIZONTAL,border=5)
        upBox.Add(self.mainFilter,1,
            flag=wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_HORIZONTAL,border=5)
        upBox.Add(self.subFilter,1,
            flag=wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_HORIZONTAL,border=5)
        upBox.Add(btnSetFilter,1,
            flag=wx.RIGHT|wx.ALIGN_CENTER_HORIZONTAL,border=5)

        midBox = wx.BoxSizer()
        self.filterParas = []
        paraList = ['3','3','1','1']
        for val in paraList:
            self.filterParas.append(wx.TextCtrl(self,size=(50,-1),value=val))
            midBox.Add(self.filterParas[-1],0,wx.ALL|wx.EXPAND, border=5)

        self.filterGrid = wx.grid.Grid(self,-1)
        self.filterGrid.CreateGrid(10,10)
        nRows = wx.grid.GridSizesInfo(25,range(10))
        nCols = wx.grid.GridSizesInfo(25,range(10))
        self.filterGrid.SetRowSizes(nRows)
        self.filterGrid.SetColSizes(nCols)
        self.filterGrid.HideColLabels()
        self.filterGrid.HideRowLabels()
        self.setFilPane(3,3,np.ones([3,3])*0.11)

        self.filterInfo = wx.TextCtrl(self,size=(40,30))

        mainBox.Add(upBox,proportion=0,flag=wx.TOP|wx.BOTTOM, border=5)
        mainBox.Add(midBox, proportion=0,flag=wx.TOP|wx.BOTTOM, border=5)
        mainBox.Add(self.filterGrid,proportion=0,
            flag=wx.ALL|wx.ALIGN_CENTER|wx.EXPAND, border=5)
        mainBox.Add(self.filterInfo,proportion=1,
            flag=wx.ALL|wx.ALIGN_CENTER|wx.EXPAND, border=5)

        self.SetSizer(mainBox)

    def OnMainFilter(self,evt):
        filters = labelDict[self.mainFilter.GetValue()]
        for i in range(len(filters)):
            self.subFilter.SetString(i, filters[i])
    
    def getSubFilter(self,flag):
        pass

    def convFilter(self,evt):
        #mode = self.mode.GetValue()
        print(self.mode.GetCurrentSelection())
        mode = self.mode.GetCurrentSelection()
        mFilter = self.mainFilter.GetValue()
        sFilter = self.subFilter.GetValue()
        
        paras = [float(self.filterParas[i].GetValue()) 
                        for i in range(4)]
        filPane = self.getFilPane(
            int(paras[0]),int(paras[1])) if sFilter=='input' else []
        
        self.doFilter = True if mode>0 else not self.doFilter
        
        func = genFilter(sFilter,paras,filPane) \
            if self.doFilter else lambda img : img
        
        if mode == 2:
            print(mode)
            self.history = lambda img : func(self.history(img))
            func = self.history
        
        self.call(func)

    def getFilPane(self,m,n):
        filPane = [float(self.filterGrid.GetCellValue(i+1,j+1)) for i in range(n) for j in range(m)]
        filPane = np.array(filPane).reshape(n,m)
        return filPane
    
    def setFilPane(self,m,n,datas):
        values = np.array(datas).reshape(n,m).astype(str)
        for i in range(m):
            for j in range(n):
                self.filterGrid.SetCellValue(i+1,j+1,values[i,j])
