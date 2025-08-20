import os
import json
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.patches as mpatches
import os
import json
import re
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
def collect_layer_stats(root_dir):
    stats = {}
    for entry in sorted(os.listdir(root_dir)):
        layer_dir = os.path.join(root_dir, entry)
        if not os.path.isdir(layer_dir):
            continue
        json_path = os.path.join(layer_dir, 'timeloop_stats.json')
        if not os.path.isfile(json_path):
            continue
        with open(json_path, 'r') as f:
            data = json.load(f)
        stats[entry] = {
            'percent_utilization': data.get('percent_utilization', None),
            'per_component_energy': data.get('per_component_energy', {})
        }
    return stats

def plot_normalized_energy_bars(stats_clean, stats_adv,
                                output_file='energy_comparison.png',
                                dpi=300):

    layers = sorted([l for l in stats_clean if l in stats_adv])
    n = len(layers)
    components = sorted({
        comp 
        for l in layers 
        for comp in stats_clean[l]['per_component_energy']
    })
    
   
    E_clean = np.zeros((n, len(components)))
    E_adv   = np.zeros((n, len(components)))
    for i, layer in enumerate(layers):
        ce = stats_clean[layer]['per_component_energy']
        ae = stats_adv[layer]['per_component_energy']
        total_c = sum(ce.get(c, 0) for c in components) or 1
        total_a = sum(ae.get(c, 0) for c in components) or 1
        for j, comp in enumerate(components):
            E_clean[i, j] = ce.get(comp, 0) / total_c
            E_adv[i, j]   = ae.get(comp, 0) / total_a

    fig, (ax1, ax2) = plt.subplots(2, 1,
                                   figsize=(max(12, n*0.3), 8),
                                   dpi=dpi, sharex=True)
    x = np.arange(n)
    width = 0.8
    

    for j, comp in enumerate(components):
        bottom = E_clean[:, :j].sum(axis=1)
        ax1.bar(x, E_clean[:, j], bottom=bottom, width=width, label=comp)
    ax1.set_ylabel('Normalized Energy')
    ax1.set_title('Per-Layer Energy Breakdown (Clean)')
    ax1.legend(loc='upper right', bbox_to_anchor=(1.15, 1))

    for j in range(len(components)):
        bottom = E_adv[:, :j].sum(axis=1)
        ax2.bar(x, E_adv[:, j], bottom=bottom, width=width)
    ax2.set_ylabel('Normalized Energy')
    ax2.set_title('Per-Layer Energy Breakdown (Adversarial)')
    ax2.set_xticks(x)
    ax2.set_xticklabels(layers, rotation=90, fontsize=6)
    
    plt.tight_layout()
    fig.savefig(output_file, dpi=dpi, bbox_inches='tight')
    plt.show()



def collect_layer_stats(root_dir):
    stats = {}
    for entry in sorted(os.listdir(root_dir)):
        layer_dir = os.path.join(root_dir, entry)
        if not os.path.isdir(layer_dir):
            continue
        js = os.path.join(layer_dir, 'timeloop_stats.json')
        if not os.path.isfile(js):
            continue
        with open(js) as f:
            data = json.load(f)
        stats[entry] = {
            'percent_utilization': data.get('percent_utilization'),
            'per_component_energy': data.get('per_component_energy', {})
        }
    return stats

def _layer_sort_key(name):
  
    m = re.search(r'_after_(\d+)$', name)
    if m:
        return int(m.group(1)) + 0.5
 
    m2 = re.search(r'(\d+)$', name)
    if m2:
        return int(m2.group(1))
 
    return float('inf')

def plot_normalized_energy_bars_side_by_side(stats_clean, stats_adv,
                                             output_file='energy_comparison.png',
                                             dpi=300):

    layers = sorted(set(stats_clean) | set(stats_adv), key=_layer_sort_key)
    n = len(layers)

  
    components = sorted({
        c
        for s in (stats_clean, stats_adv)
        for layer in s
        for c in s[layer]['per_component_energy']
    })

  
    E_clean = np.zeros((n, len(components)))
    E_adv   = np.zeros((n, len(components)))
    for i, layer in enumerate(layers):
        ce = stats_clean.get(layer, {}).get('per_component_energy', {})
        ae = stats_adv  .get(layer, {}).get('per_component_energy', {})
        total_c = sum(ce.values()) or 1.0
        total_a = sum(ae.values()) or 1.0
        for j, comp in enumerate(components):
            E_clean[i,j] = ce.get(comp, 0.0) #/ total_c
            E_adv  [i,j] = ae.get(comp, 0.0) #/ total_a


    x = np.arange(n)
    bar_w = 0.35
    cmap = plt.get_cmap('tab10')
    colors = cmap(range(len(components)))

    fig, ax = plt.subplots(figsize=(max(12, n*0.2), 6), dpi=dpi)

 
    for j, comp in enumerate(components):
        bottom = E_clean[:,:j].sum(axis=1)
        ax.bar(x - bar_w/2, E_clean[:,j], bar_w, bottom=bottom,
               color=colors[j], edgecolor='black')

  
    for j in range(len(components)):
        bottom = E_adv[:,:j].sum(axis=1)
        ax.bar(x + bar_w/2, E_adv[:,j], bar_w, bottom=bottom,
               color=colors[j], edgecolor='black', hatch='//')

    ax.set_xticks(x)
    ax.set_xticklabels(layers, rotation=90, fontsize=12, fontweight='bold')
    ax.set_ylabel('Energy (J)',fontweight='bold',fontsize=12)
    ax.set_xlabel('Layer(s)',fontweight='bold',fontsize=12)
    ax.set_title('Per-Layer Energy Breakdown: Clean vs. Adversarial',fontweight='bold')
    ax.tick_params(axis='y', labelsize=12, labelrotation=0, width=1.5)
    yticks = ax.get_yticks()
    ax.set_yticks(yticks)                                 
    ax.set_yticklabels([f"{y:.2f}" for y in yticks],      
                   fontsize=12,
                   fontweight='bold')

    comp_patches = [
        mpatches.Patch(facecolor=colors[j], edgecolor='black', label=components[j])
        for j in range(len(components))
    ]
    arch_patches = [
        mpatches.Patch(facecolor='white', edgecolor='black', label='Clean (solid)'),
        mpatches.Patch(facecolor='white', hatch='//', edgecolor='black', label='Adversarial (hatched)')
    ]
    leg1 = ax.legend(handles=comp_patches, title='Components',
                     bbox_to_anchor=(1.02, 1), loc='upper left')
    ax.add_artist(leg1)
    ax.legend(handles=arch_patches, title='Architecture',
              bbox_to_anchor=(1.02, 0.4), loc='upper left')

    plt.tight_layout()
    fig.savefig(output_file, dpi=dpi, bbox_inches='tight')
    plt.show()

THIS_SCRIPT_DIR = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
EXAMPLE_DIR_ADV = os.path.join(THIS_SCRIPT_DIR, "Adv","MTL","hda_hammer","adv_layers")
EXAMPLE_DIR_CLEAN = os.path.join(THIS_SCRIPT_DIR, "results","mtl","hda_mtl","clean_hda_layers")

clean_stats = collect_layer_stats(EXAMPLE_DIR_CLEAN)
adv_stats   = collect_layer_stats(EXAMPLE_DIR_ADV)
plot_normalized_energy_bars_side_by_side(clean_stats, adv_stats,
                             output_file='hda_energy_comparison_hammer3.png',
                             dpi=450)