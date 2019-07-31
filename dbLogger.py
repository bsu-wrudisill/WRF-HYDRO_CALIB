import sys
import os
import sqlite3
from sqlalchemy import create_engine


def LogResultsToDB(df,table_name,**kwargs):
	db_connection = kwargs.get('dbcon', 'CALIBRATION.db')
	#
	engine = create_engine('sqlite:///{}'.format(db_connection), echo=False)
	df.to_sql(table_name, con = engine)


def LogParamsToDB(iterations, directory, objectivefx, improvement, **kwargs):
	db_connection = kwargs.get('dbcon', 'CALIBRATION.db')
	#
	#
	#dbConn = sqlite3.connect("./CALIBRATION.db", timeout=10)
	dbConn = sqlite3.connect("./{}".format(db_connection), timeout=10)
	cursor = dbConn.cursor()
	
	cursor.execute('''CREATE TABLE IF NOT EXISTS CALIBRATION(
				Iteration TEXT,
				Directory TEXT,
				ObjectiveFX REAL,
				Improvement INTEGER 
				)''')
	
	cursor.execute('''INSERT INTO CALIBRATION(
				Iteration,
				Directory,
				ObjectiveFX,
				Improvement
				)
			VALUES(?,?,?,?)''',
			(iterations, directory, objectivefx,improvement))
	
	dbConn.commit()
	dbConn.close()

