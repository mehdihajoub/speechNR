import requests
import threading

RequestAccess = "RequestAccess"
ListenTo = "ListenTo"
StopListenTo = "StopListenTo"
GetStimulationParameters = "GetStimulationParameters"
GetStimulationStatus = "GetStimulationStatus"
GetEventParameters = "GetEventParameters"
StimOn = "StimOn"
StimLine = "StimLine"
StimEvent = "StimEvent"
StimOff = "StimOff"
SetStimulationParameters = "SetStimulationParameters"
SetStimulationBlocks = "SetStimulationBlocks"
SetRelativeAmplitude = "SetRelativeAmplitude"
SetAmplitude = "SetAmplitude"
StartRecording = "StartRecording"
StopRecording = "StopRecording"
SetupDataReceiver = "SetupDataReceiver"

class GdpHttpClient:
    """
    Class for initializing the conditions of a http connection with GDP
    """
    def __init__(self, name, ip, port_number, unique_key=None):
        self.ip = ip
        self.port_number = port_number
        self.name = name
        self.info = 'GdpHttpClient instance'
        self.unique_key = unique_key
        self.lock = threading.Lock() # lock to use to keep all communications synchronized

    def make_Command(self, command, extra_parameters=None):
        """
        Make a Command instance optionally with a uniqueKey
        """
        url = ('http://' + self.ip + ':' + self.port_number + '/' + command + '?' + 
            'Name='   + self.name + '&' +
            'Info='   + self.info)
        if(self.unique_key != None):
            url = url + '&' + 'UniqueKey=' + self.unique_key

        if (extra_parameters != None and extra_parameters != ""):
            if (isinstance(extra_parameters, str) != True):
                raise Exception("Extra parameters to http request should be in the form of a string")
            url = url + extra_parameters
        
        if (command == "SetStimulationParameters" or command == "SetStimulationBlocks" or command == "SetupDataReceiver"):
            method = requests.post
        else:
            method = requests.get
        return Command(url, method, self.lock)


class Command:
    """
    Class for executing a single command prepared by the GdpHttpClient
    """
    def __init__(self, url, method, lock):
        self.url = url
        self.method = method
        self.lock = lock

    def Send(self):
        """
        Blocking, thread safe method. This method throws exceptions
        for connection issues
        """
        self.lock.acquire()
        # todo: log this (call and response)
        try:
            response = self.method(url = self.url)
        finally:
            self.lock.release()

        return response

    def TrySend(self):
        """
        Try to send the command, and inform the user
        of a missing setup with option to retry
        returns None if retry is not selected, otherwise
        http response
        """

        success = False
        while True:            
            try:
                response = self.Send()
                if 'Access not allowed' in response.text:
                    print("GDrive+StartupParameters.xml is not correctly set, fix it and restart GDP")
                elif 'No activity' in response.text:
                    print("Activity must be first uploaded")
                else:
                    success = True
            except: # todo: More precise exception
                print("Is Optimisation Gate running on GDP?")
        
            if success:
                return response

            answer = input("Retry connection y/n:")
            if(answer == 'y'):
                continue
            if(answer == 'n'):
                return None