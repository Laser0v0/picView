import wx
import time
import copy
import numpy as np
import cv2 as cv

labelDict = {
    'conv':['input','rand','randgauss','test'],
    'edge':['sobel','scharr','laplacian','canny',],
    'filter':['gauss','med','mean','bilateral'],
    'feature':['thres','contour'],
    'mark':['circle','line','face'],
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
    'fourier':'傅立叶变换'
}

def test(img):
    new = copy.deepcopy(img)
    cv.rectangle(new,(100,100),(200,200),(255,0,0),2)
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

def faceDetect(img):
    t = time.time()
    faceCascade = cv.CascadeClassifier('haarcascade_frontalface_default.xml')
    eyeCascade = cv.CascadeClassifier('haarcascade_eye.xml')
    gray = cv.cvtColor(img,cv.COLOR_BGR2GRAY)
    new = copy.deepcopy(img)

    faces = faceCascade.detectMultiScale(
        gray,
        scaleFactor = 1.2,
        minNeighbors = 5,
        minSize = (32,32))
    
    result = []
    for (x,y,w,h) in faces:
        faceGray = gray[y:(y+h),x:(x+w)]
        eyes = eyeCascade.detectMultiScale(faceGray,1.3,2)
        for (ex,ey,ew,eh) in eyes:
            result.append((x+ex,y+ey,ew,eh))
    
    
    for (x,y,w,h) in result:
        cv.rectangle(new,(x,y),(x+w,y+h),(0,255,0),2)

    for (x,y,w,h) in faces:
        print(x,y,w,h)
        cv.rectangle(new,(x,y),(x+w,y+h),(255,0,0),2)
    

    print(time.time()-t)
    return new

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
    }
    
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
        self.subFilter.Bind(wx.EVT_COMBOBOX,self.OnSubFilter)

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

        self.filterInfo = wx.TextCtrl(self,size=(40,30),style=wx.TE_MULTILINE)

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

    def OnSubFilter(self,evt):
        sFilter = self.subFilter.GetValue()
        self.filterInfo.SetValue(infoDict[sFilter])

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
