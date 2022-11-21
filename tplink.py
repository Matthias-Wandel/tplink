#!/usr/bin/python3
#
# Short python program to control various TpLink smart plugs, sockets and switches.
#
import socket, struct, sys

addr_base = "192.168.0."
socket_timeout = 5 # Assumed on LAN.  If it takes more than 5 seconds, its not there.

#==============================================================================================
# Send / receive encrypted command
#==============================================================================================
def TP_send_command(ip_octet, cmd, list=0):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(socket_timeout) 
        sock.connect((addr_base+str(ip_octet), 9999))
    except KeyboardInterrupt:
        exit(-1) # So that ctrl-C works on list commend.
    except:
        if list: return "nc"
        exit(100)
        
    key = 171 # Encrypt
    encrypted = bytearray(struct.pack('>I', len(cmd)))
    for i in cmd:
        key = key ^ ord(i)
        encrypted.append(key)
    try:
        sock.send(encrypted)
        data = sock.recv(2048)
        sock.close()
    except: exit(101)

    key = 171 # Decrypt
    encrypted = data[4:]
    result = ""
    for i in encrypted:
        result += chr(i ^ key)
        key = i

    if result.find('"err_code":0') < 0:
        print("tp-link error: "+result)
        exit(102)
        
    return result

#==============================================================================================
# Turn HS100 (smart plug), HS110 (with energy monitor) or HS105, HS103 (mini) on smart switches on and off
#==============================================================================================
def TP_set_onoff(ip_octet, on_off, child_context = ""):
    cmd = '{"system":{"set_relay_state":{"state":'+str(on_off)+'}}'
    if child_context != "": cmd = cmd + ',"context":{"child_ids":["'+child_context+'"]}'
    return TP_send_command(ip_octet, cmd + '}');

#==============================================================================================
# Set dimmer value of HS220 smart dimmer
#==============================================================================================
def TP_set_dimmer(ip_octet, brightness, on_off = 1):
    cmd = '{"smartlife.iot.dimmer":{"set_brightness":{"brightness":'+str(brightness)+'}},"system":{"set_relay_state":{"state":'+str(on_off)+'}}}'
    return TP_send_command(ip_octet, cmd);

#==============================================================================================
# Retrieve on off value[s] of smart plugs and sockets
#==============================================================================================
def TP_get_onoff(ip_octet):
    cmd = '{"system":{"get_sysinfo":{}}}'
    resstr = TP_send_command(ip_octet, cmd);

    rsl = resstr.find('"relay_state":')
    if rsl > 0: return int(resstr[rsl+14:rsl+15])

    # Otherwise, multiple socket device (KP200)
    segs = (resstr.split('"state":')[1:])
    onoffs = []
    for s in segs:
        onoffs.append(int(s[:1]))

    return onoffs

#==============================================================================================
# Read power level from HS110 or KP115 smart plug with power monitoring
#==============================================================================================
def TP_read_power(ip_octet):
    resstr = TP_send_command(ip_octet, '{"emeter":{"get_realtime":{}}}');
    multiplier = 1
    if resstr.find('"power_mw"') > 0: multiplier = 0.001 # in milliwatts on KP115
    els = resstr.split(":")
    current = float((els[3].split(',')[0])[:6]) * multiplier
    volts   = float((els[4].split(',')[0])[:6]) * multiplier
    power   = float((els[5].split(',')[0])[:7]) * multiplier
    return current, volts, power




#----------------  Evertything above is what you need.  Everything below is example applications -----------------------






