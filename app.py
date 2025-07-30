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
from datetime import date, datetime
from timezonefinder import TimezoneFinder 
from dash.exceptions import PreventUpdate




#external files

from flights import classifyLoc, cleanData, summaryData, makeTotalSum
from graphing import getSRSS, separateFlights, addShapes, createActoGraphAll, flightDensity, flightLength, createActoGraph, plotHist, plotCluster, linReg, fixDate


#app creation

external_stylesheets = [dbc.themes.BOOTSTRAP,'https://codepen.io/chriddyp/pen/bWLwgP.css']
app = Dash(__name__, external_stylesheets=external_stylesheets,suppress_callback_exceptions=True)
server = app.server

#constants

tzf = TimezoneFinder() 

#layout

app.layout = html.Div([


        html.Div([
        
            dbc.Button("How To Use", id="open", n_clicks=0,style={'border-bottom':'1px dashed'}),
        
        
                dbc.Modal(
                [
                    dbc.ModalHeader(dbc.ModalTitle("Instructions")),
                    dbc.ModalBody([
                    html.P("Dash Instructions"),
            
            
                    html.Ul(children=[
                                            html.Li("Individual Bee Data: Select a bee tag from the dropdown to view data visualizations associated with that bee."),
                                            html.Li("Hive Data: Search for tags or values in empty block above values labeled 'Search..' in first table to filter table display."),
                                            html.Li("Date Range: Select an initial and final date to narrow down the data displayed to a desired date range."),
                                            html.Li("Accessing the Chronogram: Enter latitude and longitude of your desired location to display chronogram with sunrise/sunset display.")

                                        ],style={'list-style-type':'square','font-size':'12px'}),
                                        
                                        
                    html.P("Visualization Instructions"),
                    
                    html.Ul(children=[
                                            html.Li("Hover over the objects in the visualization to display details. (Chronogram for all bees does not contain this function.)"),
                                            html.Li("Drag and drop on visualization to zoom in desired region."),
                                            html.Li("Click home icon to reset zoom to default."),
                                            html.Li("Click camera icon to save a static version of the visualization to computer."),


                                        ],style={'list-style-type':'square', 'font-size':'12px'}),
                                             
                    ]),
                    dbc.ModalFooter(
                        dbc.Button("Close", id="close", className="ms-auto", n_clicks=0)
                    ),
            ],
            id="modal",
            is_open=False,
            )
        ], id="instructions-modal", style={'padding-top':'5px'}),
        
         html.Div([
         
             html.Div([
                                html.Div([
                                
                                html.Div(id='sr-ss'),
                                
                                html.H1('BeeHaive', style={'textAlign': 'center','font-family':'Bahnschrift'}),
                                
                                html.P("""This tool serves to visualize and analyze records of uniquely identified bees at the entrance to the colony. Its purpose is to
                                facilitate analysis to biologists and beekeepers unfamiliar with data science and programming.
                                It requires the following columns in order in a CSV file:"""),
                                html.Ul(id='requirements',children=[
                                    html.Li("Column with bee tag ID."),
                                    html.Li(["Column with datetime. Must follow this format order:",html.Br(),  html.I("YYYY/MM/DD H:M:S", style={'font-size':'10px'})]),
                                    html.Li("Column with entering/exiting label.")

                                ],style={'list-style-type':'square'}),
                                                               
                                
                                html.P("Upload a csv file to begin visualizing."),
                                
                                
                                html.Hr(),
                                
                                html.P("Contact here: laeticiaaucerius@gmail.com", style={'font-size':'10px', 'padding-right':'30px'}),

                                
                                ], style={'padding-top':'10px','padding-right':'30px'}),                      
                                
                                html.Img(src="https://cdn.pixabay.com/photo/2021/03/27/05/13/bee-6127510_1280.jpg",style={'width':'80%','border-radius': '10px', 'margin':'auto'}),
                                
                                                                 
             ], style={'display': 'flex', 'flexDirection': 'row'}),
        ], id='landing-page', style={'width':'100%', 'padding-right':'10px', 'height':'100%'}),
                        
        html.Div([
        
            html.Div([
            html.Div(id="latlonInput"),
            html.Div(style={'width':'25px'}),
            dcc.Upload(
                                        id='upload-csv',
                                        children=html.Button("Upload CSV"),
                                        multiple=True,
                                        style={'padding-top':'35%'}
                                    ),
            html.Div(style={'width':'25px'}),
            html.Div(id="dateSelector"),  
            ],style={'display':'flex','flexDirection':'row','align-items': 'center','justify-content': 'center', 'background-color':'white'}),
            
            html.Hr(),
        
            dcc.Loading(
                id="loading",
                type="circle",
                children=html.Div(id="output-data"),
                style={"margin-top":"20px"}
            ),
            dcc.Store(id='stored-data', storage_type='session'),
        
        ], style={'width':'100%', 'display': 'flex', 'flexDirection': 'column','margin-top':'20px'})


],style={'marginRight': '20px', 'marginLeft': '20px', 'fontFamily': 'Arial, sans-serif'})



