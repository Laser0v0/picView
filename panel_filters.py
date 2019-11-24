import wx
import time
import copy
import numpy as np
import cv2 as cv
from panel_info import getImgInfo

#####添加函数的方法
#1 在labelDict中添加函数标识
#2 在infoDict中添加函数说明
#3 在genFilter的filterDict中添加函数映射
#4 写出映射函数

BTN_START = 'start'
BTN_STOP = 'stop'

labelDict = {
    'conv':['input','rand','randgauss','test'],
    'edge':['sobel','scharr','laplacian','canny',],
    'filter':['gauss','med','mean','bilateral'],
    'feature':['thres','contour'],
    'mark':['circle','facula','face','eyes',],
    'trans':['fourier'],
}

infoDict = {
    'input':'自定义卷积\n请在表格中输入卷积模板,并在参数输入框中输入模板尺寸',
    'test':'测试函数',
    'rand':'随机卷积\n',
    'randgauss':'正态随即卷积',
    'gauss':'高斯滤波\n参数分别为模板宽度、模板高度、横向标准差、纵向标准差',
    'mean':'均值滤波\n参数为模板宽度、模板高度',
    'med':'中值滤波\n参数为模板尺寸',
    'bilateral':'双边滤波\n参数为核直径、color filter、space filter',
    'sobel': 'Sobel算子\n参数为横向求导阶数、纵向求导阶数、卷积核尺寸、缩放比例',
    'scharr':'Scharr算子\n参数为横向求导阶数、纵向求导阶数、缩放比例',
    'laplacian':'Laplacian算子\n参数为卷积核尺寸',
    'canny': 'Canny算子\n参数为下阈值、上阈值、卷积核尺寸、是否采用2范数',
    'thres': '阈值选取\n参数为下阈值、上阈值、模式',
    'contour':'轮廓绘制\n参数为模式、方法',
    'circle':'圆检测',
    'line':'线检测',
    'face':'人脸识别',
    'eyes':'人脸识别包括眼睛',
    'facula':'标记光斑',
    'fourier':'傅立叶变换',
}


def genFilter(flag='input',paras=[],pane=None):
    a,b,c,d = paras
    
    filterDict = {
        'input':lambda img : cv.filter2D(img,-1,pane),
        'test':lambda img : test(img),
        'mean': lambda img : cv.blur(img,(int(a),int(b))),
        'med': lambda img : cv.medianBlur(img,int(a)),
        'canny': lambda img : cv.Canny(img,c,d,int(a),(not b)),
        'sobel': lambda img : cv.convertScaleAbs(cv.Sobel(
            img,cv.CV_16S,int(a),int(b),ksize=int(c),scale=d)),
        'scharr': lambda img : cv.convertScaleAbs(cv.Sobel(
            img,cv.CV_16S,int(a),int(b),ksize=-1,scale=c)),
        'laplacian': lambda img : cv.convertScaleAbs(
            cv.Laplacian(img,cv.CV_16S,ksize=int(c),)),
        'gauss': lambda img : cv.GaussianBlur(img,(int(a),int(b)),c,d),
        'thres': lambda img : cv.threshold(img,a,b,int(c))[1],
        'contour': lambda img : cv.drawContours(
            img,cv.findContours(img,int(a),int(b))[2],-1),
        'circle': lambda img : cvCircle(img,a,b,int(c),int(d)),
        'fourier': lambda img : np.fft.fft2(img),
        'face': lambda img : faceDetect(img),
        'eyes': lambda img : faceDetect(img,withEye=True),
        'facula': lambda img : faculaDetect(img),
    }
    
    return filterDict[flag]

def test(img):
    new = copy.deepcopy(img)
    cv.rectangle(new,(100,100),(200,200),(255,0,0),2)
    return new

def faculaDetect(img):
    new = copy.deepcopy(img)
    new[new<20] = 0
    
    info = getImgInfo(new)
    try:
        center = (int(info['center'][0]),int(info['center'][1]))
        r = info['radius']
        cv.circle(new,center,int(info['radius'][0]),(255,0,0),2)
    except:
        pass
        #cv.circle(new,(100,100),10,(255,0,0),2)
    return new

def cvCircle(img,param1,param2,minRadius,maxRadius):
    gray = cv.cvtColor(img,cv.COLOR_BGR2GRAY)
    cimg = cv.cvtColor(gray,cv.COLOR_GRAY2BGR)
    circles = cv.HoughCircles(
        gray,cv.HOUGH_GRADIENT,1,20,
        param1=param1,param2=param2,
        minRadius=minRadius,maxRadius=maxRadius)
    circles = np.uint8(np.around(circles))
    for i in circles[0,:]:
        cv.circle(cimg,(i[0],i[1]),i[2],(0,255,0),2)
        cv.circle(cimg,(i[0],i[1]),2,(0,0,255,3))
    return cimg

