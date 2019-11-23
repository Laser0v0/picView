import wx
import wx.grid
import cv2 as cv
from time import sleep
from threading import Thread, Event
from pubsub import pub
import numpy as np
import glob
from panel_filters import FilterPanel
from panel_info import InfoPanel,getImgInfo
from panel_show import ShowPanel

FRAME_RATE = 0.15
IMG_FILE_CLASS = ['bmp','jpg','png']
VID_FILE_CLASS = ['flv','mp4','mkv']
DEFAULT_IMG = "./img/init.png"

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

        self.defaultImage = cv.imread(DEFAULT_IMG)
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
        #self.GetParent().Layout()
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
        self.interval = IntervalTimer(FRAME_RATE, self.player)    #每隔0.07s执行一次self.player

    def player(self):
        if self.callback is not None:
            frame = self.callback()         #camera.cap.capture()
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
        if self.cap.isOpened():
            self.isConnected = True
    
    def disConnect(self):
        if not self.isConnected:
            return
        if self.cap is None:
            return
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
        self.cap = Camera(0)
        self.InitPanels()
        self.InitToolBar()

    def OnMode(self):
        self.mode = (self.mode+1)%3     ##目前的三种模式分别为相机、文件浏览器和算法(预留)
        self.setPanels['Show'].setMode(self.mode)
        if self.mode == 0:
            self.cap.doConnect()
        elif self.mode==1:
            self.cap.disConnect()
        
    def InitCapture(self):
        try:
            self.fileId = int(self.fileSelect.GetValue())
        except:
            self.showText.SetValue('请输入正确的相机ID\n相机ID已置零')
            self.fileId = 0
        self.files = list(range(2))
        self.cap.id = self.fileId
        self.cap.doConnect()

    def InitPanels(self):
        self.vid = VideoView(self,self.cap.captureImage,size=(600,-1))
        self.vid.start()
        self.InitParaBook()
        self.Bind(wx.EVT_CLOSE, self.onClose)
        box = wx.BoxSizer(wx.HORIZONTAL)
        box.Add(self.vid,1,wx.ALL|wx.EXPAND,0)
        box.Add(self.paraBook,0,wx.ALL|wx.EXPAND,0)
        self.SetSizer(box)
        self.Center()

    def InitParaBook(self):
        self.paraBook = wx.Notebook(self,size=(300,-1))
        names = ["Show","Info","Filter"]
        self.setPanels = {'Show':ShowPanel(self.paraBook,-1,self.mode,self.showBack)}
        self.setPanels['Info']=InfoPanel(self.paraBook,-1,self.calcValue)
        self.setPanels['Filter'] = FilterPanel(self.paraBook,-1,self.convBack)
        
        for name in names:
            self.paraBook.AddPage(self.setPanels[name],name)


        

    def InitToolBar(self):
        toolbar = self.CreateToolBar()
        toolName = ['Mode','Open','Close','Save','Flip','Rot']
        tools = {}
        for name in toolName:
            tools[name]=toolbar.AddTool(
                -1,name,wx.Bitmap('./img/'+name+'.png'))
            self.Bind(wx.EVT_TOOL,
                lambda evt, mark = name : self.OnToolBar(evt,mark),
                tools[name])
        toolbar.Realize()

    def OnToolBar(self,evt,mark):
        op = {'Mode':self.OnMode,
              'Open':self.imgOpen,
              'Close':self.imgClose,
              'Save':self.imgSave,
              'Flip':self.imgFlip,
              'Rot':self.imgRot,}
        op[mark]()

    def imgFlip(self):
        self.vid.flip(1,self.mode,self.img)

    def imgRot(self):
        self.vid.rotate(1,self.mode,self.img)

    def imgOpen(self):
        self.setPanels['Show'].imgOpen()
            
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


    # showPanel的回调函数
    def showBack(self,flag,id=0,img=None):
        if img is not None:
            self.img = img
            self.vid.setFrame(self.img)
            return
        if flag:
            self.cap.disConnect()
            self.cap.id = id
            self.cap.doConnect()
        else:
            self.cap.disConnect()
    
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
        self.cap.disConnect()
        evt.Skip()
       
class MyApp(wx.App):
    def OnInit(self):
        frame = MyFrame(None)
        frame.Show(True)
        return True

if __name__ == "__main__":
    app = MyApp()
    app.MainLoop()