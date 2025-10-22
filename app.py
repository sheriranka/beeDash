#imports

from dash import Dash, dash_table, dcc, html, Input, Output, callback, State, clientside_callback, ctx
import dash_daq as daq


import pandas as pd
import numpy as np
import itertools 
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

from flights import classifyLoc, cleanData, summaryData, makeTotalSum, divideBees, findSimilar
from graphing import getSRSS, separateFlights, addShapes, createActoGraphAll, flightDensity, flightLength, createActoGraph, plotHist, plotClusterTimeDur, plotClusterDayDur, linReg, fixDate, beeAverage, createActoGraphSub, plotProbs


#app creation


external_stylesheets = [dbc.themes.BOOTSTRAP,'https://codepen.io/chriddyp/pen/bWLwgP.css']
#app = Dash(__name__,requests_pathname_prefix='/beeapp/', routes_pathname_prefix='/beeapp/',external_stylesheets=external_stylesheets,suppress_callback_exceptions=True,)
app = Dash(__name__,requests_pathname_prefix='/beeapp/', routes_pathname_prefix='/beeapp/',external_stylesheets=external_stylesheets,suppress_callback_exceptions=True,)
#app = Dash(__name__, external_stylesheets=external_stylesheets,suppress_callback_exceptions=True)
app.title = "BeehAIve"
server = app.server

#constants

tzf = TimezoneFinder() 
perPage = 4
gray = "#ebebeb"
orange = "#ffba7d"

#layout

app.layout = html.Div([

         html.Div([
        
         html.Div([
         
                                html.Div([
                                    html.H1("BeehAIve",style={'font-family':'Bahnschrift','textAlign': 'center','padding':'2vh'}),
                                ], style={'width':'100%','height':'10vh','backgroundSize': 'auto','border':'1px black solid','-webkit-text-stroke': '1px white', 'background-color':'rgba(255,255,255,0.7)'}),
         
             html.Div([
                                html.Div([
                                
                                dbc.Card(
                                dbc.CardBody([
                                
                                
                                html.Div(id='sr-ss'),
                                
                                
                                
                                html.P("""This tool serves to visualize and analyze records of uniquely identified bees at the entrance to the colony. Its purpose is to
                                facilitate analysis to biologists and beekeepers unfamiliar with data science and programming.
                                It requires the following columns in order in a CSV file:"""),
                                html.Ul(id='requirements',children=[
                                    html.Li("Column with bee tag ID."),
                                    html.Li(["Column with datetime. Must follow this format order:",html.Br(),  html.I("YYYY/MM/DD H:M:S", style={'font-size':'10px'})]),
                                    html.Li("Column with entering/exiting label.")

                                ],style={'list-style-type':'square'}),
                                                               
                                html.P("Dash Instructions",style={'fontWeight':'bold'}),
                        
                        
                                html.Ul(children=[
                                                        html.Li("Individual Bee Data: Select a bee tag from the dropdown to view data visualizations associated with that bee."),
                                                        html.Li("Hive Data: Search for tags or values in empty block above values labeled 'Search..' in Summary Table to filter table display."),
                                                        html.Li("Subset Bees: Select an amount of bees to observe, filter for morning and afternoon focus. Select an individual bee tag to display similar bees."),
                                                        html.Li("Date Range: Select an initial and final date to narrow down the data displayed to a desired date range."),
                                                        html.Li("Duration Filter: Input a minimum (seconds) and maximum (minutes) duration to filter flights."),
                                                        html.Li("Accessing the Chronogram: Enter latitude and longitude of your desired location in Chronogram tab to display chronogram with sunrise/sunset display.")

                                                    ],style={'list-style-type':'square','font-size':'12px'}),
                                                    
                                                    
                                html.P("Visualization Instructions",style={'fontWeight':'bold'}),
                                
                                html.Ul(children=[
                                                        html.Li("Hover over the objects in the visualization to display details."),
                                                        html.Li("Drag and drop on visualization to zoom in desired region."),
                                                        html.Li("Click home icon to reset zoom to default."),
                                                        html.Li("Click camera icon to save a static version of the visualization to computer."),


                                                    ],style={'list-style-type':'square', 'font-size':'12px'}),
                                                    
                                

                                html.P("Upload a csv file to begin visualizing."),
                                
                                ])),
                                
                                
                                ], style={'padding-top':'10px','padding-right':'30px', 'margin-bottom':'20px'},className="landing-text"),                      
                                
                                html.Img(src="/beeapp/assets/beeart.png",style={'border-radius': '50%','padding':'1%','margin':'auto'},className="logo-image"),
                                
                                                                 
             ], style={'display': 'flex'},className="landing"),
        ], id='landing-page', style={'width':'100%', 'padding-right':'10px', 'height':'100%','backgroundImage': 'url("/beeapp/assets/hex.jpg")','backgroundRepeat':'repeat'}),
            

        html.Div(children=[
        
        html.Div(id='how-to-use'),
        html.Div(id='download-flights'),
        dcc.Upload(
                                        id='upload-csv',
                                        children=html.Button("Upload CSV"),
                                        multiple=True,
                                        style={'padding-left':'10px','padding-top':'5px'}
                                    ),
        ],style={'display':'flex','flexDirection':'row'}),
        html.Div([
        
        
            html.Div(id="logo-title"),
            
            html.Div([
            html.Div(id="dateSelector"),   
            html.Div(id="durationSelector-1"),
            html.Div(id="durationSelector-2"),
            ],style={'display':'flex','flexDirection':'row','align-items': 'center','justify-content': 'space-between', 'background-color':'white'}),
            
            html.Hr(),
        
            dcc.Loading(
                id="loading-main",
                type="circle",
                children=html.Div(id="output-data"),
                style={"margin-top":"20px"},
                target_components ={"output-data": "children"},
                color="#301808"
            ),
            html.Div(id="app-body"), 
            dcc.Store(id='stored-data', storage_type='session'),
            
        
        ], style={'width':'100%', 'display': 'flex', 'flexDirection': 'column','margin-top':'20px'}),

],style={'marginRight': '20px', 'marginLeft': '20px', 'fontFamily': 'Arial, sans-serif'}),


html.Footer(children=[html.P("Contact here: laeticiaaucerius@gmail.com", style={'font-size':'10px', 'padding-right':'30px'}),])
        
])



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
        ndf['tagID'] = ndf['tagID'].apply(lambda x: str(x))
        
        allActivity, flight = cleanData(ndf)
        flight['date'] = flight['tripStart'].apply(lambda x: fixDate(x))
        flight['hour'] = flight['tripStart'].apply(lambda x: x.hour)
        flight['timeOfDay'] = flight['tripStart'].apply(lambda x: (x.hour * 60 + x.minute) * 60)
        flights_mod = separateFlights(flight)
        x_axes = {'hour':flight['hour'].unique(),'date':flight['date'].unique()}
        
        date_axes = flight[['tagID','date']].value_counts()
        hour_axes = flight[['tagID','hour']].value_counts()
        
        y_axes = {'hour':max(hour_axes)+1,'date':max(date_axes)+1}
        
        bee_division, bee_vectors = divideBees(flight)

        return html.Div([

                        
            dcc.Store(id='stored-data', data=ndf.to_dict('records')), 
            dcc.Store(id='activity', data=allActivity.to_dict('records')), 
            dcc.Store(id='flights', data=flight.to_dict('records')), 
            dcc.Store(id='all-flights', data=flight.to_dict('records')),
            dcc.Store(id='sunrise-sunset', data=None),
            dcc.Store(id='flights-mod',data=flights_mod.to_dict('records')),
            dcc.Store(id='bee-division',data=bee_division),
            dcc.Store(id='bee-vectors',data=bee_vectors),
            dcc.Store(id='x-axes',data=x_axes),
            dcc.Store(id='y-axes',data=y_axes),
            dcc.Store(id="layout-loaded")
       ])
            


    
    else:
        return "The file needs to be a csv."
        
        
        
