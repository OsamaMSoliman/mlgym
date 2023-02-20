from enum import Enum
from ml_gym.blueprints.blue_prints import BluePrint
from ml_gym.gym.gym_jobs.gym_job import AbstractGymJob
from ml_gym.persistency.io import GridSearchAPIClientConstructable
from ml_gym.persistency.logging import ExperimentStatusLogger, MLgymStatusLoggerCollectionConstructable
import torch


class GymJobType(Enum):
    HF_ACCELERATE = "HF_ACCELERATE"
    STANDARD = "STANDARD"


class GymJobFactory:

    @staticmethod
    def get_gym_job_from_blueprint(blueprint: BluePrint, device: torch.device,
                                   logger_collection_constructable: MLgymStatusLoggerCollectionConstructable,
                                   gs_restful_api_client_constructable: GridSearchAPIClientConstructable) -> AbstractGymJob:
        components = blueprint.construct(device)

        logger_collection = logger_collection_constructable.construct()
        experiment_status_logger = ExperimentStatusLogger(logger=logger_collection, grid_search_id=blueprint.grid_search_id,
                                                          experiment_id=blueprint.experiment_id)
        gs_api_client = gs_restful_api_client_constructable.construct()

        gym_job = GymJob(run_mode=blueprint.run_mode,
                         grid_search_id=blueprint.grid_search_id,
                         experiment_id=blueprint.experiment_id,
                         num_epochs=blueprint.num_epochs,
                         warm_start_epoch=blueprint.warm_start_epoch,
                         experiment_status_logger=experiment_status_logger,
                         gs_api_client=gs_api_client,
                         **components)
        return gym_job

    @staticmethod
    def get_hf_accelerate_gymjob_from_blueprint(blueprint: BluePrint,
                                                logger_collection_constructable: MLgymStatusLoggerCollectionConstructable,
                                                gs_restful_api_client_constructable: GridSearchAPIClientConstructable) -> AbstractGymJob:
        components = blueprint.construct()

        logger_collection = logger_collection_constructable.construct()
        experiment_status_logger = ExperimentStatusLogger(logger=logger_collection, grid_search_id=blueprint.grid_search_id,
                                                          experiment_id=blueprint.experiment_id)
        gs_api_client = gs_restful_api_client_constructable.construct()

        gym_job = GymJob(run_mode=blueprint.run_mode,
                         grid_search_id=blueprint.grid_search_id,
                         experiment_id=blueprint.experiment_id,
                         num_epochs=blueprint.num_epochs,
                         warm_start_epoch=blueprint.warm_start_epoch,
                         experiment_status_logger=experiment_status_logger,
                         gs_api_client=gs_api_client,
                         **components)
        return gym_job