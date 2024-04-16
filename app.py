import os
from flask import Flask, jsonify, request, send_from_directory, render_template
from flask_cors import CORS
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import matplotlib.pyplot as plt
import plotly.graph_objs as go
from dash.dependencies import Output, Input
from jproperties import Properties
import json
import pandas as pd
import numpy as np
from psutil import virtual_memory
from psutil._common import bytes2human
from distutils import util
import mysql.connector
import calendar
from flask_sqlalchemy import SQLAlchemy
from werkzeug.debug import DebuggedApplication
import pyodbc

server = Flask(__name__)
CORS(server)
local_properties = Properties()
property_result = []
header_operators = [">=","range","<="]
conn = None


server.wsgi_app = DebuggedApplication(server.wsgi_app, True)
app = dash.Dash(__name__,server=server,url_base_pathname='/getOrder/',external_stylesheets=[dbc.themes.BOOTSTRAP])

basedir = os.path.abspath(os.path.dirname(__file__))

server.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///'+os.path.join(basedir,'data.sqlite')
server.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(server)

class ServerConfig(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    url = db.Column(db.Text)
    username = db.Column(db.Text)
    password = db.Column(db.Text)

    def __init__(self,url,username,password,id=0):
        self.id = id
        self.url = url
        self.username = username
        self.password = password

db.create_all()

@server.route('/home', methods=['GET'])
def get_homepage():
    return render_template('index.html')

@server.route('/analyzer', methods=['GET'])
def get_hybrispage():
    return render_template('hybris.html')

def connectDB():
    config = ServerConfig.query.filter_by(id=0).first()
    try :
        global conn
        # conn = mysql.connector.connect( \
        #     host='localhost',    \
        #     user= config.username,   \
        #     password= config.password , \
        #     database='commerce', \
        #     port=1433
        #     )
        conn = pyodbc.connect('DRIVER={SQL Server};SERVER=localhost;DATABASE=commerce;UID=hybris;PWD=1234')

        return True
    except mysql.connector.Error as err:
        print(err.msg)

def total_memory(mem):
    for name in mem._fields:
        value = getattr(mem, name)
        if name != 'percent':
            value = bytes2human(value)
            if name.capitalize() == 'Total':
                return value[:-1]

mem = total_memory(virtual_memory())

def validate_column(operator,expected_value,current_value):
    if current_value == None:
        return False
    if operator in header_operators:
        if operator != "range":
            return eval("float(expected_value) "+operator+" float(current_value)")
        elif operator == "range":
            value_range = expected_value.split(';')
            return float(value_range[0]) <= float(current_value) <= float(value_range[1])
        # elif operator == "<=":
        #     return float(expected_value) <= float(current_value)
    else:
        if isinstance(expected_value,bool) or (current_value.lower() in ['true','false','yes','no']):
            return bool(util.strtobool(str(current_value).lower())) == bool(util.strtobool(str(expected_value).lower()))
        elif isinstance(expected_value,str) and isinstance(current_value,str):
            return expected_value.casefold() == current_value.casefold()
        else:
            return float(expected_value) == float(current_value) 

def validate_properties(req):
    path = req['config_folder_path']
    with open(path if path.endswith('/') else path+'/' +'local.properties','rb') as local_prop:
        local_properties.load(local_prop,"utf-8")
    if ServerConfig.query.filter_by(id=0).first():
        config = ServerConfig.query.filter_by(id=0).first()
        config.url = local_properties.get('db.url').data
        config.username = local_properties.get('db.username').data
        config.password = local_properties.get('db.password').data
    else :
        config = ServerConfig(local_properties.get('db.url').data,local_properties.get('db.username').data,local_properties.get('db.password').data,0)
    db.session.add(config)
    db.session.commit()

    excel_path = 'config.xlsx'
    df_local_prop = pd.read_excel(excel_path,sheet_name='local') 
    df_tomcat_prop = pd.read_excel(excel_path,sheet_name='tomcat_general_options') 
    df_prop_desc = pd.read_excel(excel_path,sheet_name='description') 
    global mem , property_result
    local_config = df_local_prop[(df_local_prop['Instance'] == req['instance']) & (df_local_prop['Hybris_Version'] == int(req['hybris_version']))]
    tomcat_config = df_tomcat_prop[df_tomcat_prop['Index'].values == local_config['Index'].values]
    tomcat_value = local_properties.get('tomcat.generaloptions').data.split(" -")
    # print(tomcat_value)
    for col in local_config.columns:
        headers = col.split('|')
        header = str(headers[0] if len(headers) == 1 else headers[1])
        operator = str(headers[0] if len(headers) == 2 else None)
        prop_config = df_prop_desc[df_prop_desc['property'].values == header]
        expected_value = local_config[col].values[0]
        current_value = local_properties.get(header).data if local_properties.get(header) is not None else None
        prop_desc = str(prop_config['description'].values[0]) if len(prop_config['description']) >= 1 else "N/A"
        if(header.lower() not in ["index","hybris_version","instance"]):
            if(header.lower() == "ram"):
                current_value = mem
                validation_result = float(current_value) >= float(expected_value)
            else:
                validation_result = validate_column(operator,expected_value,current_value)
            col_data = {
                'HEADER' : header,
                'RECOMMENDED_VALUE' : str(expected_value),
                'CURRENT_VALUE' : str(current_value),
                'PASS' : 'Pass' if bool(validation_result) else 'Fail',
                'COMMENTS' : prop_desc.format(expected_value,current_value)
            }
            property_result.append(col_data)
    

@server.route('/validate',methods=['POST'])
def validate():
    req = json.loads(request.get_data().decode('utf-8'))
    global property_result 
    property_result = []
    validate_properties(req)
    df = pd.DataFrame.from_records(property_result)
    return jsonify({'message' : 'Thanks for request', 'body': df.to_html(classes='table',index=False)}), 200


app.layout = html.Div([
            html.Div([
                        html.Button(id='submit',n_clicks=0,children="refresh",className='btn btn-primary')
                    ],style={'margin-top':'5px'}),
            dcc.Graph(id='order-graph')
],style=dict(padding='10',textAlign='center'))

@app.callback(Output('order-graph','figure'),Input('submit','n_clicks'))
def get_order(n_clicks):
    cnx = connectDB()
    if cnx:
        global conn
        cursor = conn.cursor()
        cursor.execute("select createdts,p_totalprice from orders")
        column_names = [column[0] for column in cursor.description]
        rows = cursor.fetchall()
        row_list = []
        month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        for idx, row in enumerate(rows):
            row_list.append(list(row))
        orders_df = pd.DataFrame(row_list,columns=column_names)
        orders_df['createdts'] = pd.to_datetime(orders_df['createdts'])
        orders_df['month'] = orders_df['createdts'].apply(lambda x: x.strftime("%b"))
        orders_df['month'] = pd.Categorical(orders_df['month'], categories=month, ordered=True)
        orders_df.sort_values(by='month', inplace=True)
        orders_df['p_totalprice'] = orders_df['p_totalprice'].astype(float)
        orders_df['p_totalprice'] = orders_df['p_totalprice'].apply(lambda x: np.round(x,2))
        orders_df.set_index('month',inplace=True)
        df_grouped = orders_df.groupby('month')['p_totalprice'].sum().reset_index()
        yticks = np.arange(orders_df['p_totalprice'].min(),orders_df['p_totalprice'].max(),orders_df['p_totalprice'].max()/5)
        yticks = np.append(yticks,orders_df['p_totalprice'].max())

        return {
                'data' : [
                    go.Bar(
                        x=df_grouped['month'],
                        y=df_grouped['p_totalprice'],
                        marker=dict(color='rgb(26, 118, 255)')
                    )
                ],
                'layout': go.Layout(title="Total Order profit in a month",
                                    xaxis={'title': 'Month'},
                                    yaxis={'title': 'Total Amount'})
            }
        conn.close()

if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('-p','--port',type=int,default=5000)
    args = parser.parse_args()
    port = args.port
    app.run_server(host='127.0.0.1', port=port,debug=True)