@app.callback(Output('app-body','children'),
                Output('layout-loaded', 'data'),
                Input('activity','data'),
                prevent_initial_call=True)
def display_app(activity):


    return html.Div([
                dcc.Tabs([
                    dcc.Tab(label='Individual Bee Data', children=[
                    
                        html.Div([
                            
                            html.Div([
                            dbc.Card(
                            dbc.CardBody([
                            html.P("Select bee tag."),
                            
                            dcc.Dropdown(
                                #options=selectBee,
                                placeholder="Select individual tag",
                                id="dropdown-bee",
                                multi=False,
                                searchable=True),
                            
                            ]),style={'width':'100%'}),
                            
                            dbc.Card(
                            dbc.CardBody([
                            html.P("Average of all bees in dataset."),
                            
                            ]),style={'width':'100%','alignItems':'center','justifyContent':'center'}),
                            ],style={'display':'flex','width':'100%'},className="bee-selection"),
                            
                            dcc.Tabs(
                                vertical=True,
                                children=[
                                     dcc.Tab(className="custom-tab", selected_className="selected",label='Flights at Time of Day', children=[
                                     
                                     
                                     html.Div([
                                     
                                         html.Div(id='fig1',children=[
                                         
                                         
                                         html.P("Select a bee to begin visualizing.",style={'padding-top':'10px'})
                                         
                                         ],style={'width': '100%','height':'80vh','backgroundColor':'white','display': 'flex','width': '100%','justifyContent': 'center','alignItems': 'center'}),
                                         
                                         dcc.Graph(id='fig1_',config={'responsive': True},style={'width': '100%','height':'80vh'}),
                                         
                                     ],style={'display':'flex'},className="double-display")
                                     
                                     ],style={'backgroundColor':'#feffe3'}, selected_style={'border': f'2px solid {orange}','font-weight':'bold','backgroundColor': '#301808', 'color': 'white'}),
                                     dcc.Tab(className="custom-tab", selected_className="selected",label='Flights per Day', children=[
                                     
                                     
                                     html.Div([
                                     
                                         html.Div(id='fig2',children=[
                                         
                                         
                                         html.P("Select a bee to begin visualizing.",style={'padding-top':'10px'})
                                         
                                         ],style={'width': '100%','height':'80vh','backgroundColor':'white','display': 'flex','width': '100%','justifyContent': 'center','alignItems': 'center'}),
                                         
                                         dcc.Graph(id='fig2_',config={'responsive': True},style={'width': '100%','height':'80vh'}),
                                         
                                     ],style={'display':'flex'},className="double-display")
                                     
                                     
                                     
                                     
                                     ],style={'backgroundColor':'#feffe3'}, selected_style={'border': f'2px solid {orange}','font-weight':'bold','backgroundColor': '#301808', 'color': 'white'}),
                                     dcc.Tab(className="custom-tab", selected_className="selected",label='Flight Duration per Day', children=[
                                     
                                     html.Div([
                                     
                                         html.Div(id='fig3',children=[
                                         
                                         
                                         html.P("Select a bee to begin visualizing.",style={'padding-top':'10px'})
                                         
                                         ],style={'width': '100%','height':'80vh','backgroundColor':'white','display': 'flex','width': '100%','justifyContent': 'center','alignItems': 'center'}),
                                         html.Div(id='fig3_',children=[
                                         
                                         dcc.Graph(id='fig3_',config={'responsive': True},style={'width': '100%','height':'80vh'}),
                                         
                                         ],style={'backgroundColor':'#feffe3','width': '100%','height':'80vh','display': 'flex','width': '100%','justifyContent': 'center','alignItems': 'center'})
                                         
                                     ],style={'display':'flex'},className="double-display")
                                     
                                     
                                     
                                     ],style={'backgroundColor':'#feffe3'}, selected_style={'border': f'2px solid {orange}','font-weight':'bold','backgroundColor': '#301808', 'color': 'white'}),
                                     dcc.Tab(className="custom-tab", selected_className="selected",label='Flights at Time of Day Distribution', children=[
                                     
                                     
                                     html.Div([
                                     
                                         html.Div(id='probs1',children=[
                                         
                                         
                                         html.P("Select a bee to begin visualizing.",style={'padding-top':'10px'})
                                         
                                         ],style={'width': '100%','height':'80vh','backgroundColor':'white','display': 'flex','width': '100%','justifyContent': 'center','alignItems': 'center'}),
                                         
                                         dcc.Graph(id='probs1_',config={'responsive': True},style={'width': '100%','height':'80vh'}),
                                         
                                     ],style={'display':'flex'},className="double-display")
                                     
                                     ],style={'backgroundColor':'#feffe3'}, selected_style={'border': f'2px solid {orange}','font-weight':'bold','backgroundColor': '#301808', 'color': 'white'}),
                                     
                                     dcc.Tab(className="custom-tab", selected_className="selected",label='Flights at Each Day Distribution', children=[
                                     
                                     
                                     html.Div([
                                     
                                         html.Div(id='probs2',children=[
                                         
                                         
                                         html.P("Select a bee to begin visualizing.",style={'padding-top':'10px'})
                                         
                                         ],style={'width': '100%','height':'80vh','backgroundColor':'white','display': 'flex','width': '100%','justifyContent': 'center','alignItems': 'center'}),
                                         
                                         dcc.Graph(id='probs2_',config={'responsive': True},style={'width': '100%','height':'80vh'}),
                                         
                                     ],style={'display':'flex'},className="double-display")
                                     
                                     ],style={'backgroundColor':'#feffe3'}, selected_style={'border': f'2px solid {orange}','font-weight':'bold','backgroundColor': '#301808', 'color': 'white'}),
                                     dcc.Tab(className="custom-tab", selected_className="selected",label='Flights at Time and Date', children=[
                                     
                                     
                                     html.Div([
                                     
                                         html.Div(id='fig4',children=[
                                         
                                         
                                         html.P("Select a bee to begin visualizing.",style={'padding-top':'10px'})
                                         
                                         ],style={'width': '100%','height':'80vh','backgroundColor':'white','display': 'flex','width': '100%','justifyContent': 'center','alignItems': 'center'}),
                                         html.Div(id='fig4_',children=[
                                         
                                         
                                         
                                         ],style={'backgroundColor':'#feffe3','width': '100%','height':'80vh','display': 'flex','width': '100%','justifyContent': 'center','alignItems': 'center'})
                                         
                                     ],style={'display':'flex'},className="double-display")
                                     
                                     
                                     
                                     ],style={'backgroundColor':'#feffe3'}, selected_style={'border': f'2px solid {orange}','font-weight':'bold','backgroundColor': '#301808', 'color': 'white'}),
                                     
                                     dcc.Tab(className="custom-tab", selected_className="selected",label='Clustering for Time of Day and Flight Duration', children=[
                                     
                                     
                                        dbc.Card(
                                        dbc.CardBody([
                                        
                                         dcc.Dropdown(
                                         options=[2,3,4],
                                         placeholder="Select cluster number",
                                         id="cluster-dropdown-single",
                                         multi=False),
                                         html.Div(id='cluster-single',children=[html.P("Select cluster number to display graph.")])
                                        
                                        ]),style={'height':'100%','margin-top':'5vh','margin-left':'5%'},className="cards"),
                                     
                                     ],style={'backgroundColor':'#feffe3'}, selected_style={'border': f'2px solid {orange}','font-weight':'bold','backgroundColor': '#301808', 'color': 'white'}),
                                     dcc.Tab(className="custom-tab", selected_className="selected",label='Chronogram', children=[
                                     
                                     
                                     html.Div([
                                    html.Div([
                                           html.P("Input latitude and longitude:",style={"color":"white"}),
                                                            
                                                            dcc.Input(
                                                            id="lat2", type="number",
                                                            placeholder="Latitude",
                                                            value=None
                                                            ),
                                                            dcc.Input(
                                                            id="lon2", type="number",
                                                            placeholder="Longitude",
                                                            value=None
                                                            ),
                                    ], style={'padding-top':'10px','padding-left':'10px','backgroundColor':'#301808','padding-bottom':'10px'}),
                                    
                                    

                                    html.Div([
                                            dcc.Loading(
                                                children=html.Div(id='individual-chronogram',children=[html.P("Input coordinates to display chronogram.",style={'padding-left':'30px','padding-right':'30px','padding-top':'10px'})],style={'display': 'flex','justifyContent': 'center','alignItems': 'center','width': '100%','height':'80vh','backgroundColor':'white'}),
                                                type="circle",
                                                color="#301808"
                                            ),                                   
                                        ],style={'display':'flex','height': '80vh','flexDirection':'column'}),
                                    ],className="chrono")
                                    ],style={'backgroundColor':'#feffe3'}, selected_style={'border': f'2px solid {orange}','font-weight':'bold','backgroundColor': '#301808', 'color': 'white'}), 

                                     
                                ],className="vertical-tabs")                        
                            ],style={'display': 'flex','flexDirection': 'column'},className="background-image"),										
                        ],style={'font-size':'24px','backgroundColor':'#feffe3'}, selected_style={'border': f'2px solid {orange}','font-size':'24px','font-weight':'bold','backgroundColor': '#301808', 'color': 'white'}),
                        
                        
                    dcc.Tab(label="Hive Data", children=[
                    
                        html.Div([
                        
                        dcc.Tabs(vertical=True, children=[
                        
                        
                                dcc.Tab(className="custom-tab", id='flight-summary',selected_className="selected",label="Summary Table", children=[
                                
                                      
                                ],style={'backgroundColor':'#feffe3'}, selected_style={'border': f'2px solid {orange}','font-weight':'bold','backgroundColor': '#301808', 'color': 'white'}),
                                    
                                dcc.Tab(className="custom-tab", id='general-summary', selected_className="selected",label="General Summary",children=[
                                    
                                
                                    
                                ],style={'backgroundColor':'#feffe3'}, selected_style={'border': f'2px solid {orange}','font-weight':'bold','backgroundColor': '#301808', 'color': 'white'}),
                                    
                                    dcc.Tab(className="custom-tab", selected_className="selected",label="Flights at Time of Day",children=[
                                    
                                        dbc.Card(
                                        dbc.CardBody([
                                        dcc.Graph(id='density',config={'responsive': True},style={'width': '100%'}),
                                         
                                        ]),style={'height':'100%','margin-top':'5vh','margin-left':'5%'},className="cards")
                                         
                                    ],style={'backgroundColor':'#feffe3'}, selected_style={'border': f'2px solid {orange}','font-weight':'bold','backgroundColor': '#301808', 'color': 'white'}),
                                    
                                    dcc.Tab(className="custom-tab", selected_className="selected",label="Duration of Flights at Time of Day",children=[
                                    
                                        dbc.Card(
                                        dbc.CardBody([
                                        dcc.Graph(id='length',config={'responsive': True},style={'width': '100%'})
                                        ]),style={'height':'100%','margin-top':'5vh','margin-left':'5%'},className="cards"),
                                    ],style={'backgroundColor':'#feffe3'}, selected_style={'border': f'2px solid {orange}','font-weight':'bold','backgroundColor': '#301808', 'color': 'white'}),
                                    
                                    dcc.Tab(className="custom-tab", selected_className="selected",label="Clustering for Time of Day and Flight Duration",children=[
                                        dbc.Card(
                                        dbc.CardBody([
                                        
                                         dcc.Dropdown(
                                         options=[2,3,4],
                                         placeholder="Select cluster number",
                                         id="cluster-dropdown-1",
                                         multi=False),
                                         html.Div(id='cluster-all-1',children=[html.P("Select cluster number to display graph.")])
                                        
                                        ]),style={'height':'100%','margin-top':'5vh','margin-left':'5%'},className="cards"),
                                    ],style={'backgroundColor':'#feffe3'}, selected_style={'border': f'2px solid {orange}','font-weight':'bold','backgroundColor': '#301808', 'color': 'white'}),
                                    dcc.Tab(className="custom-tab", selected_className="selected",label="Clustering for Flight Duration and Age",children=[
                                        dbc.Card(
                                        dbc.CardBody([
                                        
                                         dcc.Dropdown(
                                         options=[2,3,4],
                                         placeholder="Select cluster number",
                                         id="cluster-dropdown-2",
                                         multi=False),
                                         html.Div(id='cluster-all-2',children=[html.P("Select cluster number to display graph.")])
                                        
                                        ]),style={'height':'100%','margin-top':'5vh','margin-left':'5%'},className="cards"),
                                    ],style={'backgroundColor':'#feffe3'}, selected_style={'border': f'2px solid {orange}','font-weight':'bold','backgroundColor': '#301808', 'color': 'white'}),
                                    dcc.Tab(className="custom-tab", selected_className="selected",label="Relationship Between Time Passed and Flight Duration",children=[
                                    
                                    dbc.Card(
                                    dbc.CardBody([
                                    html.Div([
                                            dcc.Graph(id='bee-min',style={'height':'70vh'},className="double-graph"),
                                            dcc.Graph(id='bee-min-time',style={'height':'70vh'},className="double-graph"),
                                            
                                            
                                    ], style={'display': 'flex','width': '100%'},className="double-display"),
                                    
                                    ]),style={'height':'100%','margin-top':'5vh','margin-left':'5%'},className="cards"),
                                    
                                    ],style={'backgroundColor':'#feffe3'}, selected_style={'border': f'2px solid {orange}','font-weight':'bold','backgroundColor': '#301808', 'color': 'white'}),
                                    dcc.Tab(className="custom-tab", selected_className="selected",label="Relationship Between Time Passed and Average Number of Flights", children=[
                                    
                                    
                                    dbc.Card(
                                    dbc.CardBody([
                                    html.Div([
                                            dcc.Graph(id='bee-sum',style={'height':'70vh'},className="double-graph"),
                                            dcc.Graph(id='bee-sum-time',style={'height':'70vh'},className="double-graph")
                                            
                                    ],style={'display': 'flex','width':'100%'},className="double-display")
                                    
                                    ]),style={'height':'100%','margin-top':'5vh','margin-left':'5%'},className="cards"),
                                    
                                    ],style={'backgroundColor':'#feffe3'}, selected_style={'border': f'2px solid {orange}','font-weight':'bold','backgroundColor': '#301808', 'color': 'white'}),
                                    
                                    dcc.Tab(className="custom-tab", selected_className="selected",label="Chronogram", children=[
                                    
                                    html.Div([
                                    html.Div([
                                           html.P("Input latitude and longitude:",style={"color":"white"}),
                                                            
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
                                    ], style={'padding-top':'10px','padding-left':'10px','backgroundColor':'#301808','padding-bottom':'10px'}),
                                    
                                    

                                    html.Div([
                                    
                                            dcc.Loading(
                                                children=html.Div(id='chronogram-all',children=[html.P("Input coordinates to display chronogram.",style={'padding-left':'30px','padding-right':'30px','padding-top':'10px'})],style={'display': 'flex','justifyContent': 'center','alignItems': 'center','width': '100%','height':'80vh','backgroundColor':'white'}),
                                                type="circle",
                                                color="#301808"
                                            ),   
                                            
                                            html.Div(id="hover-output"),
                                     ],style={'display':'flex','height': '80vh','flexDirection':'column'}),
                                    ],className="chrono")
                                    ],style={'backgroundColor':'#feffe3'}, selected_style={'border': f'2px solid {orange}','font-weight':'bold','backgroundColor': '#301808', 'color': 'white'}),       
                                                                       
                                    ],className="vertical-tabs"),
                                    
                                    ],className="background-image")
                                    
                               ],style={'font-size':'24px','backgroundColor':'#feffe3'}, selected_style={'border': f'2px solid {orange}','font-size':'24px','font-weight':'bold','backgroundColor': '#301808', 'color': 'white'}),
                    
                    dcc.Tab(label="Subset Bees", children=[
                        
                        html.Div([
                            html.Div([
                                html.Div([
                                
                                
                                html.P("Select number of bees to observe.",style={}),
                                dcc.Input(id='select-quant', type='number', min=1)
                                
                                ],style={'width':'100%','alignItems':'center','justifyContent':'center','backgroundColor': '#301808', 'color': 'white','padding-left':'5px'}),
                                
                                html.Div([
                                
                                
                                html.P("Select filter for bees.",style={'color': 'white'}),
                                dcc.Dropdown(['All', 'Morning Focused', 'Afternoon Focused', 'Even Distribution'], 'All', id='bee-filter'),
                                
                                ],style={'width':'100%','alignItems':'center','justifyContent':'center','backgroundColor': '#301808','padding-left':'5px'}),
                                
                                
                                html.Div([
                                
                                html.P("Select a bee to find similar bees.",style={'color': 'white'}),
                                dcc.Dropdown(searchable=True, id='similar-bees'),
                                
                                ],style={'width':'100%','alignItems':'center','justifyContent':'center','backgroundColor': '#301808','padding-left':'5px'}),
                            ],style={'display':'flex'}, className="dropdown-row"),
                            
                            html.Div([
                                           html.P("Input latitude and longitude:",style={"color":"white"}),
                                                            
                                                            dcc.Input(
                                                            id="lat3", type="number",
                                                            placeholder="Latitude",
                                                            value=None
                                                            ),
                                                            dcc.Input(
                                                            id="lon3", type="number",
                                                            placeholder="Longitude",
                                                            value=None
                                                            ),
                                    ], style={'padding-top':'10px','padding-left':'10px','backgroundColor':'#301808','padding-bottom':'10px','width':'100%'}),
                            
                            dbc.Pagination(id="pagination", max_value=0, first_last=True, previous_next=True, style={'width':'100%','justify-content':'center','margin-top':'10px'}),
                            dcc.Store(id='pagination-data'),
                            
                            dcc.Loading(
                                children=html.Div(id='chrono-sub',children=[html.P("Select number of bees and input coordinates to display chronograms.",style={'padding-left':'30px','padding-right':'30px','padding-top':'10px'})],style={'display': 'flex','justifyContent': 'center','alignItems': 'center','width': '100%','height':'80vh','backgroundColor':'white'}),
                                type="circle",
                                color="#301808"
                            ),   
                        
                        ],className="background-image")
                    
                    ],style={'font-size':'24px','backgroundColor':'#feffe3'}, selected_style={'border': f'2px solid {orange}','font-size':'24px','font-weight':'bold','backgroundColor': '#301808', 'color': 'white'}),
                    
                    ], style={'width':'100%'})
                        
                    ],style={}), True


