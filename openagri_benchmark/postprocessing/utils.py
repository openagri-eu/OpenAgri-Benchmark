from pathlib import Path
import datetime
import json


from matplotlib.patches import Patch
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns



from openagri_benchmark.conf import (
    POSTPROCESSING_INPUT_DIR,
    POSTPROCESSING_TASK_PROFILES_DIR,
)



def read_benchmark_results(eval_name):
    result_dict = {}

    for setup_dir_path in Path(POSTPROCESSING_INPUT_DIR).iterdir():
        setup_name = setup_dir_path.name
        setup_result_dict = {}
        if setup_dir_path.is_dir():
            for dir_path in Path(setup_dir_path).iterdir():
                dir_name = dir_path.name

                # Extract workload type (low, medium, high)
                workload = dir_name.split('_')[-2]  # second last part

                # Extract evaluation name and service name
                after_eval = dir_name.split(f'{eval_name}.')[1]

                service_name = after_eval.split('_')[0]

                # Extract timestamp
                timestamp = dir_name.split('_')[-1]  # second last part

                # Read JSON files
                result_file = dir_path / 'result.json'
                stats_file = dir_path / 'stats.json'

                with open(result_file, 'r') as f:
                    result_content = json.load(f)

                with open(stats_file, 'r') as f:
                    stats_content = json.load(f)

                # Build nested dictionary
                setup_result_dict.setdefault(workload, {})
                setup_result_dict[workload].setdefault(service_name, {})


                setup_result_dict[workload][service_name][timestamp] = {
                    'result': result_content,
                    'stats': stats_content,
                }
            result_dict[setup_name] = setup_result_dict

    return result_dict


def prepare_evals_dataframe(raw_results):
    data = []
    for setup, workloads in raw_results.items():
        for workload, services in workloads.items():
            for service_name, evaluations in services.items():
                for eval_key, eval_data in evaluations.items():
                    result = eval_data['result']
                    eval_id = result['id']

                    for task_name, task_data in result[service_name]['tasks'].items():
                        s_container_name, db_container_name = (None, None)
                        if len(task_data['stats']) == 0:
                            task_data['stats'] = fix_empty_stats(eval_data['stats'], task_data['start_timestamp'], task_data['end_timestamp'])
                        for c_i, c_name in enumerate(task_data['stats'].keys()):
                            if c_name.endswith('_db'):
                                db_container_name = c_name
                            else:
                                s_container_name = c_name
                        if s_container_name is None:
                            print(workload, service_name,task_name)
                            print(task_data['stats'])
                            continue

                        s_cpu = task_data['stats'][s_container_name]['cpu_avg']
                        s_mem = task_data['stats'][s_container_name]['mem_avg']
                        db_cpu = task_data['stats'][db_container_name]['cpu_avg']
                        db_mem = task_data['stats'][db_container_name]['mem_avg']
                        task_name_clean = task_name.replace('generate_and_wait_', '')
                        task_name_clean = task_name_clean.replace('get_locations_by_coordinates', 'get_locations_by_coord')
                        row = {
                            'setup': setup,
                            'workload': workload,
                            'service': service_name,
                            'eval_id': eval_id,
                            'task': task_name_clean,
                            'RTT_AVG': task_data['request_times_avg'],
                            # 'RTT_STD': task_data['request_times_std'],
                            'P99_RTT': task_data['request_times_p99'],
                            'S_CPU%': s_cpu,
                            'S_MEM%': s_mem,
                            'DB_CPU%': db_cpu,
                            'DB_MEM%': db_mem,
                            'energy': None
                        }
                        data.append(row)

    df = pd.DataFrame(data)
    return df


def fix_empty_stats(all_stats, start_timestamp, end_timestamp):
    # Sort timestamps
    start_dt = datetime.datetime.fromisoformat(start_timestamp)
    end_dt = datetime.datetime.fromisoformat(end_timestamp)
    target_dt = start_dt + ((end_dt - start_dt) / 2)

    period_stats = {}
    prev_dt = None
    prev_stats = None
    for key, stats in all_stats.items():
        dt = datetime.datetime.fromisoformat(key)
        if start_dt <= dt:
            period_stats[target_dt.isoformat()] = _interpolate_stats(
                target_dt=target_dt,
                prev_dt=prev_dt,
                prev_stats=prev_stats,
                next_dt=dt,
                next_stats=stats
            )

        prev_dt = dt
        prev_stats = stats


    return _re_calculate_stats(period_stats)

