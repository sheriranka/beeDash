from suntime import Sun
import pytz
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import io
import base64
import datetime

#functions for graphing

#graph color constants
orange = "rgb(255, 199, 164)"
blue =  "rgb(199, 199, 255)"

#get sunrise/sunset for selected dates
def getSRSS(dataset, tz, lat, lon):
    dates = dataset['start'].apply(lambda x: x.date()).sort_values()
    dates = dates.unique()
    sunrise = []
    sunset = []
    sun = Sun(lat, lon)
    for d in dates:
        dT = datetime.datetime(d.year, d.month, d.day)
        sunrise.append(sun.get_sunrise_time(dT).astimezone(tz).time())
        sunset.append(sun.get_sunset_time(dT).astimezone(tz).time())

    srss = pd.DataFrame.from_dict({"date":dates,"sunrise":sunrise,"sunset":sunset})
    return srss


#fix up data
#separated by date for pseudo-actogram
def separateFlights(flights,missing=False,timeam="08:00:00",timepm="18:00:00"):
    newdata = []
    
    for i in range(len(flights)):
        row = flights.iloc[i].copy()
        row['day'] = row['tripStart'].to_pydatetime().day
        day = row['day']
        month0 = row['tripStart'].to_pydatetime().month
        month1 = row['tripEnd'].to_pydatetime().month
        
        if row['tripStart'].to_pydatetime().day != row['tripEnd'].to_pydatetime().day:
            #first day
            newentry = row.copy()
            newentry['tripEnd'] = row['tripEnd'].replace(hour=23,minute=59,second=59,day=1)
            newentry['tripStart'] = row['tripStart'].replace(day=1)
            newentry['date'] = f'{month0}/{day}'
            newdata.append(newentry)
            #second day
            newday = row['tripEnd'].to_pydatetime().day
            newentry = row.copy()
            newentry['tripStart'] = row['tripStart'].replace(day=1,hour=0,minute=0,second=0)
            newentry['tripEnd'] = row['tripEnd'].replace(day=1)
            newentry['day'] = newday
            newentry['date'] = f'{month1}/{newday}'
            newdata.append(newentry)
        else:
            newentry = row.copy()
            newentry['tripStart'] = row['tripStart'].replace(day=1)
            newentry['tripEnd'] = row['tripEnd'].replace(day=1)
            newentry['date'] = f'{month0}/{day}'
            newdata.append(newentry)

    if missing:
        cutoffday = str(newentry['tripStart'].date())
        #Extra for missing dataset
        for i in range(len(newdata)):
            cutoffpm = datetime.strptime(cutoffday + " " + timepm,"%Y-%m-%d %H:%M:%S")
            cutoffam = datetime.strptime(cutoffday + " " + timeam,"%Y-%m-%d %H:%M:%S")
            if newdata[i]['tripEnd'] >= cutoffpm:
                newrow = newdata[i].copy()
                newdata[i]['tripEnd'] = cutoffpm
                newdata[i]['Data'] = 'Available'
                newrow['tripStart'] = cutoffpm
                newrow['Data'] = 'Missing'
                newdata.append(newrow)
            elif newdata[i]['tripStart'] <= cutoffam:
                newrow = newdata[i].copy()
                newdata[i]['tripStart'] = cutoffam
                newdata[i]['Data'] = 'Available'
                newrow['tripEnd'] = cutoffam
                newrow['Data'] = 'Missing'
                newdata.append(newrow)
            else:
                newdata[i]['Data'] = "Available"
    else:
        for i in range(len(newdata)):
            newdata[i]['Data'] = 'Available'
    
    
    flights_mod = pd.concat(newdata, axis = 1)
    flights_mod = flights_mod.transpose().reset_index()
    flights_mod = flights_mod.drop(["index"],axis=1)
    return flights_mod


#function to change hour column into hour properly

def fixTime(hr):
    if hr < 10:
        return "0" + str(hr) + ":00"
    else:
        return str(hr) + ":00"

#add shapes to graph