#populate dropdowns
@app.callback(Output('dropdown-bee','options'),
                Output('similar-bees','options'),
                Input('flights','data'),
                Input('layout-loaded','data'),
                prevent_initial_call=True)
def populate_dropdowns(flights,loaded):

    if flights == None:
        return None
    flight = pd.DataFrame(flights)
    selectBee = pd.unique(flight['tagID'])
    return selectBee, selectBee
    
    
#populate general graphs
@app.callback(Output('fig1_','figure'),
                Output('fig2_','figure'),
                Output('fig3_','figure'),
                Output('probs1_','figure'),
                Output('probs2_','figure'),
                Input('layout-loaded','data'),
                Input('flights','data'),
                Input('y-axes','data'),
                prevent_initial_call=True)
def populate_graphs(loaded,flights,y_axes):

    if flights == None:
        return None
    flight = pd.DataFrame(flights)
    
    flight['tripStart'] = pd.to_datetime(flight['tripStart'], format='mixed') 
    flight['tripEnd'] = pd.to_datetime(flight['tripEnd'], format='mixed') 
    flight['duration'] = flight['tripEnd'] - flight['tripStart']
    flight['theTime'] = flight['tripStart'].apply(lambda x: pd.to_datetime(pd.to_datetime(x).time().strftime('%H:%M:%S')))

    #Average of all bees
    
    fig1, fig2, fig3 = beeAverage(flight, y_axes)
    
    probs1, probs2 = plotProbs(flight,flight)
    
    return fig1, fig2, fig3, probs1, probs2
    
    
