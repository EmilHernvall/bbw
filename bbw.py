# Copyright (c) 2015 WaveShare
# Author: My MX
import smbus
import time
import spidev as SPI
import SSD1306
import random
from math import pi
from BMP180 import BMP180
from PIL import Image

def beep(bus, address, dur):
    try:
        bus.write_byte(address,0x7F&bus.read_byte(address))
        time.sleep(dur)
    except: pass
    bus.write_byte(address,0x80|bus.read_byte(address))

STATE_PLAYING = 0
STATE_WINANIM = 1
STATE_GAMEWON = 2
STATE_PENDINGRESTART = 3

FRAMES_PER_SECOND = 30
WINANIM_DURATION = FRAMES_PER_SECOND*2


# load assets
splash = Image.open('splash2.png').convert('1')
restart = Image.open('restart2.png').convert('1')
wonscreenimg = Image.open('won_screen2.png').convert('1')

houseimg = Image.open('hus.png').convert('1')
iw, ih = houseimg.size

# bus
iobus = smbus.SMBus(1)
address = 0x20

# pressure sensor
bmp = BMP180()

# Raspberry Pi pin configuration:
RST = 19
DC = 16
bus = 0
device = 0

# 128x32 display with hardware I2C:
disp = SSD1306.SSD1306(rst=RST,dc=DC,spi=SPI.SpiDev(bus,device))

# Initialize library.
disp.begin()

# Clear display.
disp.clear()

display_img = Image.new(houseimg.mode, (128,64))
display_img.paste(splash, (0, 0))
disp.image(display_img)
disp.display()

time.sleep(3)

skew = 0
pressure = 100000
pressure_alpha = 0.9
started = False
state = STATE_PLAYING
winanim_frame = 0
while True:
    cur_pressure = bmp.read_pressure()
    pressure = pressure_alpha * pressure + (1 - pressure_alpha) * cur_pressure

    #print "Pressure:    %.2f hPa" % pressure
    #print "Current Pressure:    %.2f hPa" % cur_pressure

    skew = 10*abs(cur_pressure - pressure)/100

    if skew < 3: started = True
    if not started: 
        continue

    if skew > 300 and state != STATE_WINANIM: 
        state = STATE_WINANIM
        beep(iobus, address, 1)

    display_img = Image.new(houseimg.mode, (128,64))

    if state == STATE_PLAYING:
        print "skew=%d" % (skew,)

    	for row in xrange(0, 64):
    		cur_skew = int(skew * (ih-row) / float(ih))
    		row_img = houseimg.crop((0, row, iw, row+1))
    		display_img.paste(row_img, (32 + cur_skew, row))
    elif state == STATE_WINANIM:
        print "winanim: %d of %d" % (winanim_frame, WINANIM_DURATION)
        winanim_progress = winanim_frame / float(WINANIM_DURATION)
        houseimg2 = houseimg.resize((int(iw * (1 - winanim_progress)), int(ih * (1 - winanim_progress)))).rotate(winanim_progress * 3 * 360, expand=True)
        display_img.paste(houseimg2, (32 + iw/2, 0))

        winanim_frame += 1
        if winanim_frame > WINANIM_DURATION:
            winanim_frame = 0
            state = STATE_GAMEWON
    elif state == STATE_GAMEWON:
        display_img.paste(wonscreenimg, (0, 0))
        state = STATE_PENDINGRESTART
    else:
        time.sleep(5)
        display_img.paste(restart, (0, 0))
        disp.image(display_img)
        disp.display()
        while True:
            iobus.write_byte(address,0x0F|iobus.read_byte(address))
            value = iobus.read_byte(address) | 0xF0
            print "value=%x" % (value,)
            if value != 0xFF:
                state = STATE_PLAYING
                break
            time.sleep(0.1)

    # Display image.
    disp.image(display_img)
    disp.display()

    time.sleep(1/float(FRAMES_PER_SECOND))