def addShapes(fig, night_day_dataset, dataset):
    #all days must be set to the same first, with actual day and month on
    #day/month columns
    #obtain day thats set for all vals
    curday = str(dataset.iloc[0]['tripStart'].to_pydatetime().date())
    dates = dataset['date'].unique()
    #select first day and last day
    for i in range(len(dates)):
        #select row where day is day in iterator
        row = night_day_dataset[night_day_dataset['date'] == dates[i]]
        sunrise = row['sunrise'].values[0]
        sunset = row['sunset'].values[0]
        #set values for early morning rectangle
        x0 = curday + " 00:00:00"
        x1 = curday + " " + str(sunrise)
        y0 = i - 0.5
        y1 = i + 0.5
        fig.add_shape(type="rect",
            xref="x", yref="y",
            x0=x0, y0=y0,
            x1=x1, y1=y1,
            fillcolor=blue,
            line=dict(
                color=blue,
                width=0.5,
            ),
            layer="below"
         )
        #set values for day rectangle
        x0 = curday + " " + str(sunrise)
        x1 = curday + " " + str(sunset)
        fig.add_shape(type="rect",
            xref="x", yref="y",
            x0=x0, y0=y0,
            x1=x1, y1=y1,
            fillcolor=orange,
            line=dict(
                color=orange,
                width=0.5,
            ),
            layer="below"
         )
        #set values for night rectangle
        x0 = curday + " " + str(sunset)
        x1 = curday + " 23:59:59"
        fig.add_shape(type="rect",
            xref="x", yref="y",
            x0=x0, y0=y0,
            x1=x1, y1=y1,
            fillcolor=blue,
            line=dict(
                color=blue,
                width=0.5,
            ),
            layer="below"
         )

    times = [" 00:00:00"," 03:00:00", " 06:00:00", " 09:00:00", " 12:00:00", " 15:00:00", " 18:00:00", " 21:00:00", " 23:59:59"]

    for i in times:
        fig.add_vline(x=curday + i, line_width=0.5, line_dash="dash", line_color="black")

    for i in range(len(dates)-1):
        fig.add_hline(y=i+0.5, line_width=0.5, line_dash="dash", line_color="black")
    

####ENTIRE DATASET STUFF
   
#create time plot for all bee flights utilizing flights dataset
    
def createActoGraphAll(dataset, dt):
    fig = px.timeline(dataset, x_start="tripStart", x_end="tripEnd",y="date", title="All bees' flights over time")
    fig.update_traces(
        marker_line_color="black",   
        marker_line_width=1          
    )
    #change tick format to look better
    fig.update_layout(xaxis=dict(
                      title='Time', 
                      tickformat = '%H:%M:%S'),
                     plot_bgcolor="white",
    #annotations to make pseudo legend
    annotations=[
        dict(
            x=1.095,
            y=1.1,
            xref="paper",
            yref="paper",
            showarrow=False,
            text="Time of Day",
            align="left",
            font=dict(size=13,family="Open Sans",color="black")
        )
    ])
    #setup axes
    fig.update_yaxes(dtick=1)
    fig.update_yaxes(autorange="reversed",title="Day")
    vals = dataset['date'].unique()
    fig.update_yaxes(
        tickvals=vals,
    )
    fig.update_traces(marker_color='rgba(0, 0, 0, 0.1)')
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=False)

    #custom legend
    custom_legend_items = [
        dict(name="Day", color=orange, symbol="square"),
        dict(name="Night", color=blue, symbol="square"),
    ]

    addShapes(fig,dt,dataset)

    for item in custom_legend_items:
        fig.add_trace(go.Scatter(
            x=[None], y=[None],
            mode="markers",
            marker=dict(size=10, color=item["color"], symbol=item["symbol"]),
            name=item["name"],
            legendgroup="custom",
            showlegend=True
        ))

    #custom legend 
    fig.add_trace(go.Scatter(
        x=[None],  
        y=[None],
        mode='markers',
        marker=dict(
            size=0.1,  
            color=[0],  
            colorscale='gray_r',  
            cmin=0,
            cmax=len(dataset['tagID'].unique()),  
            colorbar=dict(
                x=1.008,
                y=0.4,
                title=dict(
                    text="Amount of bees",  
                    font=dict(
                    family="Droid Serif",   # Font family
                    size=13,          # Font size
                    color="black"     # Font color
                    ),
                    side="top"
                ), 
                len=0.7,            
                thickness=10,
            )
        ),
        showlegend=False  
    ))
    
    
    fig.update_traces(hoverinfo="skip", hovertemplate=None)
    
    
    return fig
 
