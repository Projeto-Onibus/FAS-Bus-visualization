import numpy as np
import datetime
import json

from bokeh.models import ColumnDataSource,Range1d
from bokeh.models.annotations import Title, Legend, LegendItem
from bokeh.plotting import figure, save, output_file
from bokeh.embed import json_item
from bokeh.tile_providers import OSM, get_provider
from bokeh.palettes import Category20_20, Inferno256
from bokeh.transform import linear_cmap, factor_cmap
class Colours:
    colourMap = Category20_20
    def __init__(self):
        self.current = 1
    
    @property
    def new(self):
        self.current += 1
        if self.current > len(self.colourMap) + 1:
            raise Exception("No more colours left")
        return self.colourMap[self.current]


def Gradient(start,end,listSize):
    # RGB to decimal
    beginRgb = np.array((int(start[1:3],16),int(start[3:5],16),int(start[5:7],16)))
    endRgb = np.array((int(end[1:3],16),int(end[3:5],16),int(end[5:7],16)))
    
    # Gets modulus, direction and step
    vect = endRgb - beginRgb
    modulusVect = (np.sqrt(np.sum((endRgb-beginRgb)**2)))
    stepUn = (vect/modulusVect)
    
    # Does the shit
    stepSize = (modulusVect/(listSize-1) * stepUn)
    gradient = []
    for i in range(listSize):
        gradient+= [np.round(beginRgb + i * stepSize).astype(int)]
    
    print(vect,modulusVect,stepUn,stepSize)
    # Truncates last part
    for vector in gradient:
        overflow = np.greater(vector,np.array((255,255,255)))
        underflow = np.less(vector,np.array((0,0,0)))
        vector[underflow] = 0
        vector[overflow] = 255

    gradient = ["#"+hex(i[0])[2:]+ "," + hex(i[1])[2:] + "," + hex(i[2])[2:] for i in gradient ]
    return gradient
 

def BasicFormatting(figure,title="Gráfico",x_label=None,y_label=None,grid=True,mapTile=False):
    figure.plot_height=700
    figure.plot_width=1500
    figure.title = Title(text=title,align='center')
    figure.title.text_font_size='18pt'
    if x_label:
        figure.xaxis.axis_label=x_label
        figure.axis.major_label_text_font_size = '12pt'
    if y_label:
        figure.yaxis.axis_label=y_label
        figure.yaxis.major_label_text_font_size = '12pt'
    if grid:
        figure.grid.grid_line_alpha=0.4
        figure.grid.grid_line_color="black"
        figure.grid.minor_grid_line_alpha=0.2
        figure.grid.minor_grid_line_color="black"
    figure.legend.click_policy="hide"
    figure.legend.label_text_font_size='11pt'
    figure.legend.border_line_width = 1
    figure.legend.border_line_color = "black"
    figure.legend.border_line_alpha = 1
    if mapTile:
        figure.add_tile(get_provider(OSM))


