import wx
import wx.grid
import cv2 as cv
from time import sleep
from threading import Thread, Event
from wx.lib.pubsub import pub
import numpy as np
import glob
from filters import FilterPanel
from info import InfoPanel,getImgInfo


def markImage(img,x,y):
    x,y = int(x),int(y)
    if len(img.shape)==2:
        img[y,:] = 0
        img[:,x] = 0
        img[x,y] = 255
    else:
        img[y,:,:] = 0
        img[:,x,:] = 0
        img[x,y,:] = 255

def markCircle(img, x0, y0, r):
    x0,y0 = 200,200
    r = 100
    w,h = img.shape[:2]
    ys = range(max(int(y0-r),0),min(int(y0+r),h))
    for y in ys:
        try:
            left = int(x0-np.sqrt(r**2-(y-y0)**2))
        except:
            print(r**2-(y-y0)**2)
        if left > 0:
            img[left,y] == 255
        right = int(x0+np.sqrt(r**2-(y-y0)**2))
        if right < w:
            img[right,y] == 255
    return img

class IntervalTimer(Thread):
    def __init__(self, interval, func):
        Thread.__init__(self)
        self.stop_event = Event()
        self._interval = interval
        self.func = func
    
    def stop(self):
        if self.isAlive():
            self.stop_event.set()
            self.join()

    def run(self):
        while not self.stop_event.is_set():
            self.func()
            sleep(self._interval)

class ImageView(wx.Panel):
    def __init__(self, parent, resize=True,
                 quality=wx.IMAGE_QUALITY_NORMAL,
                 size=(-1,-1), black=False, style=wx.NO_BORDER):
        wx.Panel.__init__(self, parent, size=size, style=style)

        self.xOffset,self.yOffset = 0, 0
        self.quality = quality

        self.picFlip = 1
        self.picRot = 0
        self.filterFunc = lambda img : img

        self.defaultImage = cv.imread("./img/init.png")
        self.img = self.defaultImage
        self.setFrame(self.img)
        
        if black:
            self.SetBackgroundColour(wx.BLACK)
        self.backBrush = wx.Brush(wx.BLACK, wx.SOLID)

        self.Bind(wx.EVT_SHOW, self.onShow)
        self.Bind(wx.EVT_PAINT, self.onPaint)

        if resize:
            self.Bind(wx.EVT_SIZE, self.onResize)

        self.hide = False

    def onShow(self, evt):
        self.GetParent().Layout()
        self.Layout()

    def onPaint(self, evt):
        if self.hide:
            return
        dc = wx.BufferedPaintDC(self)
        dc.SetBackground(self.backBrush)
        dc.Clear()
        dc.DrawBitmap(self.bitmap, self.xOffset, self.yOffset)

    def onResize(self, evt):
        self.refreshBitmap()

    def flip(self,nFlip,isStatic,img):
        self.picFlip = (self.picFlip+2*nFlip)%4-1
        if isStatic:
           self.setFrame(img)

    def rotate(self,nRot,isStatic,img):
        self.picRot = (self.picRot+nRot)%2
        if isStatic:
            self.setFrame(img)

    def setFilter(self,func):
        self.filterFunc = func
    
    #显示图片
    def setFrame(self, frame):
        if frame is None:
            return
        if self.picRot==1:
            frame = cv.transpose(frame)
        if self.picFlip < 2:
            frame = cv.flip(frame,self.picFlip)

        self.img = frame
        self.imgInfo = getImgInfo(frame)
        wx.CallAfter(pub.sendMessage,"updateinfo",msg=self.imgInfo)

        h, w = frame.shape[:2]

        frame = self.filterFunc(frame)
        
        self.image = wx.ImageFromBuffer(w, h, frame)
        self.image.SetData(frame.reshape(-1,1,1).squeeze())
        self.refreshBitmap()

    def saveImage(self,savePath,img):
        pathList = savePath.split('.')
        filtPath = 'filter.'.join(pathList)
        cv.imwrite(savePath,img)
        img = self.filterFunc(img)
        cv.imwrite(filtPath,img)

    def refreshBitmap(self):
        (w, h, self.xOffset, self.yOffset) = self.getBestSize()
        if w>0 and h>0:
            self.bitmap = wx.Bitmap(self.image.Scale(w,h,self.quality))            
            self.Refresh()

    def setDefaultFrame(self):
        self.setFrame(self.defaultImage)

    #调整最合适的尺寸
    def getBestSize(self):
        shapes = np.array(self.GetSize())
        sh = np.flipud(self.img.shape[:2]).astype(float)
        sh *= min(shapes/sh)
        offsets = (shapes-sh)/2.0
        return sh.tolist()+offsets.tolist()
       
