#imports

from dash import Dash, dash_table, dcc, html, Input, Output, callback, State
import pandas as pd
import numpy as np
import math
import dash_bootstrap_components as dbc 
import base64
import io
import dash
from io import BytesIO
import plotly.express as px
from plotly.subplots import make_subplots



#external files

from flights import classifyTrips

#app creation

external_stylesheets = [dbc.themes.BOOTSTRAP,'https://codepen.io/chriddyp/pen/bWLwgP.css']
app = Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server

#layout

app.layout = html.Div([
        
         html.Div([
                            
                            html.H1('Bee :]', style={'textAlign': 'center', 'font-size':'70px'}),
                            html.Img(src="https://cdn.pixabay.com/photo/2021/03/27/05/13/bee-6127510_1280.jpg",style={'width':'100%'}),
                            html.P("""This tool serves to visualize and analyze records of bees at the entrance to the colony.
                            It requires the following columns:"""),
                            html.Ul(id='requirements',children=[
                                html.Li("pollen_score: numerical descriptor of pollen in sighting."),
                                html.Li("event: descriptor of trajectory of sighting."),
                                html.Li("tagid: id of bee in sighting."),
                                html.Li("starttime: time of start of sighting."),
                                html.Li("endtime: time of end of sighting.")
                            ]),
                            html.P("Upload a csv file to begin."),

                            dcc.Upload(
                                        id='upload-csv',
                                        children=html.Button("Upload CSV"),
                                        multiple=True,
                                    ),
                        ], style={'width':'33%', 'display': 'flex', 'flexDirection': 'column'}),
                        
        html.Div([
        
            html.Hr(),
            dcc.Loading(
                id="loading",
                type="circle",
                children=html.Div(id="output-data")
            ),
            dcc.Store(id='stored-data', storage_type='session'),
            dcc.Store(id='flight-itinerary', storage_type='session'),
        
        ], style={'width':'66%', 'display': 'flex', 'flexDirection': 'column'})


],style={'display': 'flex', 'flexDirection': 'row', 'marginRight': '20px', 'marginLeft': '20px', 'fontFamily': 'Arial, sans-serif'})


# function to parse the contents of the selected file
def parse_contents(contents, filename, date):
    content_type, content_string = contents.split(',')

    # decode the content
    decoded = base64.b64decode(content_string)
    
    # if it is a csv then read it 
    if 'csv' in filename:
        df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        
        #unique bees for dropdown 
        selectBee = pd.unique(df['tagid'])
        
        ndf = df.copy()
        
        #fix datetime from str to datetime       
        ndf['starttime'] = pd.to_datetime(ndf['starttime'], format='mixed')   
        ndf['endtime'] = pd.to_datetime(ndf['endtime'], format='mixed')   
        
        #all bee itinerary
        newdataset = {'beeID':[],'tripstart':[],'tripend':[]}
        for bee in selectBee:
            dataset = classifyTrips(ndf[ndf['tagid'] == bee].copy())
            for index, row in dataset.iterrows():
                if row['location'] == "Outside":
                    newdataset['beeID'].append(bee)
                    newdataset['tripstart'].append(row['start'])
                    newdataset['tripend'].append(row['end'])
                    
        newdf = pd.DataFrame.from_dict(newdataset)
        newdf['duration'] = newdf['tripend'] - newdf['tripstart']
        newdf['hour'] = newdf['tripstart'].dt.hour
        newdf['day'] = newdf['tripstart'].dt.day
        
        binsy = len(newdf['day'].unique())
        binsx = len(newdf['hour'].unique())
             
        fig = px.density_heatmap(newdf, nbinsy=binsy, x="hour", y="day", nbinsx=binsx, color_continuous_scale="Viridis")
        
        inddf = newdf.drop_duplicates(subset=['beeID', 'hour'], keep='last')
        fig2 = px.density_heatmap(inddf, nbinsy=binsy, x="hour", y="day", nbinsx=binsx, color_continuous_scale="Viridis")
        
        fig3 = px.histogram(newdf, x='hour')
        
        fig4 = px.density_contour(newdf, x="hour", y="duration")
        fig4.update_traces(contours_coloring="fill", contours_showlabels = True)
        
        fig5 = px.area(newdf, x="day", y="duration", color="beeID", line_group="beeID", color_discrete_sequence=px.colors.qualitative.Dark24)
    
        
        return html.Div([
        
            dcc.Dropdown(
                options=selectBee,
                #options=['55','66'],
                placeholder="Select individual tag",
                id="dropdown-bee",
                multi=False,
                searchable=True),
            dcc.Store(id='stored-data', data=df.to_dict('records')),
            dcc.Store(id='flight-itinerary', data=newdf.to_dict('records')), 
            html.H3("Chronogram"),
            dcc.Graph(id="output-graphs"),
            html.H3("Flights by hour of individual bee"),
            dcc.Graph(id="output-hour"),

            
            
            html.H3("Heatmap of all bee flights"),
            dcc.Graph(id="heatmap-flights",figure=fig),
            html.H3("Heatmap of unique bee flights per hour"),
            dcc.Graph(id="heatmap-bee",figure=fig2),
            html.H3("Flights by hour of all bees"),
            dcc.Graph(id="flights-bar",figure=fig3),
            html.H3("Flight duration by hour of all bees"),
            dcc.Graph(id="flights-density",figure=fig4),
            html.H3("Flight duration by day of all bees"),
            dcc.Graph(id="flights-area",figure=fig5)
            
        ])

    
    else:
        return "The file needs to be a csv."



# display data from csv after processing
@app.callback([Output('output-data', 'children')],
              Input('upload-csv', 'contents'),
              State('upload-csv', 'filename'),
              State('upload-csv', 'last_modified'),
              prevent_initial_call=True)
# function parses and update the output of the selected dataset
def update_output(list_of_contents, list_of_names, list_of_dates):
    # if there is a selected file
    if list_of_contents is not None:
        # parse the content
        children = [
            parse_contents(c, n, d) for c, n, d in
            zip(list_of_contents, list_of_names, list_of_dates)]
        return children

#function to display graphs when bee is selected

@app.callback(
        Output('output-graphs', 'figure'),
        Output('output-hour', 'figure'),
        Input('dropdown-bee', 'value'),
        Input('stored-data', 'data'), 
        prevent_initial_call=True
)
def show_chronogram(bee_id, data):
    if bee_id is None:
        return None
    if data is None:
        return None
        
    df = pd.DataFrame(data)
    bee = df[df['tagid'] == bee_id].copy()
    
    #assure datetime format 
    bee['starttime'] = pd.to_datetime(bee['starttime'], format='mixed')   
    bee['endtime'] = pd.to_datetime(bee['endtime'], format='mixed')   
    
    beeTravel = classifyTrips(bee)
    beeTravel['hour'] = beeTravel['start'].dt.hour
    beeTravel['day'] = beeTravel['start'].dt.day
    
    beeTravel['duration'] = beeTravel['end'] - beeTravel['start']
    
    colors = {'Ramp':'#6379f2','inside':'#ffaa42','outside-foraging':'#52eb8a','inside-short':'#ffebbd','outside-long':'#1b5242','outside-short':'#c5ffc2'}
    fig = px.timeline(beeTravel, x_start="start", x_end="end", y="location", color="activity",color_discrete_map=colors)
    fig.update_layout(xaxis=dict(rangeslider=dict(visible=True)))
    
    fig2 = px.histogram(beeTravel, x='hour')
    
    
    return fig, fig2
    
    

#run app

if __name__ == '__main__':
    app.run_server(debug=False)