#imports

from dash import Dash, dash_table, dcc, html, Input, Output, callback, State, clientside_callback
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

from flights import classifyLoc, cleanData, summaryData, makeTotalSum, divideBees, findSimilar
from graphing import getSRSS, separateFlights, addShapes, createActoGraphAll, flightDensity, flightLength, createActoGraph, plotHist, plotClusterTimeDur, plotClusterDayDur, linReg, fixDate, beeAverage, createActoGraphSub, plotProbs


#app creation


external_stylesheets = [dbc.themes.BOOTSTRAP,'https://codepen.io/chriddyp/pen/bWLwgP.css']
#app = Dash(__name__,requests_pathname_prefix='/beeapp/', routes_pathname_prefix='/beeapp/',external_stylesheets=external_stylesheets,suppress_callback_exceptions=True,)
app = Dash(__name__, external_stylesheets=external_stylesheets,suppress_callback_exceptions=True)
app.title = "BeehAIve"
server = app.server

#constants

tzf = TimezoneFinder() 

#layout

app.layout = html.Div([

         html.Div([
        
         html.Div([
         
                                html.Div([
                                    html.H1("BeehAIve",style={'font-family':'Bahnschrift','textAlign': 'center','padding':'2vh', 'backgroundColor':'rgba(255, 255, 255,0.5)'}),
                                ], style={'backgroundImage': 'url("assets/hex.jpg")','backgroundRepeat':'repeat','width':'100%','height':'10vh','backgroundSize': 'auto','border':'1px black solid','-webkit-text-stroke': '1px white'}),
         
             html.Div([
                                html.Div([
                                
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
                                                        html.Li("Date Range: Select an initial and final date to narrow down the data displayed to a desired date range."),
                                                        html.Li("Accessing the Chronogram: Enter latitude and longitude of your desired location in Chronogram to display chronogram with sunrise/sunset display.")

                                                    ],style={'list-style-type':'square','font-size':'12px'}),
                                                    
                                                    
                                html.P("Visualization Instructions",style={'fontWeight':'bold'}),
                                
                                html.Ul(children=[
                                                        html.Li("Hover over the objects in the visualization to display details."),
                                                        html.Li("Drag and drop on visualization to zoom in desired region."),
                                                        html.Li("Click home icon to reset zoom to default."),
                                                        html.Li("Click camera icon to save a static version of the visualization to computer."),


                                                    ],style={'list-style-type':'square', 'font-size':'12px'}),

                                html.P("Upload a csv file to begin visualizing."),

                                
                                ], style={'padding-top':'10px','padding-right':'30px'},className="landing-text"),                      
                                
                                html.Img(src="https://cdn.pixabay.com/photo/2021/03/27/05/13/bee-6127510_1280.jpg",style={'border-radius': '10px','padding':'1%','margin':'auto'},className="logo-image"),
                                
                                                                 
             ], style={'display': 'flex'},className="landing"),
        ], id='landing-page', style={'width':'100%', 'padding-right':'10px', 'height':'100%'}),
            

        html.Div(children=[
        
        html.Div(id='how-to-use'),
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
            ],style={'display':'flex','flexDirection':'row','align-items': 'center','justify-content': 'center', 'background-color':'white'}),
            
            html.Hr(),
        
            dcc.Loading(
                id="loading-main",
                type="circle",
                children=html.Div(id="output-data"),
                style={"margin-top":"20px"},
                target_components ={"output-data": "children"}
            ),
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
            
            
            html.Div(id="app-body"), 
            
            
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
            
       ])
            


    
    else:
        return "The file needs to be a csv."
        
        
        
@app.callback(Output('app-body','children'),
                Input('flights','data'),
                Input('activity','data'),
                Input('all-flights','data'),
                Input('y-axes','data'),
                prevent_initial_call=True)