#populate entire hive graphs
@app.callback(Output('density','figure'),
                Output('length','figure'),
                Output('bee-min','figure'),
                Output('bee-min-time','figure'),
                Output('bee-sum','figure'),
                Output('bee-sum-time','figure'),
                Input('layout-loaded','data'),
                Input('flights','data'),
                Input('activity','data'),
                Input('all-flights','data'),
                prevent_initial_call=True)
def populate_hive_graphs(loaded,flights,activity,all_flights):

    if flights == None:
        return None
    if activity == None:
        return None
    if all_flights == None:
        return None
    flight = pd.DataFrame(flights)
    all_flight = pd.DataFrame(all_flights)
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

    density = flightDensity(flight)
    length = flightLength(flight)
        
    beeSum, beeMin, beeSumTime, beeMinTime = linReg(allActivity,all_flight)
    
    return density, length, beeMin, beeMinTime, beeSum, beeSumTime
    
    
    
       
#populate tables in general summary
@app.callback(Output('flight-summary','children'),
                Output('general-summary','children'),
                Input('layout-loaded','data'),
                Input('flights','data'),
                Input('activity','data'),
                Input('all-flights','data'),
                prevent_initial_call=True)
def populate_tables(loaded,flights,activity,all_flights):

    if flights == None:
        return None
    if activity == None:
        return None
    if all_flights == None:
        return None
                
                
    flight = pd.DataFrame(flights)
    
    flight['tripStart'] = pd.to_datetime(flight['tripStart'], format='mixed') 
    flight['tripEnd'] = pd.to_datetime(flight['tripEnd'], format='mixed') 
    flight['duration'] = flight['tripEnd'] - flight['tripStart']
    flight['theTime'] = flight['tripStart'].apply(lambda x: pd.to_datetime(pd.to_datetime(x).time().strftime('%H:%M:%S')))
    
    
    allActivity = pd.DataFrame(activity)
    allActivity['start'] = pd.to_datetime(allActivity['start'], format='mixed') 
    allActivity['end'] = pd.to_datetime(allActivity['end'], format='mixed')   

    beeSummary = summaryData(allActivity,flight).round(2)
    
    
    Summary0, Summary1 = makeTotalSum(beeSummary, flight)
      
    Summary0.reset_index(inplace=True)
    Summary0 = Summary0.rename(columns={'index': 'Classification'}).round(2)
    
    Summary1 = Summary1.round(2)
    
    return                      html.Div([
    
                                dbc.Card(
                                dbc.CardBody([
                                    html.P("General summary of all bees in dataset including data such as longest and shortest flight.")
                                ]),style={'padding':'1%'},className="cards"),
                                
                                dbc.Card(
                                dbc.CardBody([
                                    html.Div([

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
                                        style_table={'position':'relative','width':'100%','overflowX': 'auto'},
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
                                        )
                                        ],style={'width':'90%','margin':'auto'})
                                ]),style={'padding-top':'5vh'},className="cards") ]), html.Div([
                                dbc.Card(
                                dbc.CardBody([
                                    html.P("Statistical summary of all flights in the dataset.")
                                ]),style={'padding':'1%'},className="cards"),
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
                                        style_table={'overflowX': 'auto','padding-left': '15px','padding-right':'10px','margin':'2%'},
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
                                        style_table={'overflowX': 'auto','padding-left': '15px', 'padding-right':'10px', 'padding-top':'15px','margin':'2%'},
                                        )
                                        
                                        ])),
                                        
                                        
                                        ], id="tables",style={'display': 'flex','flexDirection':'column'},className="cards"),
                                    
                                    
                                    ],style={'height':'80vh'})



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
           html.P("Select date range to subset the data:"),
           dcc.DatePickerRange(
                    id='my-date-picker-range',
                    min_date_allowed=date(mindate.year, mindate.month, mindate.day),
                    max_date_allowed=date(maxdate.year, maxdate.month, maxdate.day),
                    start_date=date(mindate.year, mindate.month, mindate.day),
                    initial_visible_month=date(mindate.year, mindate.month, mindate.day),
                    end_date=date(maxdate.year, maxdate.month, maxdate.day)
    ),
    ], style={'padding-top':'10px'})
    
    

