import argparse
import pytimeloop.timeloopfe.v4 as tl
import re
from typing import List, Optional
import os
import shutil
def get_arguments():
    argparser = argparse.ArgumentParser()
    argparser.add_argument(
        "--clear-outputs",
        default=False,
        action="store_true",
        help="Clear all generated outputs",
    )
    argparser.add_argument(
        "--MTL_on",
        default=False,
        action="store_true",
        help="Support MTL",
    )
    argparser.add_argument(
        "--Adv_on",
        default=False,
        action="store_true",
        help="Support Adversarial analysis.",
    )
    argparser.add_argument(
        "--adv_layer",
        type=str,
        default="softmax",
        help="Type of irregular layer to be inserted in the given architecture for stress analysis.",
    )
    argparser.add_argument(
        "--count",
        type=int,
        default=1,
        help="Number of irregular layers to be inserted in the given architecture for stress analysis.",
    )
    argparser.add_argument(
        "--single_task_count",
        type=int,
        default=1,
        help="Number of single tasks to be supported.",
    )    
    argparser.add_argument(
        "--HDA",
        default=False,
        action="store_true",
        help="Support HDA.",
    )
    argparser.add_argument(
        "--architecture",
        type=str,
        default="eyeriss_like",
        help="Architecture to run in the example_designs directory. "
        "If 'all' is given, all architectures will be run.",
    )
    argparser.add_argument(
        "--generate-ref-outputs",
        default=False,
        action="store_true",
        help="Generate reference outputs instead of outputs",
    )
    argparser.add_argument(
        "--problem",
        type=str,
        default=None,
        help="Problem to run in the layer_shapes directory. If a directory is "
        "specified, all problems in the directory will be run. If not specified, "
        "the default problem will be run.",
    )
    argparser.add_argument(
        "--dependency_file",
        type=str,
        default=None,
        help="File that contains the graph of layers' dependency per architecture.",
    )
    argparser.add_argument(
        "--n_jobs", type=int, default=16, help="Number of jobs to run in parallel"
    )
    argparser.add_argument(
        "--remove-sparse-opts",
        default=False,
        action="store_true",
        help="Remove sparse optimizations",
    )
    return argparser.parse_args()


def remove_sparse_optimizations(spec: tl.Specification):
    """This function is used by some Sparseloop tutorials to test with/without
    sparse optimizations"""
    for s in spec.get_nodes_of_type(
        (
            tl.sparse_optimizations.ActionOptimizationList,
            tl.sparse_optimizations.RepresentationFormat,
            tl.sparse_optimizations.ComputeOptimization,
        )
    ):
        s.clear()
    return spec

def make_serializable(obj):
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    elif isinstance(obj, dict):
        return {k: make_serializable(v) for k, v in obj.items()}
    elif hasattr(obj, "__dict__"):
        return make_serializable(vars(obj))
    else:
        return obj    

def get_stat(path,problem_name):
    with open(path) as f:
        txt = f.read()
    pattern = re.compile(r"Total scalar accesses\s*:\s*([\d\.e\+]+)")
    matches = map(float, pattern.findall(txt))
    total_accesses = sum(matches)
    print(f"Total scalar accesses across all levels:{total_accesses} in problem: {problem_name}")


