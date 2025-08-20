import random
def bn_compatible(p):
    return all(k in p for k in ("M","P","Q"))

def bn_params(p):
    return {"C": p["M"], "M": p["M"], "H": p["P"], "Q": p["Q"]}


def sm_compatible(p):
    return (p.get("P",0)==1 and p.get("Q",0)==1) or len(p)<=2

def sm_params(p):
    return {"C": p["M"], "M": p["M"], "P":1, "Q":1}


def hb_compatible(p):
    return p["M"] > 64

def hb_params(p):
    return {"C": p["M"], "M": p["M"], "P": p["P"], "Q": p["Q"], "R":1, "S":1}

def get_compatible_layer_indices(layer_seq,params):
    insert_points = {
      "bn":   [i for i, L in enumerate(layer_seq) if bn_compatible(params[L])],
      "soft": [i for i, L in enumerate(layer_seq) if sm_compatible(params[L])],
      "hammer":[i for i, L in enumerate(layer_seq) if hb_compatible(params[L])],
        }
    return insert_points



def insert_every_compatible(
    layer_seq, deps, params,
    compat_fn, param_fn, prefix,
    mode="n", count=1, random_seed=None
):

    original = list(layer_seq)
    compat_idxs = [i for i, L in enumerate(original) if compat_fn(params[L])]
    sync_layers=[]
    if mode == "all":
        chosen = compat_idxs
    elif mode == "n":
        chosen = compat_idxs[:count]
    else:
        raise ValueError(f"Unsupported mode {mode!r}")

    for idx in sorted(chosen, reverse=True):
        L = layer_seq[idx]
        new_name   = f"{prefix}_after_{L}"
        new_params = param_fn(params[L])


        layer_seq.insert(idx + 1, new_name)

       
        deps[new_name] = [L]

        sync_layers.append(new_name)
        for child, parents in deps.items():
            if child == new_name:
                continue
            deps[child] = [new_name if p == L else p for p in parents]

       
        params[new_name] = new_params
    return  sync_layers       
import os, shutil
import yaml

def generate_problem_yaml(template_path, params):
       
    with open(template_path) as f:
        text = f.read()
    inst_items = ", ".join(f"{k}: {v}" for k, v in params.items())
    instance_line = f"  instance: {{{inst_items}}}"

    lines = text.splitlines()
    for i, L in enumerate(lines):
        if L.strip().startswith("instance:") and "{}" in L:
            indent = L[: L.find("instance:")]
            lines[i] = instance_line
            break
    new_text = "\n".join(lines)
    return new_text
    
def make_new_architecture(
    template_path: str,
    params: dict,
    arch_src_dir: str,
    out_dir: str,
    sync_layers: dict
):



    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)
    #os.makedirs(out_dir, exist_ok=True)

    for l in sync_layers:
        new_text=generate_problem_yaml(template_path, params[l])
        out_problem = os.path.join(out_dir, f'{l}.yaml')
        with open(out_problem, "w") as f:
            f.write(new_text)
        
        
    for fname in os.listdir(arch_src_dir):
        src = os.path.join(arch_src_dir, fname)
        dst = os.path.join(out_dir, fname)
        if os.path.isdir(src):
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)

    #out_problem = os.path.join(out_dir, "problem.yaml")
    #with open(out_problem, "w") as f:
    #    f.write(new_text)

    return #out_problem