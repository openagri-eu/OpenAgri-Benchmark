import inspect
import json
import os

from openagri_benchmark.conf import (
    POSTPROCESSING_TASK_PROFILES_DIR,
)



class BaseUseCase(object):

    def __init__(self, base_workload, deployment_setup, init_datetime, end_datatime, tasks_profiling_id):
        self.workload = base_workload
        self.deployment_setup = deployment_setup
        self.init_datetime = init_datetime
        self.current_datetime = init_datetime
        self.end_datetime = end_datatime
        self.total_hours = (self.end_datetime - self.init_datetime).total_seconds() / 3600
        self.tasks_profiling = self.load_task_profile(tasks_profiling_id)
        self.steps = {
        }

    def load_task_profile(self, tasks_profiling_id):
        profiling_file_path = os.path.join(POSTPROCESSING_TASK_PROFILES_DIR, f'{tasks_profiling_id}.json')
        with open(profiling_file_path, 'r') as f:
            return json.load(f)


    def get_stats_for_task_scheduling(self, task_scheduling):
        total_energy = 0
        deployment_profiling = self.tasks_profiling[self.deployment_setup]['tasks']
        total_duration = 0
        for task_s in task_scheduling:
            task_workloads = deployment_profiling[task_s['workload']]
            tasks_service = task_workloads[task_s['service']]

            task_profile = tasks_service[task_s['task']]
            task_energy_w = task_profile['energy']
            task_duration = task_profile['rtt'] * task_s['repetition']
            task_duration_h = task_duration / 360
            task_energy_wh = task_energy_w * task_duration_h
            total_energy += task_energy_wh
            total_duration += task_duration_h
        return {
            'energy': total_energy,
            'duration': total_duration,
            'scheduling': task_scheduling,
        }

    def calculate_iddle(self, proc_time):
        iddle_time_h = self.total_hours - proc_time
        iddle_energy = self.tasks_profiling[self.deployment_setup]['meta']['iddle_energy']
        iddle_total_energy = iddle_energy * iddle_time_h
        return {
            'iddle_energy': iddle_total_energy,
            'iddle_time': iddle_time_h,
        }


    def run(self):
        totals = {
            'proc_energy': 0,
            'proc_time': 0
        }
        steps_results = {}
        for step, step_details in self.steps.items():
            step_name = step_details['name']
            task_stats = {'step_name': step_name}

            task_scheduling_op = step_details['func']
            task_scheduling = task_scheduling_op()
            task_stats.update(self.get_stats_for_task_scheduling(task_scheduling))
            steps_results[step] = task_stats
            totals['proc_energy'] += task_stats['energy']
            totals['proc_time'] += task_stats['duration']

        totals.update(self.calculate_iddle(totals['proc_time']))
        totals['total_energy'] = totals['proc_energy'] + totals['iddle_energy']
        totals['total_time'] = totals['proc_time'] + totals['iddle_time']
        results = {
            'steps': steps_results,
            'totals': totals
        }
        return results

    @classmethod
    def get_markdown_of_usecase_steps(cls, results):
        # ---- Header: class name + class docstring ----
        title = f'# {cls.__name__}\n'
        desc = (inspect.getdoc(cls) or '').strip()
        full_md_text = title + '\n' + desc + '\n\n' if desc else title + '\n'
        full_md_text += "Table with detailed tasks per step/period: \n"
        full_md_text += "* *Service* : Which service is responsible for handling this task.\n"
        full_md_text += "* *Task* : Relates to specific a endpoint in a service web API.\n"
        full_md_text += "* *Workload* : Real-world workload profile use to simulated this task. Low = 2 Request Per Seconds(RPS); Medium = 30 RPS; High = 60 RPS\n"
        full_md_text += "* *Repetitions* : Number of times this task is repeated within a step/period, using the given workload profile. **Important to note:** 1 repetition with Medium workload (i.e., 30 RPS) is equivalent to 30 users doing the same task at the same time once.\n"
        full_md_text += "* *Description* : Description of the task being simulated.\n"
        for step_i, step_dict in results['steps'].items():
            title = f'## {step_i}: {step_dict["step_name"]}\n'
            # tasks_desc = [v['description'] for v in step_dict['scheduling']]
            # scheduling = '\n'.join(tasks_desc)
            # print(f'{scheduling}\n\n')

            headers = ["Service", "Task", "Workload", "Repetitions", "Description"]

            md_table = '\n'
            md_table += ("| " + " | ".join(headers) + " |" + "\n")
            md_table += ("|" + "|".join(["---"] * len(headers)) + "|" + "\n")

            for entry in step_dict["scheduling"]:
                row = [
                    entry["service"],
                    entry["task"],
                    entry["workload"],
                    str(entry["repetition"]),
                    entry["description"],
                ]
                md_table += ("| " + " | ".join(row) + " |" + '\n')

            step_text = title + md_table + "\n"
            full_md_text += step_text
        return full_md_text
