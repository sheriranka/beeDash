from suntime import Sun
import pytz
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
import numpy as np
import io
import base64
import datetime
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from scipy import stats

#functions for graphing

#graph color constants
orange = "rgb(219, 202, 103)"
blue =  "rgb(119, 159, 212)"

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
            newentry['tripEnd'] = row['tripEnd'].replace(hour=23,minute=59,second=59,day=1,month=1)
            newentry['tripStart'] = row['tripStart'].replace(day=1,month=1)
            newentry['date'] = fixDate(row['tripStart'])
            newdata.append(newentry)
            #second day
            newday = row['tripEnd'].to_pydatetime().day
            newentry = row.copy()
            newentry['tripStart'] = row['tripStart'].replace(day=1,hour=0,minute=0,second=0,month=1)
            newentry['tripEnd'] = row['tripEnd'].replace(day=1,month=1)
            newentry['day'] = newday
            newentry['date'] = fixDate(row['tripEnd'])
            newdata.append(newentry)
        else:
            newentry = row.copy()
            newentry['tripStart'] = row['tripStart'].replace(day=1,month=1)
            newentry['tripEnd'] = row['tripEnd'].replace(day=1,month=1)
            newentry['date'] = fixDate(row['tripStart'])
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
        
#function to change date column appropriately

def fixDate(x):
    if x.day > 9 and x.month > 9:
        return f'{x.month}/{x.day}'
    elif x.day > 9 and x.month < 10:
        return f'0{x.month}/{x.day}'
    elif x.day < 10 and x.month > 9:
        return f'{x.month}/0{x.day}'
    else:
        return f'0{x.month}/0{x.day}'

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
        fig.add_vline(x=curday + i, line_width=0.5, line_dash="solid", line_color="white")

    for i in range(len(dates)-1):
        fig.add_hline(y=i+0.5, line_width=0.5, line_dash="solid", line_color="white")
    

####ENTIRE DATASET STUFF
   
#create time plot for all bee flights utilizing flights dataset
    
def createActoGraphAll(dataset, dt):


    dataset = dataset.sort_values(by='date')
    bees = len(dataset['tagID'].unique())
    if bees > 100:
        transparency = 1/bees * (bees/100 + 1) * 2
        
        if bees > 200:
            ticks = np.arange(0,bees+1,(bees/(bees/50)))
        else:
            ticks = np.arange(0,bees+1,(bees/(bees/25)))
    elif bees > 50:
        transparency = 1/bees * (bees/50 + 1) * 2
        ticks = np.arange(0,bees+1,(bees/(bees/15)))
    else:
        transparency = 1/bees * 1.5
        ticks = np.arange(0,bees+1,(bees/(bees/10)))
        
    
    fig = px.timeline(dataset, x_start="tripStart", x_end="tripEnd",y="date", title="Flights Over Time")
    fig.update_traces(
        marker_line_color='rgba(255, 0, 0, 0)',   
        marker_line_width=0.1          
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
    fig.update_yaxes(autorange="reversed",title="Date")
    vals = dataset['date'].unique()
    fig.update_yaxes(
        tickvals=vals,
    )
    fig.update_traces(marker_color=f'rgba(0, 0, 0, {transparency})')
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
            colorscale=[[0, "rgb(191, 191, 191)"],[1, "black"]],
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
                tickvals=ticks
            )
        ),
        showlegend=False  
    ))
    
    
    fig.update_traces(hovertemplate='Date: %{y}')
    
    return fig
       
        
