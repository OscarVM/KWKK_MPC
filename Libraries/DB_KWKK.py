

import configparser
import sqlalchemy
import pyodbc


class Database:
    def __init__(self):
        self.DSN = None
        self.user = None
        self.pwd = None
        self.con = None
        self.cursor = None
        self.dict_cursor = None
        self.host = None
        self.db_name = None
        self.uri = None
        self.engine = None
        self.load_config()       
        self.connect()
        self.make_engine()
#        
    def load_config(self):        
#        config = configparser.ConfigParser(allow_no_value=True)
#        config.optionxform = str        
#        config.read('database_config.ini')
#        host_name = config.sections()[0]
#        
#        self.host = config[host_name]['host']
#        self.user = config[host_name]['user']
#        self.pwd = config[host_name]['pwd']
#        self.db_name = config[host_name]['database']
#        self.DSN = config[host_name]['dsn']
        
        self.host = r'141.79.92.111'
        self.user = r'IMGKWKK'
        self.pwd = r'C/sells2018'
        self.db_name = r'IMG'
        self.DSN = r'IMG_DB_32'
          
    def connect(self):    
#        driver_string = "DRIVER = '{ODBC Driver 11 for SQL Server}';"
#        serv_str = "SERVER='{}';DATABASE='{}';UID='{}';PWD='{}'".format(self.host, self.db_name, self.user, self.pwd)
#        connection_str = driver_string + serv_str
#        print(connection_str)
        connection_str = r"DSN={};UID={};PWD={}".format(self.DSN,self.user,self.pwd)
        print(connection_str)
        self.con = pyodbc.connect(connection_str)
        print('connection_opened')
        self.cursor = self.con.cursor()   
#        self.dict_cursor = self.con.cursor(cursor_factory=psycopg2.extras.DictCursor)
        ###https://code.google.com/archive/p/pyodbc/wikis/ConnectionStrings.wiki
        ###https://github.com/mkleehammer/pyodbc/wiki/Connecting-to-SQL-Server-from-Windows

    def make_engine(self):
#        self.uri = 'mssql+pyodbc://{user}:{pwd}@{host}/{db_name}?driver=ODBC+Driver+11+for+SQL+Server'
        self.uri = 'mssql+pyodbc://{user}:{pwd}@{dsn}'
        self.uri = self.uri.format(user=self.user, pwd=self.pwd, dsn=self.DSN)
        self.engine = sqlalchemy.create_engine(self.uri)
        ###http://docs.sqlalchemy.org/en/latest/dialects/mssql.html
        
    def disconnect(self):        
        self.con.close()
        print('connection_closed')
        
    def commit(self):
        self.con.commit()
        
    def execute(self, query):
        self.cursor.execute(query)
        
    def execute_fetchone(self, query, arg_list=None):
        self.cursor.execute(query, arg_list)
        ret = self.cursor.fetchone()
        return ret        
    
    def execute_fetchall(self, query, arg_list=None):
        self.cursor.execute(query, arg_list)
        ret = self.cursor.fetchall()
        return ret   




class DBTable(object):
    def __init__(self):
        self.database = Database()
        self.cursor = self.database.cursor
#        self.dict_cursor = self.database.dict_cursor
    
    def drop_table(self):
        drop_query = "DROP TABLE IF EXISTS {schema_name}.{table_name}".format(self.table_name)
        self.database.cursor.execute(drop_query)
        self.commit()        

    def finish(self):
#        self.database.commit()
        self.database.disconnect()
    
    def commit(self):
        self.database.commit()
        
    def latest_entry(self):
        query = "SELECT max(Timestamp) FROM {schema_name}.{table_name}"\
            .format(table_name=self.table_name, schema_name=self.schema_name)
        self.database.cursor.execute(query)
        latest_date = self.database.cursor.fetchall()[0][0]
        return latest_date
        
    def time_stamp_does_exist(self, time_stamp, Name):
        query = "SELECT Timestamp FROM {schema_name}.{table_name} WHERE Timestamp = '{dat}' and Name = '{nam}'  " \
            .format(table_name=self.table_name, schema_name=self.schema_name, dat = time_stamp, nam = Name)
        self.database.cursor.execute(query)
        ret = self.database.cursor.fetchall()
        if len(ret) == 0:
            return False
        else:
            return True
        
    def delete_row_ts(self, time_stamp, Name):
        query = "DELETE FROM {schema_name}.{table_name} " \
                "WHERE {schema_name}.{table_name}.Timestamp = '{dat}' and {schema_name}.{table_name}.Name = '{nam}'" \
            .format(table_name=self.table_name, schema_name=self.schema_name, dat = time_stamp, nam = Name)
        self.cursor.execute(query)
               
    def delete_if_already_exists(self, time_stamp, Name):
        if self.time_stamp_does_exist(time_stamp, Name):
            self.delete_row_ts(time_stamp, Name)
        
    def execute_fetchone(self, query, args=None):
        self.cursor.execute(query, args)
        return self.cursor.fetchone()  
    
    def execute_fetchall(self, query, args=None):
        self.cursor.execute(query, args)
        return self.cursor.fetchall()         
            
    def wipe(self):
        self.cursor.execute("DELETE FROM {schema_name}.{table_name}".format(schema_name=self.schema_name, table_name=self.table_name))
        self.commit()

