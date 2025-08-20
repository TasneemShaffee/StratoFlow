import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import LogLocator, LogFormatterSciNotation

def plot_roofline(
    num_fpmuls,
    frequency_hz,
    bandwidth_bytes_per_sec,
    title=None,           
    ax=None,
    label_prefix='',     
    colorx1='b',
    colorx2='g'
):
  
    peak_perf = num_fpmuls * frequency_hz
    oi = np.linspace(1e-1, 1e4, 100000)
    bw_limited = bandwidth_bytes_per_sec * oi
    oi_int = peak_perf / bandwidth_bytes_per_sec

    # split at intersection
    mask_bw   = oi <= oi_int
    mask_cp   = oi >= oi_int
    oi_bw, perf_bw = oi[mask_bw],   bw_limited[mask_bw]
    oi_cp, perf_cp = oi[mask_cp],   np.full_like(oi[mask_cp], peak_perf)


    new_fig = False
    if ax is None:
        fig, ax = plt.subplots(figsize=(7,6))
        new_fig = True

    # plot the segments
    ax.plot(oi_bw, perf_bw,  color=colorx1, linewidth=2)
    ax.plot(oi_cp, perf_cp,   color=colorx1, linewidth=2,label=f'{label_prefix} Accelerator') 

    # intersection lines
    ax.axvline(oi_int, linestyle=':', color=colorx2,
               label=f'{label_prefix}OI₀={oi_int:.2f}Muls/Byte')
    ax.axhline(peak_perf, linestyle='-.', color=colorx2,
               label=f'{label_prefix}Π₀={peak_perf/1e9:.1f}GMuls/s')

    
    if new_fig:
        ax.set_xscale('log')
        ax.set_yscale('log')
        ax.set_xlabel('Operational Intensity (Muls/Byte)')
        ax.set_ylabel('Performance (Muls/sec)')
        if title:
            ax.set_title(title)
        ax.grid(which='both', linestyle='--', linewidth=0.5)
        ax.legend(loc='lower right')
        return fig, ax
    else:
        return ax



frequency = 1e9    # 1 GHz
bandwidth = 128e9  # 256 GB/s in B/s

fig, ax = plt.subplots(figsize=(20,14))

# first curve
plot_roofline(
    num_fpmuls=16*16,
    frequency_hz=frequency,
    bandwidth_bytes_per_sec=bandwidth,
    ax=ax,
    label_prefix='baseline OS',
    colorx1='r',
    colorx2='orange'
)

# second curve
plot_roofline(
    num_fpmuls=1*128,
    frequency_hz=frequency,
    bandwidth_bytes_per_sec=bandwidth,
    ax=ax,
    label_prefix='HDA WS/OS '
)

#resNet
xb=820.51
yb=3.20E+10/2
plt.plot(xb,yb,'o',color='red')    # 'o' means circle marker
plt.text(xb, yb, f'ResNetL5-SOS',fontsize=12)
#VGG
xb=1
yb=3.20E+10/2
plt.plot(xb,yb,'o',color='red')    # 'o' means circle marker
plt.text(xb, yb, f'VGG-L20-OS',fontsize=12)
#MTL
xb=150
yb=3.20E+10/2
plt.plot(xb,yb,'o',color='red')    # 'o' means circle marker
plt.text(xb, yb, f'MTL-ENC-L9-OS',fontsize=12)
#single task
xb=95
yb=3.20E+10/2
plt.plot(xb,yb,'o',color='red')    # 'o' means circle marker
plt.text(xb-35, yb, f'ST-L17-OS',fontsize=12)


#after


#resNet
xb=93.33
yb=1.71E+11/2
plt.plot(xb,yb,'*',color='k',markersize=12 )   
plt.text(xb-65, yb+5e9, f'ResNetL5-HDA_WS',fontsize=12)
#VGG
xb=1
yb=2.56E+11/2
plt.plot(xb,yb,'*',color='k',markersize=12)   
plt.text(xb-0.4, yb+0.7e10, f'VGG-L20-HDA_OS',fontsize=12)
#MTL
xb=114
yb=1.71E+11/2
plt.plot(xb,yb,'*',color='k',markersize=12)   
plt.text(xb, yb+5e9, f'MTL-ENC-L9-HDA_WS',fontsize=12)
#single task
xb=46.24
yb=2.56E+11/2
plt.plot(xb,yb,'*',color='k',markersize=12)    
plt.text(xb-0.4, yb+0.7e10, f'ST-L17-HDA_OS',fontsize=12)







ax.set_xscale('log')
ax.set_yscale('log')
ax.set_xlabel('Operational Intensity (Muls/Byte)')
ax.set_ylabel('Performance (Muls/sec)')
ax.set_title('Roofline Comparison: Output stationary vs HDA with WS/OS')
ax.grid(which='both', linestyle='--', linewidth=0.5)
ax.legend(loc='lower right')

fig.savefig('roofline_comparison.png', dpi=300, bbox_inches='tight')

plt.show()