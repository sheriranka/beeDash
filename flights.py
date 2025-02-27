#imports

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
from scipy import stats
import warnings


#setup bee flight itinerary
#extract flights from individual bee
#input: dataframe equivalent to single bee
#output: new dataframe with locations of bee over time
#works with already processed data

def classifyTrips(dataset):
    loc = []
    start = []
    end = []
    bee = dataset
    
    for i in range(len(bee)-1):
        cur = bee.iloc[i]
        next = bee.iloc[i+1]
    
        #Add time spent on ramp
        start.append(cur['starttime'])
        loc.append("Ramp")
        end.append(cur['endtime'])
    
    
        if cur['event'] == "entering" and next['event'] == "leaving":
            loc.append("Inside")
        elif cur['event'] == "leaving" and next['event'] == "entering":
            loc.append("Outside")
        else:
            if (next['starttime'] - cur['endtime']).total_seconds() > 300:
                if cur['event'] == "leaving":
                    loc.append('Outside')
                else:
                    loc.append('Inside')
            else: 
                loc.append("Ramp")
    
        start.append(cur['endtime'])
        end.append(next['starttime'])

    BeeTravel = pd.DataFrame({'location': loc, 'start': start, 'end': end}) 
    
    #classify short outside/insides as part of another group
    flight = ['inside'] * len(BeeTravel)
    
    #Classify short flights as inside-short
    for i in range(2,len(BeeTravel)-2):
        if BeeTravel['location'].iloc[i] != "Ramp" and (BeeTravel['end'].iloc[i] - BeeTravel['start'].iloc[i]).total_seconds() < 300:
            BeeTravel['location'].iloc[i] = BeeTravel['location'].iloc[i-2]
            if BeeTravel['location'].iloc[i] == "Inside":
                flight[i] = 'inside-short'

    #Classify outside flights depending on length
    for i in range(len(BeeTravel)):
        if BeeTravel['location'].iloc[i] == "Outside":
            if (BeeTravel['end'].iloc[i] - BeeTravel['start'].iloc[i]).total_seconds() < 600:
                flight[i] = "outside-short"
            elif (BeeTravel['end'].iloc[i] - BeeTravel['start'].iloc[i]).total_seconds() < 7200: #2 hrs
                flight[i] = "outside-foraging"
            else:
                flight[i] = "outside-long"

    
    for i in range(len(BeeTravel)):
        if BeeTravel['location'].iloc[i] == "Ramp":
            flight[i] = "Ramp"

    
    BeeTravel['activity'] = flight

    return BeeTravel
    