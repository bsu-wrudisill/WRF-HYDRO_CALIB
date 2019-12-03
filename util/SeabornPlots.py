import seaborn as sns
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as ticker
import sys 

m3_to_acrefeet = 0.000810714
dtSeconds = 3600

def ParameterPlot():
    param_cmd = "SELECT * FROM PARAMETERS WHERE calib_flag = 1"
    param = pd.read_sql(sql = param_cmd, con="sqlite:///PREDUCE_WY2014.db")
    calib_cmd = "SELECT * FROM CALIBRATION"
    calib = pd.read_sql(sql = calib_cmd, con="sqlite:///PREDUCE_WY2014.db")
    merge = pd.merge(param, calib, how='outer', left_on = 'Iteration', right_on = 'Iteration')

    cullList = [u'calib_flag', u'minValue', u'maxValue', u'ini',  
                u'factor', u'bestValue', u'onOff', u'Improvement', 'Function']

    merge = merge.drop(columns=cullList)
    merge['logCV'] = np.log(merge['currentValue'])
    g = sns.FacetGrid(merge, col="parameter", col_wrap=5)
    g = g.map(plt.scatter, 'currentValue', 'Objective').set_axis_labels("multiplier", "KGE").set(xscale="log").set(xlim = (.1,10.))
    # https://seaborn.pydata.org/examples/many_facets.html


def returnQmodOnly(dbcon, **kwargs):
    # only use this when there is just one iteration 
    mod_cmd = "SELECT * FROM MODOUT"
    mod = pd.read_sql(sql = mod_cmd, con="sqlite:///{}".format(dbcon))
    mod['time'] = pd.to_datetime(mod['time']) 
    mod['type'] = 'WRF_Hydro V5'
    return mod 

def returnQmodOnly(dbcon, **kwargs):
    # only use this when there is just one iteration 
    mod_cmd = "SELECT * FROM MODOUT"
    mod = pd.read_sql(sql = mod_cmd, con="sqlite:///{}".format(dbcon))
    mod['time'] = pd.to_datetime(mod['time']) 
    mod['type'] = 'WRF_Hydro V5'
    return mod 

def returnObsOnly(dbcon, **kwargs):
    obs = pd.read_sql(sql="SELECT * FROM OBSERVATIONS", con="sqlite:///{}".format(dbcon))
    obs.rename(columns={"site_name_long":"site"}, inplace=True)
    obs['time'] = pd.to_datetime(obs['time'])
    obs.set_index('time', inplace=True) 
    idx = pd.date_range(obs.index[0], obs.index[-1])
    
    # check if there are missing times from the observations ...
    if len(idx) != len(obs.index):
        missing_list = [str(i) for i in idx if i not in obs.index]
        message = 'observations are missing the following dates: {}'.format(missing_list)    
        print(message)
    
    # reindex and interpolate
    obs = obs.reindex(idx)
    obs_interpolate = obs.interpolate()
    obs_interpolate['time'] = idx
    return obs_interpolate


def returnQmodCalib(dbcon, **kwargs):
    mod_cmd = "SELECT * FROM MODOUT"
    mod = pd.read_sql(sql = mod_cmd, con="sqlite:///{}".format(dbcon))
    # 
    calib_cmd = "SELECT * FROM CALIBRATION"
    calib = pd.read_sql(sql = calib_cmd, con="sqlite:///{}".format(dbcon))
    #
    obs = pd.read_sql(sql="SELECT * FROM OBSERVATIONS", con="sqlite:///{}".format(dbcon))
    obs['time'] = pd.to_datetime(obs['time'])
    obs.drop(columns=['site_no'], inplace=True)

    #df.drop(columns=["Directory", "Iterations"], inplace=True)
    mod['time'] = pd.to_datetime(mod['time'])
    df_cd = pd.merge(calib, mod, how='outer', left_on = 'Iteration', right_on = 'Iterations')
    df_cd['time'] = pd.to_datetime(df_cd['time'])
    return df_cd 


def integrateQ(array):
    return np.sum(array)*dtSeconds*24*m3_to_acrefeet     
    #return np.mean(array)*3600*24*365*m3_to_acrefeet


def annotateBars(ax):
    for width,patch in enumerate(ax.patches):
        hgt_str = f'{patch.get_height():,.3f}' 
        hgt = patch.get_height() - 1e5
        ax.text(width-.25, hgt, hgt_str) 

def getParameters(dbcon):
    param_cmd = "SELECT * FROM PARAMETERS WHERE calib_flag = 1"
    param = pd.read_sql(sql = param_cmd, con="sqlite:///{}".format(dbcon))
    return param

if __name__ == '__main__':
    #db = sys.argv[1]
    #obs = returnObsOnly(db)
    #mod = returnQmodOnly(db)
    #ns = returnQmodOnly('ns.db')
    
    #ax = sns.lineplot(x="time", y="qMod", data=mod, label='mod')
    #ax = sns.lineplot(x="time", y="qObs", data=obs, label='obs')
    #plt.show()

    calib = returnQmodOnly("bfeather.db")
    nwm = returnQmodOnly("bfeather_nwm.db")
    obs = returnObsOnly("bfeather_nwm.db")

    ##preduce = returnQmodOnly("PREDUCE_WY2014.db")
    ##baseline = returnQmodOnly("BASELINE_WY2014.db")

    ##df = pd.DataFrame(data = {'WRF-HydroV5:PREDUCE':[integrateQ(preduce['qMod'])], 
    ##                          'WRF-HydroV5:Baseline':[integrateQ(baseline['qMod'])], 
    ##                         'USGS SiteNo 13185000':[integrateQ(obs['qObs'])]})
    ##df['stat'] = 'total_runoff_acrefeet'
    ##df.set_index('stat', inplace=True)


    ##baseline = returnQmodOnly("BASELINE_WY2012.db")
    ##obs = returnObsOnly("BASELINE_WY2011.db")

    ## plotting below here 
    #sns.set(style="darkgrid")
    ##ax = sns.barplot(data=df)
    ##ax.set(ylabel='Acrefeet')
    ##ax.set(title = 'WY 2014 Boise River Twin Springs Total Runoff')

    ##annotateBars(ax)
    ##plt.show()
    ######--------------

    #ax = sns.lineplot(x="time", y="qMod",hue ="Objective", data=df_cd)
    #baseline = df_cd.query("Iteration == '0'")
    #best = df_cd[df_cd.Objective == min(df_cd.Objective)] 
    #best = best[best.Iteration == str(min(list(map(int, best.Iteration))))]  # lol 

    ax = sns.lineplot(x="time", y="qMod", data=nwm, label='nwm')
    ax = sns.lineplot(x="time", y="qMod", data=calib, label='bsu-calib')
    ax = sns.lineplot(x='time', y='qObs', data=obs, color='black', linestyle='dashed', label='BoiseFeatherville')
    #ax.plot(baseline.time, baseline.qMod, label='NWM Baseline', linestyle='--', color='Blue')
    #ax.plot(baseline.time, best.qMod, label='Best', color='Orange') 
    plt.legend()



    plt.show()
    ##plt.show()

    ##ax = sns.lineplot(x="time", y="qMod",data=mod, color='purple', label='WRF Hydro')
    ##ax = sns.lineplot(x="time", y="qMod",data=pred, color='orange', label='WRF Hydro--90% Precip')

    ##ax.set(xlabel='Date', ylabel='Q cms')
    ##plt.show()