#Create linear regression based on bee age (since firstSeen) and flight length 
    
def linRegAge(activity, flights):
    #new dataset of length & age
    age = []
    length = []
    for b in activity['tagID'].unique():
        #get bee by ID
        bee = activity[activity['tagID'] == b].copy()
        beeF = flights[flights['tagID'] == b].copy()
        firstDay = activity['start'].iloc[0].day

        for index, row in beeF.iterrows():
            age.append(row['day'] - firstDay)
            length.append(row['duration'].total_seconds() / 60)

    #new dataframe
    ageLen = pd.DataFrame.from_dict({'age':age, 'length':length})
    m, b, r_value, p_value, std_err = stats.linregress(x=ageLen['age'],y=ageLen['length'])
    
    
    fig = sns.scatterplot(data=ageLen, x="age", y="length") 
    fig.set(xlabel='Bee age based on first seen (days)', ylabel='Flight length (mins)')
    
    #linreg line
    x = np.linspace(min(ageLen['age']), max(ageLen['age']), 3)
    y = m * x + b
    
    
    plt.plot(x, y, color='red', label=f'y ={m}x + {b}')
    
    plt.title("Age and flight length")
    plt.legend()
    plt.show()

    print("r_value:",r_value)
    print("p_value:",p_value)
    print("std_err:",std_err)


def silhouette(flights, maxclusters, column, column_b = None):
    if column_b:
        dataset = flights[[column, column_b]]  
        title = f"Silhouette score for {column} and {column_b}"
    else:
        dataset = flights[column].values.reshape(-1,1)
        title = f"Silhouette score for {column}"

    score = []
    clusters = np.arange(2,maxclusters+1)
    for i in range(2,maxclusters+1):
        kmeans = KMeans(n_clusters=i, random_state=42,n_init='auto')
        score.append(silhouette_score(dataset, kmeans.fit_predict(dataset)))

    sns.lineplot(x=clusters, y=score, marker='o')
    plt.title(title)
        
    
   
        
        
def flightDensity(dataset):
    df = dataset
    df['hour'] = df['tripStart'].dt.hour
    df['hour'] = df['hour'].apply(lambda x: fixTime(x))
    df['day'] = df['tripStart'].dt.day
    density = df.pivot_table(index='date', columns='hour', values='tripStart', aggfunc='count')
    
    #fig = sns.heatmap(density, cmap="Reds")
    #fig.set(xlabel='Hour of Day', ylabel='Day')
    #plt.xticks(rotation=30)
    #plt.title("Number of flights at time of day")
    #plt.show()
    
    
    fig = px.imshow(density,title="Number of flights at time of day")
    
    fig.update_layout(
    xaxis=dict(
        title=dict(
            text="'Hour of Day"
        )
    ),
    yaxis=dict(
        title=dict(
            text="Date"
        )
    ),
    )

    return fig
    
    
def flightLength(dataset):
    df = dataset
    df['hour'] = df['tripStart'].dt.hour
    df['mins'] = df['duration'].apply(lambda x: x.total_seconds()/60)
    df['hourofday'] = df['hour'].apply(lambda x: fixTime(x))
    #threshold = datetime.timedelta(hours=5)
    #df = df[df['duration'] < threshold]
    density = df.pivot_table(index='date', columns='hourofday', values='mins', aggfunc="mean")
    fig = px.imshow(density, title="Average length of flights (minutes) at time of day")
    fig.update_layout(
    xaxis=dict(
        title=dict(
            text="'Hour of Day"
        )
    ),
    yaxis=dict(
        title=dict(
            text="Date"
        )
    ),
    )

    
    return fig
    
    
    #fig = sns.heatmap(density,cmap="Reds")
    #fig.set(xlabel='Hour of Day', ylabel='Day')
    #plt.xticks(rotation=30)
    #plt.title("Average length of flights (minutes) at time of day")
    #plt.show()
    #fig = sns.lineplot(means, x="date", y="mins")
    #fig.set(xlabel='Date', ylabel='Mean duration of flights - Minutes')
    #plt.title("Length of flights across days")
    #plt.show()
    
    
    
