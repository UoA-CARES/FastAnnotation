import numpy as np
import time


x = np.zeros(shape=(256,2000,1500,3), dtype=np.uint8)
include = np.arange(256)
np.random.shuffle(include)
include = include[:254]
exclude = np.delete(np.arange(256), include, 0)
tt0 = time.time()
x = np.delete(x, 6, 0)
x[slice(235)]
tt1 = time.time()
print(tt1-tt0)