@app.callback(Output('durationSelector-1', 'children'),
               Input('activity','data'),
               prevent_initial_call=True)
def select_dur1(data):
    if data is None:
        return None   
    return html.Div([
               html.P("Select minimum flight duration to filter (seconds):"),
               dcc.Input(
               id="sec-dur", type="number",
               placeholder="Seconds",
               value=0)
           ],style={'padding-top':'10px'})

@app.callback(Output('durationSelector-2', 'children'),
               Input('activity','data'),
               prevent_initial_call=True)
def select_dur2(data):
    if data is None:
        return None
    return html.Div([
               html.P("Select maximum flight duration to filter (minutes):"),
               dcc.Input(
               id="min-dur", type="number",
               placeholder="Minutes",
               value=720)
           ],style={'padding-top':'10px'})
            

@app.callback(Output('logo-title', 'children'),
               Input('activity','data'),
               prevent_initial_call=True)
def select_date(data):
    if data is None:
        return None
    
    
    return html.Div([
           html.H1("BeehAIve",style={'font-family':'Bahnschrift','textAlign': 'center','padding':'10vh', 'backgroundColor':'rgba(255, 255, 255,0.5)'}),
    ], style={'backgroundImage': 'url("/beeapp/assets/hex.jpg")','backgroundRepeat':'repeat','width':'100%','height':'30vh','backgroundSize': 'auto','border':'1px black solid','-webkit-text-stroke': '1px white'})





