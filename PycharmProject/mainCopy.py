
import os  # To work with files
import matplotlib.pyplot as plt  # This is for plotting

import psspy  # Import the PSS/E module
import dyntools  # Import the dynamic simulation module in PSS/E
import redirect  # Module for redirecting the PSS/E output to the terminal
from psse_models import load_models  # Load models from S. Jakobsen
import numpy as np
import psspyObject

# To-do:
# * Separate into machine_monitor and bus_monitor
# * Create Git synchronization schedule


case = psspyObject.psspyCase("DifferentBusOrder",5610,500)
# slackBefore = case.read_slackbus_generation()
case.setHvdcToMax()
#case.add_hvdc_buses()
case.runStaticLoadFlow()
# slackAfter = case.read_slackbus_generation()
case.save_network_data()
case.add_fault(10.0,2,5610,[1400])  # Load step
case.prepare_dynamic_simulation()
case.set_monitor_channels([3300, 5600, 7000], [1,2,4,7])
#case.set_monitor_channels([3300], [2])
case.run_dynamic_simulation(120)
case.read_results()
case.plot_results()

