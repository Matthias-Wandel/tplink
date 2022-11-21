#!/usr/bin/python3
# Log PC power usage over a longer period, best invoked from crontab.
# For short term power grapsh, use "pgraph.py"
import time, sys

sys.path.insert(0, "..") # So it can run from the examples directory
import tplink

addr_base = "192.168.0."
addr_end = 132 # Last octet of Ip4 address

socket_timeout = 10

# Measures every 30 seconds, continuous, multiple times or just once
# depending on command line argument
numrep = 1000000
if len(sys.argv) > 1: numrep = int(sys.argv[1])

print("Querying power using tplink.py every 30 seconds")
while 1:
    cvp  = tplink.TP_read_power(addr_end) # Where the HS110 is at the moment

    logstr = time.strftime("%d-%b-%y %H:%M:%S, ", time.localtime())
    c,v,p = cvp; logstr = logstr + "%5.1f, %3.0f,"%(p,v)
    numhashes = int(p/2)
    if numhashes > 80: numhashes = 80
    logstr = logstr + " "+("#"*int(numhashes/2))
    if numhashes & 1: logstr = logstr + ":"

    print (logstr)
    logfile =  open("powerlog.txt","a")
    print (logstr, file=logfile)
    logfile.close()


    numrep = numrep - 1
    if numrep <= 0: break

    time.sleep(30) 