####INDIVIDUAL BEE STUFF


def createActoGraph(dataset, dt):
    fig = px.timeline(dataset, x_start="tripStart", x_end="tripEnd",y="date", title="Selected bee's flights over time")
    fig.update_traces(
        marker_line_color="grey",   
        marker_line_width=1          
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=False)
    #change tick format to look better
    fig.update_layout(xaxis=dict(
                      title='Time', 
                      tickformat = '%H:%M:%S'),
                     plot_bgcolor="white",
    #annotations to make pseudo legend
    annotations=[
        dict(
            x=1.095,
            y=1.1,
            xref="paper",
            yref="paper",
            showarrow=False,
            text="Time of Day",
            align="left",
            font=dict(size=13,family="Open Sans",color="black")
        )
    ])
    #setup axes
    fig.update_yaxes(dtick=1)
    fig.update_yaxes(autorange="reversed",title="Day")
    vals = dataset['date'].unique()
    fig.update_yaxes(
        tickvals=vals
    )
    fig.update_traces(marker_color='brown')

    #custom legend
    custom_legend_items = [
        dict(name="Day", color=orange, symbol="square"),
        dict(name="Night", color=blue, symbol="square"),
    ]

    addShapes(fig,dt,dataset)

    for item in custom_legend_items:
        fig.add_trace(go.Scatter(
            x=[None], y=[None],
            mode="markers",
            marker=dict(size=10, color=item["color"], symbol=item["symbol"]),
            name=item["name"],
            legendgroup="custom",
            showlegend=True
        ))

    
    return fig

    

def plotHist(dataset):
    dataset['hour'] = dataset['tripStart'].apply(lambda x: x.hour)
    dataset['day'] = dataset['tripStart'].apply(lambda x: x.day)
    
    
    #fig = sns.histplot(dataset, x='hour',bins= (max(dataset['hour']) - min(dataset['hour'])))
    #fig.set_xticks(vals) 
    #fig.set_xticklabels(text)
    #fig.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    #plt.title("")
    #plt.xticks(rotation=30)
    #fig.set(xlabel='Hour', ylabel='Count of flights')
    #plt.show()
    
    
    #hour histogram
    
    fig1 = px.histogram(dataset, x="hour", nbins=(max(dataset['hour']) - min(dataset['hour'])))
    
    vals = list(range(min(dataset['hour']), max(dataset['hour'])+1))
    text = [(str(xi) + ":00") for xi in vals]

    fig1.update_xaxes(
    tickvals=vals,               
    ticktext=text,
    tickangle=30  
    )
    
    fig1.update_yaxes(
    tickmode='linear',
    dtick=1
    )
    
    fig1.update_layout(
    title = 'Number of flights at time of day.',
    xaxis=dict(
        title=dict(
            text="Hour"
        )
    ),
    yaxis=dict(
        title=dict(
            text="Count of Flights"
        )
    )
    )
    fig1.update_traces(marker_color='brown')    
    
    #day histogram
    
    
    #fig = sns.histplot(dataset, x='date',bins=(max(dataset['day']) - min(dataset['day'])))
    #fig.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    #plt.xticks(dataset['date'].unique())
    #fig.set(xlabel='Day', ylabel='Count of flights')
    #plt.title("Number of flights per day")
    #plt.show()

    dataset['date'] = dataset['tripStart'].apply(lambda x: f'{x.month}/{x.day}')
    
    fig2 = px.histogram(dataset, x="date", nbins=(max(dataset['day']) - min(dataset['day'])))
    
    fig2.update_layout(
    title = 'Number of flights per day.',
    xaxis=dict(
        title=dict(
            text="Day"
        )
    ),
    yaxis=dict(
        title=dict(
            text="Count of Flights"
        )
    )
    )
    
    fig2.update_yaxes(
    tickmode='linear',
    dtick=1
    )
    
    fig2.update_traces(marker_color='brown') 
    
    return fig1, fig2
    
    
    
    
    
    
