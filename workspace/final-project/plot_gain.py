import matplotlib.pyplot as plt

def plot_model_gains():
    models = ["Resnet18", "Alexnet", "VGG16", "MTL", "Single_Task"]
    latency_gains = [0.608405419, 0.808055428, 0.829284664, 0.83745778, 0.847560461]
    energy_gains  = [0.164190617, 0.053025013, 0.130583908, 0.031349046, 0.037897214]
    
    cmap = plt.get_cmap('tab10')
    colors = cmap(range(len(models)))
    
    x = range(len(models))
    plt.figure()
    plt.scatter(x, latency_gains, marker='o', s=100, color=colors, label='Latency Gain')
    plt.scatter(x, energy_gains,  marker='*', s=120, color=colors, label='Energy Gain')
    
    plt.xticks(x, models, rotation=45, ha='right')
    plt.ylabel('Gain (fraction)')
    plt.title('Model Gains: Latency vs Energy')
    plt.legend()
    plt.tight_layout()
    plt.show()
    plt.savefig('gain.png', dpi=300, bbox_inches='tight')

plot_model_gains()