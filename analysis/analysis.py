import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

data = pd.read_csv('hybrid_orig.csv')
index = 'Latency'
#s = pd.Series(data)
print(data[[index]].describe())
print('---')
print(data[[index]].quantile([.01, .05, .10, .25, .5, .75, .9, .95, .99]))
print('---')
print(data[[index]].var(numeric_only='None'))

data[[index]].plot(kind='kde', title='Frequency of Response Time', bw_method=0.1)
plt.show()