def BusAmount(userOptions,database,CONFIGS):
    startDate = datetime.datetime.combine(datetime.date.fromisoformat(userOptions['inicio']),datetime.time(0,0,0))
    endDate = datetime.datetime.combine(datetime.date.fromisoformat(userOptions['fim']),datetime.time(0,0,0))
    endDate += datetime.timedelta(days=1)
    with database.cursor() as cursor:
        cursor.execute("""SELECT 
                            DATE(time_detection) as dia, COUNT(DISTINCT(bus_id)) 
                        FROM bus_data 
                        WHERE time_detection BETWEEN %s AND %s
                        GROUP BY dia ORDER BY dia;
                """, (startDate,endDate))
        totalResults = cursor.fetchall()
    
    data = {
       'x': [datetime.datetime.combine(i[0],datetime.time(0)) for i in totalResults],
       'total':[i[1] for i in totalResults]
    }

    with database.cursor() as cursor:
       cursor.execute(f""" SELECT DATE(tempo) as dia, MAX(quantidade) FROM 
                           (SELECT 
                               (TIMESTAMP WITHOUT TIME ZONE 'epoch' + INTERVAL '1 second' * floor(extract('epoch' from time_detection)/600)*600) as tempo,
                               COUNT(DISTINCT(bus_id)) AS quantidade
                           FROM bus_data 
                           WHERE 
                               time_detection BETWEEN %s AND %s 
                           GROUP BY tempo) as tab
                           GROUP BY dia ORDER BY dia
                       """,(startDate,endDate)
       )
       peakResults = cursor.fetchall()
    
    data['difference'] = [data['total'][i] - peakResults[i][1] for i in range(len(peakResults))]

    source = ColumnDataSource(data)

    dataMin = np.floor(min(data['total']) - max(data['difference'])/1000)*1000
    dataMax = np.floor(max(data['total'])/1000)*1000
    fig = figure(x_axis_type="datetime",y_range=(4000,6000))
   
    # # Set x range to be at least a month
    # timeDelay = max(data['x']) - min(data['x'])
    # if timeDelay < datetime.timedelta(weeks=4,days=2):
    #     fig.x_range = Range1d((min(data['x']) - timeDelay/2), (max(data['x']) + timeDelay/2))

    total,difference = fig.vbar_stack(['total','difference'],x='x',width=datetime.timedelta(hours=20),source=source,color=['blue','orange'],legend_label=['pico','total-pico'])
    
    BasicFormatting(fig,"Quantitade de ônibus no sistema",x_label="Dia",y_label="Quantidade")

    return "",json_item(fig)
    

def linePerformanceDay(userOptions,database,CONFIGS):
    #
    #  Preparing
    # 

    desiredDate = datetime.datetime.combine(datetime.date.fromisoformat(userOptions['dia']),datetime.time(0,0,0))
    nextDate = desiredDate + datetime.timedelta(days=1)
    selectedLines = [i for i in userOptions['linha'].split(",") if len(i) > 0] 
    detectedLine = True if str(userOptions['detectada']) == "True" else False
    lineQuota = int(userOptions['cota'])
    #
    # Database acquisition
    #
    

    fig = figure(
        x_axis_type="datetime"
    )

    graphData = []
    for detectedLine in [True,False]:
        for line in selectedLines:
            with database.cursor() as cursor:
                cursor.execute(f"""SELECT 
                    (TIMESTAMP WITHOUT TIME ZONE 'epoch' + INTERVAL '1 second' * floor(extract('epoch' from time_detection)/600)*600) as tempo,
                    COUNT(DISTINCT(bus_id)) AS quantidade
                FROM bus_data 
                WHERE 
                    time_detection BETWEEN %s AND %s AND 
                    {"line_key_detected" if detectedLine else "line_key_reported"}=%s 
                GROUP BY tempo""",(desiredDate,nextDate,line))
                queryResults = cursor.fetchall()            
                graphData += [{
                    "x":[i[0] for i in queryResults],
                    'y':[i[1] for i in queryResults],
                    'label': line + (" - detectada" if detectedLine else " - reportada")
                }]
    #
    # Graph formation
    # 


    # creates new colour pallete
    colour = Colours()
    a = colour.new
    
    for lineData in graphData: 
        fig.line(
            line_color=colour.new,
            x=lineData['x'],y=lineData['y'],
            legend_label=lineData['label'],
            line_width=3)

    # Add quota user-defined   
    fig.line(
        line_color="red",
        x=graphData[0]['x'],y=[lineQuota for i in range(len(graphData[0]['x']))],
        legend_label="Meta de quantidade",
        line_dash="dashed",
        line_width=4
    )

    BasicFormatting(fig,title=f"Quantidade de ônibus na linha {selectedLines[0]}",y_label="Quantidade",x_label="Tempo (h)")
    
    return "",json_item(fig)
