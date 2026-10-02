import datetime

from .base import BaseUseCase


class UseCaseA(BaseUseCase):
    """
        Use Case A: Integrated crop-protection and pesticide use reporting for vineyards (Farm Calendar, Pest and Disease Management, Weather Service)

        A micro SME with expertise in ICT  is located in a rural area in Greece and wants to get into the smart agriculture business. They decided to collaborate with local farm advisors and to offer digital services including recording of farm management practices, decision support on crop protection and reporting about pesticides use. They have a new contract with a local farmers association cultivating vineyards.
        We consider a small use-case, with a low workload scenario, where the farmers association has 2 members/farmers and each farmer manages from 1-5 parcels. Each parcel covers an area from 1-5 hectares.

        For grapevines, the “cultivation period” usually means the period from budbreak to harvest. In most wine-grape and table-grape regions, it lasts about: 150–200 days. In Mediterranean climates, grapevines often start active growth around March–April and are harvested around August–September, depending on variety, altitude, irrigation, and intended use.

        The initial date of the simulation is set for the last day of February (one day to setup all the services and register parcels, etc..)
        and the final date is set for first day of November, after the harvest and reporting.
    """

    def __init__(self, base_workload, deployment_setup, tasks_profiling_id):
        init = datetime.date(2026, 2, 28)  # setup only, one day before March–April starts
        end = datetime.date(2026, 11, 1)   # after September–October (harvest + reporting)
        super().__init__(base_workload, deployment_setup, init, end, tasks_profiling_id)
        # if self.workload == 'low':
        #     self.farms = 2
        # elif self.workload == 'medium':
        #     self.farms = 45
        # elif self.workload == 'high':
        #     self.farms = 125
        self.farms = 2
        self.parcels_per_farm = 5
        self.parcels = self.farms * self.parcels_per_farm  # 10
        self.steps = {
            1: {
                'name': '1Day-Feb',
                'func': self.farm_parcel_and_crop_creation_step,
            },
            2: {
                'name': 'March-April',
                'func': self.march_april_budbreak_weed_first_disease_monitoring_step,
            },
            3: {
                'name': 'April-May',
                'func': self.april_may_shoot_thinning_sucker_removal_canopy_management_step,
            },
            4: {
                'name': 'May-June',
                'func': self.may_june_shoot_positioning_flowering_disease_protection_step,
            },
            5: {
                'name': 'June-July',
                'func': self.june_july_fruit_set_leaf_removal_cluster_thinning_irrigation_step,
            },
            6: {
                'name': 'July-August',
                'func': self.july_august_canopy_trimming_veraison_pest_disease_step,
            },
            7: {
                'name': 'August-September',
                'func': self.august_september_ripeness_final_irrigation_harvest_planning_step,
            },
            8: {
                'name': 'September-October',
                'func': self.september_october_harvest_and_reporting_step,
            },
        }

    def daily_navigation_tasks(self, days):
        task_scheduling = []

        # Farmer selects a parcel before viewing anything
        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'filter_parcels',
            'workload': self.workload,
            'repetition': self.parcels * days * 4,  # four times per day
            'description': 'Farmer selects a parcel from their list to view its details.',
        })

        # Then views the monthly activities list for that parcel
        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'monthly_activities',
            'workload': self.workload,
            'repetition': self.parcels * days * 2,  # twice times per day or navigating other months
            'description': 'Farmer opens the monthly calendar view for a parcel.',
        })

        # Then views into specific activity details
        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'get_activity',
            'workload': self.workload,
            'repetition': self.parcels * days * 4,  # a couple of activity details per parcel per day
            'description': 'Farmer opens detail view of a specific calendar activity.',
        })

        return task_scheduling

    def farm_parcel_and_crop_creation_step(self):
        days = 1
        task_scheduling = []
        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_farm',
            'workload': self.workload,
            'repetition': self.farms,
            'description': 'Register one farm per farmer account.',
        })
        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_parcel',
            'workload': self.workload,
            'repetition': self.parcels,
            'description': 'Register 5 parcel per farm.',
        })
        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_crop',
            'workload': self.workload,
            'repetition': self.parcels,
            'description': 'Register some grapevine crops for each parcel.',
        })
        # New activity/observation types registered for this use case (repetition = total count):
        #   March–April        (1): weed control
        #   June–July          (2): leaf removal, cluster thinning
        #   July–August        (1): canopy trimming
        #   August–September   (1): harvest planning
        #   September–October  (1): harvest
        #   ─────────────────────────────────────────────────────────────────────────────
        #   Total              (6)
        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_activity_type',
            'workload': self.workload,
            'repetition': 6,
            'description': 'Creating new generic activity types specific for the use case.',
        })
        # task_scheduling.extend(self.daily_navigation_tasks(days))
        return task_scheduling

    def march_april_budbreak_weed_first_disease_monitoring_step(self):
        # March–April period length (31 + 30 days)
        days = 31

        task_scheduling = []

        task_scheduling.append({
            'service': 'weather',
            'task': 'get_daily_forecast',
            'workload': self.workload,
            'repetition': self.parcels * days,
            'description': 'Daily weather forecast per parcel for budbreak and disease-risk context.',
        })

        task_scheduling.append({
            'service': 'pestanddisease',
            'task': 'calculate_gdd',
            'workload': self.workload,
            'repetition': self.parcels * days,
            'description': 'Daily growing-degree-day calculation per parcel to track budbreak progression.',
        })
        task_scheduling.append({
            'service': 'pestanddisease',
            'task': 'calculate_risk',
            'workload': self.workload,
            'repetition': self.parcels * days,
            'description': 'Daily pest/disease infestation risk query per parcel for first disease monitoring.',
        })

        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_obs',
            'workload': self.workload,
            'repetition': self.parcels,
            'description': 'Record budbreak monitoring observation on each parcel.',
        })

        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_gen_activity',
            'workload': self.workload,
            'repetition': self.parcels,
            'description': 'Record realised weed control activity on each parcel.',
        })

        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_obs',
            'workload': self.workload,
            'repetition': self.parcels,
            'description': 'Record first disease monitoring observation on each parcel.',
        })


        task_scheduling.extend(self.daily_navigation_tasks(days))
        return task_scheduling

    def april_may_shoot_thinning_sucker_removal_canopy_management_step(self):
        # Phenology/shoot observations during active growth, roughly weekly per parcel
        obs_rounds = 8  # ~one monitoring round per week over the period

        # April–May period length (30 + 31 days)
        days = 30

        task_scheduling = []

        task_scheduling.append({
            'service': 'weather',
            'task': 'get_daily_forecast',
            'workload': self.workload,
            'repetition': self.parcels * days,
            'description': 'Daily weather forecast per parcel to guide canopy management timing.',
        })

        task_scheduling.append({
            'service': 'pestanddisease',
            'task': 'calculate_gdd',
            'workload': self.workload,
            'repetition': self.parcels * days,
            'description': 'Daily growing-degree-day calculation per parcel to track vine development.',
        })
        task_scheduling.append({
            'service': 'pestanddisease',
            'task': 'calculate_risk',
            'workload': self.workload,
            'repetition': self.parcels * days,
            'description': 'Daily pest/disease infestation risk query per parcel during early canopy growth.',
        })

        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_obs',
            'workload': self.workload,
            'repetition': self.parcels * obs_rounds,
            'description': 'Record shoot development / phenology stage observation on each parcel during active growth.',
        })

        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_obs',
            'workload': self.workload,
            'repetition': self.parcels,
            'description': 'Record early canopy assessment observation on each parcel (density, vigor, light penetration).',
        })

        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_obs',
            'workload': self.workload,
            'repetition': self.parcels,
            'description': 'Record any early disease/pest symptoms noticed during manual canopy work on each parcel.',
        })

        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_gen_activity',
            'workload': self.workload,
            'repetition': self.parcels,        # shoot thinning: once per parcel per season
            'description': 'Record realised shoot thinning activity on each parcel.',
        })

        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_gen_activity',
            'workload': self.workload,
            'repetition': self.parcels * 2,    # sucker removal: typically repeated once
            'description': 'Record realised sucker removal activity on each parcel.',
        })

        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_gen_activity',
            'workload': self.workload,
            'repetition': self.parcels * 3,    # canopy management: several small interventions per parcel
            'description': 'Record realised early canopy management activity on each parcel.',
        })


        task_scheduling.extend(self.daily_navigation_tasks(days))
        return task_scheduling


    def may_june_shoot_positioning_flowering_disease_protection_step(self):
        # May–June period length (31 + 30 days)
        days = 31

        # Flowering monitoring is intensive; roughly every 2–3 days per parcel
        flowering_obs_rounds = 20

        task_scheduling = []

        # --- Daily automated context ---
        task_scheduling.append({
            'service': 'weather',
            'task': 'get_daily_forecast',
            'workload': self.workload,
            'repetition': self.parcels * days,
            'description': 'Daily weather forecast per parcel for flowering and disease-protection timing.',
        })

        task_scheduling.append({
            'service': 'pestanddisease',
            'task': 'calculate_gdd',
            'workload': self.workload,
            'repetition': self.parcels * days,
            'description': 'Daily growing-degree-day calculation per parcel to track flowering progression.',
        })
        task_scheduling.append({
            'service': 'pestanddisease',
            'task': 'calculate_risk',
            'workload': self.workload,
            'repetition': self.parcels * days,
            'description': 'Daily pest/disease infestation risk query per parcel during flowering.',
        })

        # --- Realised farming activities ---
        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_gen_activity',
            'workload': self.workload,
            'repetition': self.parcels * 2,
            'description': 'Record realised shoot positioning activity on each parcel.',
        })

        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_gen_activity',
            'workload': self.workload,
            'repetition': self.parcels * 3,
            'description': 'Record realised disease-protection (plant protection product) applications on each parcel.',
        })

        # --- Observations ---
        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_obs',
            'workload': self.workload,
            'repetition': self.parcels * flowering_obs_rounds,
            'description': 'Record flowering monitoring observation on each parcel (stage, uniformity, bloom).',
        })

        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_obs',
            'workload': self.workload,
            'repetition': self.parcels,
            'description': 'Record disease/pest symptoms noticed during shoot positioning and disease-protection rounds.',
        })


        task_scheduling.extend(self.daily_navigation_tasks(days))
        return task_scheduling

    def june_july_fruit_set_leaf_removal_cluster_thinning_irrigation_step(self):
        # June–July period length (30 + 31 days)
        days = 30

        task_scheduling = []

        # --- Daily automated context ---
        task_scheduling.append({
            'service': 'weather',
            'task': 'get_daily_forecast',
            'workload': self.workload,
            'repetition': self.parcels * days,
            'description': 'Daily weather forecast per parcel for irrigation and canopy-management decisions.',
        })

        task_scheduling.append({
            'service': 'pestanddisease',
            'task': 'calculate_gdd',
            'workload': self.workload,
            'repetition': self.parcels * days,
            'description': 'Daily growing-degree-day calculation per parcel to track fruit development.',
        })
        task_scheduling.append({
            'service': 'pestanddisease',
            'task': 'calculate_risk',
            'workload': self.workload,
            'repetition': self.parcels * days,
            'description': 'Daily pest/disease infestation risk query per parcel during fruit set and cluster development.',
        })

        # --- Realised farming activities ---
        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_gen_activity',
            'workload': self.workload,
            'repetition': self.parcels,
            'description': 'Record realised leaf removal activity on each parcel.',
        })

        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_gen_activity',
            'workload': self.workload,
            'repetition': self.parcels,
            'description': 'Record realised cluster thinning activity on each parcel.',
        })

        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_gen_activity',
            'workload': self.workload,
            'repetition': self.parcels * 4,
            'description': 'Record realised irrigation management activity on each parcel (repeated through the period).',
        })

        # --- Observations ---
        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_obs',
            'workload': self.workload,
            'repetition': self.parcels,
            'description': 'Record fruit set assessment observation on each parcel.',
        })

        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_obs',
            'workload': self.workload,
            'repetition': self.parcels,
            'description': 'Record any disease/pest symptoms noticed during fruit set and cluster work on each parcel.',
        })


        task_scheduling.extend(self.daily_navigation_tasks(days))
        return task_scheduling

    def july_august_canopy_trimming_veraison_pest_disease_step(self):
        # July–August period length (31 + 31 days)
        days = 31

        # Veraison monitoring is intensive during the ripening transition
        veraison_obs_rounds = 15

        task_scheduling = []

        # --- Daily automated context ---
        task_scheduling.append({
            'service': 'weather',
            'task': 'get_daily_forecast',
            'workload': self.workload,
            'repetition': self.parcels * days,
            'description': 'Daily weather forecast per parcel for canopy trimming and pest/disease control timing.',
        })

        task_scheduling.append({
            'service': 'pestanddisease',
            'task': 'calculate_gdd',
            'workload': self.workload,
            'repetition': self.parcels * days,
            'description': 'Daily growing-degree-day calculation per parcel to track veraison progression.',
        })
        task_scheduling.append({
            'service': 'pestanddisease',
            'task': 'calculate_risk',
            'workload': self.workload,
            'repetition': self.parcels * days,
            'description': 'Daily pest/disease infestation risk query per parcel during veraison.',
        })

        # --- Realised farming activities ---
        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_gen_activity',
            'workload': self.workload,
            'repetition': self.parcels * 2,
            'description': 'Record realised canopy trimming activity on each parcel.',
        })

        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_gen_activity',
            'workload': self.workload,
            'repetition': self.parcels * 3,
            'description': 'Record realised pest and disease control (plant protection product) applications on each parcel.',
        })

        # --- Observations ---
        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_obs',
            'workload': self.workload,
            'repetition': self.parcels * veraison_obs_rounds,
            'description': 'Record veraison monitoring observation on each parcel (colour change, ripening stage).',
        })

        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_obs',
            'workload': self.workload,
            'repetition': self.parcels,
            'description': 'Record pest/disease symptoms noticed during canopy trimming and control rounds on each parcel.',
        })


        task_scheduling.extend(self.daily_navigation_tasks(days))
        return task_scheduling

    def august_september_ripeness_final_irrigation_harvest_planning_step(self):
        # August–September period length (31 + 30 days)
        days = 31

        # Ripeness sampling intensifies approaching harvest
        ripeness_obs_rounds = 20

        task_scheduling = []

        # --- Daily automated context ---
        task_scheduling.append({
            'service': 'weather',
            'task': 'get_daily_forecast',
            'workload': self.workload,
            'repetition': self.parcels * days,
            'description': 'Daily weather forecast per parcel for final irrigation and harvest-planning decisions.',
        })

        task_scheduling.append({
            'service': 'pestanddisease',
            'task': 'calculate_gdd',
            'workload': self.workload,
            'repetition': self.parcels * days,
            'description': 'Daily growing-degree-day calculation per parcel to track ripening progression.',
        })
        task_scheduling.append({
            'service': 'pestanddisease',
            'task': 'calculate_risk',
            'workload': self.workload,
            'repetition': self.parcels * days,
            'description': 'Daily pest/disease infestation risk query per parcel approaching harvest.',
        })

        # --- Realised farming activities ---
        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_gen_activity',
            'workload': self.workload,
            'repetition': self.parcels * 2,
            'description': 'Record realised final irrigation decision activity on each parcel.',
        })

        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_gen_activity',
            'workload': self.workload,
            'repetition': self.parcels,
            'description': 'Record realised harvest planning activity on each parcel.',
        })

        # --- Observations ---
        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_obs',
            'workload': self.workload,
            'repetition': self.parcels * ripeness_obs_rounds,
            'description': 'Record ripeness sampling observation on each parcel (sugar, acidity, phenolics).',
        })

        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_obs',
            'workload': self.workload,
            'repetition': self.parcels,
            'description': 'Record final disease/pest symptoms check on each parcel before harvest.',
        })


        task_scheduling.extend(self.daily_navigation_tasks(days))
        return task_scheduling

    def september_october_harvest_and_reporting_step(self):
        # September–October period length (30 + 31 days)
        days = 30

        task_scheduling = []

        # --- Daily automated context (still used for harvest-timing decisions) ---
        task_scheduling.append({
            'service': 'weather',
            'task': 'get_daily_forecast',
            'workload': self.workload,
            'repetition': self.parcels * days,
            'description': 'Daily weather forecast per parcel to finalise harvest timing.',
        })

        # --- Realised farming activities ---
        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_gen_activity',
            'workload': self.workload,
            'repetition': self.parcels,
            'description': 'Record realised harvest activity on each parcel.',
        })

        # --- Observations ---
        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_obs',
            'workload': self.workload,
            'repetition': self.parcels,
            'description': 'Record final pre-harvest observation (ripeness confirmation, yield estimate) on each parcel.',
        })

        # --- Reporting ---
        task_scheduling.append({
            'service': 'reporting',
            'task': 'standalone_report',
            'workload': self.workload,
            'repetition': self.parcels,
            'description': 'Generate per-parcel report of all farm practices applied over the cultivation period.',
        })

        task_scheduling.append({
            'service': 'reporting',
            'task': 'pesticides_report',
            'workload': self.workload,
            'repetition': self.parcels,
            'description': 'Generate per-parcel annual pesticide-use report according to legislation.',
        })


        task_scheduling.extend(self.daily_navigation_tasks(days))
        return task_scheduling

