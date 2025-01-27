import argparse
import sys
import os
sys.path.append('_model')
#sys.path.append('_init')
#from environment import *
## Parameters

### Parsing arguments
parser = argparse.ArgumentParser()

parser.add_argument('--case', help='Reinforcement learning case considered. Choose one from the following list: "1", or "4"', type=str, default='4')
parser.add_argument('--rewardtype', help='Reward type [k1,k2,k3,log,] ', type=str, default='k1')
parser.add_argument('--statetype', help='State type [enstrophy,energy,psidiag,psiomegadiag,] ', type=str, default='psiomegadiag')
parser.add_argument('--actiontype', help='Action type [CS,CL,CLxyt,nuxyt,] ', type=str, default='CL')
parser.add_argument('--NLES', help='', type=int, default=128)
parser.add_argument('--gensize', help='', type=int, default=10)
parser.add_argument('--solver', help='training/postprocess ', type=str, default='training')
parser.add_argument('--runstrpost', help='Smag,', type=str, default='nosgs,leith,smag, ')

args = vars(parser.parse_args())

NLES = args['NLES']
casestr = '_C'+args['case']+'_N'+str(NLES)+'_R_'+args['rewardtype']+'_State_'+args['statetype']+'_Action_'+args['actiontype']

print(args)
print ('case:', casestr)

# Case selection
if args['case']=='1':
    sys.path.append('_init/Re20kf4')
elif args['case']=='4':
    sys.path.append('_init/Re20kf25')

# State type
if args['statetype'] == 'enstrophy' or args['statetype'] == 'energy':
    state_size = int(NLES/2)#+1
elif args['statetype'] == 'psiomegadiag':
    state_size = int(NLES*2)

# Type of the action
if args['actiontype'] == 'CL':
    action_size=1
elif args['actiontype'] == 'CS':
    action_size=1
else:
    action_size=8**2
print('Action size is:', action_size)
### Defining Korali Problem
import korali
k = korali.Engine()
e = korali.Experiment()

### Defining results folder and loading previous results, if any
resultFolder = '_result_vracer'+casestr+'/'
found = e.loadState(resultFolder + '/latest')
if found == True:
	print("[Korali] Continuing execution from previous run...\n");

# Mode settings
if args['solver']=='training':
    print('Enviroment loaded')
    from environment import *
else:
    print('Postprocess enviroment loaded')
    from environmentpost import environmentpost as environment
    args['runFolder'] = resultFolder+args['runstrpost']+'/'
    os.makedirs(args['runFolder'], exist_ok = True)
    print(args['runFolder'])

### Defining Problem Configuration
e["Problem"]["Type"] = "Reinforcement Learning / Continuous"
e["Problem"]["Environment Function"] = lambda x : environment( args, x )
e["Problem"]["Agents Per Environment"] = 1

### Defining Agent Configuration 
e["Solver"]["Type"] = "Agent / Continuous / VRACER"
e["Solver"]["Mode"] = "Training"
e["Solver"]["Episodes Per Generation"] = args['gensize'] #--> 10, 25, 50
e["Solver"]["Experiences Between Policy Updates"] = 1
e["Solver"]["Learning Rate"] = 0.0001
e["Solver"]["Discount Factor"] = 0.995
e["Solver"]["Mini Batch"]["Size"] = 256

### Defining Variables
# States
for i in range(state_size):
	e["Variables"][i]["Name"] = "Sensor " + str(i)
	e["Variables"][i]["Type"] = "State"

# Actions
for i in range(action_size): # size of action 
	e["Variables"][state_size+i]["Name"] = "Actuator " + str(i)
	e["Variables"][state_size+i]["Type"] = "Action"
	e["Variables"][state_size+i]["Lower Bound"] = -0.5**3
	e["Variables"][state_size+i]["Upper Bound"] = 0.5**3
	e["Variables"][state_size+i]["Initial Exploration Noise"] = 0.3**3 #0.15**3

### Setting Experience Replay and REFER settings
e["Solver"]["Experience Replay"]["Off Policy"]["Annealing Rate"] = 5.0e-8
e["Solver"]["Experience Replay"]["Off Policy"]["Cutoff Scale"] = 5.0
e["Solver"]["Experience Replay"]["Off Policy"]["REFER Beta"] = 0.3
e["Solver"]["Experience Replay"]["Off Policy"]["Target"] = 0.1
e["Solver"]["Experience Replay"]["Start Size"] = 10000
e["Solver"]["Experience Replay"]["Maximum Size"] = 100000

e["Solver"]["Policy"]["Distribution"] = "Squashed Normal"
e["Solver"]["State Rescaling"]["Enabled"] = True
e["Solver"]["Reward"]["Rescaling"]["Enabled"] = True
e["Solver"]["Reward"]["Outbound Penalization"]["Enabled"] = True
e["Solver"]["Reward"]["Outbound Penalization"]["Factor"] = 0.5
  
### Configuring the neural network and its hidden layers
e["Solver"]["Neural Network"]["Engine"] = "OneDNN"
e["Solver"]['Neural Network']['Optimizer'] = "Adam"
e["Solver"]["L2 Regularization"]["Enabled"] = True
e["Solver"]["L2 Regularization"]["Importance"] = 1.0

e["Solver"]["Neural Network"]["Hidden Layers"][0]["Type"] = "Layer/Linear"
e["Solver"]["Neural Network"]["Hidden Layers"][0]["Output Channels"] = 128

e["Solver"]["Neural Network"]["Hidden Layers"][1]["Type"] = "Layer/Activation"
e["Solver"]["Neural Network"]["Hidden Layers"][1]["Function"] = "Elementwise/Tanh"

e["Solver"]["Neural Network"]["Hidden Layers"][2]["Type"] = "Layer/Linear"
e["Solver"]["Neural Network"]["Hidden Layers"][2]["Output Channels"] = 128

e["Solver"]["Neural Network"]["Hidden Layers"][3]["Type"] = "Layer/Activation"
e["Solver"]["Neural Network"]["Hidden Layers"][3]["Function"] = "Elementwise/Tanh"

### Setting file output configuration
e["Solver"]["Termination Criteria"]["Max Experiences"] = 10e6
e["Solver"]["Termination Criteria"]["Max Generations"] = 51
e["Solver"]["Experience Replay"]["Serialize"] = True
e["Console Output"]["Verbosity"] = "Detailed"
e["File Output"]["Enabled"] = True
e["File Output"]["Frequency"] = 1
e["File Output"]["Path"] = resultFolder

### Over ride the settings for post process
#if args['solver'] == 'postprocess':
#    print('Generation ........... ')
#    e["Solver"]["Episodes Per Generation"] = 1
#    e["Solver"]["Mode"] = "Training" #"Training / Testing"

### Running Experiment
print("Running the experiment ---- ")
k.run(e)

### Checking if we reached a minimum performance

bestReward = e["Solver"]["Training"]["Best Reward"]
if (bestReward < 1000.0):
 print("Flow Control example did not reach minimum training performance.")
 exit(-1)
