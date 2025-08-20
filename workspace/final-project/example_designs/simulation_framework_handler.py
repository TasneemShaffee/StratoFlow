from collections import defaultdict
import yaml
def parse_dependency(architecture_path):
    with open(architecture_path) as f:
        deps = yaml.safe_load(f)
      

    layer_parents = {str(layer): list(map(str, info["parents"])) for layer, info in deps.items()}
    return layer_parents


def parse_onnx(path):
    import onnx
    model = onnx.load(path)
    graph = model.graph
    for node in graph.node:
        print(f"Node: {node.name or node.op_type}")
        print("  inputs: ", node.input)
        print("  outputs:", node.output)


def topo_sort(deps):
    # deps: dict[layer] -> list of parent layers
    
    indegree = { n: len(parents) for n, parents in deps.items() }
   
    queue = [n for n, d in indegree.items() if d == 0]
    order = []
  
    while queue:
        u = queue.pop(0)
        order.append(u)
        for v, parents in deps.items():
            if u in parents:
                indegree[v] -= 1
                if indegree[v] == 0:
                    queue.append(v)
   
    if len(order) != len(deps):
        raise ValueError("Cycle detected")
    return order

def calculate_comm_time_all_mem_levels(stats):
    t_comm = {}
    for lvl, e in stats.items():
        accesses = e.get('accesses', 0)
        bits     = e.get('word_bits', 0)
        bw       = e.get('read_bw_Bps', 0.0)
        if bw > 0:
            # bytes to move = accesses * bits/8
            t_comm[lvl] = (accesses * bits / 8.0) / bw
        else:
            t_comm[lvl] = 0.0

    total_comm_time = sum(t_comm.values())
    return t_comm, total_comm_time  
def calculate_comm_time_dram_levels(dram_stats):
    return   (dram_stats['accesses'] * dram_stats['word_bits'] / 8.0) / dram_stats['read_bw_Bps']
def prepare_timeloop_stat_per_layer(layers,raw_stats):
    stats  = {}
    t_exec = {}
    print("raw_stats: ",raw_stats )
    for L in layers:
        entry = raw_stats[L]
      
        t_exec[L] = entry['latency']
        
        ds   = entry['dram_stat']
        bw   = ds['read_bw_Bps']                           
        x_b  = (ds['accesses'] * (ds['word_bits'] / 8.0))     
        stats[L] = {
        'x_bytes': x_b,
        'BW_bytes_per_cycle': bw  
         }
        print(f"****** Layer :{L}, latency {t_exec[L]}, ds {ds}, bw {bw}, stats[L] {stats[L]}")
    return stats, t_exec

    
def get_layers_stat(layers,
                       #accesses,    # dict: layer -> total scalar accesses (words)
                       #word_bits,   # dict: layer -> bits per word
                       #BW,          # dict: layer -> bandwidth in bytes/sec
                       stats,       # dict: layer--> bits per word, total scalar accesses (words), bandwidth in bytes/sec
                       t_exec,      # dict: layer -> execution time (sec)
                       deps,        # dict: layer -> list of predecessor layers
                       slice_of,    # fn or dict: layer -> slice identifier
                       ):

    finish    = {}
    wait      = {}
    free_time = defaultdict(float) 
    for l in layers:
  
        parents=deps[l]
        dram_t_comm=stats[l]['x_bytes']/stats[l]['BW_bytes_per_cycle'] 
        parent_fin  = max((finish[p] for p in parents), default=0.0)
     
        ready = parent_fin + dram_t_comm #max( (finish[p] + dram_t_comm for p in parents),default=0.0)
       
        
        sl = slice_of[l]
     
        start = max(ready, free_time[sl])
      

  
        finish[l] = start + t_exec[l]
       

      
        free_time[sl] = finish[l]
      

        #wait[l] = start - ready
        wait[l]    = start - parent_fin
        print(f"Layer {l}, dram_t_comm: {dram_t_comm}, ready_t: {ready}, dataflow: {sl}, start_t: {start}, execution_t: {t_exec[l]}, finish_t: {finish[l]}, free_t: {free_time[sl]}, wait_t: {wait[l]}  ") 
    return finish, wait