class DBTable_KWKK(DBTable):
    def __init__(self, table_name, schema_name):
        super(DBTable_KWKK,self).__init__()
        self.schema_name = schema_name
        self.table_name = table_name
#        self.database = D

    def create_table(self):
        query = "CREATE TABLE IF NOT EXISTS {schema_name}.{table_name} " \
                "(ID bigint PRIMARY KEY, Timestamp datetime2(7), " \
                "Name varchar(40), Value float )"
        query = query.format(schema_name=self.schema_name, table_name=self.table_name)
        self.database.cursor.execute(query)
        self.commit()
    
    def insert_row(self, time_stamp, Name, Value):
        self.delete_if_already_exists(time_stamp, Name)
        query = "INSERT INTO {schema_name}.{table_name} " \
                "(Timestamp, Name, Value) " \
                "Values ('{dat}','{nam}', {val})"
        query = query.format(schema_name=self.schema_name, table_name=self.table_name, dat = time_stamp, nam = Name, val = Value)
        self.database.cursor.execute(query)
        self.commit()
        
    def delete_row(self,time_stamp, Name):
        self.delete_if_already_exists(time_stamp, Name)
        self.commit()
    
    def close_connection(self):
        self.finish()
        
    def insert_dataframe(self, df):
        df.to_sql(name=self.table_name, con=self.database.engine, schema=self.schema_name, if_exists='append', index=False)

    def upsert_dataframe(self, df):
        query = "INSERT INTO {schema_name}.{table_name} " \
                "(Timestamp, Name, Value) " \
                "Values ('{dat}','{nam}', {val})"
        for row in df.iterrows():
            time_stamp = str(row[1]['time'])
            price = str(row[1]['Price'])
            query_row = query.format(schema_name=self.schema_name, table_name=self.table_name, dat = time_stamp, nam = 'price', val = price)
            self.delete_if_already_exists(time_stamp, 'price')
            self.database.cursor.execute(query_row)
        self.commit()
  
    def delete_dataframe(self, df):
        for row in df.iterrows():
            time_stamp = str(row[1]['time'])
            price = str(row[1]['Price'])
            self.delete_if_already_exists(time_stamp, 'price')
        self.commit()
    
    def last_n_date_values(self, n_val, Name, time_stamp = None):
        """ retrieve values from the database """
    #nval is the number of values to retrieve
    #Name is a string corresponding to the name of the value in the name list
    # If timestamp is none, then it will retrieve the last n_val values of the db.
        # else if a stamp is given, it will look for it, if exists, will retrieve the last n_values if not, it will retrieve from the latest entry to n_val
        if time_stamp == None:
            query = "SELECT Top {n} Value FROM {schema_name}.{table_name} where Name = '{nam}' order by Timestamp DESC" 
            query = query.format(n=n_val, schema_name=self.schema_name, table_name=self.table_name, nam = Name)
        else:
            if self.time_stamp_does_exist(time_stamp, Name):
                query = "SELECT Top {n} Value FROM {schema_name}.{table_name} where Timestamp < '{dat}' and Name = '{nam}' order by Timestamp DESC" 
                query = query.format(n=n_val, schema_name=self.schema_name, table_name=self.table_name, dat = time_stamp, nam = Name)
            else:
                query = "SELECT Top {n} Value FROM {schema_name}.{table_name} where Name = '{nam}' order by Timestamp DESC" 
                query = query.format(n=n_val, schema_name=self.schema_name, table_name=self.table_name, nam = Name)
            
        self.database.cursor.execute(query)
        return self.database.cursor.fetchall()
                    
    def next_n_date_values(self, n_val, Name, time_stamp ):
        """ retrieve values from the database from a specific date and beyond """
    #nval is the number of values to retrieve
    #Name is a string corresponding to the name of the value in the name list
    # If timestamp is none, then it will retrieve the last n_val values of the db.
        # else if a stamp is given, it will look for it, if exists, will retrieve the next n_values if not, it will retrieve from the latest entry to n_val

        if self.time_stamp_does_exist(time_stamp, Name):
            query = "SELECT Top {n} Value FROM {schema_name}.{table_name} where Timestamp > '{dat}' and Name = '{nam}' order by Timestamp ASC" 
            query = query.format(n=n_val, schema_name=self.schema_name, table_name=self.table_name, dat = time_stamp, nam = Name)
        else:
            print('Selected timestamp does not exist')

            
        self.database.cursor.execute(query)
        return self.database.cursor.fetchall()
                    