@app.callback(Output('how-to-use', 'children'),
               Input('activity','data'),
               prevent_initial_call=True)
def show_instructions(data):               
    if data is None:
        return None    
               
    return html.Div([
        
            dbc.Button("How To Use", id="open", n_clicks=0,style={'background-color':'#301808'}),
        
        
                dbc.Modal(
                [
                    dbc.ModalHeader(dbc.ModalTitle("Instructions")),
                    dbc.ModalBody([
                    html.P("Dash Instructions"),
            
            
                    html.Ul(children=[
                                            html.Li("Individual Bee Data: Select a bee tag from the dropdown to view data visualizations associated with that bee."),
                                            html.Li("Hive Data: Search for tags or values in empty block above values labeled 'Search..' in Summary Table to filter table display."),
                                            html.Li("Subset Bees: Select an amount of bees to observe, filter for morning and afternoon focus. Select an individual bee tag to display similar bees."),
                                            html.Li("Date Range: Select an initial and final date to narrow down the data displayed to a desired date range."),
                                            html.Li("Duration Filter: Input a minimum (seconds) and maximum (minutes) duration to filter flights."),
                                            html.Li("Accessing the Chronogram: Enter latitude and longitude of your desired location in Chronogram tab to display chronogram with sunrise/sunset display.")

                                        ],style={'list-style-type':'square','font-size':'12px'}),
                                        
                                        
                    html.P("Visualization Instructions"),
                    
                    html.Ul(children=[
                                            html.Li("Hover over the objects in the visualization to display details."),
                                            html.Li("Drag and drop on visualization to zoom in desired region."),
                                            html.Li("Click home icon to reset zoom to default."),
                                            html.Li("Click camera icon to save a static version of the visualization to computer."),


                                        ],style={'list-style-type':'square', 'font-size':'12px'}),
                                             
                    ]),
                    dbc.ModalFooter(
                        dbc.Button("Close", id="close", className="ms-auto", n_clicks=0,style={'background-color':'#301808'})
                    ),
            ],
            id="modal",
            is_open=False,
            )
        ], id="instructions-modal", style={'padding-top':'5px'}),
        
        
@app.callback(Output('download-flights', 'children'),
               Input('activity','data'),
               prevent_initial_call=True)
def download_display(data):               
    if data is None:
        return None    
               
    return html.Div([
                html.Button("Download Activity", id="download-button",style={'background-color':'#301808','color':'white'}),
                dcc.Download(id="download-setting")
           
        ], id="download-div", style={'padding-top':'5px','padding-left':'5px'})
        
  

@callback(
    Output("download-setting", "data"),
    Input("download-button", "n_clicks"),
    State("activity",'data'),
    prevent_initial_call=True,
)
def func(n_clicks, data):
    df = pd.DataFrame(data)
    #df = df[['tagID','tripStart','tripEnd']]
    return dcc.send_data_frame(df.to_csv, filename="activity.csv", index=False)  
        

@app.callback(Output('flights', 'data'),
              Output('flights-mod', 'data'),
              Output('bee-division', 'data'),
              Output('bee-vectors', 'data'), 
              Output('y-axes', 'data'),
              Output('x-axes', 'data'),
                Input('sec-dur', 'value'),
                Input('min-dur', 'value'),
                Input('my-date-picker-range', 'start_date'),
                Input('my-date-picker-range', 'end_date'),
                State('all-flights', 'data'),
                prevent_initial_call=True)
def filter_a_flight(seconds,minutes,start, end, data):
    end = date.fromisoformat(end)
    end_time = datetime(end.year, end.month, end.day, hour=23, minute=59, second=59)
    flights = pd.DataFrame(data)
    flights['tripStart'] = pd.to_datetime(flights['tripStart'], format='mixed')  
    flights['tripEnd'] = pd.to_datetime(flights['tripEnd'], format='mixed')  
    flights['duration'] = flights['duration'].apply(lambda x: pd.to_timedelta(x))
    dates = flights[(flights['tripStart'] >= start) & (flights['tripStart'] <= end_time)]
    dates = dates[(dates['duration'].dt.total_seconds() >= seconds) & (dates['duration'].dt.total_seconds()/60 <= minutes)]
    
    flights_mod = separateFlights(dates)
    
    date_axes = dates[['tagID','date']].value_counts()
    hour_axes = dates[['tagID','hour']].value_counts()
    y_axes = {'hour':max(hour_axes)+1,'date':max(date_axes)+1}
    x_axes = {'hour':dates['hour'].unique(), 'date':dates['date'].unique()} 
    
    bee_div, bee_vect = divideBees(dates)
    
    return dates.to_dict('records'), flights_mod.to_dict('records'), bee_div, bee_vect, y_axes, x_axes

    
    
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
              Input('flights-mod', 'data'),
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
    
    flights = pd.DataFrame(data)
    flights['tripStart'] = pd.to_datetime(flights['tripStart'], format='mixed')
    flights['tripEnd'] = pd.to_datetime(flights['tripEnd'], format='mixed')

    dt = pd.DataFrame(srss)
    
    fig = createActoGraphAll(flights,dt)
    
    return [dcc.Graph(figure=fig, id="chronogram-all-graph",style={'width':'100%','height':'100%'}, config={'responsive': True},clear_on_unhover=True)]
    
    
