import uno
import string
import unohelper
import xmlrpclib
from com.sun.star.task import XJobExecutor
if __name__<>"package":
    from lib.gui import *
    from lib.error import ErrorDialog
    from lib.functions import *
    from Change import *

class ServerParameter( unohelper.Base, XJobExecutor ):
    def __init__(self,ctx):
        self.ctx     = ctx
        self.module  = "tiny_report"
        self.version = "0.1"
        desktop=getDesktop()
        doc = desktop.getCurrentComponent()
        docinfo=doc.getDocumentInfo()
        self.win=DBModalDialog(60, 50, 160, 108, "Server Connection Parameter")

        self.win.addFixedText("lblVariable", 2, 12, 60, 15, "Server URL")
        res=getConnectionStatus(docinfo.getUserFieldValue(0))
        if res == -1:
            ErrorDialog("Could not connect to the server!","")
        elif res == 0:
            ErrorDialog("No Database found !!!","")

        self.win.addEdit("txtHost",-34,9,91,15,docinfo.getUserFieldValue(0))
        self.win.addButton('btnChange',-2 ,9,30,15,'Change'
                      ,actionListenerProc = self.btnChange_clicked )

        self.win.addFixedText("lblDatabaseName", 6, 31, 60, 15, "Database")
        #self.win.addFixedText("lblMsg", -2,28,123,15)
        self.win.addComboListBox("lstDatabase", -2,28,123,15, True)
        self.lstDatabase = self.win.getControl( "lstDatabase" )
        for i in range(res.__len__()):
            self.lstDatabase.addItem(res[i],i)
        #self.win.selectListBoxItem( "lstDatabase", docinfo.getUserFieldValue(2), True )
        #self.win.setEnabled("lblMsg",False)

        self.win.addFixedText("lblLoginName", 17, 51, 60, 15, "Login")
        self.win.addEdit("txtLoginName",-2,48,123,15,docinfo.getUserFieldValue(1))

        self.win.addFixedText("lblPassword", 6, 70, 60, 15, "Password")
        self.win.addEdit("txtPassword",-2,67,123,15)

        self.win.addButton('btnOK',-2 ,-5, 60,15,'Test Connection'
                      ,actionListenerProc = self.btnOkOrCancel_clicked )

        self.win.addButton('btnCancel',-2 - 60 - 5 ,-5, 35,15,'Cancel'
                      ,actionListenerProc = self.btnOkOrCancel_clicked )

        self.win.doModalDialog("lstDatabase",docinfo.getUserFieldValue(2))

    def btnOkOrCancel_clicked(self,oActionEvent):
        if oActionEvent.Source.getModel().Name == "btnOK":
            sock = xmlrpclib.ServerProxy(self.win.getEditText("txtHost")+'/xmlrpc/common')
            sDatabase=self.win.getListBoxSelectedItem("lstDatabase")
            sLogin=self.win.getEditText("txtLoginName")
            sPassword=self.win.getEditText("txtPassword")
            UID = sock.login(sDatabase,sLogin,sPassword)
            if not UID:
                ErrorDialog("Connection Refuse...","Please enter valid Login/Password")
            else:
                desktop=getDesktop()
                doc = desktop.getCurrentComponent()
                docinfo=doc.getDocumentInfo()
                docinfo.setUserFieldValue(0,self.win.getEditText("txtHost"))
                docinfo.setUserFieldValue(1,self.win.getEditText("txtLoginName"))
                global passwd
                passwd=self.win.getEditText("txtPassword")
                global loginstatus
                loginstatus=True
                docinfo.setUserFieldValue(2,self.win.getListBoxSelectedItem("lstDatabase"))
                docinfo.setUserFieldValue(3,"")
                self.win.endExecute()
        elif oActionEvent.Source.getModel().Name == "btnCancel":
            self.win.endExecute()

    def btnChange_clicked(self,oActionEvent):
        aVal=[]
        Change(aVal)
        if aVal[1]== -1:
            ErrorDialog(aVal[0],"")
        elif aVal[1]==0:
            ErrorDialog(aVal[0],"")
        else:
            self.win.setEditText("txtHost",aVal[0])
            for i in range(aVal[1].__len__()):
                self.lstDatabase.addItem(aVal[1][i],i)


if __name__<>"package" and __name__=="__main__":
    ServerParameter(None)
elif __name__=="package":
    g_ImplementationHelper.addImplementation( \
            ServerParameter,
            "org.openoffice.tiny.report.serverparam",
            ("com.sun.star.task.Job",),)

