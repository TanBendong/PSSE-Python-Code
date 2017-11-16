
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

# Input for setting HVDC-cables

hvdc = [
    [5610, 1400, "Abra"],
    [5620, 1400, "Kadabra"]
]
hvdc_numbers = [5610, 5620]  # Bus numbers of HVDC connections
hvdc_capacities = [1400, 1400]  # Check the second parameter here
hvdc_names = ["Abra", "Kadabra"]  # Add names for HVDC names here


case = psspyObject.PsspyCase("LowerLimit5610")
# slackBefore = case.read_slackbus_generation()
case.set_hvdc_active_power(5610, -1400)
#case.set_hvdc_to_max(5620, 1400)
case.add_hvdc_buses()
case.run_static_load_flow()
#case.redist_slack()
# slackAfter = case.read_slackbus_generation()
case.save_network_data()
case.add_fault(10.0,2,5610,[-1400])  # Load step
#case.add_fault(10.0,2,5620,[1400])
case.prepare_dynamic_simulation(0.005)
case.set_monitor_channels([3300, 5600, 7000], [1,2,4,7])
#case.set_monitor_channels([3300], [2])
case.run_dynamic_simulation(120)
case.read_results()
case.plot_results()