class VideoView(ImageView):
    def __init__(self, parent, callback=None,
                 size=(-1,-1), black=False):
        ImageView.__init__(self, parent, size=size, black=black)
        self.callback = callback
        self.interval = IntervalTimer(0.07, self.player)    #每隔0.07s执行一次self.player

    def player(self):
        if self.callback is not None:
            frame = self.callback()
            wx.CallAfter(self.setFrame, frame)

    def start(self):
        self.interval.start()

    def stop(self):
        self.interval.stop()
        self.setDefaultFrame()

class Camera(object):
    def __init__(self, camId=1):
        self.id = camId
        self.cap = None
        self.isConnected = False
        self.doConnect()

    def doConnect(self):
        self.isConnected = False
        self.cap = cv.VideoCapture(self.id)
        sleep(0.2)
        if self.cap.isOpened():
            self.isConnected = True

    def disConnect(self):
        if self.isConnected:
            if self.cap is not None:
                if self.cap.isOpened():
                    self.isConnected = False
                    self.cap.release()

    def captureImage(self, flush=0):
        if not self.isConnected:
            return
        if flush > 0:
            for i in range(0, flush):
                self.cap.grab()
        ret, self.img = self.cap.read()
        if ret:
            img = cv.cvtColor(self.img, cv.COLOR_BGR2RGB)
            return img

    def setResolution(self, height, width):
        if not self.isConnected:
            return
        self.cap.set(cv.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv.CAP_PROP_FRAME_HEIGHT, height)