def _interpolate_stats(target_dt, prev_dt, prev_stats, next_dt, next_stats):
    ratio = (target_dt - prev_dt) / (next_dt - prev_dt)
    prev_by_id = {stat["Container"]: stat for stat in prev_stats}
    next_by_id = {stat["Container"]: stat for stat in next_stats}

    stats = []
    # go from next, since makes sense to have more new containers in future than pass...
    for container_id, c_next_stat in next_by_id.items():
        if container_id in prev_by_id:
            c_prev_stat = prev_by_id[container_id]

            prev_cpu = float(c_prev_stat['CPUPerc'].rstrip('%'))
            next_cpu = float(c_next_stat['CPUPerc'].rstrip('%'))
            prev_mem = float(c_prev_stat['MemPerc'].rstrip('%'))
            next_mem = float(c_next_stat['MemPerc'].rstrip('%'))
            container_name = c_next_stat.get('Name', '--')

            cpu_interp = prev_cpu + ((next_cpu - prev_cpu) * ratio)
            mem_interp = prev_mem + ((next_mem - prev_mem) * ratio)
            interpolated = {
                "Container": container_id,
                "Name": container_name,
                "CPUPerc": f"{cpu_interp:.2f}%",
                "MemPerc": f"{mem_interp:.2f}%",
                "Interpolated": True,
            }
            stats.append(interpolated)

    return stats

def _re_calculate_stats(stats):
    if len(stats) == 0:
        return {}
    records = []
    container_names_map = {}
    has_interpolated = False
    for timestamp, containers in stats.items():
        for container in containers:
            records.append({
                'timestamp': timestamp,
                'container': container.get('Container'),
                'cpu': min(100, float(container.get('CPUPerc').rstrip('%'))),
                'mem': min(100, float(container.get('MemPerc').rstrip('%'))),
                'interp': container.get('Interpolated', False),
            })
            if container.get('Interpolated'):
                has_interpolated = True
            if container.get('Name') != '--':
                clean_name = container.get('Name').split('-')[-2]
                container_names_map[container.get('Container')] = clean_name

    # Convert to DataFrame
    df = pd.DataFrame(records)
    df['name'] = df['container'].map(container_names_map)

    # Group by container and calculate stats
    result = {}
    for container_name, group in df.groupby('name'):
        result[container_name] = {
            'cpu_avg': group['cpu'].mean(),
            'cpu_std': group['cpu'].std(),
            'mem_avg': group['mem'].mean(),
            'mem_std': group['mem'].std(),
            'count': len(group),
            'interp': has_interpolated,
        }

    return result



def plot_resource(df, setup):
    """
    Plot stacked CPU and memory bars per task, grouped by service.
    One row per service: left column = CPU, right column = memory.
    """
    df = df[df['setup'] == setup]
    # Aggregate means for CPU and memory
    cpu_agg = df.groupby(['workload', 'service', 'task'])[['S_CPU%', 'DB_CPU%']].mean().reset_index()
    mem_agg = df.groupby(['workload', 'service', 'task'])[['S_MEM%', 'DB_MEM%']].mean().reset_index()

    for workload in ['low', 'medium', 'high']:
        if workload not in cpu_agg['workload'].unique():
            continue
        cpu_wl = cpu_agg[cpu_agg['workload'] == workload]
        mem_wl = mem_agg[mem_agg['workload'] == workload]
        services = cpu_wl['service'].unique()
        n_services = len(services)

        # 2 columns: CPU left, memory right; sharey per column
        fig, axes = plt.subplots(n_services, 2,
                                 figsize=(10, 5 * n_services),
                                 sharey='col')
        # axes is 2D: axes[row, 0] = CPU, axes[row, 1] = memory

        for i, service in enumerate(services):
            # --- CPU subplot (left) ---
            cpu_data = cpu_wl[cpu_wl['service'] == service]
            ax_cpu = axes[i, 0]
            ax_cpu.bar(cpu_data['task'], cpu_data['S_CPU%'],
                       label='Service CPU', color='darkorange')
            ax_cpu.bar(cpu_data['task'], cpu_data['DB_CPU%'],
                       bottom=cpu_data['S_CPU%'], label='DB CPU', color='steelblue')
            ax_cpu.set_title(f'{service} CPU')
            ax_cpu.set_ylabel('Avg CPU %')
            ax_cpu.tick_params(axis='x', rotation=90)
            ax_cpu.set_ylim(0, 100)

            # --- Memory subplot (right) ---
            mem_data = mem_wl[mem_wl['service'] == service]
            ax_mem = axes[i, 1]
            ax_mem.bar(mem_data['task'], mem_data['S_MEM%'],
                       label='Service MEM', color='lightgreen')
            ax_mem.bar(mem_data['task'], mem_data['DB_MEM%'],
                       bottom=mem_data['S_MEM%'], label='DB MEM', color='darkgreen')
            ax_mem.set_title(f'{service} MEM')
            ax_mem.set_ylabel('Avg MEM % (Axis zoomed in)')
            ax_mem.tick_params(axis='x', rotation=90)

        # Unified legend for all four components
        legend_elements = [
            Patch(facecolor='darkorange', label='Service CPU'),
            Patch(facecolor='steelblue',   label='DB CPU'),
            Patch(facecolor='lightgreen',  label='Service MEM'),
            Patch(facecolor='darkgreen',   label='DB MEM')
        ]
        fig.legend(handles=legend_elements, loc='lower center', ncol=4)
        fig.suptitle(f'{setup} Resource Usage – Workload: {workload}', fontsize=14)
        plt.tight_layout()
        plt.subplots_adjust(top=0.95)
        plt.show()