def display_app(flights, activity, all_flights, y_axes):

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
        
    #cluster1, cluster2 = plotCluster(allActivity, flight)
    #unique bees for dropdown 
    selectBee = pd.unique(flight['tagID'])
    
    beeSummary = beeSummary.astype(str)
    
    #print(type(beeSummary['tagID'].iloc[0]))
    
    #Average of all bees
    
    fig1_, fig2_, fig3_ = beeAverage(flight, y_axes)
    
    probs1, probs2 = plotProbs(flight,flight)
    
    beeLen = len(flight['tagID'].unique())
    
    #fig4_ = flightDensity(flight_sub)
    

    return html.Div([
                dcc.Tabs([
                    dcc.Tab(label='Individual Bee Data', children=[
                    
                        html.Div([
                            
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
                            
                            ]),style={'width':'100%'}),
                            
                            dbc.Card(
                            dbc.CardBody([
                            html.P("Average of all bees in dataset."),
                            
                            ]),style={'width':'100%','alignItems':'center','justifyContent':'center'}),
                            ],style={'display':'flex','width':'100%','backgroundImage': 'url("assets/hex.jpg")','backgroundRepeat':'repeat'},className="bee-selection"),
                            
                            dcc.Tabs(
                                vertical=True,
                                children=[
                                     dcc.Tab(className="custom-tab", selected_className="selected",label='Flights at Time of Day', children=[
                                     
                                     
                                     html.Div([
                                     
                                         html.Div(id='fig1',children=[
                                         
                                         
                                         html.P("Select a bee to begin visualizing.",style={'padding-top':'10px'})
                                         
                                         ],style={'width': '100%','height':'80vh','backgroundColor':'white','display': 'flex','width': '100%','justifyContent': 'center','alignItems': 'center'}),
                                         
                                         dcc.Graph(figure = fig1_,config={'responsive': True},style={'width': '100%','height':'80vh'}),
                                         
                                     ],style={'display':'flex'},className="double-display")
                                     
                                     ],style={'backgroundColor':'#feffe3'}, selected_style={'font-weight':'bold','backgroundColor': '#301808', 'color': 'white'}),
                                     dcc.Tab(className="custom-tab", selected_className="selected",label='Flights per Day', children=[
                                     
                                     
                                     html.Div([
                                     
                                         html.Div(id='fig2',children=[
                                         
                                         
                                         html.P("Select a bee to begin visualizing.",style={'padding-top':'10px'})
                                         
                                         ],style={'width': '100%','height':'80vh','backgroundColor':'white','display': 'flex','width': '100%','justifyContent': 'center','alignItems': 'center'}),
                                         
                                         dcc.Graph(figure = fig2_,config={'responsive': True},style={'width': '100%','height':'80vh'}),
                                         
                                     ],style={'display':'flex'},className="double-display")
                                     
                                     
                                     
                                     
                                     ],style={'backgroundColor':'#feffe3'}, selected_style={'font-weight':'bold','backgroundColor': '#301808', 'color': 'white'}),
                                     dcc.Tab(className="custom-tab", selected_className="selected",label='Flight Duration per Day', children=[
                                     
                                     html.Div([
                                     
                                         html.Div(id='fig3',children=[
                                         
                                         
                                         html.P("Select a bee to begin visualizing.",style={'padding-top':'10px'})
                                         
                                         ],style={'width': '100%','height':'80vh','backgroundColor':'white','display': 'flex','width': '100%','justifyContent': 'center','alignItems': 'center'}),
                                         html.Div(id='fig3_',children=[
                                         
                                         dcc.Graph(figure = fig3_,config={'responsive': True},style={'width': '100%','height':'80vh'}),
                                         
                                         ],style={'backgroundColor':'#feffe3','width': '100%','height':'80vh','display': 'flex','width': '100%','justifyContent': 'center','alignItems': 'center'})
                                         
                                     ],style={'display':'flex'},className="double-display")
                                     
                                     
                                     
                                     ],style={'backgroundColor':'#feffe3'}, selected_style={'font-weight':'bold','backgroundColor': '#301808', 'color': 'white'}),
                                     dcc.Tab(className="custom-tab", selected_className="selected",label='Flights at Time of Day Distribution', children=[
                                     
                                     
                                     html.Div([
                                     
                                         html.Div(id='probs1',children=[
                                         
                                         
                                         html.P("Select a bee to begin visualizing.",style={'padding-top':'10px'})
                                         
                                         ],style={'width': '100%','height':'80vh','backgroundColor':'white','display': 'flex','width': '100%','justifyContent': 'center','alignItems': 'center'}),
                                         
                                         dcc.Graph(figure = probs1,config={'responsive': True},style={'width': '100%','height':'80vh'}),
                                         
                                     ],style={'display':'flex'},className="double-display")
                                     
                                     ],style={'backgroundColor':'#feffe3'}, selected_style={'font-weight':'bold','backgroundColor': '#301808', 'color': 'white'}),
                                     
                                     dcc.Tab(className="custom-tab", selected_className="selected",label='Flights at Each Day Distribution', children=[
                                     
                                     
                                     html.Div([
                                     
                                         html.Div(id='probs2',children=[
                                         
                                         
                                         html.P("Select a bee to begin visualizing.",style={'padding-top':'10px'})
                                         
                                         ],style={'width': '100%','height':'80vh','backgroundColor':'white','display': 'flex','width': '100%','justifyContent': 'center','alignItems': 'center'}),
                                         
                                         dcc.Graph(figure = probs2,config={'responsive': True},style={'width': '100%','height':'80vh'}),
                                         
                                     ],style={'display':'flex'},className="double-display")
                                     
                                     ],style={'backgroundColor':'#feffe3'}, selected_style={'font-weight':'bold','backgroundColor': '#301808', 'color': 'white'}),
                                     dcc.Tab(className="custom-tab", selected_className="selected",label='Flights at Time and Date', children=[
                                     
                                     
                                     html.Div([
                                     
                                         html.Div(id='fig4',children=[
                                         
                                         
                                         html.P("Select a bee to begin visualizing.",style={'padding-top':'10px'})
                                         
                                         ],style={'width': '100%','height':'80vh','backgroundColor':'white','display': 'flex','width': '100%','justifyContent': 'center','alignItems': 'center'}),
                                         html.Div(id='fig4_',children=[
                                         
                                         
                                         
                                         ],style={'backgroundColor':'#feffe3','width': '100%','height':'80vh','display': 'flex','width': '100%','justifyContent': 'center','alignItems': 'center'})
                                         
                                     ],style={'display':'flex'},className="double-display")
                                     
                                     
                                     
                                     ],style={'backgroundColor':'#feffe3'}, selected_style={'font-weight':'bold','backgroundColor': '#301808', 'color': 'white'}),
                                     
                                     dcc.Tab(className="custom-tab", selected_className="selected",label='Clustering for Time of Day and Flight Duration', children=[
                                     
                                     
                                        dbc.Card(
                                        dbc.CardBody([
                                        
                                         dcc.Dropdown(
                                         options=[2,3,4],
                                         placeholder="Select cluster number",
                                         id="cluster-dropdown-single",
                                         multi=False),
                                         html.Div(id='cluster-single',children=[html.P("Select cluster number to display graph.")])
                                        #dcc.Graph(figure=cluster2, config={'responsive': True}, style={'width':'100%'})
                                        
                                        ]),style={'height':'100%','margin-top':'5vh','margin-left':'5%'},className="cards"),
                                     
                                     ],style={'backgroundColor':'#feffe3'}, selected_style={'font-weight':'bold','backgroundColor': '#301808', 'color': 'white'}),
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
                                            html.Div(id='individual-chronogram',children=[html.P("Input coordinates to display chronogram.",style={'padding-left':'30px','padding-right':'30px','padding-top':'10px'})],style={'display': 'flex','justifyContent': 'center','alignItems': 'center','width': '100%','height':'80vh','backgroundColor':'white'}),
                                   
                                     ],style={'display':'flex','height': '80vh','flexDirection':'column'}),
                                    ],className="chrono")
                                    ],style={'backgroundColor':'#feffe3'}, selected_style={'font-weight':'bold','backgroundColor': '#301808', 'color': 'white'}), 

                                     
                                ],className="vertical-tabs")                        
                            ],style={'display': 'flex','flexDirection': 'column','backgroundImage': 'url("assets/hex.jpg")','backgroundRepeat':'repeat'},className="background-image"),										
                        ],style={'font-size':'24px','backgroundColor':'#feffe3'}, selected_style={'font-size':'24px','font-weight':'bold','backgroundColor': '#301808', 'color': 'white'}),
                        
                        
                    dcc.Tab(label="Hive Data", children=[
                    
                        html.Div([
                        
                        dcc.Tabs(vertical=True, children=[
                        
                        
                                dcc.Tab(className="custom-tab", selected_className="selected",label="Summary Table", children=[
                                
                                
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
                                ]),style={'padding-top':'5vh'},className="cards")        
                                ],style={'backgroundColor':'#feffe3'}, selected_style={'font-weight':'bold','backgroundColor': '#301808', 'color': 'white'}),
                                    
                                dcc.Tab(className="custom-tab", selected_className="selected",label="General Summary",children=[
                                    
                                html.Div([
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
                                        style_table={'overflowX': 'auto','padding-left': '15px','padding-right':'10px'},
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
                                        style_table={'overflowX': 'auto','padding-left': '15px', 'padding-right':'10px', 'padding-top':'15px'},
                                        )
                                        
                                        ])),
                                        
                                        
                                        ], id="tables",style={'display': 'flex','flexDirection':'column'},className="cards"),
                                    
                                    
                                    ],style={'height':'80vh'})
                                    
                                    ],style={'backgroundColor':'#feffe3'}, selected_style={'font-weight':'bold','backgroundColor': '#301808', 'color': 'white'}),
                                    
                                    dcc.Tab(className="custom-tab", selected_className="selected",label="Flights at Time of Day",children=[
                                    
                                        dbc.Card(
                                        dbc.CardBody([
                                         dcc.Graph(figure = density,config={'responsive': True},style={'width': '100%'}),
                                         
                                        ]),style={'height':'100%','margin-top':'5vh','margin-left':'5%'},className="cards")
                                         
                                    ],style={'backgroundColor':'#feffe3'}, selected_style={'font-weight':'bold','backgroundColor': '#301808', 'color': 'white'}),
                                    dcc.Tab(className="custom-tab", selected_className="selected",label="Duration of Flights at Time of Day",children=[
                                    
                                        dbc.Card(
                                        dbc.CardBody([
                                        dcc.Graph(figure = length,config={'responsive': True},style={'width': '100%'})
                                        ]),style={'height':'100%','margin-top':'5vh','margin-left':'5%'},className="cards"),
                                    ],style={'backgroundColor':'#feffe3'}, selected_style={'font-weight':'bold','backgroundColor': '#301808', 'color': 'white'}),
                                    dcc.Tab(className="custom-tab", selected_className="selected",label="Clustering for Time of Day and Flight Duration",children=[
                                        dbc.Card(
                                        dbc.CardBody([
                                        
                                         dcc.Dropdown(
                                         options=[2,3,4],
                                         placeholder="Select cluster number",
                                         id="cluster-dropdown-1",
                                         multi=False),
                                         html.Div(id='cluster-all-1',children=[html.P("Select cluster number to display graph.")])
                                        #dcc.Graph(figure=cluster1, config={'responsive': True}, style={'width':'100%'})
                                        
                                        ]),style={'height':'100%','margin-top':'5vh','margin-left':'5%'},className="cards"),
                                    ],style={'backgroundColor':'#feffe3'}, selected_style={'font-weight':'bold','backgroundColor': '#301808', 'color': 'white'}),
                                    dcc.Tab(className="custom-tab", selected_className="selected",label="Clustering for Flight Duration and Age",children=[
                                        dbc.Card(
                                        dbc.CardBody([
                                        
                                         dcc.Dropdown(
                                         options=[2,3,4],
                                         placeholder="Select cluster number",
                                         id="cluster-dropdown-2",
                                         multi=False),
                                         html.Div(id='cluster-all-2',children=[html.P("Select cluster number to display graph.")])
                                        #dcc.Graph(figure=cluster2, config={'responsive': True}, style={'width':'100%'})
                                        
                                        ]),style={'height':'100%','margin-top':'5vh','margin-left':'5%'},className="cards"),
                                    ],style={'backgroundColor':'#feffe3'}, selected_style={'font-weight':'bold','backgroundColor': '#301808', 'color': 'white'}),
                                    dcc.Tab(className="custom-tab", selected_className="selected",label="Relationship Between Time Passed and Flight Duration",children=[
                                    
                                    dbc.Card(
                                    dbc.CardBody([
                                    html.Div([
                                            dcc.Graph(figure = beeMin,style={'height':'70vh'},className="double-graph"),
                                            dcc.Graph(figure = beeMinTime,style={'height':'70vh'},className="double-graph"),
                                            
                                            
                                    ], style={'display': 'flex','width': '100%'},className="double-display"),
                                    
                                    ]),style={'height':'100%','margin-top':'5vh','margin-left':'5%'},className="cards"),
                                    
                                    ],style={'backgroundColor':'#feffe3'}, selected_style={'font-weight':'bold','backgroundColor': '#301808', 'color': 'white'}),
                                    dcc.Tab(className="custom-tab", selected_className="selected",label="Relationship Between Time Passed and Average Number of Flights", children=[
                                    
                                    
                                    dbc.Card(
                                    dbc.CardBody([
                                    html.Div([
                                            dcc.Graph(figure = beeSum,style={'height':'70vh'},className="double-graph"),
                                            dcc.Graph(figure = beeSumTime,style={'height':'70vh'},className="double-graph")
                                            
                                    ],style={'display': 'flex','width':'100%'},className="double-display")
                                    
                                    ]),style={'height':'100%','margin-top':'5vh','margin-left':'5%'},className="cards"),
                                    
                                    ],style={'backgroundColor':'#feffe3'}, selected_style={'font-weight':'bold','backgroundColor': '#301808', 'color': 'white'}),
                                    
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
                                            html.Div(id='chronogram-all',children=[html.P("Input coordinates to display chronogram.",style={'padding-left':'30px','padding-right':'30px','padding-top':'10px'})],style={'display': 'flex','justifyContent': 'center','alignItems': 'center','width': '100%','height':'80vh','backgroundColor':'white'}),
                                     
                                            html.Div(id="hover-output"),
                                     ],style={'display':'flex','height': '80vh','flexDirection':'column'}),
                                    ],className="chrono")
                                    ],style={'backgroundColor':'#feffe3'}, selected_style={'font-weight':'bold','backgroundColor': '#301808', 'color': 'white'}),       
                                                                       
                                    ],className="vertical-tabs"),
                                    
                                    ],style={'backgroundImage': 'url("assets/hex.jpg")','backgroundRepeat':'repeat'},className="background-image")
                                    
                               ],style={'font-size':'24px','backgroundColor':'#feffe3'}, selected_style={'font-size':'24px','font-weight':'bold','backgroundColor': '#301808', 'color': 'white'}),
                    
                    dcc.Tab(label="Subset Bees", children=[
                        
                        html.Div([
                            html.Div([
                                html.Div([
                                
                                
                                html.P("Select number of bees to observe.",style={}),
                                dcc.Input(id='select-quant', type='number', min=1, max=beeLen)
                                
                                ],style={'width':'100%','alignItems':'center','justifyContent':'center','backgroundColor': '#301808', 'color': 'white','padding-left':'5px'}),
                                
                                html.Div([
                                
                                
                                html.P("Select filter for bees.",style={'color': 'white'}),
                                dcc.Dropdown(['All', 'Morning Focused', 'Afternoon Focused', 'Even Distribution'], 'All', id='bee-filter'),
                                
                                ],style={'width':'100%','alignItems':'center','justifyContent':'center','backgroundColor': '#301808','padding-left':'5px'}),
                                
                                
                                html.Div([
                                
                                html.P("Select a bee to find similar bees.",style={'color': 'white'}),
                                dcc.Dropdown(options=selectBee,searchable=True, id='similar-bees'),
                                
                                ],style={'width':'100%','alignItems':'center','justifyContent':'center','backgroundColor': '#301808','padding-left':'5px'}),
                            ],style={'display':'flex'}, className="dropdown-row"),
                            
                            dcc.Tabs(vertical=True,id='chrono-sub',className="vertical-tabs vertical-scroll")
                        
                        ],style={'backgroundImage': 'url("assets/hex.jpg")','backgroundRepeat':'repeat'},className="background-image")
                    
                    ],style={'font-size':'24px','backgroundColor':'#feffe3'}, selected_style={'font-size':'24px','font-weight':'bold','backgroundColor': '#301808', 'color': 'white'}),
                    
                    ], style={'width':'100%'})
                        
                    ],style={})

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


