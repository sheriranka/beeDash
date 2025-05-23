#imports

from dash import Dash, dash_table, dcc, html, Input, Output, callback, State
import dash_daq as daq


import pandas as pd
import numpy as np
import math
import dash_bootstrap_components as dbc 
import base64
import io
import dash
import pytz
from io import BytesIO

from timezonefinder import TimezoneFinder 



#external files

from flights import classifyLoc, cleanData, summaryData, makeTotalSum
from graphing import getSRSS, separateFlights, addShapes, createActoGraphAll, flightDensity, flightLength, createActoGraph, plotHist


#app creation

external_stylesheets = [dbc.themes.BOOTSTRAP,'https://codepen.io/chriddyp/pen/bWLwgP.css']
app = Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server

#constants

tzf = TimezoneFinder() 

#layout

app.layout = html.Div([
        
         html.Div([
                            html.Div(id='sr-ss'),
                            html.H5('Bee Analysis Dashboard', style={'textAlign': 'center'}),
                            html.Img(src="https://cdn.pixabay.com/photo/2021/03/27/05/13/bee-6127510_1280.jpg",style={'width':'100%'}),
                            html.P("""This tool serves to visualize and analyze records of bees at the entrance to the colony.
                            It requires the following columns in order:"""),
                            html.Ul(id='requirements',children=[
                                html.Li("Column with bee tag ID."),
                                html.Li("Column with datetime."),
                                html.Li("Column with entering/exiting label.")

                            ]),
                            
                            html.P("Input latitude and longitude:"),
                            
                            dcc.Input(
                            id="lat", type="number",
                            placeholder="Latitude",
                            value="None"
                            ),
                            dcc.Input(
                            id="lon", type="number",
                            placeholder="Longitude",
                            value="None"
                            ),
                            
                            html.P("Upload a csv file to begin."),

                            dcc.Upload(
                                        id='upload-csv',
                                        children=html.Button("Upload CSV"),
                                        multiple=True,
                                    ),
                        ], style={'width':'20%', 'display': 'flex', 'flexDirection': 'column'}),
                        
        html.Div([
        
            html.Hr(),
            dcc.Loading(
                id="loading",
                type="circle",
                children=html.Div(id="output-data")
            ),
            dcc.Store(id='stored-data', storage_type='session'),
        
        ], style={'width':'80%', 'display': 'flex', 'flexDirection': 'column'})


],style={'display': 'flex', 'flexDirection': 'row', 'marginRight': '20px', 'marginLeft': '20px', 'fontFamily': 'Arial, sans-serif'})