def plot_p99_rtt(df, setup=''):
    """
    Plot P99 RTT (request round trip time) bars per task, grouped by service.
    One row per service, with P99 RTT values displayed.
    """
    df = df[df['setup'] == setup]
    # Aggregate mean P99 RTT
    rtt_agg = df.groupby(['workload', 'service', 'task'])['P99_RTT'].mean().reset_index()

    for workload in ['low', 'medium', 'high']:
        if workload not in rtt_agg['workload'].unique():
            continue
        rtt_wl = rtt_agg[rtt_agg['workload'] == workload]
        services = rtt_wl['service'].unique()
        n_services = len(services)

        # Single column for P99 RTT
        fig, axes = plt.subplots(n_services, 1,
                                 figsize=(10, 5 * n_services),
                                 sharey=True)

        for i, service in enumerate(services):
            rtt_data = rtt_wl[rtt_wl['service'] == service]
            ax = axes[i]

            # Plot P99 RTT as bars
            ax.bar(rtt_data['task'], rtt_data['P99_RTT'],
                   color='coral', edgecolor='darkred', linewidth=0.5)

            ax.set_yscale('log')

            # Add value labels on top of bars (only for non-zero values)
            for j, v in enumerate(rtt_data['P99_RTT']):
                if v > 0:
                    # Position label slightly above the bar in log space
                    label_y = v * 1.1  # 10% above the bar
                    ax.text(j, label_y,
                           f'{v:.3f}', ha='center', va='bottom', fontsize=9)

            ax.set_title(f'{service} - P99 RTT')
            ax.set_ylabel('P99 RTT (s)')
            ax.tick_params(axis='x', rotation=90)
            ax.grid(axis='y', alpha=0.3, linestyle='--')

            # For log scale, set bottom to a small positive value based on data
            # positive_values = rtt_data[rtt_data['P99_RTT'] > 0]['P99_RTT']
            # if len(positive_values) > 0:
            #     min_positive = positive_values.min()
            #     # Set bottom to half of the minimum positive value
            #     ax.set_ylim(bottom=min_positive * 0.5)
            # else:
            #     # If all values are 0, use a default small value
            top = 10
            if workload == 'medium':
                top = 20
            ax.set_ylim(bottom=0.0001, top=80)

        fig.suptitle(f'{setup} P99 Request Round Trip Time – Workload: {workload}', fontsize=14)
        plt.tight_layout()
        plt.subplots_adjust(top=0.95)
        plt.show()


def plot_p99_rtt_distribution_violin(df, setup):
    """
    Plot P99 RTT distribution using violin plots for all services in a single plot.
    Shows the full distribution of P99 RTT values per service.
    """
    # Aggregate P99 RTT data (keep all values, not just mean)
    # Assuming you want the distribution of individual measurements
    # If you already have aggregated data, use that instead


    df = df[df['setup'] == setup]
    all_services = sorted(df['service'].unique())
    for workload in ['low', 'medium', 'high']:
        if workload not in df['workload'].unique():
            continue
        df_wl = df[df['workload'] == workload]

        # Create figure
        fig, ax = plt.subplots(figsize=(12, 7))

        # Get services and prepare data
        services = all_services
        data_for_violin = []
        positions = []

        # Collect data for each service
        for i, service in enumerate(services):
            service_data = df_wl[df_wl['service'] == service]['P99_RTT'].dropna()
            if len(service_data) > 0:
                data_for_violin.append(service_data.values)
                positions.append(i)

        # Create violin plot
        parts = ax.violinplot(data_for_violin, positions=positions,
                            showmeans=True, showmedians=True,
                            showextrema=True, widths=0.7)

        # Customize violin plot colors
        for i, pc in enumerate(parts['bodies']):
            pc.set_facecolor(plt.cm.Set3(i / len(parts['bodies'])))
            pc.set_alpha(0.7)
            pc.set_edgecolor('black')
            pc.set_linewidth(0.5)

        # Annotate the median value on each violin
        for pos, data in zip(positions, data_for_violin):
            median_val = np.mean(data)
            ax.text(pos, median_val, f'{median_val:.2f}',
                    ha='center', va='bottom', fontsize=9,
                    color='darkblue', fontweight='bold')

        # Set labels and title
        ax.set_xticks(positions)
        ax.set_xticklabels(services, rotation=45, ha='right')
        ax.set_ylabel('P99 RTT (s)')
        ax.set_title(f'{setup}: P99 RTT Distribution by Service – Workload: {workload}')
        ax.grid(axis='y', alpha=0.3, linestyle='--')

        # Use log scale if data spans multiple orders of magnitude
        ax.set_yscale('log')

        plt.tight_layout()
        plt.show()


