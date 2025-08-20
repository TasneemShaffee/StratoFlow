import yaml
import re
from copy import deepcopy
def parse_pe_container(yaml_file_path):

    with open(yaml_file_path) as f:
        arch = yaml.safe_load(f)

  
    for container in arch:
        if container.get("name") == "PE":
            pe = container
            break
    else:
        raise ValueError("PE container not found in YAML")

   
    mesh_x = pe["spatial"]["meshX"]
    mesh_y = pe["spatial"]["meshY"]

  
    spatial_constraints = pe["constraints"]["spatial"]
    permutation = spatial_constraints["permutation"]
    split = spatial_constraints["split"]

  
    raw_factors = spatial_constraints["factors"]  
    factors = {}
    for item in raw_factors:
        key, val = item.split("=")
        factors[key] = int(val)

    return {
        "mesh_x": mesh_x,
        "mesh_y": mesh_y,
        "permutation": permutation,
        "split": split,
        "factors": factors
    }
class TLLoader(yaml.SafeLoader):
    pass


def _noop_multi(loader, tag_suffix, node):
    return loader.construct_mapping(node)
TLLoader.add_multi_constructor('!', _noop_multi)

def parse_pe_mesh(yaml_file_path):

    with open(yaml_file_path) as f:
        #arch = yaml.safe_load(f)
        arch = yaml.load(f, Loader=TLLoader)

    for container in arch:
        #print("container ",container)
        if container.get("name") == "PE":
            pe = container
            break
    else:
        raise ValueError("PE container not found in YAML")
 
    mesh_x = pe["spatial"]["meshX"]
    mesh_y = pe["spatial"]["meshY"]
    return mesh_x, mesh_y

def is_exist(param,param_dict):
    return (param in param_dict)
    
def choose_dataflow(layer):
    M, C, H, W, R, S = (layer[k] for k in ("M", "C", "H", "W", "R", "S"))

    def util(size, mesh_dim):
        return min(size, mesh_dim) / mesh_dim

    occ_os = util(M, mesh_x) * util(C, mesh_y)
    occ_ws = util(M, mesh_x) * util(C, mesh_y)

    if R == 1 and S == 1:
        return "os" if occ_os >= occ_ws else "ws"

    if abs(occ_os - occ_ws) > 0.05:         
        return "os" if occ_os > occ_ws else "ws"
    else:
        return "ws" if (M >= 256 and R * S <= 9) else "os"



def dataflow_assignment(paramaters_dict):
    if len(paramaters_dict)==2:
          return "os"
    elif (is_exist("R",paramaters_dict) and paramaters_dict["R"]==1) and  (is_exist("S",paramaters_dict) and paramaters_dict["S"]==1):
          return "ws"
    elif (is_exist("M",paramaters_dict) and paramaters_dict["M"]>= 256) and \
    (is_exist("R",paramaters_dict) and is_exist("S",paramaters_dict) and (paramaters_dict["S"]*paramaters_dict["R"])<=9): 
           return "ws"
    else:  return "os"

def split_and_sort_layers_generic(parents):
    encoder = []
    decoder_map = {}
    
    for layer in parents:
        
        m = re.match(r'^dec_(\d+)_(\d+)$', layer)
      
        if m:
            task_id = int(m.group(1))
            layer_idx = int(m.group(2))
            decoder_map.setdefault(task_id, []).append((layer_idx, layer))
            
        else:
          
            try:
                idx = int(layer)
            except ValueError:
            
                idx = float('inf')
            encoder.append((idx, layer))
    
   
    encoder_sorted = [layer for _, layer in sorted(encoder, key=lambda x: x[0])]
    
   
    dec_sorted = {}
    for task_id, lst in decoder_map.items():
        dec_sorted[task_id] = [layer for _, layer in sorted(lst, key=lambda x: x[0])]
    
    return encoder_sorted, dec_sorted