#function to display hover on chronogram

@app.callback(Output('hover-output', 'children'),
                Input('chronogram-all-graph', 'hoverData'),
                State('flights-mod', 'data'))
def update_on_hover(data, flights):
    if data is None:
        return dbc.Card(dbc.CardBody([html.P(f"Bees:0")]),style={'margin':'auto', 'text-align':'center','width':'30%'})
        
        
    flight = pd.DataFrame(flights)
        
    point = data['points'][0]
    x_val = point.get('x')
    y_val = point.get('y')
    
    
    
    
    flight['tripStart'] = pd.to_datetime(flight['tripStart'], format='mixed') 
    flight['tripEnd'] = pd.to_datetime(flight['tripEnd'], format='mixed') 
    
    flight_sub = flight[(flight['tripStart'] <= x_val) & (flight['tripEnd'] >= x_val) & (flight['date'] == y_val)]
    bees = len(flight_sub)
    
    return dbc.Card(dbc.CardBody([html.P(f"Bees:{bees}")]),style={'margin':'auto', 'text-align':'center','width':'30%'})
     

#synchronize lat/lon

@app.callback(
    Output('lon', 'value'),
    Output('lon2', 'value'),
    Output('lon3', 'value'),
    Input('lon', 'value'),
    Input('lon2', 'value'),
    Input('lon3', 'value'),
    prevent_initial_call=True
)
def sync_lon(lon, lon2, lon3):
    triggered_id = ctx.triggered_id

    if triggered_id == 'lon' and lon != lon2:
        return lon, lon, lon
    elif triggered_id == 'lon2' and lon2 != lon:
        return lon2, lon2, lon2
    elif triggered_id == 'lon3' and lon3 != lon:
        return lon3, lon3, lon3
    raise PreventUpdate
    
    
@app.callback(
    Output('lat', 'value'),
    Output('lat2', 'value'),
    Output('lat3', 'value'),
    Input('lat', 'value'),
    Input('lat2', 'value'),
    Input('lat3', 'value'),
    prevent_initial_call=True
)
def sync_lat(lat, lat2, lat3):
    triggered_id = ctx.triggered_id
    
    if triggered_id == 'lat' and lat != lat2:
        return lat, lat, lat
    elif triggered_id == 'lat2' and lat2 != lat:
        return lat2, lat2, lat2
    elif triggered_id == 'lat3' and lat3 != lat:
        return lat3, lat3, lat3
    raise PreventUpdate


#function to display clusters by user selection
@app.callback(
        Output('cluster-all-1', 'children'),
        Input('cluster-dropdown-1', 'value'),
        Input('flights','data'),
        Input('activity','data'),
        prevent_initial_call=True
)
def cluster_all_1(clusters, data, activity):
    if clusters is None:
        return None
    if data is None:
        return None
    if activity is None:
        return None
        
        
    flight = pd.DataFrame(data)
    allActivity = pd.DataFrame(activity)
    
    flight['tripStart'] = pd.to_datetime(flight['tripStart'], format='mixed') 
    flight['tripEnd'] = pd.to_datetime(flight['tripEnd'], format='mixed') 
    flight['duration'] = flight['tripEnd'] - flight['tripStart']
    flight['theTime'] = flight['tripStart'].apply(lambda x: pd.to_datetime(pd.to_datetime(x).time().strftime('%H:%M:%S')))    
    
    allActivity['start'] = pd.to_datetime(allActivity['start'], format='mixed') 
    allActivity['end'] = pd.to_datetime(allActivity['end'], format='mixed') 
    
    
    fig = plotClusterTimeDur(allActivity,flight,clusters)
    
    return [dcc.Graph(figure=fig, config={'responsive': True}, style={'width':'100%'})]
    

@app.callback(
        Output('cluster-all-2', 'children'),
        Input('cluster-dropdown-2', 'value'),
        Input('flights','data'),
        Input('activity','data'),
        prevent_initial_call=True
)
def cluster_all_1(clusters, data, activity):
    if clusters is None:
        return None
    if data is None:
        return None
    if activity is None:
        return None
        
        
    flight = pd.DataFrame(data)
    allActivity = pd.DataFrame(activity)
    
    flight['tripStart'] = pd.to_datetime(flight['tripStart'], format='mixed') 
    flight['tripEnd'] = pd.to_datetime(flight['tripEnd'], format='mixed') 
    flight['duration'] = flight['tripEnd'] - flight['tripStart']
    flight['theTime'] = flight['tripStart'].apply(lambda x: pd.to_datetime(pd.to_datetime(x).time().strftime('%H:%M:%S')))    
    
    allActivity['start'] = pd.to_datetime(allActivity['start'], format='mixed') 
    allActivity['end'] = pd.to_datetime(allActivity['end'], format='mixed') 
    
    
    fig = plotClusterDayDur(allActivity,flight,clusters)
    
    return [dcc.Graph(figure=fig, config={'responsive': True}, style={'width':'100%'})]
    

@app.callback(
        Output('cluster-single', 'children'),
        Input('cluster-dropdown-single', 'value'),
        Input('dropdown-bee','value'),
        Input('flights','data'),
        Input('activity','data'),
        prevent_initial_call=True
)
def cluster_all_1(clusters, beeID, data, activity):
    if clusters is None:
        raise PreventUpdate
    if data is None:
        raise PreventUpdate
    if activity is None:
        raise PreventUpdate
    if beeID is None:
        raise PreventUpdate
        
        
    flight = pd.DataFrame(data)
    allActivity = pd.DataFrame(activity)
    
    flight['tripStart'] = pd.to_datetime(flight['tripStart'], format='mixed') 
    flight['tripEnd'] = pd.to_datetime(flight['tripEnd'], format='mixed') 
    flight['duration'] = flight['tripEnd'] - flight['tripStart']
    flight['theTime'] = flight['tripStart'].apply(lambda x: pd.to_datetime(pd.to_datetime(x).time().strftime('%H:%M:%S')))    
    
    allActivity['start'] = pd.to_datetime(allActivity['start'], format='mixed') 
    allActivity['end'] = pd.to_datetime(allActivity['end'], format='mixed') 
    
    flight = flight[flight['tagID']==beeID]
    
    fig = plotClusterTimeDur(allActivity,flight,clusters)
    
    return [dcc.Graph(figure=fig, config={'responsive': True}, style={'width':'100%'})]
    



