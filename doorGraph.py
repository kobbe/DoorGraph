
""" program to make a graph from door log in moebius.

The input is sent with stdin so built in efficient metods like tail can be used in
order to not read a whole log file. Filters out dates that are prior to input --t (minutes)

The data is assumed to be on the from yyyymmddhhmmdds where s is o (open),c (closed) or e (error) 

Hans Koberg, 2015.

Either do own graph but with their ledgend?
Continuisgeneration?
Switch package?
Group the data into diff lenght intervals.
How do we see 1 closed in all open?
Generate same picture or new ones?

#Optimizing for speed!
Can reuse the same plot in order to save time and memmory

"""

#Create graphs directely, do not store any immediate file.


import argparse
import sys
#import numpy as np
import matplotlib
matplotlib.use('SVG') #Use SVG for speed!
#matplotlib.use('Agg')
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import datetime
import time
import re
import subprocess
#OFFSET = 30 #Which second to offset to
sys.stderr = open('/home/pi/doorgraph/errorlog.txt', 'a')
#sys.stdout = open('/home/pi/doorgraph/stdout.txt','a')
ERRLOG = "/home/pi/doorgraph/errorlog.txt"
LOG = "/home/pi/doorgraph/stdout.txt"


#Makes sure the time interval is >0
def positive_int(val):
    try:
        assert(int(val) > 0)
    except:
        raise ArgumentTypeError("'%s' is not a valid positive int" % val)
    return int(val)

if __name__ == "__main__":
    reg = re.compile('^[0-9]{14}(o|c|e)$')
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--timespan", dest='timeSpan', help="The number of minutes to show", type=positive_int)
    parser.add_argument("-o", "--output", help="output file to write picture to")
    parser.add_argument("-O", "--Offset",help="Offset seconds  when to run the plot on the minute",type=positive_int)
    parser.add_argument("-s", "--sleep",help="how long in minutes to sleep between plots",type=positive_int)
    parser.add_argument("file", help="Input file")
    args = parser.parse_args()
    sleepUntil = datetime.datetime.now().replace(second=args.Offset,microsecond=0) + datetime.timedelta(minutes=(args.sleep+1))
    while True:
        #print("after while True")
        endTime = datetime.datetime.now().replace(second=0,microsecond=0)
        log = [['y',endTime - i*datetime.timedelta(minutes=1)] for i in range(args.timeSpan -1,-1,-1)]
        output = subprocess.check_output(["tail","-n",str(args.timeSpan+60),str(args.file)])
        
        for line in output.decode("utf-8").split("\n"):
            if reg.match(line) != None:
                date = datetime.datetime.strptime(line[0:14],"%Y%m%d%H%M%S")
                if date >= log[0][1]:
                    index = int((date-log[0][1]).total_seconds()) // 60
                    if line[14:15] == 'o':
                        log[index][0] = 'green'
                    elif line[14:15] == 'c':
                        log[index][0] = 'r'
                    #else: #use this if error values should differ from missing values
                    #    log[index][0] = 'yellow'
        
        
        #print("Start after read input")
        #start = datetime.datetime.now()
        
        #log is never empty
        compressedLog = [log[0][1]]
        colors = [log[0][0]]
        widths = [1] #in fractions of days
        tempWidths = 1
        
        for (color,date) in log:
            if (color == colors[-1]):
                #same state, can be compressed, continue.
                tempWidths += 1
                widths[-1] = tempWidths/(24*60) #interval lenght +1
            else:
                #End the current streak
                compressedLog.append(date)
                widths.append(1/(24*60))
                tempWidths = 1
                colors.append(color)
        
        #color to state
        state = ["<font color='green'>Öppet</font>" if i=="green" else "<font color='red'>Strängt</font>" if i=="r" else "<font color='FFC200'>Ingen data</font>" for i in colors]
        
        #Save the intervals in a text file.
        with open(args.output + ".compressed.txt",'w') as f:
            for i in range(len(compressedLog)-1):
                f.write(compressedLog[i].strftime('%Y-%m-%d %H:%M:%S') + " till " + (compressedLog[i+1] -datetime.timedelta(minutes=1)).strftime('%Y-%m-%d %H:%M:%S ') + state[i] + '\n')
            f.write(compressedLog[-1].strftime('%Y-%m-%d %H:%M:%S') + " till " + (log[-1][1]).strftime('%Y-%m-%d %H:%M:%S ') + state[-1])
                
        if len(compressedLog) < 100*args.sleep: #Takes < 15s on the raspberry
            y = len(compressedLog)*[1]
            
            fig, ax = plt.subplots()
            ax.axes.get_yaxis().set_visible(False)
            fig.autofmt_xdate()
            
            #Sets the discription of colors box to the right of the graph
            closed_patch = mpatches.Patch(color='red', label='Stängt')
            open_patch = mpatches.Patch(color='green', label='Öppet')
            error_patch = mpatches.Patch(color='yellow', label='Ingen data')
            legend = plt.legend(handles=[open_patch,closed_patch,error_patch],loc=6, bbox_to_anchor=(1, 0.5))
            
            plt.title("Möbius dörr\n(Genererad: " + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ")")
            
            #Somehow I want to point out the time when it switches from open to closed for example so it is easier to
            #see exactely which time it opened/closed. Can not be to many points etc.
            #end = datetime.datetime.now()
            
            #print("Before theplot: ", end-start, " time")
            barlist = ax.bar(compressedLog,y,width=widths)
            for i,bar in enumerate(barlist): #Set colors
                bar.set_color(colors[i])
            ax.xaxis.set_major_formatter( mdates.DateFormatter('%Y-%m-%d %H:%M:00') )
            ax.xaxis_date()
            
            #end = datetime.datetime.now()
            #print("Before Savefig: ", end-start, " time")
            plt.savefig(args.output,bbox_extra_artists=(legend,), bbox_inches='tight')
            plt.close('all')
            #print("just saved fig")
            #end = datetime.datetime.now()
            #print("it took ", end-start, " time")
        else:
            with open(LOG,'a'):
                write("Was too many points: "+ str(len(compressedLog)) + " points")
        #print("before logging sleeptime")
        sleepSeconds = (sleepUntil-datetime.datetime.now()).total_seconds()
        with open(LOG,'a') as f:
            f.write("Sleeping to " + str(sleepUntil) + " which is " + str(sleepSeconds) + "seconds\n")
        #print("have logged sleep")
        time.sleep(sleepSeconds)
        sleepUntil = sleepUntil + datetime.timedelta(minutes=args.sleep)
    
    
    
    
    
    
