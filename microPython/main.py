# main.py -- put your code here!

import pyb, select, ssd1306
from machine import I2C, Pin
from pyb import ExtInt
from time import sleep, sleep_ms
from fdrawer import FontDrawer

_VERSION = 'v1.34 2020-11-22'


class Application:
    ''' appli principale '''
    def __init__(self):
        pyb.freq(48000000)           # pybstick lite 48MHz pour autoalimentation sur compteur Linky
        self.i2c=I2C(1, freq=400000) # init bus i2c 400KHz
        self.info = pyb.UART(2, 1200, bits=7, parity=0, stop=1, timeout=0)
        self.buffer_size = 128

        # initialisation dictionnaire index linky  'INDEXE' : [taille, 'unité', 'valeur']
        self.idx = {'HCHC':   [6,'Wh','xxxxx'], # indexe heure creuses (Wh)
                    'HCHP':   [6,'Wh','xxxxx'], # indexe heures pleines (Wh)
                    'BASE':   [6,'Wh','xxxxx'], # indexe base (Wh)
                    'PAPP':   [5,'W','xxxxx'],  # puissance apparante (W)
                    'ISOUSC': [2,'A','xx'],     # intensitée souscrite (A)
                    'PTEC':   [2,'','xx'],      # période tarrifaire en cours
                    'OPTARIF':[4,'','xxxx'],    # option tarrifaire
                   }

        # Initialisation afficheur
        self.afficheur=Afficheur_i2c(self.i2c)

    def print_idx(self):
        ''' print les indexes '''
        str = 'indexes lus: '
        for idx in self.idx:
            str = str + idx + ":" + self.idx[idx][2] + " | "
        print(str)

    def loop(self):
        ''' boucle principale de l'appli'''
        while True:
            tampon=self.info.read(self.buffer_size)  #tampon est un tableau de bytes
            print('tampon lu:',tampon) # debug
            if tampon != None:         # décodage tampon dans le dictionnaire self.idx
                for index in self.idx:
                    x=tampon.find(b'\n'+index) #les indexes sont tjrs devant un \n
                    x_debut = x + len(index) + 2
                    x_end = x_debut + self.idx[index][0]
                    if x>=0 and x_end < len(tampon):
                        self.idx[index][2] = tampon[x_debut : x_end].decode()
            self.print_idx() #debug

            if self.afficheur.etat:
                if self.afficheur.id_affichage == 0:
                    self.afficheur.display_w(self.idx)
                else:
                    self.afficheur.display_contrat(self.idx)


    def destroy(self):
        ''' destructeur '''
        print('Bye')
        self.afficheur.off() #extinction écran Oled


class Afficheur_i2c:
    def __init__(self, i2c):
        ''' constructeur'''
        self.oled = ssd1306.SSD1306_I2C(width=128, height=64, i2c=i2c, addr=0x3c, external_vcc=False)
        self.oled.init_display()
        self.oled.rotate(True)                     # rotation écran 180°
        self.nb_affichages = 2                     # nb d'affichages total
        self.id_affichage = 0                      # id affichage en cours
        self.etat = True                           # True: ecran actif
        self.buttonOnOff = pyb.Switch()            # bouton user A pybstick: on/off écran OLED
        self.buttonOnOff.callback(self.switchEtat) # callback appelé avec bouton user A
        self.buttonAffichage = Pin( 'SW2', Pin.IN) # bouton user B: change l'affichage
        self.extint = ExtInt('SW2', ExtInt.IRQ_FALLING, Pin.PULL_NONE, self.switchAffichage) #callback bouton user B

    def switchAffichage(self, line):
        sleep_ms(50) # stabilisation 50 ms pour éviter faux rebonds
        if not(self.buttonAffichage.value()): # bouton tjrs enfoncé après stabilisation ?
            self.id_affichage = (self.id_affichage + 1) % self.nb_affichages
            print('affichage num:', self.id_affichage) #debug

    def switchEtat(self):
        ''' switch etat on/off écran OLED '''
        self.etat = not(self.etat)
        if not(self.etat):
            self.off()
        else:
            self.oled.poweron()

    def off(self):
        ''' extinction éran oled'''
        self.oled.fill(0)
        self.oled.show()
        self.oled.poweroff()

    def display_cadres(self):
        ''' affichage des cadres '''
        # cadres
        self.oled.fill(0)
        self.oled.rect( 0, 0, 128, 64, 1 )
        self.oled.line( 92, 30, 92, 64, 1 )
        self.oled.line( 0, 30, 128, 30, 1 )

    def display_w(self, idx):
        ''' affichage puissance W '''
        self.display_cadres()
        fd = FontDrawer( frame_buffer=self.oled, font_name = 'vera_23' )
        fd.print_str(idx['PAPP'][2], 16, 5 )   # valeur PAPP
        fd.print_str(idx['PAPP'][1], 100, 5 )  # unite PAPP
        fd.print_str(idx['PTEC'][2], 96, 36 )  # valeur PTEC
        fd = FontDrawer( frame_buffer=self.oled, font_name = 'vera_15' )
        if idx['PTEC'][2] != 'TH' : #tarif heure creuse
            fd.print_str("HP:", 8, 30 )
            fd.print_str("HC:", 8, 46 )
            fd.print_str(idx['HCHP'][2], 35, 30 )  # valeur HCHP
            fd.print_str(idx['HCHC'][2], 35, 46 )  # valeur HCHC
        else: #tarif base
            fd.print_str('Wh:', 8, 38 )
            fd.print_str(idx['BASE'][2], 38, 38 )  # valeur index base
        if self.etat: self.oled.show()

    def display_contrat(self, idx):
        ''' affichage données du contrat '''
        self.display_cadres()
        fd = FontDrawer( frame_buffer=self.oled, font_name = 'vera_23' )
        fd.print_str('CONTRAT', 8, 5 )
        fd.print_str(idx['PTEC'][2], 96, 36 )  # valeur PTEC
        fd = FontDrawer( frame_buffer=self.oled, font_name = 'vera_15' )
        fd.print_str('TARIF:', 8, 30 )
        fd.print_str('I(A):', 26, 46 )
        fd.print_str(idx['OPTARIF'][2], 54, 30 )  # option tarrifaire
        fd.print_str(idx['ISOUSC'][2], 54, 46 )   # intensité souscrite
        if self.etat: self.oled.show()


#--- script principal
print('linky start ', _VERSION)
appl=Application()

try:
    appl.loop()
except KeyboardInterrupt:
    appl.destroy()