@app.callback(Output('logo-title', 'children'),
               Input('activity','data'),
               prevent_initial_call=True)
def select_date(data):
    if data is None:
        return None
    
    
    return html.Div([
           html.H1("BeehAIve",style={'font-family':'Bahnschrift','textAlign': 'center','padding':'10vh', 'backgroundColor':'rgba(255, 255, 255,0.5)'}),
    ], style={'backgroundImage': 'url("assets/hex.jpg")','backgroundRepeat':'repeat','width':'100%','height':'30vh','backgroundSize': 'auto','border':'1px black solid','-webkit-text-stroke': '1px white'})





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
                                            html.Li("Date Range: Select an initial and final date to narrow down the data displayed to a desired date range."),
                                            html.Li("Accessing the Chronogram: Enter latitude and longitude of your desired location in Chronogram to display chronogram with sunrise/sunset display.")

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
                        dbc.Button("Close", id="close", className="ms-auto", n_clicks=0)
                    ),
            ],
            id="modal",
            is_open=False,
            )
        ], id="instructions-modal", style={'padding-top':'5px'}),

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
              State('flights-mod', 'data'),
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

#lat
@app.callback(
    Output('lat','value'),
    Input('lat2','value'),
    State('lat','value'),
    prevent_initial_call=True)
def updateLat1(value,value2):
    if value != value2:    
        return value
    raise PreventUpdate



