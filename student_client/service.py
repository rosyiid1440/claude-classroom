import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import time
from client import StudentClient

class ClassroomService(win32serviceutil.ServiceFramework):
    _svc_name_ = "ClaudeClassroomClient"
    _svc_display_name_ = "Claude Classroom Client"
    _svc_description_ = "Student client for the Claude Classroom Management System."

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)
        self.client = StudentClient()
        self.is_running = False

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        self.is_running = False
        self.client.stop()

    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_, ''))
        self.main()

    def main(self):
        self.is_running = True
        self.client.start()
        while self.is_running:
            time.sleep(1)

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(ClassroomService)