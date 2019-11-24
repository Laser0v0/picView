import wx
import time
import numpy as np
from pubsub import pub

infoDict = {
    'center':[0,0],
    'shape':[0,0],
    'radius':[1],
    'frames':[0],
    'fps':[0,0]
}

def getFrameInfo():
    t = [time.time()]
    def recordTime():
        t.append(time.time())
        num = len(t)
        if num < 2:
            return {'frames':num,'fps':[0,0]}
        fps = 0 if t[-1]==t[0] else num/(t[-1]-t[0])
        lastps = 0 if t[-1]==t[-2] else 1/(t[-1]-t[-2])
        return {'frames':[len(t)],'fps':[fps,lastps]}
    return recordTime

def getImgInfo(img):
    try:
        if len(img.shape)==3:
            img = np.mean(1.0*img,2)
    except:
        return infoDict

    nY,nX = img.shape
    xySum = np.sum(img)

    y = np.arange(nY)@np.sum(img,1)/xySum
    x = np.sum(img,0)@np.arange(nX)/xySum

    num = np.sum(img>np.max(img)/np.e**2)
    r = np.sqrt(num/np.pi)

    return {'center':[x,y],
            'shape':[nX,nY],
            'radius':[r]}

class InfoPanel(wx.Panel):
    def __init__(self,parent,size,call):
        wx.Panel.__init__(self,parent,size)
        self.call = call
        self.isDynamic = True
        self.frameRecord = getFrameInfo()
        xyBox = wx.BoxSizer(wx.VERTICAL)

        self.infoText = {}
        for  key in infoDict:
            pBox = wx.BoxSizer()
            pBox.Add(wx.StaticText(self,label=key,size=(80,30)),flag=wx.RIGHT)
            self.infoText[key]=[
                wx.TextCtrl(self,size=(-1,30)) for _ in range(len(infoDict[key]))]
            for i in range(len(infoDict[key])):
                pBox.Add(self.infoText[key][i],proportion=1,flag=wx.LEFT|wx.RIGHT, border=5)
            xyBox.Add(pBox,flag=wx.TOP, border=10)
        
        stBtn = wx.Button(self,size=(-1,20),label="start")
        stBtn.Bind(wx.EVT_BUTTON,self.OnStart)
        xyBox.Add(stBtn, flag=wx.TOP, border=10)
        
        self.SetSizer(xyBox)
        pub.subscribe(self.OnInfo,"updateinfo")#将self.OnInfo绑定"updateinfo"标识，从setFrame中回传信息
    
    def OnStart(self,evt):
        self.isDynamic = not self.isDynamic
        self.frameRecord = getFrameInfo()
        if self.isDynamic:
            self.call()

    def OnInfo(self,msg):
        if not self.isDynamic:
            return
        self.imgInfo = msg
        self.imgInfo.update(self.frameRecord())
        for key in self.infoText:
            for i in range(len(self.infoText[key])):
                self.infoText[key][i].SetValue(str(msg[key][i]))