@app.callback(
    Output("modal", "is_open"),
    [Input("open", "n_clicks"), Input("close", "n_clicks")],
    [State("modal", "is_open")],
)
def toggle_modal(n1, n2, is_open):
    if n1 or n2:
        return not is_open
    return is_open


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
        
        #fix datetime from str to datetime       
        ndf['datetime'] = pd.to_datetime(ndf['datetime'], format='mixed')    
        
        allActivity, flight = cleanData(ndf)
        flight['date'] = flight['tripStart'].apply(lambda x: fixDate(x))
        flight['timeOfDay'] = flight['tripStart'].apply(lambda x: (x.hour * 60 + x.minute) * 60)
        

        return html.Div([
            
            
            html.Div(id="app-body"), 
            
            
            dcc.Store(id='stored-data', data=ndf.to_dict('records')), 
            dcc.Store(id='activity', data=allActivity.to_dict('records')), 
            dcc.Store(id='flights', data=flight.to_dict('records')), 
            dcc.Store(id='all-flights', data=flight.to_dict('records')),
            dcc.Store(id='sunrise-sunset', data=None)
            
       ])
            


    
    else:
        return "The file needs to be a csv."
        
        
        
@app.callback(Output('app-body','children'),
                Input('flights','data'),
                Input('activity','data'),
                Input('all-flights','data'),
                prevent_initial_call=True)