faceCascade = cv.CascadeClassifier('xml/cvFace.xml')
eyeCascade = cv.CascadeClassifier('xml/cvEye.xml')
def faceDetect(img,minNeighbor=5,scale=1.2,withEye=False):
    gray = cv.cvtColor(img,cv.COLOR_BGR2GRAY)
    new = copy.deepcopy(img)

    faces = faceCascade.detectMultiScale(gray,
        scaleFactor = scale,minNeighbors = minNeighbor,minSize = (32,32))
    
    result = []
    for (x,y,w,h) in faces:
        cv.rectangle(new,(x,y),(x+w,y+h),(0,255,0),2)
        if not withEye:
            continue
        faceGray = gray[y:(y+h),x:(x+w)]
        eyes = eyeCascade.detectMultiScale(faceGray,1.3,2)
        for (ex,ey,ew,eh) in eyes:
            cv.rectangle(new,(ex+x,ey+y),(ex+ew+x,ey+eh+y),(255,0,0),2)
            
    return new

#函数复合
def comDef(defList):
    if len(defList)>2:
        return comDef([defList[0]]+comDef(defList[1:]))
    elif len(defList) == 1:
        return defList
    else:
        return [lambda x : defList[0](defList[1](x))]

class FilterPanel(wx.Panel):
    def __init__(self,parent,size=-1,call=None):
        wx.Panel.__init__(self,parent,size)
        self.doFilter = False
        self.call = call
        self.history = []
        self.func = lambda img : img
        self.isUpdated = False
        self.mode = 0
        self.Init()

    def Init(self):
        filters = list(labelDict.keys())
        subfilters = labelDict[filters[0]]

        mainBox = wx.BoxSizer(wx.VERTICAL)

        upBox = wx.BoxSizer()
        self.modeCombo = wx.ComboBox(self,value='general',size=(60,30),
            choices=['general','continus','overlay'])
        self.mainFilter = wx.ComboBox(self,
            value=filters[0],size=(60,30),choices=filters)
        self.subFilter = wx.ComboBox(self,
            value=subfilters[0],size=(60,30),choices=subfilters)
        self.btnSetFilter = wx.Button(self,label=BTN_START,size=(55,25))
        self.btnSetFilter.Bind(wx.EVT_BUTTON, self.convFilter)
        self.modeCombo.Bind(wx.EVT_COMBOBOX,self.OnMode)
        self.mainFilter.Bind(wx.EVT_COMBOBOX,self.OnMainFilter)
        self.subFilter.Bind(wx.EVT_COMBOBOX,self.OnSubFilter)

        upBox.Add(self.modeCombo,1,
            flag=wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_HORIZONTAL,border=5)
        upBox.Add(self.mainFilter,1,
            flag=wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_HORIZONTAL,border=5)
        upBox.Add(self.subFilter,1,
            flag=wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_HORIZONTAL,border=5)
        upBox.Add(self.btnSetFilter,1,
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

        self.filterInfo = wx.TextCtrl(self,size=(40,30),style=wx.TE_MULTILINE)

        mainBox.Add(upBox,proportion=0,flag=wx.TOP|wx.BOTTOM, border=5)
        mainBox.Add(midBox, proportion=0,flag=wx.TOP|wx.BOTTOM, border=5)
        mainBox.Add(self.filterGrid,proportion=0,
            flag=wx.ALL|wx.ALIGN_CENTER|wx.EXPAND, border=5)
        mainBox.Add(self.filterInfo,proportion=1,
            flag=wx.ALL|wx.ALIGN_CENTER|wx.EXPAND, border=5)

        self.SetSizer(mainBox)

    def OnMode(self,evt):
        self.mode = self.modeCombo.GetCurrentSelection()
        self.btnSetFilter.SetLabel(BTN_START)
        self.history = []
        self.doFilter = True if self.mode else False
        self.call(lambda x : x)

    def OnMainFilter(self,evt):
        filters = labelDict[self.mainFilter.GetValue()]
        for i in range(len(filters)):
            self.subFilter.SetString(i, filters[i])

    def OnSubFilter(self,evt):
        self.UpdateFunc()

    def UpdateFunc(self):
        self.isUpdated = True
        sFilter = self.subFilter.GetValue()
        self.filterInfo.SetValue(infoDict[sFilter])

        paras = [float(self.filterParas[i].GetValue())
                        for i in range(4)]
        
        filPane = self.getFilPane(
            int(paras[0]),int(paras[1])) if sFilter=='input' else []
        
        func = genFilter(sFilter,paras,filPane)

        if self.mode == 2:
            self.history.append(func)
            self.func = comDef(self.history)[0]
        else:
            self.func = func

    def convFilter(self,evt):
        if not self.isUpdated:
            self.UpdateFunc()
        self.isUpdated = False
        if self.mode < 1:
            self.doFilter = not self.doFilter
            flag = BTN_STOP if self.doFilter else BTN_START
            self.btnSetFilter.SetLabel(flag)

        func = self.func if self.doFilter else lambda img : img
        self.call(func)
        
    def getFilPane(self,m,n):
        filPane = [float(self.filterGrid.GetCellValue(i+1,j+1)) 
                for i in range(n) for j in range(m)]
        filPane = np.array(filPane).reshape(n,m)
        return filPane
    
    def setFilPane(self,m,n,datas):
        values = np.array(datas).reshape(n,m).astype(str)
        for i in range(m):
            for j in range(n):
                self.filterGrid.SetCellValue(i+1,j+1,values[i,j])
