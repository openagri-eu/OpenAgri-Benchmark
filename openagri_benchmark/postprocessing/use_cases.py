import json
import os

from openagri_benchmark.conf import (
    POSTPROCESSING_TASK_PROFILES_DIR,
)



class BaseUseCase(object):

    def __init__(self, deployment_setup, init_datetime, end_datatime, tasks_profiling_id):
        self.deployment_setup = deployment_setup
        self.init_datetime = init_datetime
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
        for step, task_scheduling_op in self.steps.items():
            task_scheduling = task_scheduling_op()
            task_stats = self.get_stats_for_task_scheduling(task_scheduling)
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




class UseCase1(BaseUseCase):

    def __init__(self, deployment_setup, init_datetime, end_datatime,  tasks_profiling_id):
        super().__init__(deployment_setup, init_datetime, end_datatime, tasks_profiling_id)
        self.steps = {
            1: self.farm_parcel_and_crop_creation_step,
            2: self.march_april_budbreak_weed_first_disease_monitoring_step,
            3: self.april_may_shoot_thinning_sucker_removal_canopy_management_step,
            4: self.may_june_shoot_positioning_flowering_disease_protection_step,
            5: self.june_july_fruit_set_leaf_removal_cluster_thinning_irrigation_step,
            6: self.july_august_canopy_trimming_veraison_pest_disease_step,
            7: self.august_september_ripeness_final_irrigation_harvest_planning_step,
            8: self.september_october_harvest_and_reporting_step,
        }

    def farm_parcel_and_crop_creation_step(self):
        workload = 'low'
        task_scheduling = []
        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_farm',
            'workload': workload,
            'repetition': 2,
            'description': 'Register one farm per farmer account.',
        })
        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_parcel',
            'workload': workload,
            'repetition': 10,
            'description': 'Register 5 parcel per farm.',
        })
        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_crop',
            'workload': workload,
            'repetition': 10,
            'description': 'Register some grapevine crops for each parcel.',
        })
        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_activity_type',
            'workload': workload,
            'repetition': 3,
            'description': 'Define activity types for march_april period.',
        })
        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_activity_type',
            'workload': workload,
            'repetition': 3,
            'description': 'Define observation types for april_may period.',
        })
        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_activity_type',
            'workload': workload,
            'repetition': 1,
            'description': 'Define observation types for may_june period.',
        })
        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_activity_type',
            'workload': workload,
            'repetition': 4,
            'description': 'Define activity types for june_july period.',
        })
        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_activity_type',
            'workload': workload,
            'repetition': 3,
            'description': 'Define activity types for july_august period.',
        })
        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_activity_type',
            'workload': workload,
            'repetition': 3,
            'description': 'Define activity types for august_september period.',
        })
        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_activity_type',
            'workload': workload,
            'repetition': 1,
            'description': 'Define activity types for september_october period.',
        })
        return task_scheduling


    def march_april_budbreak_weed_first_disease_monitoring_step(self):
        workload = 'low'

        # Reduced simulation workload: 2 farms, 5 parcels each => 10 parcels total
        farms = 2
        parcels_per_farm = 5
        parcels = farms * parcels_per_farm  # 10

        # March–April period length (31 + 30 days)
        days = 61

        task_scheduling = []

        task_scheduling.append({
            'service': 'weather',
            'task': 'get_daily_forecast',
            'workload': workload,
            'repetition': parcels * days,
            'description': 'Daily weather forecast per parcel for budbreak and disease-risk context.',
        })

        task_scheduling.append({
            'service': 'pestanddisease',
            'task': 'calculate_gdd',
            'workload': workload,
            'repetition': parcels * days,
            'description': 'Daily growing-degree-day calculation per parcel to track budbreak progression.',
        })
        task_scheduling.append({
            'service': 'pestanddisease',
            'task': 'calculate_risk',
            'workload': workload,
            'repetition': parcels * days,
            'description': 'Daily pest/disease infestation risk query per parcel for first disease monitoring.',
        })

        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_obs',
            'workload': workload,
            'repetition': parcels,
            'description': 'Record budbreak monitoring observation on each parcel.',
        })

        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_gen_activity',
            'workload': workload,
            'repetition': parcels,
            'description': 'Record realised weed control activity on each parcel.',
        })

        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_obs',
            'workload': workload,
            'repetition': parcels,
            'description': 'Record first disease monitoring observation on each parcel.',
        })

        return task_scheduling

    def april_may_shoot_thinning_sucker_removal_canopy_management_step(self):
        workload = 'low'

        # Reduced simulation workload: 2 farms, 5 parcels each => 10 parcels total
        farms = 2
        parcels_per_farm = 5
        parcels = farms * parcels_per_farm  # 10

        # Phenology/shoot observations during active growth, roughly weekly per parcel
        obs_rounds = 8  # ~one monitoring round per week over the period

        # April–May period length (30 + 31 days)
        days = 61

        task_scheduling = []

        task_scheduling.append({
            'service': 'weather',
            'task': 'get_daily_forecast',
            'workload': workload,
            'repetition': parcels * days,
            'description': 'Daily weather forecast per parcel to guide canopy management timing.',
        })

        task_scheduling.append({
            'service': 'pestanddisease',
            'task': 'calculate_gdd',
            'workload': workload,
            'repetition': parcels * days,
            'description': 'Daily growing-degree-day calculation per parcel to track vine development.',
        })
        task_scheduling.append({
            'service': 'pestanddisease',
            'task': 'calculate_risk',
            'workload': workload,
            'repetition': parcels * days,
            'description': 'Daily pest/disease infestation risk query per parcel during early canopy growth.',
        })

        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_obs',
            'workload': workload,
            'repetition': parcels * obs_rounds,
            'description': 'Record shoot development / phenology stage observation on each parcel during active growth.',
        })

        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_obs',
            'workload': workload,
            'repetition': parcels,
            'description': 'Record early canopy assessment observation on each parcel (density, vigor, light penetration).',
        })

        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_obs',
            'workload': workload,
            'repetition': parcels,
            'description': 'Record any early disease/pest symptoms noticed during manual canopy work on each parcel.',
        })

        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_gen_activity',
            'workload': workload,
            'repetition': parcels,        # shoot thinning: once per parcel per season
            'description': 'Record realised shoot thinning activity on each parcel.',
        })

        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_gen_activity',
            'workload': workload,
            'repetition': parcels * 2,    # sucker removal: typically repeated once
            'description': 'Record realised sucker removal activity on each parcel.',
        })

        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_gen_activity',
            'workload': workload,
            'repetition': parcels * 3,    # canopy management: several small interventions per parcel
            'description': 'Record realised early canopy management activity on each parcel.',
        })

        return task_scheduling


    def may_june_shoot_positioning_flowering_disease_protection_step(self):
        workload = 'low'

        # Reduced simulation workload: 2 farms, 5 parcels each => 10 parcels total
        farms = 2
        parcels_per_farm = 5
        parcels = farms * parcels_per_farm  # 10

        # May–June period length (31 + 30 days)
        days = 61

        # Flowering monitoring is intensive; roughly every 2–3 days per parcel
        flowering_obs_rounds = 20

        task_scheduling = []

        # --- Daily automated context ---
        task_scheduling.append({
            'service': 'weather',
            'task': 'get_daily_forecast',
            'workload': workload,
            'repetition': parcels * days,
            'description': 'Daily weather forecast per parcel for flowering and disease-protection timing.',
        })

        task_scheduling.append({
            'service': 'pestanddisease',
            'task': 'calculate_gdd',
            'workload': workload,
            'repetition': parcels * days,
            'description': 'Daily growing-degree-day calculation per parcel to track flowering progression.',
        })
        task_scheduling.append({
            'service': 'pestanddisease',
            'task': 'calculate_risk',
            'workload': workload,
            'repetition': parcels * days,
            'description': 'Daily pest/disease infestation risk query per parcel during flowering.',
        })

        # --- Realised farming activities ---
        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_gen_activity',
            'workload': workload,
            'repetition': parcels * 2,
            'description': 'Record realised shoot positioning activity on each parcel.',
        })

        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_gen_activity',
            'workload': workload,
            'repetition': parcels * 3,
            'description': 'Record realised disease-protection (plant protection product) applications on each parcel.',
        })

        # --- Observations ---
        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_obs',
            'workload': workload,
            'repetition': parcels * flowering_obs_rounds,
            'description': 'Record flowering monitoring observation on each parcel (stage, uniformity, bloom).',
        })

        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_obs',
            'workload': workload,
            'repetition': parcels,
            'description': 'Record disease/pest symptoms noticed during shoot positioning and disease-protection rounds.',
        })

        return task_scheduling

    def june_july_fruit_set_leaf_removal_cluster_thinning_irrigation_step(self):
        workload = 'low'

        # Reduced simulation workload: 2 farms, 5 parcels each => 10 parcels total
        farms = 2
        parcels_per_farm = 5
        parcels = farms * parcels_per_farm  # 10

        # June–July period length (30 + 31 days)
        days = 61

        task_scheduling = []

        # --- Daily automated context ---
        task_scheduling.append({
            'service': 'weather',
            'task': 'get_daily_forecast',
            'workload': workload,
            'repetition': parcels * days,
            'description': 'Daily weather forecast per parcel for irrigation and canopy-management decisions.',
        })

        task_scheduling.append({
            'service': 'pestanddisease',
            'task': 'calculate_gdd',
            'workload': workload,
            'repetition': parcels * days,
            'description': 'Daily growing-degree-day calculation per parcel to track fruit development.',
        })
        task_scheduling.append({
            'service': 'pestanddisease',
            'task': 'calculate_risk',
            'workload': workload,
            'repetition': parcels * days,
            'description': 'Daily pest/disease infestation risk query per parcel during fruit set and cluster development.',
        })

        # --- Realised farming activities ---
        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_gen_activity',
            'workload': workload,
            'repetition': parcels,
            'description': 'Record realised leaf removal activity on each parcel.',
        })

        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_gen_activity',
            'workload': workload,
            'repetition': parcels,
            'description': 'Record realised cluster thinning activity on each parcel.',
        })

        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_gen_activity',
            'workload': workload,
            'repetition': parcels * 4,
            'description': 'Record realised irrigation management activity on each parcel (repeated through the period).',
        })

        # --- Observations ---
        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_obs',
            'workload': workload,
            'repetition': parcels,
            'description': 'Record fruit set assessment observation on each parcel.',
        })

        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_obs',
            'workload': workload,
            'repetition': parcels,
            'description': 'Record any disease/pest symptoms noticed during fruit set and cluster work on each parcel.',
        })

        return task_scheduling

    def july_august_canopy_trimming_veraison_pest_disease_step(self):
        workload = 'low'

        # Reduced simulation workload: 2 farms, 5 parcels each => 10 parcels total
        farms = 2
        parcels_per_farm = 5
        parcels = farms * parcels_per_farm  # 10

        # July–August period length (31 + 31 days)
        days = 62

        # Veraison monitoring is intensive during the ripening transition
        veraison_obs_rounds = 15

        task_scheduling = []

        # --- Daily automated context ---
        task_scheduling.append({
            'service': 'weather',
            'task': 'get_daily_forecast',
            'workload': workload,
            'repetition': parcels * days,
            'description': 'Daily weather forecast per parcel for canopy trimming and pest/disease control timing.',
        })

        task_scheduling.append({
            'service': 'pestanddisease',
            'task': 'calculate_gdd',
            'workload': workload,
            'repetition': parcels * days,
            'description': 'Daily growing-degree-day calculation per parcel to track veraison progression.',
        })
        task_scheduling.append({
            'service': 'pestanddisease',
            'task': 'calculate_risk',
            'workload': workload,
            'repetition': parcels * days,
            'description': 'Daily pest/disease infestation risk query per parcel during veraison.',
        })

        # --- Realised farming activities ---
        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_gen_activity',
            'workload': workload,
            'repetition': parcels * 2,
            'description': 'Record realised canopy trimming activity on each parcel.',
        })

        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_gen_activity',
            'workload': workload,
            'repetition': parcels * 3,
            'description': 'Record realised pest and disease control (plant protection product) applications on each parcel.',
        })

        # --- Observations ---
        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_obs',
            'workload': workload,
            'repetition': parcels * veraison_obs_rounds,
            'description': 'Record veraison monitoring observation on each parcel (colour change, ripening stage).',
        })

        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_obs',
            'workload': workload,
            'repetition': parcels,
            'description': 'Record pest/disease symptoms noticed during canopy trimming and control rounds on each parcel.',
        })

        return task_scheduling

    def august_september_ripeness_final_irrigation_harvest_planning_step(self):
        workload = 'low'

        # Reduced simulation workload: 2 farms, 5 parcels each => 10 parcels total
        farms = 2
        parcels_per_farm = 5
        parcels = farms * parcels_per_farm  # 10

        # August–September period length (31 + 30 days)
        days = 61

        # Ripeness sampling intensifies approaching harvest
        ripeness_obs_rounds = 20

        task_scheduling = []

        # --- Daily automated context ---
        task_scheduling.append({
            'service': 'weather',
            'task': 'get_daily_forecast',
            'workload': workload,
            'repetition': parcels * days,
            'description': 'Daily weather forecast per parcel for final irrigation and harvest-planning decisions.',
        })

        task_scheduling.append({
            'service': 'pestanddisease',
            'task': 'calculate_gdd',
            'workload': workload,
            'repetition': parcels * days,
            'description': 'Daily growing-degree-day calculation per parcel to track ripening progression.',
        })
        task_scheduling.append({
            'service': 'pestanddisease',
            'task': 'calculate_risk',
            'workload': workload,
            'repetition': parcels * days,
            'description': 'Daily pest/disease infestation risk query per parcel approaching harvest.',
        })

        # --- Realised farming activities ---
        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_gen_activity',
            'workload': workload,
            'repetition': parcels * 2,
            'description': 'Record realised final irrigation decision activity on each parcel.',
        })

        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_gen_activity',
            'workload': workload,
            'repetition': parcels,
            'description': 'Record realised harvest planning activity on each parcel.',
        })

        # --- Observations ---
        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_obs',
            'workload': workload,
            'repetition': parcels * ripeness_obs_rounds,
            'description': 'Record ripeness sampling observation on each parcel (sugar, acidity, phenolics).',
        })

        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_obs',
            'workload': workload,
            'repetition': parcels,
            'description': 'Record final disease/pest symptoms check on each parcel before harvest.',
        })

        return task_scheduling

    def september_october_harvest_and_reporting_step(self):
        workload = 'low'

        # Reduced simulation workload: 2 farms, 5 parcels each => 10 parcels total
        farms = 2
        parcels_per_farm = 5
        parcels = farms * parcels_per_farm  # 10

        # September–October period length (30 + 31 days)
        days = 61

        task_scheduling = []

        # --- Daily automated context (still used for harvest-timing decisions) ---
        task_scheduling.append({
            'service': 'weather',
            'task': 'get_daily_forecast',
            'workload': workload,
            'repetition': parcels * days,
            'description': 'Daily weather forecast per parcel to finalise harvest timing.',
        })

        # --- Realised farming activities ---
        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_gen_activity',
            'workload': workload,
            'repetition': parcels,
            'description': 'Record realised harvest activity on each parcel.',
        })

        # --- Observations ---
        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_obs',
            'workload': workload,
            'repetition': parcels,
            'description': 'Record final pre-harvest observation (ripeness confirmation, yield estimate) on each parcel.',
        })

        # --- Reporting ---
        task_scheduling.append({
            'service': 'reporting',
            'task': 'standalone_report',
            'workload': workload,
            'repetition': parcels,
            'description': 'Generate per-parcel report of all farm practices applied over the cultivation period.',
        })

        task_scheduling.append({
            'service': 'reporting',
            'task': 'pesticides_report',
            'workload': workload,
            'repetition': parcels,
            'description': 'Generate per-parcel annual pesticide-use report according to legislation.',
        })

        return task_scheduling