def display_app(flights, activity, all_flights):

    if flights == None:
        return None
    if activity == None:
        return None
    if all_flights == None:
        return None

    all_flight = pd.DataFrame(all_flights)
    flight = pd.DataFrame(flights)
    allActivity = pd.DataFrame(activity)
    
    flight['tripStart'] = pd.to_datetime(flight['tripStart'], format='mixed') 
    flight['tripEnd'] = pd.to_datetime(flight['tripEnd'], format='mixed') 
    flight['duration'] = flight['tripEnd'] - flight['tripStart']
    flight['theTime'] = flight['tripStart'].apply(lambda x: pd.to_datetime(pd.to_datetime(x).time().strftime('%H:%M:%S')))
    
    all_flight['tripStart'] = pd.to_datetime(all_flight['tripStart'], format='mixed') 
    all_flight['tripEnd'] = pd.to_datetime(all_flight['tripEnd'], format='mixed') 
    all_flight['duration'] = all_flight['tripEnd'] - all_flight['tripStart']       
    
    allActivity['start'] = pd.to_datetime(allActivity['start'], format='mixed') 
    allActivity['end'] = pd.to_datetime(allActivity['end'], format='mixed')    

    beeSummary = summaryData(allActivity,flight).round(2)
    #beeSummary['tagID'] = beeSummary['tagID'].apply(lambda x: str(x))
        
    density = flightDensity(flight)
    length = flightLength(flight)
        
    Summary0, Summary1 = makeTotalSum(beeSummary, flight)
      
    Summary0.reset_index(inplace=True)
    Summary0 = Summary0.rename(columns={'index': 'Classification'}).round(2)
    
    Summary1 = Summary1.round(2)
        
    beeSum, beeMin, beeSumTime, beeMinTime = linReg(allActivity,all_flight)
        
    cluster1, cluster2 = plotCluster(allActivity, flight)
    #unique bees for dropdown 
    selectBee = pd.unique(flight['tagID'])
    
    beeSummary = beeSummary.astype(str)
    
    #print(type(beeSummary['tagID'].iloc[0]))

    return html.Div([
    dcc.Tabs([
										                   
                    
					dcc.Tab(label='Individual Bee Data', children=[
                    
					
                    html.Div([   
                        
                        dbc.Card(
                        dbc.CardBody([
                        html.P("Select bee tag."),
                        dcc.Dropdown(
                            options=selectBee,
                            #options=['55','66'],
                            placeholder="Select individual tag",
                            id="dropdown-bee",
                            multi=False,
                            searchable=True),
                        
                        ])
                        ),
                        html.Div(id="individual-chronogram"),
                        html.Div(id="individual-bee")                        
                        ],style={'display': 'flex', 'flexDirection': 'column'}),										
					],style={'font-size':'24px'}, selected_style={'font-size':'24px','font-weight':'bold','backgroundColor': '#007bff', 'color': 'white'}),
                    
                    
											
					dcc.Tab(label='Hive Data', children=[
                        html.Div([
                        
                        html.Div(id='chronogram-all'),              
                        
                        dbc.Card(
                        dbc.CardBody([
                        
                            dash_table.DataTable(
                            id='datatable',
                            columns=[
                                {"name": str(i), "id": str(i)} for i in beeSummary.columns
                            ],
                            data=beeSummary.to_dict('records'),
                            page_action="native",
                            filter_action="native",
                            page_current= 0,
                            page_size= 10,
                            style_table={'overflowX': 'auto','padding-left': '1px'},
                            style_data={
                                'width': '150px', 'minWidth': '150px', 'maxWidth': '250px',
                                
                            },
                            filter_options={
                               'placeholder_text': 'Search...',
                               'case': 'insensitive'
                            },
                            style_data_conditional=[
                                {
                                    'if': {'row_index': 'odd'},
                                    'backgroundColor': 'rgb(240, 240, 240)',
                                }
                            ],
                            ),
                       ]))
                        
                        
                        ],style={'display': 'flex', 'flexDirection': 'column'}),
                        
                        html.Hr(),
                        
                  
                        html.Div([
                                
                            dbc.Card(
                            dbc.CardBody([
                            dash_table.DataTable(
                            id='datatable-sum0',
                            columns=[
                                {"name": str(i), "id": str(i)} for i in Summary0.columns
                            ],
                            data=Summary0.to_dict('records'),
                            page_action="native",
                            style_table={'overflowX': 'auto','padding-left': '10px','padding-right':'10px'},
                            ),
                            
                            ])),
                            
                            dbc.Card(
                            dbc.CardBody([
                            dash_table.DataTable(
                            id='datatable-sum1',
                            columns=[
                                {"name": str(i), "id": str(i)} for i in Summary1.columns
                            ],
                            data=Summary1.to_dict('records'),
                            page_action="native",
                            style_table={'overflowX': 'auto','padding-left': '10px', 'padding-right':'10px', 'padding-top':'15px'},
                            )
                            
                            ])),
                            
                        

                            ], id='tables', style={'display': 'flex', 'flexDirection': 'row', 'flex-wrap': 'nowrap','justify-content': 'space-between'}),
                            
                        html.Hr(),
                            
                        html.Div([
                                
                                    dcc.Graph(figure = density,config={'responsive': True},style={'width': '100vh'}),
                                    dcc.Graph(figure = length,config={'responsive': True},style={'width': '100vh'}),

                                ], id='heatmaps', style={'display': 'flex', 'flexDirection': 'row', "width": "100%",'height': '100vh'}),
                                
                       html.Div([
                       
                        dcc.Graph(figure=cluster1, config={'responsive': True}, style={'width':'100vh'}),
                        dcc.Graph(figure=cluster2, config={'responsive': True}, style={'width':'100vh'})
                       
                       ], id='clusters', style={'display': 'flex', 'flexDirection': 'row', "width": "100%",'height': '100vh'}),
                       
                       
                            
                        html.H5("Tendencies of full timeframe."),
                            
                        html.Div([
                                
                                    dcc.Graph(figure = beeMin,style={'width': '100vh'}),
                                    dcc.Graph(figure = beeSum,style={'width': '100vh'}),

                                ], id='analysis', style={'display': 'flex', 'flexDirection': 'row', "width": "100%",'height': '100vh'}),                           


                        html.Div([
                                
                                    dcc.Graph(figure = beeMinTime,style={'width': '100vh'}),
                                    dcc.Graph(figure = beeSumTime,style={'width': '100vh'}),

                                ], id='analysis', style={'display': 'flex', 'flexDirection': 'row', "width": "100%",'height': '100vh'})  
    
                                      

                        
                        
                    ], style={'font-size':'24px'}, selected_style={'font-weight':'bold','font-size':'24px','backgroundColor': '#007bff', 'color': 'white'})
																			
			], style={'position': 'sticky', 'z-index': '100', 'top': '0'})
      ],style={'padding-left':'20px','padding-right':'20px'})
            

