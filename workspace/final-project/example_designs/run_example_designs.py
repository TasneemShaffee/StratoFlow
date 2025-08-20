from typing import Optional
import os
import json
import threading
import pytimeloop.timeloopfe.v4 as tl
from util_functions import *
from scheduler_handler import *
from simulation_framework_handler import *
from adversarial_analysis_handler import *
import joblib
from joblib import Parallel, delayed
import yaml
import re
import csv    
layers_stats = {}
Specification = tl.Specification
THIS_SCRIPT_DIR = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
EXAMPLE_DIR = os.path.join(THIS_SCRIPT_DIR, "example_designs")
TOP_JINJA_PATH = os.path.join(EXAMPLE_DIR, "top.yaml.jinja2")
DEPENDENCY_DIR = os.path.join(THIS_SCRIPT_DIR, "dependencies")
MTL_DIR=os.path.join(THIS_SCRIPT_DIR, "layer_shapes","MTL")


def get_architecture_targets():
    targets = []
    for root, dirs, files in os.walk(EXAMPLE_DIR):
        if "arch.yaml" in files:
            c = open(os.path.join(root, "arch.yaml")).read()
            if "version: 0.4" not in c:
                continue
            targets.append(os.path.relpath(root, EXAMPLE_DIR))
    return sorted(targets)


def run_mapper(
    arch_target,
    problem: Optional[str] = None,
    generate_ref_outputs: Optional[bool] = False,
    remove_sparse_opts: Optional[bool] = False,
    task_count: Optional[int]=1,
    task_id: Optional[int]=1
):
    # This data will be supplied when rendering the top jinja2 template
    jinja_parse_data = {"architecture": arch_target}
    local_layer_stat={}

    if problem is None:
        problem_name = "default_problem"
    else:
        problem_name = os.path.basename(problem).split(".")[0]
        jinja_parse_data["problem"] = problem
    print("problem_name ",problem_name)
    # Set up output directory
    if generate_ref_outputs:
        output_dir = f"{EXAMPLE_DIR}/{arch_target}/ref_outputs/{problem_name}"
    else:
        output_dir = f"{EXAMPLE_DIR}/{arch_target}/outputs/{problem_name}"

    print(f"\n\nRunning mapper for target {arch_target} in {output_dir}...")

    # Set up output directory
    if os.path.exists(output_dir):
        os.system(f"rm -rf {output_dir}")
    os.makedirs(output_dir, exist_ok=True)

    spec = tl.Specification.from_yaml_files(
        TOP_JINJA_PATH, jinja_parse_data=jinja_parse_data
    )

    # Used for some Sparseloop tutorials to test with/without sparse optimizations
    if remove_sparse_opts:
        remove_sparse_optimizations(spec)
    

    result=tl.call_mapper(
        spec,
        output_dir=output_dir,
        dump_intermediate_to=output_dir,
    )
 
    local_layer_stat['latency']=vars(result).get('latency')
    local_layer_stat['energy']=vars(result).get('energy')
    local_layer_stat['area']=vars(result).get('area')
        
    #print(f"==== latency: {latency}, energy: {energy}, area: {area} ========")
    serializable_stats = {k: make_serializable(v) for k, v in vars(result).items()}
    json_path = os.path.join(output_dir, f"timeloop_stats.json")
    with open(json_path, "w") as f:
        json.dump(serializable_stats, f, indent=2)

    assert os.path.exists(f"{output_dir}/timeloop-mapper.stats.txt"), (
        f"Mapper did not generate expected output for {arch_target}. "
        f"Please check the logs for more details."
    )
    stat_txt_path=f"{output_dir}/timeloop-mapper.stats.txt"
    
    #if task_count>1:
    #    problem_name=f"{problem_name}_t{task_id}"
    dram_dict=parse_dram_stats(stat_txt_path,problem_name=problem_name)
    local_layer_stat['dram_stat']=dram_dict
    #finish_t, wait_t=get_stat(f"{output_dir}/timeloop-mapper.stats.txt",problem_name)
    return local_layer_stat, problem_name
    
