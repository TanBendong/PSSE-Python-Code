
# Standard Python-packages
import os
import matplotlib.pyplot as plt
import numpy as np

# PSSPY-related packages
import psspy
import dyntools
import redirect

# Custom packages
#from psse_models import load_models


# Default variables for PSSPY
_i = psspy.getdefaultint()
_f = psspy.getdefaultreal()
_s = psspy.getdefaultchar()


class psspyCase(object):
    """Base class for cases"""
    # Constructor
    def __init__(self, output_name, hvdcBusNr = 5610, hvdcLimit = 1400, input_network = "Scenario1"):
        """
            Constructor for case.
            Input:
                outputName: name of output-file
        """

        self.output_name = output_name  # For naming of plots and output
        self.hvdcBusNr = hvdcBusNr  # PSS/E bus number for hvdc connection
        self.hvdcLimit = hvdcLimit  # For setting limits of hvdc connection
        self.input_network = input_network  # For naming of plots and output
        self.filename = "Bus" + str(self.hvdcBusNr) + "_" + self.input_network + "_" + self.output_name

        redirect.psse2py()  # Redirect the PSS/E output to the terminal
        psspy.throwPsseExceptions = True

        # Files and folders
        os.chdir("..")
        cwd = os.getcwd()  # Get the current directory
        models = os.path.join(cwd, "Models")  # Name of the folder with the models

        self.input_network = input_network
        self.casefile = os.path.join(models, input_network + ".sav")  # Static network data
        self.dyrfile = os.path.join(models, input_network + ".dyr")  # Dynamic model parameters
        self.output_name = output_name  # For naming of plots and output
        self.input_network = input_network

        self.events_overview = []  # For dynamic events, 1st column time, 2nd column type of fault, 3rd param bus nr

        # Initialize case
        # * Why are these initializations not in local scope?
        #   -> Because they are part of constructor?
        # * How do the other member functions access the psspy case?
        psspy.psseinit(10000)
        psspy.case(self.casefile)  # Read in the power flow data
        psspy.dyre_new([1, 1, 1, 1], self.dyrfile, "", "", "")

    # Public classes
    def setHvdcToMax(self):
        # Define bus number and read load at this bus
        hvdcBusNr = self.hvdcBusNr  # PSS/E bus number
        hvdcLimit = self.hvdcLimit  # Maximum capacity of this HVDC link
        loadP = np.array(psspy.aloadcplx(-1, 1, "MVAACT")[1][
                             0])  # Actual MVA (MVAACT) and Nominal MVA (MVANOM) seem to give same value
        loadNumbers = np.array(psspy.aloadint(-1, 1, "NUMBER")[1][0])  # Load all bus numbers
        loadP = loadP[
            np.where(loadNumbers == hvdcBusNr)[0][0]]  # Select only the load of the desired cable by finding index

        # Set cable to max export
        psspy.load_chng_4(hvdcBusNr, _s, [_i, _i, _i, _i, _i, _i],
                          [hvdcLimit, _f, _f, _f, _f, _f])

        # The generation necessary for increased export at the cable is distributed over available capacity in the system
        # This is so the slack bus doesn't have to take all the extra load
        slackP = hvdcLimit - loadP  # Warning: loadP is a complex value
        slackP = slackP.real  # Convert to real value, no longer complex as

        # Area of the HVDC bus
        busNumbers = np.array(psspy.abusint(-1, 1, "NUMBER")[1][0])  # Get all bus numbers
        busAreas = np.array(psspy.abusint(-1, 1, "AREA")[1][0])
        hvdcBusArea = busAreas[
            np.where(busNumbers == hvdcBusNr)[0][0]]  # Use bus numbers to index for the area of HVDC bus

        # Find generation capacity of this specific area
        areaBuses = np.array(psspy.agenbusint(-1, 1, "AREA")[1][0])
        indices = np.where(areaBuses == hvdcBusArea)[0]
        sysGen = np.array(psspy.agenbusreal(-1, 1, "PGEN")[1][0])  # Extract active power generation of all plants
        areaGen = sysGen[indices]  # Only include area of hvdc bus
        sysGenCap = np.array(psspy.agenbusreal(-1, 1, "PMAX")[1][0])  # Extract generation capacity of all plants
        areaGenCap = sysGenCap[indices]
        areaRemGenCap = (sum(areaGenCap) - sum(areaGen))  # Remaining generation capacity in the HVDC area
        sysRemGenCap = (sum(sysGenCap)) - sum(sysGen)

        print("Bus count is: ", psspy.agenbuscount(-1, 1)[1])

        # psspy.amachint can not return "AREA", thus we need a workaround using machine numbers and bus areas
        # Find "AREA" of each machine
        machineNumbers = np.array(psspy.amachint(-1, 1, "NUMBER")[1][0])
        machineAreas = np.zeros(len(machineNumbers))
        for i in range(len(machineNumbers)):
            machineAreas[i] = busAreas[np.where(busNumbers == machineNumbers[i])]

        indices = np.where(machineAreas == hvdcBusArea)[0]
        machGen = np.array(psspy.amachreal(-1, 1, "PGEN")[1][0])  # Read PGEN of machines
        machGenCap = np.array(psspy.amachreal(-1, 1, "PMAX")[1][0])  # Read PMAX of machines
        machSlack = machGenCap - machGen  # NB: machSlack includes ALL machines, not just the ones in HVDC area

        currentMachineNr = 0  # machine_chng_2 needs both number and ID
        machineId = 0  # which complicates the iteration through the machines

        # Distribute slack
        if areaRemGenCap > slackP:  # If true distribute slack over local area
            slackRatio = slackP / areaRemGenCap
            machSlack = machSlack * slackRatio

            # Set each generator to unique value
            for i in indices:  # Iterate through each in-service machine and set load
                if currentMachineNr != machineNumbers[i]:  # new machine
                    machineId = 1
                    currentMachineNr = machineNumbers[i]
                else:  # Same machine as previous
                    machineId = machineId + 1

                psspy.machine_chng_2(currentMachineNr, str(machineId),
                                     [_i, _i, _i, _i, _i, _i],
                                     [machGen[i] + machSlack[i], _f, _f, _f, _f, _f, _f,
                                      _f, _f, _f, _f, _f, _f, _f, _f,
                                      _f, _f])

        else:
            # 1st set all generation to max in local area
            for i in indices:  # Iterate through machines in local area and set max generation
                if currentMachineNr != machineNumbers[i]:  # new machine
                    machineId = 1
                    currentMachineNr = machineNumbers[i]
                else:  # Same machine as previous
                    machineId = machineId + 1

                psspy.machine_chng_2(currentMachineNr, str(machineId),
                                     [_i, _i, _i, _i, _i, _i],
                                     [machGenCap[i], _f, _f, _f, _f, _f, _f, _f,
                                      _f, _f, _f, _f, _f, _f, _f, _f, _f])

            # Recalculate slack
            slackP = slackP - sum(machSlack[indices])  # Recalculate the slack that needs to be distributed
            # AREAREMGENCAP IS THE PROBLEM! CHECK IF THIS HAS LEAD TO OTHER ERRORS?
            sysRemGenCap = sysRemGenCap - sum(machSlack[indices])  # Recalculate remaining generation capacity
            machSlack[indices] = 0  # Maxed generators = can't take more slack
            slackRatio = slackP / sysRemGenCap
            machSlack = machSlack * slackRatio

            # Distribute this new slack across the rest of the system
            machineId = 0
            currentMachineNr = 0
            for i in range(len(machSlack)):  # Increase generation of all generators in system
                if currentMachineNr != machineNumbers[i]:  # New machine
                    machineId = 1
                    currentMachineNr = machineNumbers[i]
                else:  # Same machine as previous
                    machineId = machineId + 1
                psspy.machine_chng_2(currentMachineNr, str(machineId),
                                     [_i, _i, _i, _i, _i, _i],
                                     [machGen[i] + machSlack[i], _f, _f, _f, _f, _f, _f,
                                      _f, _f, _f, _f, _f, _f, _f, _f,
                                      _f,
                                      _f])

                # All generation has now been distributed
    def runStaticLoadFlow(self):
        psspy.fdns([0, 0, 0, 1, 1, 1, 99, 0])  # Fixed slope decoupled Newton-Raphson
    def prepare_dynamic_simulation(self,p_zip = [10.0, 10.0], q_zip = [10.0, 10.0]):
        self.outputfile = os.path.join(os.getcwd(), self.filename)  # Store dynamic simulation

        # Convert the loads for dynamic simulation
        psspy.cong(0)
        psspy.conl(0, 1, 1, [0, 0], [p_zip[0], p_zip[1], q_zip[0], q_zip[1]])  # Active power IY(P), Reactive power IY(P)
        psspy.conl(0, 1, 2, [0, 0], [p_zip[0], p_zip[1], q_zip[0], q_zip[1]])  # p_zip[0] = I, p_zip[1] = Y for IYP model, another name for ZIP-load model
        psspy.conl(0, 1, 3, [0, 0], [p_zip[0], p_zip[1], q_zip[0], q_zip[1]])  # Default tuning from S. M. Hamre's thesis tuning

        # Set the time step for the dynamic simulation
        psspy.dynamics_solution_params(realar=[_f, _f, 0.005, _f, _f, _f, _f, _f])
    def set_monitor_channels(self,buses = (5600, 3300, 7000), quantities = (1,2,4,7)):

        machine_monitor = np.zeros([len(buses)*len(quantities), 3])
        for i in range(len(buses)):
            for j in range(len(quantities)):
                # Add channels to monitor
                # machine_array_channel(channel index, quantity to monitor (ex. PELEC), bus number)
                psspy.machine_array_channel([4*i+j+1, quantities[j], buses[i]])

                # Store for plotting later on
                machine_monitor[4*i+j][0] = int(4*i+j+1)
                machine_monitor[4*i+j][1] = int(quantities[j])
                machine_monitor[4*i+j][2] = int(buses[i])

        self.machine_monitor = machine_monitor
    def run_dynamic_simulation(self,end_time = 10.0):
        self.ierr = psspy.strt(0, self.outputfile)  # Tell PSS/E to write to the output file

        # Run and perform scheduled faults in queue
        # First need the initial run
        time = self.events_overview[0][0]  # The first event
        psspy.run(0, time, 100, 10, 0)  # Run until the first event occurs

        # Now iterate through all faults
        time = self._find_unique_times()  # Returns a numpy array
        for i in range(len(time)):
            indices = np.where(time == time[i])[0]
            self._exec_fault(indices)
            if (i + 1) < len(time):  # Avoid going out of bounds
                psspy.run(0, time[i + 1], 100, 10, 0)

        # At the last fault, run till end_time
        psspy.run(0, end_time, 100, 10, 0)
    def read_results(self):
        # Read the output file
        chnf = dyntools.CHNF(self.outputfile + ".out")
        # assign the data to variables
        self.sh_ttl, self.ch_id, self.ch_data = chnf.get_data()
    def plot_results(self, show_plots = True, lcl_plcmnt=True):

        plt.close("all")# Close plots from previous runs

        # Directory of plot files
        if lcl_plcmnt:  # Local placement, save in folder near script being run
            os.chdir("Plots")  # To save in a separate folder for Plots
        else:  # Save in folder for LaTeX-document for rapid changes
            os.chdir("C:\Users\Espen\OneDrive - NTNU\Prosjekt\LaTeX\plots")


        machine_quantities = ("ANGLE", "PELEC", "QELEC", "ETERM", "EFD", "PMECH",
                               "SPEED", "XADIFD", "ECOMP", "VOTHSG", "VREF", "VUELL",
                               "VOEL", "GREF", "LCREF", "WVLCTY", "WTRBSP", "WPITCH",
                               "WAEROT", "WROTRV", "WROTRI", "WPCMND", "WQCMND")

        quantities = np.unique(self.machine_monitor[:,1])
        for i in range(len(quantities)):
            plot_title = machine_quantities[int(quantities[i]) - 1]
            plt.figure(plot_title)
            indices = np.where(self.machine_monitor[:,1] == quantities[i])[0]
            for j in range(len(indices)):
                plt.plot(self.ch_data['time'], self.ch_data[indices[j]+1])

            plt.xlabel("Time (s)")
            plt.ylabel(self.generate_ylabel(plot_title))  # Remains work on ylabel!!!!
            plt.legend(self.generate_legend(indices))  # Remains work on legend!!!
            plt.grid()
            plt.savefig(machine_quantities[int(quantities[i]-1)] + "_" + self.filename)

        if show_plots:
            plt.show()
    def add_hvdc_buses(self):
        # North Sea Link nsl ( http://www.statnett.no/en/Projects/Cable-to-the-UK/ )
        nsl_nr = 6010
        nsl_area = 14
        nsl_connection = 6000  # Kvilldal
        nsl_voltage = 500.0
        nsl_reactance = 0.006
        nsl_initial_power = 0.0

        psspy.bus_data_3(nsl_nr, [_i, nsl_area, _i, _i], [nsl_voltage, _f, _f, _f, _f, _f, _f], _s)
        psspy.load_data_4(nsl_nr, r"""1""", [_i, _i, _i, _i, _i, _i], [_f, _f, _f, _f, _f, _f])  # Create bus before any values can be set
        psspy.load_chng_4(nsl_nr, r"""1""", [_i, _i, _i, _i, _i, _i], [nsl_initial_power, _f, _f, _f, _f, _f])  # Set values (power)
        psspy.branch_data(nsl_connection, nsl_nr, r"""1""", [_i, _i, _i, _i, _i, _i],
                          [_f, _f, _f, _f, _f, _f, _f, _f, _f, _f, _f, _f, _f, _f, _f])  # Create branch before setting values
        psspy.branch_chng(nsl_connection, nsl_nr, r"""1""", [_i, _i, _i, _i, _i, _i],
                          [_f, nsl_reactance, _f, _f, _f, _f, _f, _f, _f, _f, _f, _f, _f, _f, _f])  # Set values (reactance)


        # NordLink nl ( http://www.statnett.no/Nettutvikling/NORDLINK/ )
        nl_nr = 5630
        nl_area = 13
        nl_connection = 5600  # Kristiansand?
        nl_voltage = 525.0
        nl_reactance = 0.006
        nl_initial_power = 0.0

        psspy.bus_data_3(nl_nr, [_i, nl_area, _i, _i], [nl_voltage, _f, _f, _f, _f, _f, _f], _s)
        psspy.load_data_4(nl_nr, r"""1""", [_i, _i, _i, _i, _i, _i], [_f, _f, _f, _f, _f, _f])  # Create bus before any values can be set
        psspy.load_chng_4(nl_nr, r"""1""", [_i, _i, _i, _i, _i, _i], [nl_initial_power, _f, _f, _f, _f, _f])  # Set values (power)
        psspy.branch_data(nl_connection, nl_nr, r"""1""", [_i, _i, _i, _i, _i, _i],
                          [_f, _f, _f, _f, _f, _f, _f, _f, _f, _f, _f, _f, _f, _f, _f])  # Create branch before setting values
        psspy.branch_chng(nl_connection, nl_nr, r"""1""", [_i, _i, _i, _i, _i, _i],
                          [_f, nl_reactance, _f, _f, _f, _f, _f, _f, _f, _f, _f, _f, _f, _f, _f])  # Set values (reactance)
    def read_slackbus_generation(self,slack_bus_number = 3300):
        plant_bus_numbers = np.array(psspy.agenbusint(-1,1,"NUMBER")[1][0])
        plant_gen = np.array(psspy.agenbusreal(-1,1,"PGEN")[1][0])
        index = np.where(plant_bus_numbers == slack_bus_number)
        return plant_gen[index]
    def save_network_data(self,filename = "SavedNetworkData"):
        psspy.save(os.path.join(os.getcwd(),self.filename+".sav"))
    def alternative_plotting(self):
        # If I can't get the smart plotting to work before displaying to Sigurd & Co.
        # Do the plotting
        plt.figure("ANGLE")
        plt.plot(self.ch_data['time'], self.ch_data[1])  # See channel monitoring
        plt.plot(self.ch_data['time'], self.ch_data[5])
        plt.plot(self.ch_data['time'], self.ch_data[9])
        plt.xlabel("Time (s)")
        plt.ylabel("Angle (deg)")
        plt.legend(["Bus 5600", "Bus 3300", "Bus 7000"])
        plt.grid()
        plt.savefig("Angle"+"_"+self.filename)

        plt.figure("PELEC")
        plt.plot(self.ch_data['time'], self.ch_data[2])  # See channel monitoring
        plt.plot(self.ch_data['time'], self.ch_data[6])
        plt.plot(self.ch_data['time'], self.ch_data[10])
        plt.xlabel("Time (s)")
        plt.ylabel("Pelec (p.u.)")
        plt.legend(["Bus 5600", "Bus 3300", "Bus 7000"])
        plt.grid()
        plt.savefig("Pelec"+"_"+self.filename)

        plt.figure("ETERM")
        plt.plot(self.ch_data['time'], self.ch_data[3])  # See channel monitoring
        plt.plot(self.ch_data['time'], self.ch_data[7])
        plt.plot(self.ch_data['time'], self.ch_data[11])
        plt.xlabel("Time (s)")
        plt.ylabel("Terminal voltage (p.u.)")
        plt.legend(["Bus 5600", "Bus 3300", "Bus 7000"])
        plt.grid()
        plt.savefig("Eterm"+"_"+self.filename)

        plt.figure("SPEED")
        plt.plot(self.ch_data['time'], self.ch_data[4])  # See channel monitoring
        plt.plot(self.ch_data['time'], self.ch_data[8])
        plt.plot(self.ch_data['time'], self.ch_data[12])
        plt.xlabel("Time (s)")
        plt.ylabel("Speed (p.u.)")
        plt.legend(["Bus 5600", "Bus 3300", "Bus 7000"])
        plt.grid()
        plt.savefig("Speed"+"_"+self.filename)

        plt.show()
    def add_fault(self,time, type, bus, extras):
        # Input param extras will be read differently depending on type
        # Example: time=0.1, type=1, bus=5600, extras=(6000) to trip branch connecting 5600 and 6000
        if type == 1 or 2 or 3:  # Load step
            self.events_overview.append((time,type,bus,extras))
        else:
            return "Faulty argument type given"

    # Private functions
    def _exec_fault(self,indices):  # Index of fault in events_overview
        # indices = indices of faults to execute (potentially multiple at once)
        # Remember for the run_dynamic_simulation to use np.unique to decide for each time
        for i in range(len(indices)):
            type_of_fault = self.events_overview[indices[i]][1]  # Type of fault at the specified index

            if type_of_fault == 1:  # Branch trip
                self._exec_branch_trip(indices[i])
            elif type_of_fault == 2:
                self._exec_load_step(indices[i])  # Load step
            elif type_of_fault == 3:
                self._exec_bus_trip(indices[i])  # Disconnect bus
            else:
                return "Undefined fault type"
    def _exec_branch_trip(self, index):
        # Function not yet tested
        time = self.events_overview[index][0]
        bus = self.events_overview[index][2]

        otherEnd = self.events_overview[index][3][0]
        branchStart = min(bus, otherEnd)
        branchEnd = max(bus, otherEnd)
        psspy.dist_branch_trip(branchStart, branchEnd, 1)  # Last integer assumes branch ID 1!!!!
    def _exec_bus_trip(self, index):
        # Function not yet tested
        bus_number = self.events_overview[index][2]
        psspy.dist_bus_trip(bus_number)
    def _exec_load_step(self, index):
        # Applies a step load (MW) at the specified time (in seconds)
        bus_number = self.events_overview[index][2]
        load_step = self.events_overview[index][3][0]  # Third index refers to list of 'extras' for the specific type of fault

        load_numbers = np.array(psspy.aloadint(-1,1,"NUMBER")[1][0])
        load_index = np.where(load_numbers == bus_number)[0]
        load_step = load_step / len(load_index)  # To split step over all loads at bus
        loadP = np.array(psspy.aloadcplx(-1, 1, "MVAACT")[1][0])
        present_load = loadP[load_index]
        for i in range(len(load_index)):  # CREATE FOR LOOP NOW TO ITERATE THROUGH AND STEP LOAD AT EACH LOAD AT BUS
            load_id = str(i + 1)
            psspy.load_chng_4(bus_number, load_id, [_i, _i, _i, _i, _i, _i], [present_load[i] + load_step, _f, _f, _f, _f, _f])
        # NB!! The present_load seems to take values from the Machines-tab
    def _find_unique_times(self):
        time = []
        for i in range(len(self.events_overview)):
            time.append(self.events_overview[i][0])
        time.sort()
        return np.array(time)
    def generate_ylabel(self, quantity="ANGLE"):
        return {  # Define dictionary
            # Machine quantities
            "ANGLE": "Angle (deg)",
            "PELEC": "Active power (p.u.)",
            "QELEC": "Reactive power (p.u.)",
            "ETERM": "Terminal voltage (p.u.)",
            "EFD": "UNDEFINED YLABEL",
            "PMECH": "Mechanical power (p.u.)",
            "SPEED": "Rotor speed (p.u.)",
            "XADIFD": "UNDEFINED YLABEL",
            "ECOMP": "UNDEFINED YLABEL",
            "VOTHSG": "UNDEFINED YLABEL",
            "VREF": "Reference voltage (p.u)",
            "VUELL": "UNDEFINED YLABEL",
            "VOEL": "UNDEFINED YLABEL",
            "GREF": "UNDEFINED YLABEL",
            "LCREF": "UNDEFINED YLABEL",
            "WVLCTY": "UNDEFINED YLABEL",
            "WTRBSP": "UNDEFINED YLABEL",
            "WPITCH": "UNDEFINED YLABEL",
            "WAEROT": "UNDEFINED YLABEL",
            "WROTRV": "UNDEFINED YLABEL",
            "WROTRI": "UNDEFINED YLABEL",
            "WPCMND": "UNDEFINED YLABEL",
            "WQCMND": "UNDEFINED YLABEL"

            # Bus quantities
        }[quantity]  # Return key quantity
    def generate_legend(self, indices):
        legend = []
        for i in range(len(indices)):
            legend.append("Bus " + str(int(self.machine_monitor[indices[i]][2])))

        return legend
    def redist_slack(self):
        # Use same methodology as described in setHvdcToMax
        # Continue until the excess slack is less than 1% of max slack generator capacity
        #
        pass