#!/usr/bin/python3
#
# Using tplink.py to read tplink, and graph it for motor power experiments.  Apr 2022
# 
import time,sys

sys.path.insert(0, "..") # So it can run from the examples directory
import tplink


addr_end = 132 # Last octet of Ip4 address

columns = 100
per_hash = 20
interval = 1

#===========================================================================================
# Show big numbers top right of screen
#===========================================================================================
digits = [
"                                                                                                 ",
"                  @   @@@     @     @@@    @@@     @@   @@@@@   @@@   @@@@@   @@@    @@@         ",
"                  @  @   @   @@    @   @  @   @   @ @   @      @   @      @  @   @  @   @        ",
"                 @   @   @    @    @   @      @   @ @   @      @          @  @   @  @   @        ",
"                 @   @   @    @        @      @  @  @   @@@@   @         @   @   @  @   @        ",
" @@@@@          @    @   @    @       @     @@   @  @       @  @@@@      @    @@@    @@@@        ",
"               @     @   @    @      @        @  @@@@@      @  @   @    @    @   @      @        ",
"               @     @   @    @     @         @     @       @  @   @    @    @   @      @        ",
"         @@   @      @   @    @    @      @   @     @   @   @  @   @    @    @   @  @   @        ",
"         @@   @       @@@     @    @@@@@   @@@      @    @@@    @@@     @     @@@    @@@         "]

def ShowBigNum(x,y,str):
    print("\033[s", end="") # Save cursor position
    for line in range (10):
        linestr = "\033[%d;%dH"%(y+line,x) # position cursor.
        for cp in range(len(str)):
            if (str[cp] == " "):
                index = 13
            else:
                index = ord(str[cp])-45
                if index < 0 or index >= 14: index = 0
            index = index * 7
            linestr = linestr + digits[line][index:index+7]
        print (linestr.replace("@",u"\u2588")) # Print, but use solid block characters instead

    print("\033[u", end="") # restore cursor position


print("\033[0;97m") # Switch to brighgt white color

testinfo = " ".join(sys.argv[1:])
if len(testinfo) > 0: testinfo = " "+testinfo

filename = time.strftime("Pow %m%d-%H%M%S"+testinfo, time.localtime())
logfile = open(filename+".txt","w")
print("Test:",filename, file=logfile)

p_amps, p_volts, p_watts = tplink.TP_read_power(addr_end)
n=0
if interval == 1:
    while True:
        # Tplink only updtes values once per second, wait till after a value change to 
        # syncronize reading times to that to minimize latency.
        starttime = time.time()
        amps, volts, watts = tplink.TP_read_power(addr_end)
        if p_amps != amps or p_volts != volts or p_watts != watts: break; # New data.
        p_amps = amps
        p_volts = volts
        p_watts = watts
        n=n+1
        if n > 50: 
            print("Not syncronizing to level changes because level is not changing")
            break
        time.sleep(0.05)

next_time = starttime + 0.05 # give it some grace in case of jitter

while True:
    # Wait till even seconds since edge was seen.
    wait = next_time-time.time()
    if wait > 0: time.sleep(next_time-time.time())
    power = tplink.TP_read_power(addr_end)
    if power[2] > 2500: power = tplink.TP_read_power(ip_octet) # Probably bad reading, read again.
    logstr = time.strftime("%H:%M:%S,", time.localtime())
    numhashes = int((power[2])/per_hash + 0.5)
    if interval > 2: logfile = open(filename+".txt","a") # reopen log file each time so I can write other stuff to it too.
    print(logstr + "%5.2fA %5.1fV %4.1fW  "%power+ "#"*numhashes, file=logfile)
    if interval > 2: logfile.close()
    if numhashes > columns: numhashes = columns # don't wrap around
    print(logstr + "%5.2fA %5.1fV %4.1fW  "%power+ "#"*numhashes)
    ShowBigNum(60,1,"%4.1f"%power[2])
    next_time = next_time+interval