class MyFrame(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, size=(840, 480))
        self.mode = 0
        self.img = None
        self.InitCapture()
        self.InitParaBook()
        self.InitToolBar()

    def OnMode(self):
        if self.mode == 0:
            self.cap.doConnect()
        elif self.mode==1:
            self.cap.disConnect()
            #self.vid.stop()
        
    def InitCapture(self,camId =0):
        self.cap = Camera(camId)
        #self.cap.setResolution(960,1280)

    def InitParaBook(self):
        self.vid = VideoView(self,self.cap.captureImage,size=(600,-1))
        self.vid.start()

        self.paraBook = wx.Notebook(self,size=(300,-1))
        names = ["Show","Info","Filter"]
        self.setPanels = {'Show':wx.Panel(self.paraBook)}
        self.setPanels['Info']=InfoPanel(self.paraBook,-1,self.calcValue)
        self.setPanels['Filter'] = FilterPanel(self.paraBook,-1,self.convBack)
        
        for name in names:
            self.paraBook.AddPage(self.setPanels[name],name)

        self.InitShow()

        self.Bind(wx.EVT_CLOSE, self.onClose)
        box = wx.BoxSizer(wx.HORIZONTAL)
        box.Add(self.vid,1,wx.ALL|wx.EXPAND,0)
        box.Add(self.paraBook,0,wx.ALL|wx.EXPAND,0)
        self.SetSizer(box)
        self.Center()

    def InitToolBar(self):
        toolbar = self.CreateToolBar()
        toolName = ['Mode','Open','Close','Save','Flip','Rot']
        tools = {}
        for name in toolName:
            tools[name]=toolbar.AddLabelTool(
                -1,name,wx.Bitmap('./img/'+name+'.png'))
            self.Bind(wx.EVT_TOOL,
                lambda evt, mark = name : self.OnToolBar(evt,mark),
                tools[name])
        toolbar.Realize()

    def OnToolBar(self,evt,mark):
        if mark=='Mode':
            self.mode = (self.mode+1)%3     ##目前的三种模式分别为相机、图片浏览器和视频
            self.OnMode()
        else:
            op = {'Open':self.imgOpen,
                  'Close':self.imgClose,
                  'Flip':self.imgFlip,
                  'Rot':self.imgRot,
                  'Save':self.imgSave}
            op[mark]()

    def imgFlip(self):
        self.vid.flip(1,self.mode,self.img)

    def imgRot(self):
        self.vid.rotate(1,self.mode,self.img)

    def initImg(self,filePath):
        self.oriImg = cv.imread(filePath)
        self.oriImg = cv.cvtColor(self.oriImg,cv.COLOR_BGR2RGB)
        self.img = self.oriImg
        self.vid.setFrame(self.img)

    def imgOpen(self):
        if self.mode==0:
            if self.cap.isConnected:
                self.cap.disConnect()
            try:
                self.cap.id = int(self.capIdSelect.GetValue())
            except:
                self.showText.SetValue('请输入正确的相机ID\n相机ID已置零')
                self.cap.id = 0
            self.cap.doConnect()
        elif self.mode==1:
            self.cap.disConnect()
            self.vid.setDefaultFrame()
            dlg = wx.FileDialog(self,message="请打开图片",defaultDir='',
                                defaultFile='',style=wx.FD_OPEN)
            if dlg.ShowModal() == wx.ID_OK:
                filePath = dlg.GetPath()
                print(filePath)
                dirPath = '\\'.join(filePath.split('\\')[:-1])
                backName = '.'+filePath.split('.')[-1]
                self.files = glob.glob(dirPath+"\\*"+backName)
                self.imgId = np.squeeze(np.where(np.array(self.files)==filePath))
                dlg.Destroy()
            self.initImg(filePath)
        elif self.mode==2:
            pass

    def imgClose(self):
        if self.mode==0:
            self.cap.disConnect()
        self.vid.setDefaultFrame()

    def imgSave(self):
        if self.mode == 0:
            img = self.cap.img
        elif self.mode == 1:
            img = self.img
        filesFilter = "bmp(*.bmp)|*.bmp|png(*.png)|*.png|All files(*.*)|*.*"
        fileDialog = wx.FileDialog(self,message="select your saving path", 
            wildcard=filesFilter,style=wx.FD_SAVE)
        dialogResult = fileDialog.ShowModal()
        fileName = fileDialog.GetFilename()
        savePath =  fileDialog.GetDirectory()+'/'+fileName
        if dialogResult != wx.ID_SAVE:
            self.vid.saveImage(savePath,img)

    def InitShow(self):
        thisBox = wx.BoxSizer(wx.VERTICAL)

        topBox = wx.BoxSizer()
        self.capIdSelect = wx.TextCtrl(self.setPanels['Show'],value='0',size=(150,30))
        btnSelectID = wx.Button(self.setPanels['Show'],label='select',size=(40,30))
        topBox.Add(self.capIdSelect,proportion=0,flag=wx.EXPAND|wx.ALL, border=10)
        topBox.Add(btnSelectID,proportion=0,flag=wx.EXPAND|wx.ALL, border=10)
        
        btnSelectID.Bind(wx.EVT_BUTTON,self.selectCapID)

        upBox = wx.BoxSizer()
        btnLabels = {'front':-1,'info':0,'back':1}
        btnCtrls = {}
        for key in btnLabels:
            btnCtrls[key] = wx.Button(
                self.setPanels['Show'],label=key,size=(60,30))
            upBox.Add(btnCtrls[key],proportion=1,
                flag=wx.EXPAND|wx.ALL|wx.ALIGN_CENTER,border=10)
            self.Bind(wx.EVT_BUTTON,
                lambda evt,mark = btnLabels[key] : self.OnImgCtrl(evt,mark),
                btnCtrls[key])

        midBox = wx.BoxSizer()
        self.exp0 = wx.StaticText(self.setPanels['Show'],
            label='0',size=(20,-1))
        self.expSlider=wx.Slider(self.setPanels['Show'],
            minValue=1,maxValue=1000,size=(250,-1))
        self.expEnd = wx.StaticText(self.setPanels['Show'],
            label='0',size=(20,-1))
        midBox.Add(self.exp0,proportion=0,flag=wx.LEFT|wx.RIGHT,border=10)
        midBox.Add(self.expSlider,proportion=1,flag=wx.EXPAND)
        midBox.Add(self.expEnd,proportion=0,flag=wx.LEFT|wx.RIGHT,border=10)

        self.showText = wx.TextCtrl(self.setPanels['Show'],
            size=(-1,-1),style=wx.TE_MULTILINE)

        thisBox.Add(topBox,proportion=0,flag=wx.TOP,border=20)
        thisBox.Add(upBox,proportion=0,flag=wx.ALL,border=10)
        thisBox.Add(midBox,proportion=0,flag=wx.ALL,border=10)
        thisBox.Add(self.showText,proportion=1,flag=wx.ALL|wx.EXPAND,border=10)

        self.setPanels['Show'].SetSizer(thisBox)

    def selectCapID(self,evt):
        self.imgOpen()

    def OnImgCtrl(self,evt,mark):
        if mark:
            self.imgRoll(mark)
        else:
            pass
    
    def imgRoll(self,num):
        self.imgId = (self.imgId + num)%len(self.files)
        self.initImg(self.files[self.imgId])
        name = self.files[self.imgId].split('\\')[-1]
        self.capIdSelect.SetValue(name)

    # filterPanel的回调函数
    def convBack(self,func):
        self.vid.setFilter(func)
        self.vid.setFrame(self.img)

    #infoPanel的回调函数
    def calcValue(self):
        if self.mode == 0:
            return
        elif self.mode == 1:
            self.vid.setFrame(self.img)
              
    def onClose(self, evt):
        #self.vid.stop()
        self.cap.disConnect()
        evt.Skip()

    def setExposure(self,evt):
        self.cap.cap.set(cv.CV_CAP_PROP_EXPOSURE,float(self.expText.Value))
       
class MyApp(wx.App):
    def OnInit(self):
        frame = MyFrame(None)
        frame.Show(True)
        return True

if __name__ == "__main__":
    app = MyApp()
    app.MainLoop()