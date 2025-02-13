from functools import partial
from ml_gym.error_handling.exception import GymError
from ml_gym.gym.gym_jobs.gym_job_factory import GymJobFactory
from ml_gym.persistency.io import GridSearchAPIClientConstructable
from ml_gym.persistency.logging import JobStatusLogger, MLgymStatusLoggerCollectionConstructable
import torch
from typing import Callable, List
from ml_gym.multiprocessing.pool import Pool, Job
from ml_gym.blueprints.blue_prints import BluePrint
from ml_gym.util.devices import get_devices
import tqdm
from abc import ABC, abstractmethod
from enum import Enum
from accelerate import Accelerator

torch.multiprocessing.set_start_method('spawn', force=True)


class Gym(ABC):
    def __init__(self, logger_collection_constructable: MLgymStatusLoggerCollectionConstructable):
        self.job_status_logger = JobStatusLogger(logger_collection_constructable.construct())


    @abstractmethod
    def run(self, blueprints: List[BluePrint]):
        """Executes the jobs. Note that this function blocks until all jobs have been executed!
        """
        raise NotImplementedError

    def get_jobs_from_blueprints(self, blueprints: List[BluePrint], exec_fun: Callable) -> List[Job]:
        jobs = []
        for job_id, blueprint in enumerate(blueprints):
            job = Job(job_id=f"{blueprint.grid_search_id}-{job_id}", fun=exec_fun, blueprint=blueprint)
            jobs.append(job)
            self.job_status_logger.log_experiment_config(grid_search_id=blueprint.grid_search_id,
                                                         experiment_id=blueprint.experiment_id,
                                                         job_id=job_id,
                                                         config=blueprint.config)
        return jobs


class ParallelSingleNodeGym(Gym):
    def __init__(self, logger_collection_constructable: MLgymStatusLoggerCollectionConstructable,
                 exec_fun: Callable, process_count: int = 1, device_ids: List[int] = None):
        super().__init__(logger_collection_constructable)
        self.devices = get_devices(device_ids)
        self.pool = Pool(num_processes=process_count, devices=self.devices, logger_collection_constructable=logger_collection_constructable)
        self.exec_fun = exec_fun

    def run(self, blueprints: List[BluePrint]):
        """Executes the jobs. Note that this function blocks until all jobs have been executed!
        """
        jobs = self.get_jobs_from_blueprints(blueprints, exec_fun=self.exec_fun)
        for job in jobs:
            self.pool.add_job(job)
        self.pool.run()


class SequentialGym(Gym):
    def __init__(self, logger_collection_constructable: MLgymStatusLoggerCollectionConstructable,
                 exec_fun: Callable, device_id: int = None):
        super().__init__(logger_collection_constructable)
        self.exec_fun = exec_fun
        self.device = None if device_id is None else torch.device(device_id)

    def run(self, blueprints: List[BluePrint]):
        """Executes the jobs. Note that this function blocks until all jobs have been executed!
        """

        jobs = self.get_jobs_from_blueprints(blueprints, exec_fun=self.exec_fun)
        for job in tqdm.tqdm(jobs, desc="Models trained"):
            job.execute()
        self.job_status_logger.disconnect()

    def work(self, job: Job):
        # we don't set the device in job because every job executed on the main thread should be handled via accelerate
        job.execute(device=self.device)


class GymType(Enum):
    SEQUENTIAL_GYM = SequentialGym
    PARALLEL_SINGLE_NODE_GYM = ParallelSingleNodeGym


class GymFactory:

    @staticmethod
    def get_sequential_gym(logger_collection_constructable: MLgymStatusLoggerCollectionConstructable,
                           gs_restful_api_client_constructable: GridSearchAPIClientConstructable,
                           num_epochs: int, device_id: int = None,
                           num_batches_per_epoch: int = None,
                           accelerator: Accelerator = None) -> Gym:
        if accelerator is not None:
            exec_fun = partial(GymFactory._run_accelerate_gym_job, logger_collection_constructable=logger_collection_constructable,
                               gs_restful_api_client_constructable=gs_restful_api_client_constructable,
                               num_epochs=num_epochs, num_batches_per_epoch=num_batches_per_epoch, accelerator=accelerator)
            if device_id is not None:
                raise GymError("You cannot run the accelerate env on a specific device id")
        else:
            exec_fun = partial(GymFactory._run_standard_gym_job, logger_collection_constructable=logger_collection_constructable,
                               gs_restful_api_client_constructable=gs_restful_api_client_constructable,
                               num_epochs=num_epochs, num_batches_per_epoch=num_batches_per_epoch)

        return SequentialGym(logger_collection_constructable=logger_collection_constructable,
                             exec_fun=exec_fun,
                             device_id=device_id)

    @staticmethod
    def get_parallel_single_node_gym(logger_collection_constructable: MLgymStatusLoggerCollectionConstructable,
                                     gs_restful_api_client_constructable: GridSearchAPIClientConstructable,
                                     num_epochs: int, process_count: int = 1, device_ids: List[int] = None,
                                     num_batches_per_epoch: int = None) -> Gym:

        exec_fun = partial(GymFactory._run_standard_gym_job, logger_collection_constructable=logger_collection_constructable,
                           gs_restful_api_client_constructable=gs_restful_api_client_constructable,
                           num_epochs=num_epochs, num_batches_per_epoch=num_batches_per_epoch)

        return ParallelSingleNodeGym(logger_collection_constructable=logger_collection_constructable,
                                     process_count=process_count, device_ids=device_ids, exec_fun=exec_fun)

    @staticmethod
    def _run_standard_gym_job(blueprint: BluePrint, device: torch.device, num_epochs: int,
                              logger_collection_constructable: MLgymStatusLoggerCollectionConstructable,
                              gs_restful_api_client_constructable: GridSearchAPIClientConstructable,
                              num_batches_per_epoch: int = None):
        gym_job = GymJobFactory.get_gym_job_from_blueprint(blueprint, device=device, num_epochs=num_epochs,
                                                           logger_collection_constructable=logger_collection_constructable,
                                                           gs_restful_api_client_constructable=gs_restful_api_client_constructable,
                                                           num_batches_per_epoch=num_batches_per_epoch)

        return gym_job.execute(device=device)

    @staticmethod
    def _run_accelerate_gym_job(blueprint: BluePrint, num_epochs: int,
                                logger_collection_constructable: MLgymStatusLoggerCollectionConstructable,
                                gs_restful_api_client_constructable: GridSearchAPIClientConstructable,
                                accelerator: Accelerator, num_batches_per_epoch: int = None):
        gym_job = GymJobFactory.get_accelerate_gymjob_from_blueprint(blueprint,
                                                                     num_epochs=num_epochs,
                                                                     logger_collection_constructable=logger_collection_constructable,
                                                                     gs_restful_api_client_constructable=gs_restful_api_client_constructable,
                                                                     num_batches_per_epoch=num_batches_per_epoch,
                                                                     accelerator=accelerator)
        return gym_job.execute()