# ---------------------------------------------------------------------------------------------------------------------------------------------------
# 
#  
# 
# 
# 
# 
# 
# ----------------------------------------------------------------------------------------------------------------------------------------------------

def MapTrajectory(userOptions,database,CONFIGS):
    
    # ---------------------------------------------
    # PREPARATION
    # ---------------------------------------------

    # declaring and pre processing of user input variables
    desiredDate = userOptions["dia"]
    busGradientType = userOptions['gradienteOnibus']
    linesList = userOptions['linha'].split(',')
    busList = userOptions['onibus'].split(',')
    directionSelection = userOptions['direcaoLinha']
    desiredDate = datetime.datetime.combine(datetime.date.fromisoformat(desiredDate),datetime.time(0,0,0))
    nextDay = desiredDate + datetime.timedelta(days=1)
    
    # Removes last element of linesList and busList if their last element is null
    for givenLists in [linesList,busList]:
        if len(givenLists[-1]) == 0:
            givenLists.pop()
    
    # Raises error if no lines nor buses were given
    if len(linesList) == 0 and len(busList) == 0:
        raise InvalidUserInput("There must be at least one line or one bus selected")


    # Expanding line list to fit line selection if line was requested
    if directionSelection == 'nenhum' and len(linesList)>0:
        raise InvalidUserInput("If no direction is selected, the line list must be zero length")
    elif directionSelection == "0":
        lineDirectionList = [(i,"0") for i in linesList]
    elif directionSelection == "1":
        lineDirectionList = [(i,"1") for i in linesList]
    elif directionSelection == "ambas":
        lineDirectionList = [(i,"0") for i in linesList]
        lineDirectionList += [(i,"1") for i in linesList]
    else:
        raise InvalidUserInput("The direction input is not valid")

    # -----------------------------------------------------------
    # DATABASE QUERIES
    # -----------------------------------------------------------

    data= dict()
    data['line'] = dict()

    # Queries values for lines and list in database
    for line,direction in lineDirectionList:
        # Create line if not created yet
        if not line in data['line'].keys():
            data['line'][line] = dict()
        
        if not direction in data['line'][line].keys():
            data['line'][line][direction] = dict()

        # Queries line position and adds to data collected
        with database.cursor() as cursor:
            cursor.execute("SELECT latitude,longitude FROM line_data_simple WHERE line_id=%s AND direction=%s ORDER BY position ASC",(line,direction))
            queryResult = cursor.fetchall()

        if len(queryResult) == 0:
            raise Exception("No line match at database")

        #print(queryResult)
        # Sort and save data
        data['line'][line][direction]['lat'] = [i[0] for i in queryResult]
        data['line'][line][direction]['lon'] = [i[1] for i in queryResult]

    del queryResult
    
    # Queries values for buses in database
    data['bus'] = dict()
    for busId in busList:
        # Query data in database
        with database.cursor() as cursor:
            cursor.execute("""SELECT time_detection,latitude,longitude,line_key_reported,line_key_detected 
                FROM bus_data WHERE time_detection BETWEEN %(atual)s AND %(seguinte)s AND bus_id=%(busId)s""",
                {"atual":desiredDate,"seguinte":nextDay,"busId":busId})        
            queryResult = cursor.fetchall()
        
        # Sort and save data
        data['bus'][busId] =dict()
        data['bus'][busId]["time"] = [(i[0]).isoformat() for i in queryResult]
        data['bus'][busId]['lat'] = [i[1] for i in queryResult]
        data['bus'][busId]['lon'] = [i[2] for i in queryResult]
        data['bus'][busId]['line_reported'] = [i[3] for i in queryResult]
        data['bus'][busId]['line_detected'] = [i[4] for i in queryResult]

    # ----------------------------------------------------------------------------------------------------------
    # DATA CONVERSION
    # ------------------------------------------------------------------------------------------------------------

    # Translate data to web_mercator
    for lineName,lineData in data['line'].items():
        for lineDirection in lineData.keys():
            #print(lineTrajectory)
            lineData[lineDirection]['lon'],lineData[lineDirection]['lat'] = geographic_to_web_mercator(lineData[lineDirection]['lat'],lineData[lineDirection]['lon'])
            #print(lineTrajectory)

    for busName, busValues in data['bus'].items():
        #print(busValues['trajectory'])
        busValues['lon'],busValues['lat'] = geographic_to_web_mercator(busValues['lat'],busValues['lon'])
        #print(busValues['trajectory'])
    
    # -------------------------------------------------------------------------------------------------------------
    # PLOTTING
    # -------------------------------------------------------------------------------------------------------------

    hoverMenu = [
            ("indice", "$index"),
            ("(lat,lon)", "($x, $y)"),
            ("detectado", "@time"),
            ("linha reportada","@line_reported"),
            ("linha detectada","@line_detected")
        ]

    # Starting figure creation
    fig = figure(
        #x_range=(-4864661.74766606, -4809002.00226942), # Fits Rio de Janeiro in the map display
        #y_range=(-2668339.10575019, -2595778.80430713),
        x_axis_type="mercator", # Defines axis as 'mercator' so values can be displayed as lat/lon
        y_axis_type="mercator",
        tooltips=hoverMenu)
    
    
    # Adds OSM background
    #fig.add_tile(get_provider(OSM))

    # creates new colour pallete
    colour = Colours()

    # Plot data per selection in lines
    for lineName,lineData in data['line'].items():
        for lineDirection in lineData.keys():
            dataSource = ColumnDataSource(lineData[lineDirection])
            #print(lineTrajectory)
            fig.circle(
                x='lon', # Coordinates
                y='lat',
                source=dataSource,
                size=9, # size in screen (not affected by zoom in/out)
                fill_color=colour.new, # Colour inside
                legend_label=f"{lineName} - {lineDirection}")
            

    for busName, busValues in data['bus'].items():
        dataSource = ColumnDataSource(busValues)

        #mapper = linear_cmap('time',Inferno256,min(busValues['time']),max(busValues['time']))
        mapper = "navy"
        fig.circle(
            x='lon',
            y='lat',
            source=dataSource,
            size=4,
            fill_color=mapper,
            legend_label=f"{busName}")
    BasicFormatting(fig,title='Trajetórias',grid=False,mapTile=True)
    return json_item(fig)