def get_layer_description(yaml_path):
    with open(yaml_path) as f:
        content = f.read()
    
    cleaned = re.sub(r'\{\{.*?\}\}', '', content)        
    cleaned = re.sub(r'<<<:.*', '', cleaned)            
    data = yaml.safe_load(cleaned)
    instance = data.get('problem', {}).get('instance', {})
    return instance


  


def sim(results,deps,slice_of,layers):
    layer_stats = {}
    for stats_dict, layer_name in results:
       
        layer_stats[layer_name] = stats_dict

    stats, t_exec=prepare_timeloop_stat_per_layer(layers,layer_stats)
    print(f"*** stats {stats}, t_exec {t_exec}")
    finish, wait = get_layers_stat(layers, stats, t_exec, deps, slice_of)
    end_to_end_latency = max(finish.values())
    total_energy       = sum(layer_stats[L]['energy'] for L in layers)
    #max_area = max(layer_stats[L]['area'] for L in layers)
    max_os = max(layer_stats[L]['area'] for L, flow in slice_of.items() if flow == 'os')
    max_ws = max(layer_stats[L]['area'] for L, flow in slice_of.items() if flow == 'ws')
    max_area = max_os + max_ws
    print(f"max_os {max_os}")
    print(f"max_ws {max_ws}")
    #print("Topological layer order:", layers)
    print("Per-layer finish times:", finish)
    print(f"End-to-end latency: {end_to_end_latency:.6f} sec")
    print(f"Total energy:       {total_energy:.6f} J")
    print(f"Max area:           {max_area:.6f} mm²") 
    #print(f"Max OS area:           {max_os:.6f} mm²") 
    rows = [
    ["end_to_end_latency", "total_energy", "max_area", "os area", "ws area"],
    [end_to_end_latency,   total_energy,     max_area, max_os,max_ws]
    ]

    csv_path = "results.csv"
    full_path=os.path.join(THIS_SCRIPT_DIR,csv_path)
    with open(full_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    #print("stat ",stats)
    #print("result_dict ",layer_stats)
    
def MTL_preparation(encoder_threshold):
    mtl_encoder_list=[]
    decoder_1_list=[]
    decoder_2_list=[]
    for entry in os.listdir(MTL_DIR):
        path = os.path.join(MTL_DIR, entry)
        if os.path.isfile(path):
            layer_name= os.path.basename(path).split(".")[0]
            if int(layer_name)<=encoder_threshold:
                mtl_encoder_list.append(path)
            else:
                decoder_1_list.append(path)
                decoder_2_list.append(path)
    return  mtl_encoder_list,  decoder_1_list,  decoder_2_list             
    
if __name__ == "__main__":
    slice_of={}
    args = get_arguments()
    arch_targets = get_architecture_targets()
    #encoder_threshold= 13
    template_path=""
    arch_src_dir=""
    out_dir=""
    mapping = {
      'os': 'layer_output_stationary',
      'ws': 'layer_weight_stationary'
        }
    pes={
      'os': {
       'meshX':1 ,
       'meshY': 128
      },
      'ws': {
       'meshX':1 ,
       'meshY': 128
      }
        }
    os_path=os.path.join(EXAMPLE_DIR,mapping['os'],'arch.yaml')
    ws_path=os.path.join(EXAMPLE_DIR,mapping['ws'],'arch.yaml')
    if args.clear_outputs:
        os.system(f"rm -rf {EXAMPLE_DIR}/*/outputs")
        os.system(f"rm -rf {EXAMPLE_DIR}/*/ref_outputs")
        os.system(f"rm -rf {EXAMPLE_DIR}/*/*/outputs")
        os.system(f"rm -rf {EXAMPLE_DIR}/*/*/ref_outputs")
        exit(0)

    arch = args.architecture
    dep_file_name= args.dependency_file #"mtl.yaml"
    
    archi_path=os.path.join(DEPENDENCY_DIR, dep_file_name)
    deps=parse_dependency(archi_path) 

    if arch is None or not arch:
        arch = arch_targets[0]
   
    if str(arch).lower() == "all":
        arch = arch_targets

    arch = [arch] if isinstance(arch, str) else arch

    # Put togher the list of problems to run
    problems = [None]
    if args.MTL_on:
        print("MTL is ",args.MTL_on)
        #mtl_encoder_lst,decoder_1_lst,decoder_2_lst=MTL_preparation(encoder_threshold)
        encoder_sorted, dec_sorted=split_and_sort_layers_generic(deps)
        #print(f"mtl_encoder_lst {mtl_encoder_lst}, decoder_1_lst {decoder_1_lst}, decoder_2_lst {decoder_2_lst}")
        #print("encoder_sorted ",encoder_sorted)
        #print("dec_sorted ",dec_sorted)
        seq= interleave_decoders_zigzag(encoder_sorted, dec_sorted)
        #print("*********seq  zigzag ",seq)
    else:
        seq = topo_sort(deps)

            
        
    
    if args.problem:
        problem = os.path.join(THIS_SCRIPT_DIR, "layer_shapes", args.problem)
        if os.path.isdir(problem):
            problems = [os.path.join(problem, f) for f in os.listdir(problem)]
        else:
            problems = [problem]

    # i = get_layer_description(problems[0])
    
    # Run parallel processes for all architectures and problems
    new_arch=[]
    layers_instances={}
   
    for p in problems:
           
            if not p.endswith('.yaml') and not p.endswith('.json'):
                continue
            layer_dict = get_layer_description(p)
           
            problem_name = os.path.basename(p).split(".")[0]
            
            layers_instances[(problem_name)]=layer_dict
            
    if args.single_task_count > 1:
       
            deps, layers_instances =replicate_workload(deps, layers_instances, args.single_task_count)
            original_seq=  seq  
            seq = topo_sort(deps)
        
   
    if args.Adv_on:
        if args.adv_layer== "hammer":
            sync_layers=insert_every_compatible(
            seq, deps, layers_instances,
            compat_fn=hb_compatible,
            param_fn=hb_params,
            prefix="Hammer",
            count=args.count    
            )
        elif args.adv_layer=="bn":
            sync_layers=insert_every_compatible(
            seq, deps, layers_instances,
            compat_fn=bn_compatible,
            param_fn=bn_params,
            prefix="BN",
            count=args.count    
            )
        else:   
            sync_layers=insert_every_compatible(
            seq, deps, layers_instances,
            compat_fn=sm_compatible,
            param_fn=sm_params,
            prefix="Softmax",
            count=args.count )
        
        #print("sync_layers ",sync_layers)
        template_path=os.path.join(THIS_SCRIPT_DIR, "templates","template.yaml")
        arch_src_dir=problem
        out_dir=os.path.join(THIS_SCRIPT_DIR, "layer_shapes","Adv_layers")
        
        make_new_architecture(template_path,layers_instances,arch_src_dir,out_dir,sync_layers)


        problems = [os.path.join(out_dir, f) for f in os.listdir(out_dir)]
    print("problems ",problems)
    if args.single_task_count > 1:
         dst= os.path.join(THIS_SCRIPT_DIR, "layer_shapes", f'{args.problem}_{args.single_task_count}')
         copy_and_rename_files(problem, dst, task_count=args.single_task_count)
         problems = [os.path.join(dst, f'{f}.yaml') for f in seq]
         print("problems ",problems)
    assignment=schedule_topo(seq, deps, layers_instances,os_path, ws_path,pes)
    print("assignment of dataflow to each layer: ",assignment)
    for layer_id, flow in assignment.items():
        slice_of[layer_id]=flow
        new_arch.append(mapping[flow])
  
    if args.HDA:
        print("Support HDA")
        pairs = zip(new_arch, problems)
        print("pairs ",pairs)
    else:
        print("simple architecture without HDA")
        pairs = ((a, p) for p in problems for a in arch)
    
    print("problems ",problems)
    results=joblib.Parallel(n_jobs=args.n_jobs)(
        joblib.delayed(run_mapper)(
            a, p, args.generate_ref_outputs, args.remove_sparse_opts
        )
      
        for a, p in pairs
      
    )
 
    sim(results,deps,slice_of,seq)