# display data from csv after processing
@app.callback([Output('output-data', 'children'),
              Output('landing-page', 'style')],
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
        
        return children, {'display': 'none'}
        

@app.callback(Output('dateSelector', 'children'),
               Input('activity','data'),
               prevent_initial_call=True)
def select_date(data):
    if data is None:
        return None
    
    allActivity = pd.DataFrame(data)
    allActivity['start'] = pd.to_datetime(allActivity['start'], format='mixed')  
    #date = allActivity['start'].apply(lambda x: fixDate(x))
    #date = date.unique()
    dates = allActivity['start']
    mindate = min(dates)
    maxdate = max(dates)
    
    
    return html.Div([
           html.P("Select date range:"),
           dcc.DatePickerRange(
                    id='my-date-picker-range',
                    min_date_allowed=date(mindate.year, mindate.month, mindate.day),
                    max_date_allowed=date(maxdate.year, maxdate.month, maxdate.day),
                    start_date=date(mindate.year, mindate.month, mindate.day),
                    initial_visible_month=date(mindate.year, mindate.month, mindate.day),
                    end_date=date(maxdate.year, maxdate.month, maxdate.day)
    ),
    ], style={'margin-top':'10px','padding-top':'10px'})
    

@app.callback(Output('latlonInput', 'children'),
               Input('activity','data'),
               prevent_initial_call=True)
def select_latlon(data):
    if data is None:
        return None
    
    return html.Div([
           html.P("Input latitude and longitude:"),
                            
                            dcc.Input(
                            id="lat", type="number",
                            placeholder="Latitude",
                            value=None
                            ),
                            dcc.Input(
                            id="lon", type="number",
                            placeholder="Longitude",
                            value=None
                            ),
    ], style={'margin-top':'10px','padding-top':'10px'})




@app.callback(Output('flights', 'data'),
                Input('my-date-picker-range', 'start_date'),
                Input('my-date-picker-range', 'end_date'),
                Input('all-flights', 'data'),
                prevent_initial_call=True)
def select_a_date(start, end, data):
    #print(start)
    end = date.fromisoformat(end)
    #print(end)
    end_time = datetime(end.year, end.month, end.day, hour=23, minute=59, second=59)
    flights = pd.DataFrame(data)
    flights['tripStart'] = pd.to_datetime(flights['tripStart'], format='mixed')  
    #print(flights[flights['tripStart'] > end])
    #dates = selected
    #s = flights[flights['date'].isin(dates)]
    #return s.to_dict('records')
    dates = flights[(flights['tripStart'] >= start) & (flights['tripStart'] <= end_time)]
    #print(dates)
    return dates.to_dict('records')


@app.callback(Output('sunrise-sunset', 'data'),
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
    dt['date'] = dt['date'].apply(lambda x: fixDate(x))
    
    return dt.to_dict('records')


@app.callback([Output('chronogram-all', 'children')],
              Input('sunrise-sunset', 'data'),
              State('flights', 'data'),
              State('activity', 'data'),
              prevent_initial_call=True)             
def displayChronogramAll(srss, data, activity):

    #none checks
    if data is None:
        raise PreventUpdate
    if activity is None:
        raise PreventUpdate
    if srss is None:
        raise PreventUpdate
        
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
    flights['duration'] = (flights['tripEnd'] - flights['tripStart'])
    flights['duration'] = flights['duration'].apply(lambda x: x.total_seconds()/60)
        
    bee = flights[flights['tagID'] == bee_id].copy()
    
    
    fig1, fig2, fig3 = plotHist(bee)
    fig4 = flightDensity(bee)
    
    
    return [
    
    
    
        html.Div([
                                
                                    dcc.Graph(figure = fig1,style={'width': '100vh'}),
                                    dcc.Graph(figure = fig2,style={'width': '100vh'}),

                                ], id='barcharts', style={'display': 'flex', 'flexDirection': 'row', "width": "100%",'height': '100vh'}),  

       html.Div([
                                
                                    dcc.Graph(figure = fig3,style={'width': '100vh'}),
                                    dcc.Graph(figure = fig4,style={'width': '100vh'}),

                                ], id='summary', style={'display': 'flex', 'flexDirection': 'row', "width": "100%",'height': '100vh'}), 
    
    ]
    


@app.callback([Output('individual-chronogram', 'children')],
              Input('dropdown-bee', 'value'),
              Input('sunrise-sunset', 'data'),
              State('flights', 'data'),
              State('activity', 'data'),
              prevent_initial_call=True)             
def displayChronogramSingle(beeid, srss, data, activity):

    #none checks
    if data is None:
        raise PreventUpdate
    if activity is None:
        raise PreventUpdate
    if srss is None:
        raise PreventUpdate
    if beeid is None:
        raise PreventUpdate
        
        
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
    app.run(debug=True)