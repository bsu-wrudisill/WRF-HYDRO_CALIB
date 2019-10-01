import pandas as pd

param_cmd = "SELECT * FROM PARAMETERS WHERE calib_flag = 1"
param = pd.read_sql(sql = param_cmd, con="sqlite:///CALIBRATION.db")


