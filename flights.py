#imports

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from scipy import stats
from numpy.linalg import norm
import warnings


#setup bee flight itinerary
#extract flights from individual bee
#input: dataframe equivalent to single bee
#output: new dataframe with locations of individual bee over time
#works with already processed data

#max time of trip
t3 = 21600

def classifyLoc(dataset):

    loc = []
    start = []
    end = []
    age = []
    bee = dataset
    
    for i in range(len(bee)-1):
        cur = bee.iloc[i]
        next = bee.iloc[i+1]
        if cur['event'] == "entering" and next['event'] == "exiting":
            loc.append("Inside")
            start.append(cur['datetime'])
            end.append(next['datetime'])
        elif cur['event'] == "exiting" and next['event'] == "entering":
            loc.append("Outside")
            start.append(cur['datetime'])
            end.append(next['datetime'])
        elif cur['event'] == "entering" and next['event'] == "entering":
            loc.append("Inside-Unknown")
            start.append(cur['datetime'])
            end.append(next['datetime'])
        else:
            loc.append("Outside-Unknown")
            start.append(cur['datetime'])
            end.append(next['datetime'])
            
        age.append((cur['datetime'] - bee['datetime'].iloc[0]).days)

    #new dataset with inside/outside and time start/end
    BeeTravel = pd.DataFrame({'location': loc, 'start': start, 'end': end, 'age':age}) 
    
    #classify short outside/insides as part of another group
    flight = ['undefined'] * len(BeeTravel)
    

    #Classify outside flights depending on length
    for i in range(len(BeeTravel)):
        if BeeTravel['location'].iloc[i] == "Outside":
            if (BeeTravel['end'].iloc[i] - BeeTravel['start'].iloc[i]).total_seconds() < 300:
                flight[i] = "outside-short"
            elif (BeeTravel['end'].iloc[i] - BeeTravel['start'].iloc[i]).total_seconds() < 7200: #2 hrs
                flight[i] = "outside-foraging"
            else:
                flight[i] = "outside-long"
        elif BeeTravel['location'].iloc[i] == "Inside":
            flight[i] = "inside"
            


    BeeTravel['activity'] = flight
    return BeeTravel


#run previous function for all bees in dataset
#input: dataframe with all bees
#output: dataframe with activity of all bees

def cleanData(data):

    newdataset = {'tagID':[],'tripStart':[],'tripEnd':[]}
    activity = []
    for b in pd.unique(data['tagID']):
        dataset = classifyLoc(data[data['tagID'] == b])
        dataset = dataset.assign(tagID = b)
        activity.append(dataset)
        for index, row in dataset.iterrows():
            if row['location'] == "Outside":
                newdataset['tagID'].append(b)
                newdataset['tripStart'].append(row['start'])
                newdataset['tripEnd'].append(row['end'])


    allActivity = pd.concat(activity, axis = 0) 
    
    df = pd.DataFrame.from_dict(newdataset)
    df['duration'] = df['tripEnd'] - df['tripStart']

    return allActivity, df
    
#setup bee hive summary
#creates summary of all data
#input: both dataframes from previous function
#output: summary of all bees


