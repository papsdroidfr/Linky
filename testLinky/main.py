# main.py -- put your code here!

import pyb
from time import sleep

print('Linky start')

# pybstick lite à 48MHz, config UART
pyb.freq(48000000)
buffer_size = 128
info = pyb.UART(2, 1200, bits=7, parity=0, stop=1, timeout=0)

def lecture_linky():
    while True:
        tampon=info.read(buffer_size)
        print('tampon lu: ', tampon)
        sleep(0.5)

try:
    lecture_linky()
except KeyboardInterrupt:
    print('Bye')
