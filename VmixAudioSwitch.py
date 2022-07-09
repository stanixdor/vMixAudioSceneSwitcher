import pyaudio
import audioop
import math
import requests
import time
import keyboard

# Some constants for setting PyAudio
BUFFER_SIZE             = 2048
CHANNELS                = 2
FORMAT                  = pyaudio.paInt16
SAMPLE_RATE             = 48000
HOP_SIZE                = BUFFER_SIZE//2
PERIOD_SIZE_IN_FRAME    = HOP_SIZE


class InputDevice:
    #init microphone, be sure about the device index. If it fails, check channels/rate parameters
    def __init__(self, i, pAudio):
        self.index = i
        #mic instance creation
        self.mic = pAudio.open(format=FORMAT, channels=CHANNELS, rate=SAMPLE_RATE, input=True, frames_per_buffer=PERIOD_SIZE_IN_FRAME, input_device_index=i, output=False)
        self.decibels = []
        self.averageDecibels = -999.99
        

    def AddFrame(self):
        data = self.mic.read(PERIOD_SIZE_IN_FRAME)

        #WTF is this 32767 magic number -_-
        #RMS stands for root mean square (media cuadratica)
        rms = audioop.rms(data, 2) / 32767

        #here you could probaby use -math.inf for initialization
        decibel = -999.99
        if rms != 0.0: #sanity check to avoid math error
            #no idea how this really works, but it gets the decibel output :)
            decibel = 20 * math.log10(rms)
        
        #add decibel measurement to the list
        self.decibels.append(decibel)

    def UpdateAverage(self):
        #get total decibel average from last X seconds and reset list
        totalDecibles = 0.0
        for d in self.decibels:
            totalDecibles += d
        self.averageDecibels = totalDecibles / len(self.decibels)

        self.decibels.clear()
    

    def __del__(self):
        #ensure proper object destruction / free resources
        self.mic.stop_stream()
        self.mic.close()

def main():
    # Initialize PyAudio
    pA = pyaudio.PyAudio()

    #don't pay attention to this
    # print(int(pA.get_default_input_device_info()['defaultSampleRate']))
    # print(pA.get_default_input_device_info()['index'])
    # print(pA.get_default_input_device_info())

    #update logic every "updateRate" seconds
    updateRate = 2.0
    elapsedTime = 0.0
    #more fps will mean more decibel samples, more data, thus more accuracy
    fps = 59.94
    maxDeltaTime = 1.0/fps
    
    #display every device by index, usefull to identify every device, both input and output
    for i in range(0, pA.get_device_count()):
        print(i, pA.get_device_info_by_index(i)['name'])

    #create new device input instances
    elgato = InputDevice(1,pA)
    cam = InputDevice(4,pA)

    #press ctrl + * to terminate program
    while not keyboard.is_pressed('ctrl + *'):
        start = time.perf_counter()

        #if enough time is elapsed, update average volume levels for your input devices and check your logic
        if elapsedTime >= updateRate:
            elapsedTime = 0
            elgato.UpdateAverage()
            cam.UpdateAverage()

            #debug info, display average decibels of your input devices for the last X seconds(updateRate)
            print(f'elgato {elgato.averageDecibels}')
            print(f'cam {cam.averageDecibels}')

            #implement your logic here to switch your vmix scenes based on different microphone volume levels
            if elgato.averageDecibels < -40.0 and cam.averageDecibels < -40.0:
                #Vmix request example, Fade to promo scene with a 800 miliseconds duration
                r = requests.get('http://127.0.0.1:8088/api/?Function=Fade&Duration=800&Input=promo')
            elif elgato.averageDecibels > -30.0 and cam.averageDecibels > -30.0:
                r = requests.get('http://127.0.0.1:8088/api/?Function=Cut&Input=screen')
            elif cam.averageDecibels > -30.0:
                r = requests.get('http://127.0.0.1:8088/api/?Function=Cut&Input=cam')
        
        #add volume levels of your input devices
        elgato.AddFrame()
        cam.AddFrame()

        #wait until maxdeltatime based on your preferred fps to avoid overworking
        while maxDeltaTime > (time.perf_counter() - start):
            pass
        #proper way to do this, not doing it because time.sleep is kind of inaccurate
        # deltatime = time.perf_counter() - start
        # if maxDeltaTime > deltatime:
        #     timeToSleep = maxDeltaTime - deltatime
        #     time.sleep(timeToSleep)

        elapsedTime += time.perf_counter() - start

    #shut down PyAudio system
    pA.terminate()


if __name__ == "__main__":
    main()