def summaryData(activity,flights):
    beeIDs = pd.unique(activity['tagID'])
    firstSeen = []
    lastSeen = []
    firstFlight = []
    lastFlight = []
    avgTrip = []
    medianTrip = []
    longestFlight = []
    shortestFlight = []
    numTrips = []
    tripsPerDay = []
    
    for b in beeIDs:
    
        indFlight = flights[flights['tagID'] == b].reset_index()
        
        beeDF = activity[activity['tagID'] == b].reset_index()
        firstSeen.append(beeDF['start'].iloc[0].replace(microsecond=0))    
        lastSeen.append(beeDF['end'].iloc[len(beeDF)-1].replace(microsecond=0))
        if len(indFlight) > 0:
            firstFlight.append(indFlight['tripStart'].iloc[0].replace(microsecond=0))
            lastFlight.append(indFlight['tripStart'].iloc[len(indFlight)-1].replace(microsecond=0))
        else:
            firstFlight.append(pd.NA)
            lastFlight.append(pd.NA)
        avgTrip.append(flights[flights['tagID'] == b]['duration'].mean())
        medianTrip.append(flights[flights['tagID'] == b]['duration'].median())
        numTrips.append(len(flights[flights['tagID'] == b]['duration']))

        #average flights per day
        indFlight['day'] = indFlight['tripStart'].apply(lambda x: x.date())
        #trips per day
        tpd = indFlight['day'].value_counts().sum()
        divisor = (lastSeen[-1].date() - firstSeen[-1].date()).days + 1
        tripsPerDay.append(tpd/divisor)
        
        if len(flights[flights['tagID'] == b]) > 0:
             #longest flight per bee
            longest = flights[flights['tagID'] == b]['duration'].idxmax()
            mins = int(flights.iloc[longest]['duration'].total_seconds()//60)%60
            if mins < 10:
                mins = f'0{mins}'
            longestLen = f"{int(flights.iloc[longest]['duration'].total_seconds()//3600)}:{mins}"
            longestFlight.append(f"{flights.iloc[longest]['tripStart'].replace(microsecond=0)} ~ {longestLen}")
            #shortest flight per bee
            shortest = flights[flights['tagID'] == b]['duration'].idxmin()
            mins = int(flights.iloc[shortest]['duration'].total_seconds()//60)%60
            if mins < 10:
                mins = f'0{mins}'
            shortestLen = f"{int(flights.iloc[shortest]['duration'].total_seconds()//3600)}:{mins}"
            shortestFlight.append(f"{flights.iloc[longest]['tripStart'].replace(microsecond=0)} ~ {shortestLen}")
            
        else:
            longestFlight.append(pd.NA)
            shortestFlight.append(pd.NA)

    avg = []
    for i in avgTrip:
        mins = (i.seconds//60)%60
        if mins < 10:
            mins = f'0{mins}'
        avg.append(f'{i.seconds//3600}:{mins}')
    avgTrip = avg
    
    beeDict = {"tagID":beeIDs, "First Seen":firstSeen, "Last Seen":lastSeen, 'First Flight':firstFlight, 'Last Flight':lastFlight, 'Longest Flight': longestFlight, 'Shortest Flight': shortestFlight, "Average Length of Flights":avgTrip, "# of Flights":numTrips, 'Average Flights per Day':tripsPerDay}
    beeSummary = pd.DataFrame.from_dict(beeDict)
    return beeSummary
   

#setup bee hive summary 2
#creates summary of all data 2
#input: previous dataframe
#output: max and min flights of all hive
    
def makeTotalSum(summary, flights):
    #general overview
    totalFlights = sum(summary['# of Flights'])
    flights['day'] = flights['tripStart'].apply(lambda x: x.date())
    totalPerDay = flights['day'].value_counts().mean()
    totalLength = flights['duration'].mean()
    totalLength = totalLength.total_seconds()/60

    #longest and shortest flights
    longest = flights['duration'].idxmax()
    shortest = flights['duration'].idxmin()

    longestDate = flights.iloc[longest]['tripStart']
    longestID = flights.iloc[longest]['tagID']
    longestLen = flights.iloc[longest]['duration'].total_seconds()/60

    shortestDate = flights.iloc[shortest]['tripStart']
    shortestID = flights.iloc[shortest]['tagID']
    shortestLen = flights.iloc[shortest]['duration'].total_seconds()/60

    #create tables
    #general info
    totalDict = {"Total Flights":totalFlights, "Avg Flights per Day":totalPerDay, "Avg Length per Day (minutes)":totalLength}
    totalSum = pd.DataFrame.from_dict(totalDict, orient='index')
    totalSum = totalSum.rename(columns={0: "Overall Statistics"})

    #info on longest/shortest trip
    tripDict = {"Classification":["Longest Flight", "Shortest Flight"],"Date":[longestDate, shortestDate], "BeeID":[longestID, shortestID], "Length (minutes)":[longestLen, shortestLen]}
    tripSum = pd.DataFrame.from_dict(tripDict)
    
    return totalSum, tripSum
    
    
#divide groups into morning/afternoon focused
#additionally, create vectors of all bee hour distribution
#input: all flights
#output: dictionary with morning/afternoon/even split
#output: dictionary with all vectors of bees
def divideBees(dataset):
    hour = dataset['hour'].unique()
    hour.sort()
    split = np.where(hour == 12)[0][0]
    final = {"morning":[],"afternoon":[],"even":[]}
    vectors = {}
    #print(split)
    for i in dataset['tagID'].unique():
        bee = dataset[dataset['tagID'] == i]
        data, bins = np.histogram(bee['hour'], bins=hour,density=True)
        #print(i)
        #print(data)
        morning = sum(data[0:split])
        afternoon = sum(data[split:])
        if morning > 0.7:
            final['morning'].append(i)
        elif afternoon > 0.7:
            final['afternoon'].append(i)
        else:
            final['even'].append(i)

        vectors[str(i)] = data.tolist()
            
    return final,vectors
        
        
#find cosine similarity between all bee vectors
#input: vector dictionary and desired tagID
#output: list of tagIDs with similar vectors
def findSimilar(vectors, tagID):
    similars = []
    current = vectors[str(tagID)]
    for key,value in vectors.items():
        A = value
        B = current
        cosine = np.dot(A, B) / (norm(A) * norm(B))
        if cosine > 0.8:
            similars.append(key)
    return(similars)

