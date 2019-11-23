import wx
import glob
import cv2 as cv
import numpy as np


IMG_FILE_CLASS = ['bmp','jpg','png']
VID_FILE_CLASS = ['flv','mp4','mkv']

class ShowPanel(wx.Panel):
    def __init__(self,parent,size,mode,call):
        wx.Panel.__init__(self,parent)
        self.call = call
        self.setMode(mode)

        thisBox = wx.BoxSizer(wx.VERTICAL)

        topBox = wx.BoxSizer()
        self.fileSelect = wx.TextCtrl(self,value='0',size=(150,30))
        btnOpen = wx.Button(self,label='select',size=(40,30))
        topBox.Add(self.fileSelect,proportion=0,flag=wx.EXPAND|wx.ALL, border=10)
        topBox.Add(btnOpen,proportion=0,flag=wx.EXPAND|wx.ALL, border=10)
        
        btnOpen.Bind(wx.EVT_BUTTON,self.OnOpen)

        upBox = wx.BoxSizer()
        btnLabels = {'front':-1,'info':0,'back':1}
        btnCtrls = {}
        for key in btnLabels:
            btnCtrls[key] = wx.Button(self,label=key,size=(60,30))
            upBox.Add(btnCtrls[key],proportion=1,
                flag=wx.EXPAND|wx.ALL|wx.ALIGN_CENTER,border=10)
            self.Bind(wx.EVT_BUTTON,
                lambda evt,mark = btnLabels[key] : self.OnImgCtrl(evt,mark),
                btnCtrls[key])

        midBox = wx.BoxSizer()
        self.exp0 = wx.StaticText(self,label='0',size=(20,-1))
        self.expSlider=wx.Slider(self,minValue=1,maxValue=1000,size=(250,-1))
        self.expEnd = wx.StaticText(self,label='0',size=(20,-1))
        midBox.Add(self.exp0,proportion=0,flag=wx.LEFT|wx.RIGHT,border=10)
        midBox.Add(self.expSlider,proportion=1,flag=wx.EXPAND)
        midBox.Add(self.expEnd,proportion=0,flag=wx.LEFT|wx.RIGHT,border=10)

        self.showText = wx.TextCtrl(self,size=(-1,-1),style=wx.TE_MULTILINE)

        thisBox.Add(topBox,proportion=0,flag=wx.TOP,border=20)
        thisBox.Add(upBox,proportion=0,flag=wx.ALL,border=10)
        thisBox.Add(midBox,proportion=0,flag=wx.ALL,border=10)
        thisBox.Add(self.showText,proportion=1,flag=wx.ALL|wx.EXPAND,border=10)

        self.SetSizer(thisBox)

    def setMode(self,mode):
        self.mode = mode

    def OnImgCtrl(self,evt,mark):
        if mark:
            self.fileId = (self.fileId + mark)%len(self.files)
            self.openFile(self.files[self.fileId])
        else:
            pass
    
    def OnOpen(self,evt):
        self.imgOpen()

    # 文件初始化，生成当前目录下当前文件名的文件序列
    # 确定当前文件的序号
    def initFile(self,filePath):
        dirPath = '\\'.join(filePath.split('\\')[:-1])
        fileFlag = filePath.split('.')[-1]
        self.files = glob.glob(dirPath+'\\*.'+fileFlag)
        self.fileId = np.squeeze(np.where(np.array(self.files)==filePath))
        self.openFile(filePath)

    def openFile(self,filePath):
        name = filePath.split('\\')[-1]
        self.fileSelect.SetValue(name)
        fileFlag = name.split('.')[-1]
        if self.mode == 0:
            self.InitCapture()
            return
        if fileFlag in IMG_FILE_CLASS:
            self.oriImg = cv.imread(filePath)
            self.oriImg = cv.cvtColor(self.oriImg,cv.COLOR_BGR2RGB)
            self.img = self.oriImg
            self.call(False,img=self.img)#self.vid.setFrame(self.img)
        elif fileFlag in VID_FILE_CLASS:
            self.call(True,id=filePath)#self.cap.doConnect()

    def InitCapture(self):
        try:
            self.fileId = int(self.fileSelect.GetValue())
        except:
            self.showText.SetValue('请输入正确的相机ID\n相机ID已置零')
            self.fileId = 0
        self.files = list(range(2))
        self.call(True,self.fileId)#self.cap.doConnect()

    def imgOpen(self):
        if self.mode==0:
            self.InitCapture()
        elif self.mode == 1:
            dlg = wx.FileDialog(self,message="请打开文件",defaultDir='',
                                    defaultFile='',style=wx.FD_OPEN)
            if dlg.ShowModal() != wx.ID_OK:
                return
            filePath = dlg.GetPath()
            dlg.Destroy()
            self.initFile(filePath)