# function to parse the contents of the selected file
def parse_contents(contents, filename, date):
    content_type, content_string = contents.split(',')

    # decode the content
    decoded = base64.b64decode(content_string)
    
    # if it is a csv then read it 
    if 'csv' in filename:
        df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        
        ndf = df.copy()
        
        ndf.columns.values[0] = "tagID"
        ndf.columns.values[1] = "datetime"
        ndf.columns.values[2] = "event"
        
        #unique bees for dropdown 
        selectBee = pd.unique(ndf['tagID'])
        
        #fix datetime from str to datetime       
        ndf['datetime'] = pd.to_datetime(ndf['datetime'], format='mixed')    
        
        allActivity, flight = cleanData(ndf)
        flight['date'] = flight['tripStart'].apply(lambda x: f'{x.month}/{x.day}')
        
        beeSummary = summaryData(allActivity,flight)
        
        density = flightDensity(flight)
        length = flightLength(flight)
        
        Summary0, Summary1 = makeTotalSum(beeSummary, flight)
        
        Summary0.reset_index(inplace=True)
        Summary0 = Summary0.rename(columns={'index': 'Classification'})
        

        return html.Div([
            
            dcc.Store(id='stored-data', data=ndf.to_dict('records')), 
            dcc.Store(id='activity', data=allActivity.to_dict('records')), 
            dcc.Store(id='flights', data=flight.to_dict('records')), 
            
            
            dcc.Tabs([
										                  
                    
					dcc.Tab(label='Individual Bee Data', children=[
                    
					html.Div([          
                        html.P("Utilize the dropdown to select individual bee tag."),
                        dcc.Dropdown(
                            options=selectBee,
                            #options=['55','66'],
                            placeholder="Select individual tag",
                            id="dropdown-bee",
                            multi=False,
                            searchable=True),
                        html.Div(id="individual-chronogram"),
                        html.Div(id="individual-bee")                        
                        ],style={'display': 'flex', 'flexDirection': 'column','marginRight': '10px', 'marginLeft': '10px'}),										
					]),
											
					dcc.Tab(label='Hive Data', children=[
                        html.Div([
                        
                            dash_table.DataTable(
                            id='datatable',
                            columns=[
                                {"name": str(i), "id": str(i)} for i in beeSummary.columns
                            ],
                            data=beeSummary.to_dict('records'),
                            page_action="native",
                            page_current= 0,
                            page_size= 10,
                            style_table={'overflowX': 'auto'},
                            ),
                        
                        
                        ],style={'display': 'flex', 'flexDirection': 'column','marginRight': '10px', 'marginLeft': '10px'}),

                        

                        html.Div([
                                
                            dash_table.DataTable(
                            id='datatable-sum0',
                            columns=[
                                {"name": str(i), "id": str(i)} for i in Summary0.columns
                            ],
                            data=Summary0.to_dict('records'),
                            page_action="native",
                            style_table={'overflowX': 'auto'},
                            ),
                        
                            html.Div(style={'width': '200px'}),
                            
                            dash_table.DataTable(
                            id='datatable-sum1',
                            columns=[
                                {"name": str(i), "id": str(i)} for i in Summary1.columns
                            ],
                            data=Summary1.to_dict('records'),
                            page_action="native",
                            style_table={'overflowX': 'auto'},
                            )
                        

                            ], id='tables', style={'display': 'flex', 'flexDirection': 'row', 'flex-wrap': 'nowrap'}),
    
                         html.Div([
                                
                                    dcc.Graph(figure = density),
                                    dcc.Graph(figure = length),

                                ], id='heatmaps', style={'display': 'flex', 'flexDirection': 'row', "width": "100%"}),

                        
                        html.Div(id='chronogram-all')
                    ])
																			
			])
            
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


@app.callback([Output('sr-ss', 'children')],
              Input('lat', 'value'),
              Input('lon', 'value'),
              Input('activity', 'data'),
              prevent_initial_call=True)    
def sunrise_sunset(lat, lon, activity):
    #none checks
    if activity is None:
        return None
    if lat is None:
         return None
    if lon is None:
         return None
        
    allActivity = pd.DataFrame(activity)
    allActivity['start'] = pd.to_datetime(allActivity['start'], format='mixed')  

    lt = float(lat)
    ln = float(lon)
    
    tz = pytz.timezone(tzf.timezone_at(lng=ln, lat=lt))
    dt = getSRSS(allActivity, tz, lt, ln)
    dt['date'] = dt['date'].apply(lambda x: f'{x.month}/{x.day}')
    
    return [dcc.Store(id='sunrise-sunset', data=dt.to_dict('records'))]


@app.callback([Output('chronogram-all', 'children')],
              Input('sunrise-sunset', 'data'),
              State('flights', 'data'),
              State('activity', 'data'),
              prevent_initial_call=True)             
def displayChronogramAll(srss, data, activity):

    #none checks
    if data is None:
        return None
    if activity is None:
        return None
    if srss is None:
        return None
        
    allActivity = pd.DataFrame(activity)
    allActivity['start'] = pd.to_datetime(allActivity['start'], format='mixed')   
    
    
    flights = pd.DataFrame(data)
    flights['tripStart'] = pd.to_datetime(flights['tripStart'], format='mixed')
    flights['tripEnd'] = pd.to_datetime(flights['tripEnd'], format='mixed')

    dt = pd.DataFrame(srss)
    
    flights_mod = separateFlights(flights)
    fig = createActoGraphAll(flights_mod,dt)
    
    return [dcc.Graph(figure=fig)]


#function to display graphs when bee is selected

@app.callback(
        Output('individual-bee', 'children'),
        Input('dropdown-bee', 'value'),
        Input('flights', 'data'), 
        prevent_initial_call=True
)
def show_individual(bee_id, data):
    if bee_id is None:
        return None
    if data is None:
        return None
        
        
    flights = pd.DataFrame(data)
    flights['tripStart'] = pd.to_datetime(flights['tripStart'], format='mixed')
    flights['tripEnd'] = pd.to_datetime(flights['tripEnd'], format='mixed')
        
    bee = flights[flights['tagID'] == bee_id].copy()
    
    
    fig1, fig2 = plotHist(bee)
    
    
    
    return [
    
        dcc.Graph(figure = fig1),
        dcc.Graph(figure = fig2)
    
    ]
    


@app.callback([Output('individual-chronogram', 'children')],
              Input('dropdown-bee', 'value'),
              State('sunrise-sunset', 'data'),
              State('flights', 'data'),
              State('activity', 'data'),
              prevent_initial_call=True)             
def displayChronogramSingle(beeid, srss, data, activity):

    #none checks
    if data is None:
        return None
    if activity is None:
        return None
    if srss is None:
        return None
    if beeid is None:
        return None
        
        
    flights = pd.DataFrame(data)
    flights['tripStart'] = pd.to_datetime(flights['tripStart'], format='mixed')
    flights['tripEnd'] = pd.to_datetime(flights['tripEnd'], format='mixed')

    dt = pd.DataFrame(srss)
    
    flights_mod = separateFlights(flights)
    bee = flights_mod[flights_mod['tagID'] == beeid]
    fig = createActoGraph(bee,dt)
    
    return [dcc.Graph(figure=fig)]

#run app

if __name__ == '__main__':
    app.run_server(debug=False)