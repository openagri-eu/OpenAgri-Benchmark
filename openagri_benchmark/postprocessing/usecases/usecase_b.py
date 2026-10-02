import datetime

from .base import BaseUseCase


class UseCaseB(BaseUseCase):
    """
    Use Case B — Irrigation workflow for irrigated field crops (Farm Calendar, Irrigation Service, Weather Service, Reporting Service)

    A micro SME with expertise in ICT is located in a rural area in Poland and wants to get into the smart agriculture business.
    Given the increasing frequency of droughts in the region, they decided to collaborate with local farm advisors and to offer
      digital services to irrigated-field farmers, including recording of farm management practices, decision support on irrigation timing and dose,
      and reporting about water use. They have a new contract with a local farmers cooperative.

    We consider a low workload for this use case, with very sparse brust of medium workload use case,
        where the cooperative has 30 members/farmers and each farmer manages 5 parcels.
    Each parcel covers an area from 1–5 hectares.

    The irrigation season runs from crop establishment to harvest, roughly March–October depending on the crop (e.g., potatoes, sugar beet, maize) and the intended use.

    The initial date of the simulation is set for the last day of February (one day to setup all the services and register farms, parcels and crops) and
        the final date is set for the first day of November, after the harvest and reporting.
    """

    def __init__(self, base_workload, deployment_setup, tasks_profiling_id):
        init = datetime.date(2026, 2, 28)  # setup only, one day before the season starts
        end = datetime.date(2026, 11, 1)   # after harvest + reporting
        super().__init__(base_workload, deployment_setup, init, end, tasks_profiling_id)
        self.farms = 30
        self.parcels_per_farm = 5
        self.parcels = self.farms * self.parcels_per_farm  # 150 at medium

        self.steps = {
            1: {
                'name': '1Day-Feb',
                'func': self.registering_and_initial_setup,
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

    def registering_and_initial_setup(self):
        days = 1
        task_scheduling = []

        # --- Farm / parcel / crop registration ---
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
            'description': 'Register 5 parcels per farm.',
        })
        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_crop',
            'workload': self.workload,
            'repetition': self.parcels,
            'description': 'Register the crop on each parcel (potatoes, sugar beet, maize, vegetables).',
        })

        # New activity/observation types registered for this use case (repetition = total count):
        #   Planting                     (1)
        #   Harvest                      (1)
        #   Weather observation          (1)
        #   Soil moisture observation    (1)
        #   ─────────────────────────────────────
        #   Total                        (4)
        #
        # Note: irrigation operations and crop growth stage observations use the
        # existing Farm Calendar built-in types (IrrigationOperation,
        # CropGrowthStageObservation).
        task_scheduling.append({
            'service': 'farmcalendar',
            'task': 'register_activity_type',
            'workload': self.workload,
            'repetition': 4,
            'description': 'Creating new generic activity types specific for the use case.',
        })

        # --- Regular daily navigation (only 1 day here, setup day) ---
        task_scheduling.extend(self.daily_navigation_tasks(days))
        return task_scheduling
