import sys
import os
import sqlite3
from sqlalchemy import create_engine


def LogResultsToDB(df,table_name,**kwargs):
	db_connection = kwargs.get('dbcon', 'CALIBRATION.db')
	#
	engine = create_engine('sqlite:///{}'.format(db_connection), echo=False)
	df.to_sql(table_name, con = engine, if_exists='append')


def LogObjToDB(iterations, objectivefx, improvement, **kwargs):
	db_connection = kwargs.get('dbcon', './CALIBRATION.db')
	#
	#
	#dbConn = sqlite3.connect("./CALIBRATION.db", timeout=10)
	dbConn = sqlite3.connect(db_connection, timeout=10)
	cursor = dbConn.cursor()

	cursor.execute('''CREATE TABLE IF NOT EXISTS CALIBRATION(
	Iteration TEXT,
	ObjectiveFX REAL,
	Improvement INTEGER 
	)''')

	cursor.execute('''INSERT INTO CALIBRATION(
	Iteration,
	ObjectiveFX,
	Improvement
	)
	VALUES(?,?,?)''',
	(iterations, objectivefx,improvement))

	dbConn.commit()
	dbConn.close()

