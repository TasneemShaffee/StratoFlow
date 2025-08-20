# StratoFlow: Heterogeneous Dataflow Accelerator Framework

StratoFlow is an end-to-end framework for designing, optimizing, and evaluating Heterogeneous Dataflow Accelerators (HDAs). These accelerators feature multiple specialized processing engines, each optimized for a distinct dataflow pattern, enabling them to efficiently handle a wide range of deep neural network (DNN) workloads—from classic single-task models like ResNet-18, VGG-16, and AlexNet to custom multi-task architectures.

### Key Features

- Heterogeneous Dataflow Support: Efficiently maps each DNN layer to the most suitable sub-accelerator based on its shape, memory-access behavior, and computational pattern.
- Synthetic Layer Insertion: Systematically injects stress-inducing “adversarial” layers (e.g., Softmax, BatchNorm, high-bandwidth “hammer” kernels) to expose bottlenecks and evaluate corner-case performance.
- Layer-Wise Scheduling: Uses a heuristic-driven algorithm to optimize workload distribution, balancing latency and energy consumption across multiple processing engines.
- Integrated Simulation Pipeline: Combines Timeloop-based performance modeling with a custom simulator for accurate end-to-end latency and energy estimates.
- Flexible Workload Support: Supports both single-task and multi-task CNNs, revealing critical stress points and guiding future hardware partitioning strategies.

### File Structure
- example_designs: 
   - architecture descriptions, compound component descriptions.
   - top.yaml.jinja2: Top-level file gathering
   - _components directory: Compound components
   - _include directory: Default problem file and mapper description
- layer_shapes: 
    - Example workloads: AlexNet, Resnet18, VGG16
- dependencies:
    - It has yaml files describes the dependency graph of the layers of the given workload.
    - The supported ones: VGG16, Resnet18, Alexnet, MTL, and Single Task. 
### Output of the framework
1. The end-to-end latency, overall energy consumption, and total PE area will be printed to the terminal and saved in the result.csv file located under final-project/example_designs/.
2. Additionally, for each layer, a JSON file will be generated inside its corresponding output folder. This JSON file contains detailed Timeloop results, including per-component energy consumption, area, number of cycles, per-layer latency, and more.
## Command-Line Arguments

| Argument | Type | Default | Description |
|:---------|:-----|:--------|:------------|
| `--clear-outputs` | `flag` | `False` | Clear all generated outputs. |
| `--MTL_on` | `flag` | `False` | Enable Multi-Task Learning (MTL) support. |
| `--Adv_on` | `flag` | `False` | Enable Adversarial analysis support. |
| `--adv_layer` | `str` | `"softmax"` | Type of irregular layer to insert for stress analysis (`softmax`, `hammer`, `bn`). |
| `--count` | `int` | `1` | Number of irregular layers to insert for stress analysis. |
| `--single_task_count` | `int` | `1` | Number of single tasks to be supported (task replication factor). |
| `--HDA` | `flag` | `False` | Enable Heterogeneous Dataflow Accelerator (HDA) support. |
| `--architecture` | `str` | `"eyeriss_like"` | Target architecture from `example_designs` to run. Use `'all'` to run all architectures. |
| `--generate-ref-outputs` | `flag` | `False` | Generate reference outputs instead of normal outputs. |
| `--problem` | `str` | `None` | Path to a problem YAML file or directory under `layer_shapes`. If a directory is given, runs all problems inside. |
| `--dependency_file` | `str` | `None` | YAML file defining the graph of layer dependencies for the architecture. |
| `--n_jobs` | `int` | `16` | Number of parallel jobs for running mapping tasks. |
| `--remove-sparse-opts` | `flag` | `False` | Remove sparse optimization options when mapping. |

### Getting Started

To run a basic end-to-end evaluation:

1. Prepare your DNN workload (e.g., AlexNet, ResNet-18, VGG-16, or a custom multi-task model).
2. Define the layer shapes and dataflow preferences (baseline or HDA).
3. Use StratoFlow’s synthetic layer generator to inject stress tests if needed.
4. Run the layer-wise scheduler and custom simulator for performance analysis.
5. Visualize and interpret the latency, energy, and utilization metrics.


### Example Usage
First, navigate to the correct folder using the following command:
```
cd final-project/example_designs/
```
To run AlexNet on the baseline model:
```
python3 run_example_designs.py --architecture simple_output_stationary --problem alexnet --remove-sparse-opts --generate-ref-outputs --dependency_file alexnet.yaml 
```
To run the baseline model, with single task:
```
python3 run_example_designs.py --architecture simple_output_stationary --problem Single_Task --remove-sparse-opts --generate-ref-outputs --dependency_file single_task.yaml 
```
add --single_task_count 2 to the above command if you want to run two single tasks and add --HDA if you want to run on HDA, where  --HDA will replace "--architecture simple_output_stationary".


To run the baseline model, with MTL:
```
python3 run_example_designs.py --architecture simple_output_stationary --problem mtl --remove-sparse-opts --generate-ref-outputs --dependency_file mtl.yaml
```
For adversarial analysis on alexnet using HDA, run this to insert the synthetic layer - Batch Normalization.
```
python3 run_example_designs.py --architecture simple_output_stationary --problem alexnet --remove-sparse-opts --generate-ref-outputs --dependency_file alexnet.yaml --Adv_on --adv_layer bn  --count 1 --HDA
```
To run MTL on HDA:
```
python3 run_example_designs.py --architecture all --problem mtl --remove-sparse-opts --MTL_on --HDA --dependency_file alexnet.yaml
```