@app.callback(
    Output('lat2','value'),
    Input('lat','value'),
    State('lat2','value'),
    prevent_initial_call=True)
def updateLat2(value,value2):
    if value != value2:    
        return value
    raise PreventUpdate
    
#lon


@app.callback(
    Output('lon','value'),
    Input('lon2','value'),
    State('lon', 'value'),
    prevent_initial_call=True)
def updateLon1(value, value2):
    if value != value2:    
        return value
    raise PreventUpdate



@app.callback(
    Output('lon2','value'),
    Input('lon','value'),
    State('lon2','value'),
    prevent_initial_call=True)
def updateLon2(value, value2):
    if value != value2:    
        return value
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
        return None
    if data is None:
        return None
        
        
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
              State('flights-mod', 'data'),
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

@app.callback([Output('chrono-sub', 'children')],
              Input('select-quant', 'value'),
              Input('sunrise-sunset', 'data'),
              Input('bee-filter','value'),
              Input('similar-bees','value'),
              State('flights-mod', 'data'),
              State('activity', 'data'),
              State('bee-division','data'),
              State('bee-vectors','data'),
              prevent_initial_call=True)             
def displayChronogramMulti(bees, srss, filter, similar, data, activity, division, vectors):

    #none checks
    if data is None:
        raise PreventUpdate
    if activity is None:
        raise PreventUpdate
    if srss is None:
        raise PreventUpdate
    if bees is None:
        raise PreventUpdate
        
    flights = pd.DataFrame(data)
    
    ids = flights['tagID'].unique()
    
    dt = pd.DataFrame(srss)
    
    flights['tripStart'] = pd.to_datetime(flights['tripStart'], format='mixed')
    flights['tripEnd'] = pd.to_datetime(flights['tripEnd'], format='mixed')

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
        bees = bees
        
        
    if similar is not None:
        similars = findSimilar(vectors,similar)
        ids = list(set(ids).intersection(similars))
        bees = min(bees,len(ids))
            
            
            
            
    tabs = []
    counter = 1
    for i in range(0,bees,4):
    
            columns = [[],[]]
            
            if counter * 4 <= bees:
                limit = 4
            else:
                limit = bees % 4
            for j in range(limit):
                bee = ids[i+j]
                bee = flights[flights['tagID']==bee]
                graph = createActoGraphSub(bee,dt)
                if j%2 == 0:
                    columns[0].append(dcc.Graph(figure = graph,style={'width':'100%','height':'100%'},config={'responsive': True}))
                else:
                    columns[1].append(dcc.Graph(figure = graph,style={'width':'100%','height':'100%'},config={'responsive': True}))
            
            counter += 1
            
           
           
            tabs.append(dcc.Tab(className="custom-tab", selected_className="selected",label=f"Bees {i} to {i+limit-1}", children=[
            
                html.Div([
                   
                   html.Div(children=columns[0],style={'display':'flex','flexDirection':'column'},className="display-col"),
                   
                   html.Div(children=columns[1],style={'display':'flex','flexDirection':'column'},className="display-col")
                
                
                ],style={'display':'flex'},className='double-display')
            
            
            ],style={'backgroundColor':'#feffe3'}, selected_style={'font-weight':'bold','backgroundColor': '#301808', 'color': 'white'}))
            
    
    
    return [tabs]
    
    
#run app

if __name__ == '__main__':
    app.run(debug=True)