def flightDensity(dataset):
    df = dataset
    df['hour'] = df['tripStart'].dt.hour
    df['hour'] = df['hour'].apply(lambda x: fixTime(x))
    df['day'] = df['tripStart'].dt.day
    density = df.pivot_table(index='date', columns='hour', values='tripStart', aggfunc='count')
    
    #fig = sns.heatmap(density, cmap="Reds")
    #fig.set(xlabel='Hour of Day', ylabel='Date')
    #plt.xticks(rotation=30)
    #plt.title("Number of flights at time of day")
    #plt.show()
    
    
    max_color = max(dataset[['hour','day']].value_counts())
    if max_color < 5:
        tick_vals = np.arange(0,max_color+1)
    else:
        tick_vals = np.arange(0, max_color+1, max_color//5)    
    if len(df['tagID'].unique()) > 1:
        fig = px.imshow(density,title="Number of Flights at Time of Day",color_continuous_scale="brwnyl")
    else:
        fig = px.imshow(density,title=f"Number of Flights at Time of Day<br>for Bee {df['tagID'].iloc[0]}",color_continuous_scale="brwnyl")
        
        
    fig.update_layout(
    xaxis=dict(
        title=dict(
            text="Hour of Day"
        )
    ),
    yaxis=dict(
        title=dict(
            text="Date"
        )
    ),
    coloraxis_colorbar=dict(
        tickmode='array',
        tickvals=tick_vals, 
        tickformat=',d',
        title='Flight Count'
    )
    )
    
    fig.update_traces(hovertemplate='Hour: %{x} <br>Date: %{y} <br>Flights: %{z}')

    return fig
    
    
def flightLength(dataset):
    df = dataset
    df['hour'] = df['tripStart'].dt.hour
    df['mins'] = df['duration'].apply(lambda x: x.total_seconds()/60)
    df['hourofday'] = df['hour'].apply(lambda x: fixTime(x))
    #threshold = datetime.timedelta(hours=5)
    #df = df[df['duration'] < threshold]
    density = df.pivot_table(index='date', columns='hourofday', values='mins', aggfunc="mean")
    fig = px.imshow(density, title="Average Length of Flights (Minutes) at Time of Day",color_continuous_scale="brwnyl")
    fig.update_layout(
    xaxis=dict(
        title=dict(
            text="Hour of Day"
        )
    ),
    yaxis=dict(
        title=dict(
            text="Date"
        )
    ),
    coloraxis_colorbar=dict(
        title='Flight Duration'
    )
    )


    fig.update_traces(hovertemplate='Hour: %{x} <br>Date: %{y} <br>Average: %{z:.2f} minutes')
    
    return fig
    
    
    #fig = sns.heatmap(density,cmap="Reds")
    #fig.set(xlabel='Hour of Day', ylabel='Date')
    #plt.xticks(rotation=30)
    #plt.title("Average length of flights (minutes) at time of day")
    #plt.show()
    #fig = sns.lineplot(means, x="date", y="mins")
    #fig.set(xlabel='Date', ylabel='Mean duration of flights - Minutes')
    #plt.title("Length of flights across days")
    #plt.show()
    
    
def plotClusterTimeDur(activity,flights,clusters):
    
    mins = []
    time = []
    theTime = []
    for b in activity['tagID'].unique():
        #get bee by ID
        bee = activity[activity['tagID'] == b].copy()
        beeF = flights[flights['tagID'] == b].copy()

        for index, row in beeF.iterrows():
            mins.append(row['duration'].total_seconds()/60)
            time.append(row['timeOfDay'])
            theTime.append(row['theTime'])
            
    dict0 = {'mins':mins,'time':time,'theTime':theTime}     

    dataset = pd.DataFrame(dict0)
    
    clusters = min(clusters,len(flights))
    
    kmeans = KMeans(n_clusters=clusters, random_state=42)
    X = dataset[["time", "mins"]] 
    
    cluster_labels = kmeans.fit_predict(X)
    dataset['labels'] = [str(x) for x in cluster_labels]
    
    fig1 = px.scatter(dataset, x='theTime',y='mins',color='labels',title="Clustering for Time of Day and Flight Duration")
    fig1.update_layout(
    xaxis=dict(
        title=dict(
            text="Time of Day"
        )
    ),
    title=dict(
        font=dict(
            size=12
        )
    ),
    yaxis=dict(
        title=dict(
            text="Flight Duration (minutes)"
        )
    )
    )
    
    fig1.update_traces(hovertemplate='Time of Day: %{x} <br>Flight Duration: %{y:.2f}')    
    return fig1
    
def plotClusterDayDur(activity,flights,clusters):

    #new dataset of age
    age = []
    mins = []
    
    for b in activity['tagID'].unique():
        #get bee by ID
        bee = activity[activity['tagID'] == b].copy()
        beeF = flights[flights['tagID'] == b].copy()
        firstDay = bee['start'].iloc[0].date()

        for index, row in beeF.iterrows():
            age.append((row['tripStart'].date() - pd.to_datetime(firstDay).date()).days)
            mins.append(row['duration'].total_seconds()/60)
            
    dict0 = {'mins':mins,'age':age}
            
    dataset = pd.DataFrame(dict0)
    
    kmeans = KMeans(n_clusters=clusters, random_state=42)
    X = dataset[["mins","age"]]
    
    cluster_labels = kmeans.fit_predict(X)
    dataset['labels'] = [str(x) for x in cluster_labels]
    
    fig2 = px.scatter(dataset, x='age',y='mins',color='labels',title="Clustering for Time Since First Seen and Flight Duration")
    fig2.update_layout(
    xaxis=dict(
        title=dict(
            text="Days Since First Seen"
        )
    ),
    title=dict(
        font=dict(
            size=12
        )
    ),
    yaxis=dict(
        title=dict(
            text="Flight Duration (minutes)"
        )
    )
    )
    
    fig2.update_traces(hovertemplate='Time Passed: %{x} day(s) <br>Flight Duration: %{y:.2f}')
    
    return fig2


def plotCluster(activity,flights):

    #new dataset of age
    age = []
    mins = []
    time = []
    theTime = []
    
    for b in activity['tagID'].unique():
        #get bee by ID
        bee = activity[activity['tagID'] == b].copy()
        beeF = flights[flights['tagID'] == b].copy()
        firstDay = bee['start'].iloc[0].date()

        for index, row in beeF.iterrows():
            age.append((row['tripStart'].date() - pd.to_datetime(firstDay).date()).days)
            mins.append(row['duration'].total_seconds()/60)
            time.append(row['timeOfDay'])
            theTime.append(row['theTime'])
            
    dict0 = {'mins':mins,'age':age,'time':time,'theTime':theTime}
            
    dataset = pd.DataFrame(dict0)
    
    kmeans = KMeans(n_clusters=2, random_state=42)
    X = dataset[["time", "mins"]] 
    
    cluster_labels = kmeans.fit_predict(X)
    dataset['labels'] = [str(x) for x in cluster_labels]
    
    fig1 = px.scatter(dataset, x='theTime',y='mins',color='labels',title="Clustering for Time of Day and Flight Duration")
    fig1.update_layout(
    xaxis=dict(
        title=dict(
            text="Time of Day"
        )
    ),
    title=dict(
        font=dict(
            size=12
        )
    ),
    yaxis=dict(
        title=dict(
            text="Flight Duration (minutes)"
        )
    )
    )
    
    fig1.update_traces(hovertemplate='Time of Day: %{x} <br>Flight Duration: %{y:.2f}')
    
    kmeans = KMeans(n_clusters=2, random_state=42)
    X = dataset[["mins","age"]]
    
    cluster_labels = kmeans.fit_predict(X)
    dataset['labels'] = [str(x) for x in cluster_labels]
    
    fig2 = px.scatter(dataset, x='age',y='mins',color='labels',title="Clustering for Time Since First Seen and Flight Duration")
    fig2.update_layout(
    xaxis=dict(
        title=dict(
            text="Days Since First Seen"
        )
    ),
    title=dict(
        font=dict(
            size=12
        )
    ),
    yaxis=dict(
        title=dict(
            text="Flight Duration (minutes)"
        )
    )
    )
    
    fig2.update_traces(hovertemplate='Time Passed: %{x} day(s) <br>Flight Duration: %{y:.2f}')
    
    return fig1, fig2
    
    
    
    
def linReg(activity, flights):

    #new dataset of length & age
    flights['time'] = flights['tripStart'].apply(lambda x: "AM" if pd.to_datetime(x).time() < datetime.time(12,0) else "PM")
    #new dataset of length & age
    age = []
    tag = []
    time = []
    dur = []
    for b in activity['tagID'].unique():
        #get bee by ID
        bee = activity[activity['tagID'] == b].copy()
        beeF = flights[flights['tagID'] == b].copy()
        firstDay = bee['start'].iloc[0].date()

        for index, row in beeF.iterrows():
            age.append((row['tripStart'].date() - pd.to_datetime(firstDay).date()).days)
            tag.append(b)
            dur.append(row['duration'].total_seconds()/60)
            time.append(row['time'])
        
    dict0 = {'tag':tag, 'age':age}

    count = pd.DataFrame(dict0).groupby(['tag', 'age']).value_counts().reset_index(name='count')
    count.drop(['tag'],axis=1,inplace=True)
    countmean = count.groupby(['age']).mean().reset_index()
    
    ##OVERALL LINE FOR AMT OF FLIGHTS AND TIME PASSED
    beeSum = px.line(countmean, x="age", y="count", title='Relationship Between Time Passed and<br>Average Number of Flights',markers=True)
    beeSum.update_layout(
    xaxis=dict(
        title=dict(
            text="Time Passed Since First Seen (Days)"
        )
    ),
    title=dict(
        font=dict(
            size=12
        )
    ),
    yaxis=dict(
        title=dict(
            text="Average Number of Flights per Bee"
        )
    )
    )
    beeSum.update_traces(line_color='brown') 
    
    beeSum.update_traces(hovertemplate='Time Passed: %{x} day(s) <br>Average Flights: %{y:.2f}')
    
    
    dict0 = {'age':age,'dur':dur} 
    count = pd.DataFrame(dict0).groupby(['age']).mean().reset_index()
    
    beeMin = px.line(count, x="age", y="dur", title='Relationship Between Time Passed and<br>Average Flight Duration',markers=True)
    beeMin.update_layout(
    xaxis=dict(
        title=dict(
            text="Time Passed Since First Seen (Days)"
        )
    ),
    title=dict(
        font=dict(
            size=12
        )
    ),
    yaxis=dict(
        title=dict(
            text="Average Flight Duration (Minutes)"
        )
    ),
    )
    beeMin.update_traces(line_color='brown') 
    
    beeMin.update_traces(hovertemplate='Time Passed: %{x} day(s) <br>Duration: %{y:.2f} minutes')
    
    
    
    dict0 = {'tag':tag, 'age':age,'time':time}
    countAMPM = pd.DataFrame(dict0).groupby(['tag', 'age', 'time']).value_counts().reset_index(name='count')
    countAMPM.drop(['tag'],axis=1,inplace=True)
    
    fig=go.Figure()

    for i, time in enumerate(countAMPM['time'].unique()):
        df_plot=countAMPM[countAMPM['time']==time]

        if time == "AM":
            fig.add_trace(go.Box(x=df_plot['age'], y=df_plot['count'],
                                 line=dict(color='black',width=1),
                                 #line=dict(color=colors[i]),
                                 fillcolor='orange',
                                 #fillcolor=colors[i+4],
                                 name=time,
                                 hovertemplate="<b>Time Passed:</b> %{x} day(s)<br>" +
                                 "<b>Flights: </b>%{y}<br>" +
                                 "<extra></extra>"))
        else:
            fig.add_trace(go.Box(x=df_plot['age'], y=df_plot['count'],
                                 line=dict(color='black', width=1),
                                 #line=dict(color=colors[i]),
                                 fillcolor='blue',
                                 #fillcolor=colors[i+4],
                                 name=time,
                                 hovertemplate="<b>Time Passed:</b> %{x} day(s)<br>" +
                                 "<b>Flights: </b>%{y}<br>" +
                                 "<extra></extra>"))
    fig.update_layout(boxmode='group', xaxis_tickangle=0)

    fig.update_layout(title="Relationship Between Time Passed and<br>Average Number of Flights",
                      yaxis_title="Average Number of Flights per Bee",
                     xaxis_title = "Time Passed Since First Seen (Days)")
                     
    fig.update_layout(title_font_size=12)
    beeSumTime = fig
    
    time = flights['tripStart'].apply(lambda x: "AM" if pd.to_datetime(x).time() < datetime.time(12,0) else "PM")
    dict0 = {'age':age, 'dur':dur, 'time':time}
    df = pd.DataFrame(dict0).round(2)
    
    
    fig=go.Figure()

    for i, time in enumerate(df['time'].unique()):
        df_plot=df[df['time']==time]

        if time == "AM":
            fig.add_trace(go.Box(x=df_plot['age'], y=df_plot['dur'],
                                 line=dict(color='black',width=1),
                                 #line=dict(color=colors[i]),
                                 fillcolor='orange',
                                 #fillcolor=colors[i+4],
                                 name=time,
                                 hovertemplate=
                                "<b>Time Passed:</b> %{x} day(s)<br>" +
                                "<b>Duration: </b>%{y} minutes<br>" +
                                "<extra></extra>"))
        else:
            fig.add_trace(go.Box(x=df_plot['age'], y=df_plot['dur'],
                                 line=dict(color='black', width=1),
                                 #line=dict(color=colors[i]),
                                 fillcolor='blue',
                                 #fillcolor=colors[i+4],
                                 name=time,
                                 hovertemplate=
                                "<b>Time Passed:</b> %{x} day(s)<br>" +
                                "<b>Duration: </b>%{y} minutes<br>" +
                                "<extra></extra>"))
                                 
    fig.update_layout(boxmode='group', xaxis_tickangle=0)

    fig.update_layout(title="Relationship Between Time Passed and<br>Average Flight Duration",
                      yaxis_title="Average Flight Duration (Minutes)",
                     xaxis_title = "Time Passed Since First Seen (Days)")
    fig.update_layout(title_font_size=12)
    
    beeMinTime = fig
    
    # ###ALL BEES INDIVIDUALLY
    # beeAll = make_subplots(rows=2, cols=2,  
    # subplot_titles=("Time passed since first seen and number of flights taken for each bee", "Stable regressions", "Increasing Regressions", "Decreasing Regressions"))
    
    # bee1 = px.line(count, x="age", y="count",color='tag')
    # bee1.update_layout(showlegend=False)
    
    # stable = []
    # increasing = []
    # decreasing = []
    # for t in count['tag'].unique():
        # bee = count[count['tag']==t]
        # m, b, r_value, p_value, std_err = stats.linregress(x=bee['age'],y=bee['count'])
        # if np.abs(m) < 0.01:
            # stable.append(t)
        # elif m > 0:
            # increasing.append(t)
        # else:
            # decreasing.append(t)
    # countstable = count[count['tag'].isin(stable)]
    # countinc = count[count['tag'].isin(increasing)]
    # countdec = count[count['tag'].isin(decreasing)]
        
    # bee2 = px.line(countstable, x="age", y="count",color='tag')
    # bee2.update_layout(showlegend=False)
    # bee3 = px.line(countinc, x="age", y="count",color='tag')
    # bee3.update_layout(showlegend=False)
    # bee4 = px.line(countdec, x="age", y="count",color='tag')
    # bee4.update_layout(showlegend=False)
    
    # for trace in bee1.data:
        # beeAll.add_trace(trace, row=1, col=1)
        
    # for trace in bee2.data:
        # beeAll.add_trace(trace, row=1, col=2)
        
    # for trace in bee3.data:
        # beeAll.add_trace(trace, row=2, col=1)
        
    # for trace in bee4.data:
        # beeAll.add_trace(trace, row=2, col=2)
        
    # beeAll.update_layout(showlegend=False)
        
        
    
    return beeSum, beeMin, beeSumTime, beeMinTime #, beeAll
    
    
####INDIVIDUAL BEE STUFF

def beeAverage(dataset, y):

    dataset['hour'] = dataset['tripStart'].apply(lambda x: x.hour)
    dataset['day'] = dataset['tripStart'].apply(lambda x: x.day)
    
    averages = (dataset[['hour']].value_counts()/len(dataset['tagID'].unique())).round(2)
    hours = dataset['hour'].unique()
    
    #hour bar
    
    fig1 = px.bar(x=hours,y=averages)
    
    vals = list(range(min(dataset['hour']), max(dataset['hour'])+1))
    text = [(str(xi) + ":00") for xi in vals]

    fig1.update_xaxes(
    tickvals=vals,               
    ticktext=text,
    tickangle=45  
    )
    
    fig1.update_layout(
    title = f'Average Number of Flights at Time of Day<br>for all Bees',
    xaxis=dict(
        title=dict(
            text="Hour"
        )
    ),
    yaxis=dict(
        title=dict(
            text="Number of Flights"
        )
    )
    )
    fig1.update_yaxes(range = [0,y['hour']])
    fig1.update_traces(hovertemplate='Hour: %{x} <br>Flights: %{y}')
    fig1.update_traces(marker_color='brown',marker_line_width=1,marker_line_color="white")    

    #day bar

    dataset['date'] = dataset['tripStart'].apply(lambda x: fixDate(x))
    averages = (dataset[['date']].value_counts()/len(dataset['tagID'].unique())).round(2)
    dates = dataset['date'].unique()
    
    fig2 = px.bar(x=dates, y=averages)
    
    
    fig2.update_layout(
    title = f'Average Number of Flights per Day<br>for all Bees',
    xaxis=dict(
        title=dict(
            text="Date"
        )
    ),
    yaxis=dict(
        title=dict(
            text="Number of Flights"
        )
    )
    )
    
    fig2.update_yaxes(range = [0,y['date']])
    fig2.update_traces(marker_color='brown',marker_line_width=1,marker_line_color="white") 
    fig2.update_traces(hovertemplate='Date: %{x} <br>Flights: %{y}')
    

    dataset['duration'] = dataset['duration'].apply(lambda x: x.total_seconds()/60).round(2)
    fig3=go.Figure()
    fig3.add_trace(go.Box(x=dataset['date'], y=dataset['duration'],
                                 line=dict(color='black',width=1),
                                 #line=dict(color=colors[i]),
                                 fillcolor='brown',
                                 hovertemplate="<b>Date:</b> %{x}<br>" +
                                 "<b>Duration: </b>%{y}<br> minutes" +
                                 "<extra></extra>"))
                                 
    fig3.update_layout(boxmode='group', xaxis_tickangle=0)

    fig3.update_layout(title=f"Distribution of Avg Flight Duration per Day<br>for all Bees",
                      yaxis_title="Flight Duration (Minutes)",
                     xaxis_title = "Date")
                     
    fig3.update_xaxes(
    tickangle=45  
    )


    return fig1, fig2, fig3

def createActoGraph(dataset, dt):

    dataset = dataset.copy()
    dataset["tripEnd_hover"] = pd.to_datetime(dataset["tripStart"]).dt.strftime("%H:%M:%S")
    
    tagID = dataset['tagID'].iloc[0]

    fig = px.timeline(dataset, x_start="tripStart", x_end="tripEnd",y="date", title=f"Bee {tagID}'s Flights Over Time",custom_data=["tripEnd_hover"])
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
    fig.update_yaxes(autorange="reversed",title="Date")
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

    
    fig.update_traces(hovertemplate='Time Started: %{customdata[0]} <br>Time Ended: %{x}  <br>Date: %{y}')
    return fig

def createActoGraphSub(dataset, dt):

    dataset = dataset.copy()
    dataset["tripEnd_hover"] = pd.to_datetime(dataset["tripStart"]).dt.strftime("%H:%M:%S")
    dataset["tripStart_hover"] = pd.to_datetime(dataset["tripEnd"]).dt.strftime("%H:%M:%S")
    
    tagID = dataset['tagID'].iloc[0]

    fig = px.timeline(dataset, x_start="tripStart", x_end="tripEnd",y="date", title=f"Tag {tagID}",custom_data=["tripEnd_hover","tripStart_hover"])
    fig.update_traces(
        marker_line_color="grey",   
        marker_line_width=1          
    )
    
    fig.update_xaxes(showgrid=False,showticklabels=False)
    fig.update_yaxes(showgrid=False)
    #change tick format to look better
    fig.update_layout(xaxis=dict(
                      title='Time', 
                      tickformat = '%H:%M:%S'),
                     plot_bgcolor="white")
    #setup axes
    fig.update_yaxes(dtick=1)
    fig.update_yaxes(autorange="reversed",title="Date")
    vals = dataset['date'].unique()
    fig.update_yaxes(
        tickvals=vals
    )
    fig.update_traces(marker_color='brown')

    addShapes(fig,dt,dataset)

    
    fig.update_traces(hovertemplate='Time Started: %{customdata[0]} <br>Time Ended: %{customdata[1]}  <br>Date: %{y}')
    return fig

    

def plotHist(dataset,x,y):
    dataset['hour'] = dataset['tripStart'].apply(lambda x: x.hour)
    dataset['date'] = dataset['tripStart'].apply(lambda x: fixDate(x))
    
    tagID = dataset['tagID'].iloc[0]
    
    #hour bar
    
    hour = x['hour']
    
    averages = dataset['hour'].value_counts().reindex(hour)
    
    fig1 = px.bar(x=hour,y=averages)
    
    text = [(str(xi) + ":00") for xi in hour]

    fig1.update_xaxes(
    tickvals=hour,               
    ticktext=text,
    tickangle=45 
    )
    
    fig1.update_layout(
    title = f'Number of Flights at Time of Day<br>for Bee {tagID}',
    xaxis=dict(
        title=dict(
            text="Hour"
        )
    ),
    yaxis=dict(
        title=dict(
            text="Number of Flights"
        )
    )
    )
    fig1.update_yaxes(range = [0,y['hour']])
    fig1.update_traces(hovertemplate='Hour: %{x} <br>Flights: %{y}')
    fig1.update_traces(marker_color='brown',marker_line_width=1,marker_line_color="white")    
    
    #day bar
    
    dates = x['date']
    
    averages = dataset['date'].value_counts().reindex(dates,fill_value=0)
    
    fig2 = px.bar(x=dates, y=averages)
    
    
    fig2.update_layout(
    title = f'Number of Flights per Day for<br>Bee {tagID}',
    xaxis=dict(
        title=dict(
            text="Date"
        )
    ),
    yaxis=dict(
        title=dict(
            text="Number of Flights"
        )
    )
    )
    
    
    fig2.update_yaxes(range = [0,y['date']])
    fig2.update_traces(marker_color='brown',marker_line_width=1,marker_line_color="white") 
    fig2.update_traces(hovertemplate='Date: %{x} <br>Flights: %{y}')
    
    
    fig3=go.Figure()
    fig3.add_trace(go.Box(x=dataset['date'], y=dataset['duration'],
                                 line=dict(color='black',width=1),
                                 #line=dict(color=colors[i]),
                                 fillcolor='brown',
                                 hovertemplate="<b>Date:</b> %{x}<br>" +
                                 "<b>Duration: </b>%{y}<br> minutes" +
                                 "<extra></extra>"))
                                 
    fig3.update_layout(boxmode='group', xaxis_tickangle=0)

    fig3.update_layout(title=f"Distribution of Flight Duration per Day<br>for Bee {tagID}",
                      yaxis_title="Flight Duration (Minutes)",
                     xaxis_title = "Date")
                     
    fig3.update_xaxes(
    tickangle=45  
    )
    
    return fig1, fig2, fig3
    
    
    
    
def plotProbs(dataset,flights):
    dataset['hour'] = dataset['tripStart'].apply(lambda x: x.hour)
    flights['hour'] = flights['tripStart'].apply(lambda x: x.hour)
    
    tagID = dataset['tagID'].iloc[0]
    hour = flights['hour'].unique()
    hour.sort()
    
    averages = dataset['hour'].value_counts().reindex(hour, fill_value=0)/len(dataset['hour'])
    averages = averages.sort_index()

    fig1 = px.bar(x=hour, y=averages)
    
    text = [(str(xi) + ":00") for xi in hour]

    if len(dataset['tagID'].unique()) > 1:
        title = "All Bees"
    else:   
        title = f"Bee {tagID}"

    fig1.update_xaxes(
    tickvals=hour,               
    ticktext=text,
    tickangle=45 
    )
    fig1.update_layout(
    title = f'Flight Number Distribution at Time of Day<br>for {title}',
    xaxis=dict(
        title=dict(
            text="Hour"
        )
    ),
    yaxis=dict(
        title=dict(
            text="Flight Number Distribution"
        )
    )
    )
    #fig.update_yaxes(range = [0,1])
    fig1.update_traces(hovertemplate='Hour: %{x} <br>Flight Distribution: %{y}')
    fig1.update_traces(marker_color='brown',marker_line_width=1,marker_line_color="white")    
    
    cumsum = averages.cumsum().tolist()
    hour = np.append(hour, hour[-1] + 1)
    cumsum.append(1)

    fig1.add_trace(go.Scatter(x=hour, y=cumsum, zorder=-1,name='CDF',opacity=0.1, fill='tozeroy',mode= 'none'))
    #fig1.show()
    
    #day density

    dataset['date'] = dataset['tripStart'].apply(lambda x: fixDate(x)) 
    flights['date'] = flights['tripStart'].apply(lambda x: fixDate(x))
    dates = flights['date'].unique()
    dates.sort()

    averages = dataset['date'].value_counts().reindex(dates, fill_value=0)/len(dataset['date'])
    averages = averages.sort_index()

    fig2 = px.bar(x=dates, y=averages)

    fig2.update_layout(
    title = f'Flight Number Distribution per Day for<br>{title}',
    xaxis=dict(
        title=dict(
            text="Date"
        )
    ),
    yaxis=dict(
        title=dict(
            text="Flight Distribution"
        )
    )
    )
    
    #fig.update_yaxes(range = [0,1])
    fig2.update_traces(marker_color='brown',marker_line_width=1,marker_line_color="white") 
    fig2.update_traces(hovertemplate='Date: %{x} <br>Flight Distribution: %{y}')
    
    cumsum = averages.cumsum().tolist()
    dates = np.append(dates,'')
    cumsum.append(1)

    fig2.add_trace(go.Scatter(x=dates, y=cumsum, zorder=-1,name='CDF',opacity=0.1, fill='tozeroy',mode= 'none'))

    #fig2.show()
    return fig1, fig2
    

    
