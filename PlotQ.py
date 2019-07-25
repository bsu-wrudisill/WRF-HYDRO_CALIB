import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# read stuff from the database and create a plot 
sql_cmd = "SELECT * FROM ITERATION_1" 
df = pd.read_sql(sql = sql_cmd, con="sqlite:///CALIBRATION.db")
df['time'] = pd.to_datetime(df['time'])
df.set_index('time', inplace=True)

# read obs from the table 
obs = pd.read_sql(sql="SELECT * FROM OBSERVATIONS", con="sqlite:///CALIBRATION.db")
obs['time'] = pd.to_datetime(obs['time'])
obs.set_index('time', inplace=True)
obs.drop(columns=['site_no'], inplace=True)

# merge
merged = obs.copy()
merged['qMod'] = df['qMod']
merged.plot()
plt.savefig('qtest')