def parse_timeloop_stats(stat_txt_path, freq_hz=1e9):
    text = open(stat_txt_path).read()
    stats = {}

    
    parts = re.split(r"===\s*(.+?)\s*===", text)
    
    for i in range(1, len(parts), 2):
        level = parts[i].strip()
        block = parts[i+1]

        entry = {}
        m_bits = re.search(r"Word bits\s*:\s*(\d+)", block)
        if m_bits:
            entry["word_bits"] = int(m_bits.group(1))
        else:
            entry["word_bits"] = None

        m_acc = re.search(r"Total scalar accesses\s*:\s*([\d\.eE\+\-]+)", block)
        if m_acc:
            entry["accesses"] = int(float(m_acc.group(1)))
        else:
            entry["accesses"] = None


        m_r = re.search(r"Read bandwidth \(total\)\s*:\s*([\d\.]+)\s*words/cycle", block)
        m_w = re.search(r"Write bandwidth \(total\)\s*:\s*([\d\.]+)\s*words/cycle", block)
        entry["read_bw_wpc"]  = float(m_r.group(1)) if m_r else None
        entry["write_bw_wpc"] = float(m_w.group(1)) if m_w else None

       
        if entry["word_bits"] is not None:
            bpw = entry["word_bits"] / 8.0  # bytes per word
            if entry["read_bw_wpc"] is not None:
                entry["read_bw_Bps"] = entry["read_bw_wpc"] * bpw * freq_hz
            if entry["write_bw_wpc"] is not None:
                entry["write_bw_Bps"] = entry["write_bw_wpc"] * bpw * freq_hz

        stats[level] = entry

    return stats       

def parse_dram_stats(stat_txt_path, freq_hz=1e9,problem_name=""):
 
    text = open(stat_txt_path).read()

    
    m_block = re.search(r"===\s*DRAM\s*===(.*?)(?:\n===|\Z)", text, re.S)
    
    if not m_block:
        raise ValueError("No DRAM section found in stat file")

    block = m_block.group(1)
    def find_total_access(pattern):
        dram_accesses=None  
        m_block = re.findall(r"===\s*DRAM\s*===(.*?)(?:\n===|\Z)", text,flags=re.DOTALL)
        
        for i in range(1, len(m_block), 2):
            
            block = m_block[1]
           
            m_acc = re.search(r"Total scalar accesses\s*:\s*([\d\.eE\+\-]+)", block)
            if m_acc:
                dram_accesses = int(float(m_acc.group(1))) 
                
                return dram_accesses
        return dram_accesses    
   
        
        
    def find_int(pattern):
        m = re.search(pattern, block)
        return int(float(m.group(1))) if m else None

    def find_float(pattern):
        m = re.search(pattern, block)
        return float(m.group(1)) if m else None

    bits       = find_int(r"Word bits\s*:\s*(\d+)")
    accesses   = find_total_access(r"Total scalar accesses\s*:\s*([\d\.eE\+\-]+)")
    rbw_wpc    = find_float(r"Read bandwidth\s*:\s*([\d\.]+)")
    wbw_wpc    = find_float(r"Write bandwidth\s*:\s*([\d\.]+)")
    print(f"***** bits: {bits}, accesses: {accesses}, rbw_wpc: {rbw_wpc} in problem: {problem_name} ****** ")
    
    bpw = bits / 8.0 if bits is not None else 0.0
    read_bw  = rbw_wpc * bpw * freq_hz if rbw_wpc else 0.0
    write_bw = wbw_wpc * bpw * freq_hz if wbw_wpc else 0.0

    return {
        "word_bits":   bits,
        "accesses":    accesses,
        "read_bw_Bps": read_bw,
        "write_bw_Bps": write_bw,
    }

def copy_and_rename_files(
    src_dir: str,
    dst_dir: str,
    task_count:int,
    file_list: Optional[List[str]] = None
) -> None:
    os.makedirs(dst_dir, exist_ok=True)
    if file_list is None:
        file_list = [f for f in os.listdir(src_dir) if os.path.isfile(os.path.join(src_dir, f))]
    task_id=0
    for fname in file_list:
        src_path = os.path.join(src_dir, fname)
        if not os.path.isfile(src_path):
            continue

        layer_name, ext = os.path.splitext(fname)
        for task_id in range(task_count):
            new_fname = f"{layer_name}_t{task_id}{ext}"
            dst_path = os.path.join(dst_dir, new_fname)

            shutil.copy2(src_path, dst_path)
        
        #print(f"Copied {src_path} → {dst_path}")
      
  