def LineDay():
    pass

def LinePeriod():
    pass

def geographic_to_web_mercator(lat,lon):
    y_lat,x_lon = (np.array(lat),np.array(lon))
    x = 6378137.0 * x_lon * 0.017453292519943295
    a = y_lat * 0.017453292519943295
    x_mercator = x 
    y_mercator = 3189068.5 * np.log((1.0 + np.sin(a)) / (1.0 - np.sin(a)))
    lat,lon = (x_mercator.tolist(),y_mercator.tolist())
    return (x_mercator,y_mercator)


def main():
    import sys
    sys.path.append("/home/fdias/Documents/Repositories/GatheringInfo")
    import psycopg2
    from GatheringInfo.data_handling.DatabaseInteraction import DatabaseHandler
    from GatheringInfo.main.ConfigurationScript import createConfig
    CONFIGS = createConfig()
    CONFIGS.read("DatabaseConfigs.ini")
    options = {"linha":"371","onibus":"A27532","direcaoLinha":"ambas","dia":"2019-05-03","gradienteOnibus":"nenhum"}
    database = psycopg2.connect(**CONFIGS['database'])
    results = MapTrajectory(options,database,CONFIGS)
    output_file("www/data/MapTrajectory.html")
    save(results)



if __name__ == "__main__":
    main()
    #print(geographic_to_web_mercator(vals))
    #print(np.split(vals,2,axis=1)[0].T[0])
#
# Errors and exceptions
# 
# 
class InvalidUserInput(Exception):
    def __init__(self,message):
        self.message = message