#function to display graphs when bee is selected

@app.callback(
        Output('fig1', 'children'),
        Output('fig2', 'children'),
        Output('fig3', 'children'),
        Output('fig4', 'children'),
        Output('probs1','children'),
        Output('probs2','children'),
        Input('dropdown-bee', 'value'),
        Input('flights', 'data'), 
        Input('x-axes','data'),
        Input('y-axes','data'),
        prevent_initial_call=True
)
def show_individual(bee_id, data, x_axes, y_axes):
    if bee_id is None:
        raise PreventUpdate
    if data is None:
        raise PreventUpdate
        
        
    flights = pd.DataFrame(data)
    flights['tripStart'] = pd.to_datetime(flights['tripStart'], format='mixed')
    flights['tripEnd'] = pd.to_datetime(flights['tripEnd'], format='mixed')
    flights['duration'] = (flights['tripEnd'] - flights['tripStart'])
    flights['duration'] = flights['duration'].apply(lambda x: x.total_seconds()/60).round(2)
        
    bee = flights[flights['tagID'] == bee_id].copy()
    
    
    fig1, fig2, fig3 = plotHist(bee,x_axes,y_axes)
    fig4 = flightDensity(bee)
    
    probs1, probs2 = plotProbs(bee,flights)
    
    return [dcc.Graph(figure = fig1,style={'width': '100%'},config={'responsive': True})], [dcc.Graph(figure = fig2,style={'width': '100%'},config={'responsive': True})], [dcc.Graph(figure = fig3,style={'width': '100%'},config={'responsive': True})], [dcc.Graph(figure = fig4,style={'width': '100%'},config={'responsive': True})], [dcc.Graph(figure = probs1,style={'width': '100%'},config={'responsive': True})], [dcc.Graph(figure = probs2,style={'width': '100%'},config={'responsive': True})]
    


@app.callback([Output('individual-chronogram', 'children')],
              Input('dropdown-bee', 'value'),
              Input('sunrise-sunset', 'data'),
              Input('flights-mod', 'data'),
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
    
    bee = flights[flights['tagID'] == beeid]
    fig = createActoGraph(bee,dt)
    
    
    return [dcc.Graph(figure = fig,style={'width':'100%'},config={'responsive': True})]
    
   
#subselection of graphs   

@app.callback(Output('pagination', 'max_value'),
              Output('pagination', 'active_page'), 
              Output('pagination-data','data'),
              Input('select-quant', 'value'),
              Input('sunrise-sunset', 'data'),
              Input('bee-filter','value'),
              Input('similar-bees','value'),
              State('flights', 'data'),
              State('bee-division','data'),
              State('bee-vectors','data'),
              prevent_initial_call=True)             
def displayChronogramMulti(bees, srss, filter, similar, data, division, vectors):

    #none checks
    if srss is None:
        raise PreventUpdate
    if bees is None:
        raise PreventUpdate
        
    
    flights = pd.DataFrame(data)
    ids = flights['tagID'].unique()
    

    if filter == "Morning Focused":
        bees = min(bees,len(division['morning']))
        ids = division['morning']
    elif filter == "Afternoon Focused":
        bees = min(bees,len(division['afternoon']))
        ids = division['afternoon']
    elif filter == "Even Distribution":
        bees = min(bees,len(division['even']))
        ids = division['even']
    else:
        bees = min(bees, len(ids))
        
        
    if similar is not None:
        similars = findSimilar(vectors,similar)
        ids = list(set(ids).intersection(similars))
        bees = min(bees,len(ids))
                      
            
    counter = math.ceil(bees/perPage)
    lists = itertools.zip_longest(*(iter(ids[:bees]),) * perPage)
    bee_ids = []
    for l in lists:
        index = None
        theList = list(l)
        try:
            index = theList.index(None)
        except ValueError as e:
            pass
    
        if index:
            del theList[index:]
        bee_ids.append(theList)
        
    return counter, 1, bee_ids
    
    
    
@app.callback(
    Output('chrono-sub', 'children'),
    Input('pagination', 'active_page'),
    Input('flights-mod', 'data'),
    State('pagination-data', 'data'),
    State('sunrise-sunset', 'data')
)
def displayChronoPage(page, data, bee_ids, srss):


    if page is None:
        raise PreventUpdate
    if srss is None:
        raise PreventUpdate
        
    dt = pd.DataFrame(srss)
    if len(bee_ids) > 0:
        bees = bee_ids[page - 1] 
    else:
        return html.Div(children=[html.P("No bees fit the specified criteria.",style={'padding-left':'30px','padding-right':'30px','padding-top':'10px'})],style={'display': 'flex','justifyContent': 'center','alignItems': 'center','width': '100%','height':'80vh','backgroundColor':'white'})
    flights = pd.DataFrame(data)
    flights['tripStart'] = pd.to_datetime(flights['tripStart'], format='mixed')
    flights['tripEnd'] = pd.to_datetime(flights['tripEnd'], format='mixed')  

    columns = [[] for i in range(perPage//2)]
    
    for i in range(len(bees)):
        bee = flights[flights['tagID'] == bees[i]]
        graph = createActoGraphSub(bee,dt)
        col = i%(perPage//2)
        columns[i%(perPage//2)].append(dcc.Graph(figure = graph,style={'width':'100%','height':'100%'},config={'responsive': True}))
        
      
    children = []
    for c in columns:
        children.append(html.Div(children=c,style={'display':'flex','flexDirection':'column'},className="display-col"))
    
    return html.Div(children = children,style={'display':'flex', 'margin':'auto', 'border':'1px black solid', 'background-color':'white'},className='multi-chrono')
   
#run app

if __name__ == '__main__':
    app.run(debug=False)