#==============================================================================================
# Find all the smart plugs on the lan in range x.x.x.100 to x.x.x.255
# becuse DHCP assignments typically start at 100.
#==============================================================================================
def TP_find_smartplugs():
    import threading, json # only pull in these libs if needed.
    def Detect_plug (i, seen):
        cmd = '{"system":{"get_sysinfo":{}}}'
        resstr = TP_send_command(i, cmd, 1);
        seen[i%num_threads] = 0
        if resstr.find('"get_sysinfo"') >= 0:
            struct = json.loads(resstr)["system"]["get_sysinfo"]
            alias = onoff = sep = ""
            if "children" in struct: # Multiple socket device, like KP200  Show each socket status
                onoff = alias = "("
                for ch in struct["children"]:
                    alias = alias + sep + ch["alias"]
                    onoff = onoff + sep + ("off","ON")[ch["state"]]
                    sep = ","
                onoff = onoff + ")"
                alias = alias + ")"
            else:
                alias = struct["alias"]
                onoff = ("","ON")[struct["relay_state"]]

            seen[i%num_threads] = addr_base+str(i), struct["model"], struct["rssi"], alias, onoff

    global socket_timeout
    socket_timeout = 2
    num_threads = 80
    threads = [0]*num_threads
    seen = [0]*num_threads
    i = 100;
    print("IP address,    Model,    RSSI, Alias,  [ON]")
    while i < 255+num_threads:
        ti = i % num_threads
        if threads[ti] != 0: threads[ti].join();
        if seen[ti] != 0: print ("%s, %s, %3d, %s, %s"%seen[ti])
        threads[ti] = 0
        if i < 256:
            threads[ti] = threading.Thread(target=Detect_plug, args=(i,seen,))
            threads[ti].start()
        i += 1;


#==============================================================================================
# Continuously monitor power.  tplink.py ADDR mon [interval] [count]
#==============================================================================================
def TP_power_monitor(ip_octet):
    import time

    delay = 0.96 # roughly once per second.  Meter's readings only update once per second anyway.
    if len(sys.argv) > 3: delay = float(sys.argv[3])

    count = 1000
    if len(sys.argv) > 4: count = int(sys.argv[4])

    while 1:
        (i,v,p) = TP_read_power(ip_octet)
        tm = time.localtime()
        timestr = time.strftime("%d-%b-%y %H:%M:%S ", tm)

        print(timestr,"%6.3fA  %5.1fV %6.1fW"%(i,v,p), "#"*int(p/10))
        count = count - 1
        if count <= 0: break

        time.sleep(delay) # Power reading only updates once per second.


#==============================================================================================
# Demonstrate what the above functions can do:
# Syntax: tplink.py ADDR FUNCTION
# Were ADDR is the last octet of the IP address, and FUNCTION is one of:
#     list, on, off, state, power, info, mon
#
# examples: tplink.py list
#           tplink.py 102 on
#           tplink.py 102 power
#==============================================================================================
if len (sys.argv) == 2 and __name__ == "__main__":
    if sys.argv[1] == "list": TP_find_smartplugs()

if len(sys.argv) >= 3 and __name__ == "__main__":
    ip_octet = sys.argv[1]
    if sys.argv[2] == "on" or sys.argv[2] == "off":
        child_context = ""; onoff = 0
        if len(sys.argv)== 4: child_context = sys.argv[3]
        if sys.argv[2] == "on": onoff = 1
        TP_set_onoff(ip_octet,onoff, child_context)
    elif sys.argv[2] == "state": print("onoff=%s"%TP_get_onoff(ip_octet))
    elif sys.argv[2] == "power": print("%6.3fA  %5.1fV %6.1fW"%TP_read_power(ip_octet))
    elif sys.argv[2] == "mon": TP_power_monitor(ip_octet)
    elif sys.argv[2] == "dimmer":
        if len(sys.argv)== 4:  TP_set_dimmer(ip_octet, int(sys.argv[3]))
        else: print("Need brightness.  Usage:\n  tplink.py <addr> dimmer <brightness>")
    elif sys.argv[2] == "info": 
        resstr = TP_send_command(ip_octet, '{"system":{"get_sysinfo":{}}}');
        indent = 0 # Print thee JSON structure that was returned, but with added lines and whitespace for readability
        for c in resstr:
            if c == '{' or c == '[':
                indent = indent + 1
                print(c+"\n"+"  "*indent,end="")
            elif c == '}' or c == ']':
                indent = indent - 1
                print("\n"+"  "*indent+c,end="")
            elif c == ',':
                print(",\n"+"  "*indent,end="")
            else:
                print(c,end="")
    else:
        print("Unknown option: "+sys.argv[2])