def create_tasks_energy_profile(df_eval, setup_devices):
    profile = {}
    for setup, device_name in setup_devices:
        device_profile = get_device_energy_profile(device_name)
        tasks = {}
        setup_df = df_eval[df_eval['setup'] == setup]
        for _, row in setup_df.iterrows():
            total_cpu = row['S_CPU%'] + row['DB_CPU%']
            energy = row['energy']
            if pd.isna(row['energy']):
                energy = energy_from_cpu_estimation(device_profile, total_cpu)

            task_profile = {
                'rtt': row['RTT_AVG'],
                # 'rtt_std': row['RTT_STD'],
                'energy': energy
            }

            tasks.setdefault(
                row['workload'], {}
            ).setdefault(
                row['service'], {}
            ).setdefault(
                row['task'], task_profile
            )

        profile[setup] = {
            'tasks': tasks,
            'meta': {
                'device_id': device_profile['id'],
                'iddle_energy': device_profile['p_idle']
            }
        }
    return profile


def get_device_energy_profile(profile_id):
    """
    (Dinita et al 2013) (Lin et al., 2018) have
    P_max = 239 W/hour (full load)
    P_idle = 124 W/hour (baseline)

    more recent rack servers have better energy usage, like the powerEdge R7715 for instance.
    """
    # 32CPU and 128GB RAM

    profiles = {
        'PowerEdge-R7715-320-threads-VM-32-CPU': {
            'id': 'PowerEdge-R7715-320-threads-VM-32-CPU',
            'p_max': 134,
            'p_idle': 70
        },
        'Cloud-Dinita et al 2013': {
            'id': 'Dinita et al 2013',
            'p_max': 239,
            'p_idle': 124
        },
        'Rpi4Test': {
            'id': 'Rpi4Test',
            'p_max': 12,
            'p_idle': 2
        }
    }

    # using as ref PowerEdge R7715: https://www.spec.org/power_ssj2008/results/res2025q4/power_ssj2008-20250915-01539-power.html#1
    # 32 of 320 available from the benchmark, gives 10% usage at full capacity of the VM cpu.
    return profiles.get(profile_id)


def energy_from_cpu_estimation(device_profile, cpu_perc):
    """
    Based on:
        Hanafy, Walid A., Amr E. Mohamed, and Sameh A. Salem. "A new infrastructure elasticity control algorithm for containerized cloud." IEEE Access 7 (2019): 39731-39741.
    and:
        Li, Zhihua, et al. "Energy-Efficient and Load-Aware VM Placement in Cloud Data Centers: Energy-Efficient and Load-Aware VM Placement in Cloud Data Centers." Journal of Grid Computing 20.4 (2022): 39.


    A commonly used model is the one from Hanafy et al. and from Li et al.,  that calculates total server power (P_total) utilization
    over a given period:
    P_total = (P_max - P_idle) × CPU_utilization + P_idle
    Where:
    P_total is in W
    P_max = 239 W (full load)
    P_idle = 124 W (baseline)
    CPU_utilization = current CPU usage (0-100%)
    """
    p_max = device_profile['p_max']
    p_idle = device_profile['p_idle']

    # relative consumption from cpu usaged
    p_total = ((p_max - p_idle) * (cpu_perc)) / 100
    # basic usage from idle:
    p_total += p_idle

    return p_total


# def estimate_total_energy_consumption(energy_profile, schedule):
#     """
#     Eq. (4) from Li et al. (2022): EC = ∫ P(U(t)) dt

#     schedule: iterable of (cpu_perc, duration_hours)
#     """
#     total_wh = 0.0
#     for cpu_perc, duration_h in schedule:
#         p_total = energy_from_cpu_estimation(energy_profile, cpu_perc)
#         total_wh += p_total * duration_h
#     return total_wh  # Wh


def create_task_profiling_json(df, profiling_id, setup_devices):
    profiling_file_path = Path(POSTPROCESSING_TASK_PROFILES_DIR) / f'{profiling_id}.json'
    tasks_profile = create_tasks_energy_profile(df, setup_devices)
    with open(profiling_file_path, 'w') as f:
        json.dump(tasks_profile, f, indent=4)
    return profiling_file_path
