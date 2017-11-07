
#basicLossOfGeneratorsEditedAndFormatted.py

import os  # I use this to work with files
import matplotlib.pyplot as plt  # This is for plotting

import psspy  # Import the psse module
import dyntools  # Import the dynamic simulation module
import redirect  # Module for redirecting the PSS/E output to the terminal
from psse_models import load_models  # The load models

# Define default PSS/E variables
_i = psspy.getdefaultint()
_f = psspy.getdefaultreal()
_s = psspy.getdefaultchar()

# Redirect the PSS/E output to the terminal
redirect.psse2py()

psspy.throwPsseExceptions = True

# Files and folders
os.chdir("..") # Up one folder from cwd
cwd = os.getcwd()  # Get the current directory
modelsfolder = os.path.join(cwd, "Models and libraries")  # Name of the folder with the models
modelsfolder = os.path.join(modelsfolder,"N44 Baseline") # Name of folder with N44 baseline model


# Names of the case files
casefile = os.path.join(modelsfolder, "N44_BC.sav")
dyrfile = os.path.join(modelsfolder, "N44_BC.dyr")

# Name of the file where the dynamic simulation output is stored
outputfolder = os.path.join(cwd, "Output")
outputfile = os.path.join(outputfolder,"testRunOfRecordedCode")

# Start PSS/E
psspy.psseinit(10000) # 10 000 is requested bus size. Count of buses = 10 000?

# Initiation----------------------------------------------------------------------------------------------------------------------------------
psspy.case(casefile)  # Read in the power flow data
psspy.dyre_new([1, 1, 1, 1], dyrfile, "", "", "") # Read the dynamics data

# Establish which channels we wish to analyze in the output
#psspy.chsb(0,1,[-1,-1,-1,1,1,0]) # Channel 1 ANGLE, machine relative rotor angle (degrees)
#psspy.chsb(0,1,[-1,-1,-1,1,2,0]) # Channel 2 PELEC, machine electrical power (pu on SBASE).
#psspy.chsb(0,1,[-1,-1,-1,1,4,0]) # Channel 4 ETERM, machine terminal voltage (pu)
#psspy.chsb(0,1,[-1,-1,-1,1,12,0]) # Channel 12 BSFREQ, bus pu frequency deviations
#psspy.chsb(0,1,[-1,-1,-1,1,13,0]) # Channel 13 VOLT, bus pu voltages (complex)
#psspy.chsb(0,1,[-1,-1,-1,1,16,0]) # Channel 16 branch flow (P and Q)

# Convert the loads for dynamic simulation
psspy.cong(0)
psspy.conl(0, 1, 1, [0, 0], [50.0, 50.0, 0.0, 100.0]) # Convert loads, IZP-format 
psspy.conl(0, 1, 2, [0, 0], [50.0, 50.0, 0.0, 100.0])
psspy.conl(0, 1, 3, [0, 0], [50.0, 50.0, 0.0, 100.0])

# Set the time step for the dynamic simulation
psspy.dynamics_solution_params(realar=[_f, _f, 0.005, _f, _f, _f, _f, _f])

psspy.machine_array_channel([1, 2, 6000])  # Monitor Kvilldal Power
psspy.machine_array_channel([2, 7, 6000])  # Monitor Kvilldal Frequency

load = load_models.Load(6500)  # Create a load consisting of Trondheim

ierr = psspy.strt(outfile=outputfile)  # Tell PSS/E to write to the output file

# Simulation----------------------------------------------------------------------------------------------------------------------------------

if ierr == 0: # If output file can be opened??? CHECK THIS

    psspy.run(0, 0.1,1,1,0)

    psspy.machine_chng_2(5600,r"""1""",[0,_i,_i,_i,_i,_i],[ 261.115, 289.52,_f,_f,_f,_f,_f,_f,_f,_f,_f,_f,_f,_f,_f,_f,_f])
    psspy.machine_chng_2(5600,r"""2""",[0,_i,_i,_i,_i,_i],[ 261.115, 289.52,_f,_f,_f,_f,_f,_f,_f,_f,_f,_f,_f,_f,_f,_f,_f])
	
    psspy.run(0, 0.3,1,1,0)
	
    #psspy.machine_chng_2(5600,r"""3""",[0,_i,_i,_i,_i,_i],[ 278.17, 473.175,_f,_f,_f,_f,_f,_f,_f,_f,_f,_f,_f,_f,_f,_f,_f])
    #psspy.machine_chng_2(5600,r"""1""",[1,_i,_i,_i,_i,_i],[_f,_f,_f,_f,_f,_f,_f,_f,_f,_f,_f,_f,_f,_f,_f,_f,_f])
    #psspy.machine_chng_2(5600,r"""2""",[1,_i,_i,_i,_i,_i],[_f,_f,_f,_f,_f,_f,_f,_f,_f,_f,_f,_f,_f,_f,_f,_f,_f])
    #psspy.machine_chng_2(5600,r"""3""",[1,_i,_i,_i,_i,_i],[_f,_f,_f,_f,_f,_f,_f,_f,_f,_f,_f,_f,_f,_f,_f,_f,_f])
    #psspy.run(0, 1.0,1,1,0)


else:
        print(ierr)

# Read the putput file
chnf = dyntools.CHNF(outputfile)
# assign the data to variables
sh_ttl, ch_id, ch_data = chnf.get_data()

# Do the plotting
plt.figure(1)
plt.plot(ch_data['time'], ch_data[1])  # Kvilldal Power

plt.figure(2)
plt.plot(ch_data['time'], ch_data[2])  # Kvilldal frequency

plt.show()