def interleave_decoders_generic(encoder, dec_sorted, start_task_id=None):
 
    seq = encoder.copy()
    task_ids = sorted(dec_sorted.keys())
    #print("task_ids ",task_ids)
    if not task_ids:
        return seq

  
    if start_task_id is None:
        start_task_id = task_ids[0]
    if start_task_id not in task_ids:
        raise ValueError(f"start_task_id {start_task_id} not in decoder tasks {task_ids}")

    idx = task_ids.index(start_task_id)
    ordered_tasks = task_ids[idx:] + task_ids[:idx]

   
    max_len = max(len(dec_sorted[t]) for t in ordered_tasks)

    
    for i in range(max_len):
        for tid in ordered_tasks:
            layers = dec_sorted[tid]
            if i < len(layers):
                seq.append(layers[i])

    return seq   

def interleave_decoders_zigzag(encoder, dec_sorted):
    seq = encoder.copy()
    task_ids = sorted(dec_sorted.keys()) 
    max_len  = max(len(dec_sorted[t]) for t in task_ids)
    for i in range(max_len):
        if i % 2 == 0:
            order = task_ids
        else:
            order = list(reversed(task_ids))

        for tid in order:
            layers = dec_sorted[tid]
            if i < len(layers):
                seq.append(layers[i])

    return seq

def replicate_workload(deps, layers_instances, K):
    combined_deps = {}
    combined_layers = {}
    pipelines = []
    
    for task_idx in range(K):
        suffix = f"_t{task_idx}"
       
        this_deps = {}
        for layer, parents in deps.items():
            new_layer   = layer + suffix
            new_parents = [p + suffix for p in parents]
            this_deps[new_layer] = new_parents
            combined_layers[new_layer] = deepcopy(layers_instances[layer])
        
     
        combined_deps.update(this_deps)

        #pipeline = topo_sort(this_deps)
        #pipelines.append(pipeline)

    return combined_deps, combined_layers #, pipelines
def interleave_pipelines(pipelines,num_tasks):
    
 
    seq = []
    max_len = max(len(p) for p in pipelines)
    
    for i in range(max_len):
        order = list(range(num_tasks)) if (i % 2 == 0) else list(reversed(range(num_tasks)))
        for t in order:
            if i < len(pipelines[t]):
                seq.append(pipelines[t][i])
    return seq    
def compute_macs(params):
    macs = 1
    for v in params.values():
        macs *= v
    return macs
def get_active_pes(instances,yaml_file_path,pes_per_dataflow):
    #mesh_x,mesh_y=parse_pe_mesh(yaml_file_path)
    mesh_x=pes_per_dataflow['meshX']
    mesh_y=pes_per_dataflow['meshY']
    active_pes = min(instances['C'], mesh_x) * min(instances['M'], mesh_y)
    if active_pes == 0:
        active_pes = 1 
    return active_pes    
    


def schedule_topo(topo_layers, parents, layers_instances, path_os, path_ws,pes):
    finish_time  = {"os": 0.0, "ws": 0.0}
    finish_layer = {}       
    assignment   = {}

    for lid in topo_layers:
      
        assert all(p in finish_layer for p in parents[lid])
        if parents[lid]:
            ready_time = max(finish_layer[p] for p in parents[lid])
        else:
            ready_time = 0.0

        #print("layers_instances[lid] ",lid)
        pref  = dataflow_assignment(layers_instances[lid])     
        other = "ws" if pref == "os" else "os"

        path_pref= path_os if pref == "os" else path_ws
        path_other= path_os if other == "os" else path_ws
        
        macs       = compute_macs(layers_instances[lid])
        dur_pref   = macs / get_active_pes(layers_instances[lid], path_pref,pes[pref])
        dur_other  = macs / get_active_pes(layers_instances[lid], path_other,pes[other])


        start_pref  = max(finish_time[pref],  ready_time)
        start_other = max(finish_time[other], ready_time)

        ft_pref  = start_pref  + dur_pref
        ft_other = start_other + dur_other


        if ft_pref <= ft_other:
            chosen, finish = pref,  ft_pref
        else:
            chosen, finish = other, ft_other


        assignment[lid]        = chosen
        finish_time[chosen]    = finish
        finish_layer[lid]      = finish

    return assignment



    