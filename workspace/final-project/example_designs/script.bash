#!/bin/bash

python3 run_example_designs.py --architecture simple_output_stationary --problem mtl --remove-sparse-opts --generate-ref-outputs --dependency_file mtl.yaml

#python3 run_example_designs.py --architecture simple_output_stationary --problem Single_Task --remove-sparse-opts --generate-ref-outputs --dependency_file single_task.yaml --clear-outputs


#python3 run_example_designs.py --architecture simple_output_stationary --problem alexnet --remove-sparse-opts --generate-ref-outputs --dependency_file alexnet.yaml 

#python3 run_example_designs.py --architecture simple_output_stationary --problem alexnet --remove-sparse-opts --generate-ref-outputs --dependency_file alexnet.yaml --Adv_on --adv_layer bn  --count 2

#python3 run_example_designs.py --architecture all --problem mtl --remove-sparse-opts --MTL_on --HDA 

#run_example_designs.py --architecture all --problem mtl --remove-sparse-opts --MTL_on --clear-outputs

#--generate-ref-outputs
#run in root 
#find . -type d -name ".ipynb_checkpoints" -exec rm -rf {} +
#find /home/workspace/final-project -name '.DS_Store' -type f -delete