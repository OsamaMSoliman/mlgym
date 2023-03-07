from abc import ABC, abstractmethod
import os
import glob
import re
from typing import Dict, List
from ml_gym.error_handling.exception import InvalidPathError
import json
from ml_board.backend.restful_api.data_models import RawTextFile, CheckpointResource, ExperimentStatus


class DataAccessIF(ABC):
    """
    DataAccessIF class

    Declare Abstract methods to be used in FileDataAccess Class.
    """

    @abstractmethod
    def get_experiment_statuses(self, grid_search_id: str):
        raise NotImplementedError

    @abstractmethod
    def add_raw_config_to_grid_search(self, grid_search_id: str, config_name: str, config_file: RawTextFile):
        raise NotImplementedError

    @abstractmethod
    def add_config_to_experiment(self, grid_search_id: str, experiment_id: str, config_name: str, config: RawTextFile):
        raise NotImplementedError
    
    @abstractmethod
    def get_grid_config_exec(self, grid_search_id: str, config_name: str):
        raise NotImplementedError
    
    @abstractmethod
    def get_experiment_config_exec(self, grid_search_id: str, experiment_id: str, config_name: str):
        raise NotImplementedError

    @abstractmethod
    def get_checkpoint_resource(self, grid_search_id: str, experiment_id: str, epoch: str, checkpoint_resource: CheckpointResource):
        raise NotImplementedError

    @abstractmethod
    def post_checkpoint_resource_exec(self, grid_search_id: str, experiment_id: str, epoch: str, checkpoint_resource: CheckpointResource, payload_pickle: bytes):
        raise NotImplementedError
    
    @abstractmethod
    def del_checkpoint_resource_exec(self, grid_search_id: str, experiment_id: str, epoch: str, checkpoint_resource: CheckpointResource):
        raise NotImplementedError

    @abstractmethod
    def get_checkpoint_dict_epoch(self, grid_search_id: str, experiment_id: str, epoch: str):
        raise NotImplementedError


class FileDataAccess(DataAccessIF):
    """
    FileDataAccess Class

    :params: DataAccessIF object

    The rest server uses this class to use methods to access event storage files.
    Used to add new files, delete current files and fetch current files.
    """

    def __init__(self, top_level_logging_path: str):
        print(top_level_logging_path)
        self.top_level_logging_path = top_level_logging_path

    @staticmethod
    def is_safe_path(base_dir, requested_path, follow_symlinks=True):
        # resolves symbolic links
        if follow_symlinks:
            matchpath = os.path.realpath(requested_path)
        else:
            matchpath = os.path.abspath(requested_path)
        return base_dir == os.path.commonpath((base_dir, matchpath))

    @staticmethod
    def get_checkpoint_files(path: str, base_path: str):
        full_paths = glob.glob(os.path.join(
            path, "**", "*.bin"), recursive=True)
        return [os.path.relpath(full_path, base_path) for full_path in full_paths]

    @staticmethod
    def iterfile(file_path: str):
        with open(file_path, mode="rb") as file_like:
            yield from file_like

    def get_experiment_statuses(self, grid_search_id: str) -> List[ExperimentStatus]:
        """
        Fetch experiment status for a Grid Search ID.

        :params: 
             grid_search_id (str): Grid Search ID

        :returns: List - experiment_statuses
        """
        def get_last_checkpoint_ids(top_level_logging_path: str, grid_search_id: str) -> Dict:
            paths = glob.glob(os.path.join(
                top_level_logging_path, grid_search_id, '**/*'), recursive=True)
            regex_checkpoints = r".*-\d\d\/(\d)\/(\d)$"
            regex_experiments = r".*-\d\d\/(\d)$"

            experiment_id_to_checkpoint_ids = {}
            for path in paths:
                # experiment match
                match = re.match(regex_experiments, path)
                if match is not None:
                    experiment_id = int(match.groups()[0])
                    if experiment_id not in experiment_id_to_checkpoint_ids:
                        experiment_id_to_checkpoint_ids[experiment_id] = [-1]

                # checkpoint match
                match = re.match(regex_checkpoints, path)
                if match is not None:
                    experiment_id, checkpoint_id = int(
                        match.groups()[0]), int(match.groups()[1])
                    if experiment_id not in experiment_id_to_checkpoint_ids:
                        experiment_id_to_checkpoint_ids[experiment_id] = []
                    experiment_id_to_checkpoint_ids[experiment_id].append(
                        checkpoint_id)
            epxeriment_id_to_last_checkpoint = {
                k: max(v) for k, v in experiment_id_to_checkpoint_ids.items()}
            return epxeriment_id_to_last_checkpoint

        def load_experiment_config(top_level_logging_path: str, grid_search_id: str, experiment_id: int) -> Dict:
            full_path = os.path.join(top_level_logging_path, grid_search_id, str(
                experiment_id), "experiment_config.json")
            with open(full_path, "r") as fp:
                experiment_config = json.load(fp)
            return experiment_config

        requested_full_path = os.path.realpath(
            os.path.join(self.top_level_logging_path, grid_search_id))

        if FileDataAccess.is_safe_path(base_dir=self.top_level_logging_path, requested_path=requested_full_path):
            epxeriment_id_to_last_checkpoint_id = get_last_checkpoint_ids(
                self.top_level_logging_path, grid_search_id)
            response = [ExperimentStatus(**{"experiment_id": experiment_id,
                                            "last_checkpoint_id": last_checkpoint_id,
                                            "experiment_config": load_experiment_config(self.top_level_logging_path, grid_search_id,
                                                                                        experiment_id)})
                        for experiment_id, last_checkpoint_id in epxeriment_id_to_last_checkpoint_id.items()]
            return response

        else:
            raise InvalidPathError(
                f"File path {requested_full_path} is not safe.")

    def add_raw_config_to_grid_search(self, grid_search_id: str, config_name: str, config_file: RawTextFile):
        """
        Add Config for a Grid Search ID to event storage

        :params: 
             grid_search_id (str): Grid Search ID
             config_name (str): Name of Configuration file
             config_file (RawTextFile) : RawTextFile Object

        """
        requested_full_path = os.path.realpath(os.path.join(
            self.top_level_logging_path, str(grid_search_id), config_name))

        if FileDataAccess.is_safe_path(base_dir=self.top_level_logging_path, requested_path=requested_full_path):
            os.makedirs(os.path.dirname(requested_full_path), exist_ok=True)
            with open(requested_full_path, "w") as fp:
                fp.writelines(config_file.content)
        else:
            raise InvalidPathError(
                f"File path {requested_full_path} is not safe.")

    def add_config_to_experiment(self, grid_search_id: str, experiment_id: str, config_name: str, config: RawTextFile):
        """
        Add experiment config given the experiment ID & grid search ID to event storage.

        :params: 
             grid_search_id (str): Grid Search ID
             experiment_id (str): Experiment ID
             config_name (str): Name of Configuration file
             config (RawTextFile) : RawTextFile Object

        """
        requested_full_path = os.path.realpath(os.path.join(
            self.top_level_logging_path, str(grid_search_id), str(experiment_id), config_name))

        if FileDataAccess.is_safe_path(base_dir=self.top_level_logging_path, requested_path=requested_full_path):
            os.makedirs(os.path.dirname(requested_full_path), exist_ok=True)
            with open(requested_full_path, "w") as fp:
                fp.writelines(config.content)

        else:
            raise InvalidPathError(
                f"File path {requested_full_path} is not safe.")
    
    def get_grid_config_exec(self, grid_search_id: str, config_name: str):
        """
        Fetch grid config for a Grid Search ID from the event storage.

        :params: 
             grid_search_id (str): Grid Search ID
             config_name (str): Name of Configuration file

        :returns: bytes response of YML file
        """
        requested_full_path = os.path.realpath(os.path.join(self.top_level_logging_path, str(grid_search_id), f"{config_name}.yml"))
        if FileDataAccess.is_safe_path(base_dir=self.top_level_logging_path, requested_path=requested_full_path):
            if not os.path.isfile(requested_full_path):
                raise InvalidPathError(
                    f"Resource {requested_full_path} not found.")

            generator = FileDataAccess.iterfile(requested_full_path)
            return generator
        else:
            raise InvalidPathError(
                f"File path {requested_full_path} is not safe.")
    
    def get_experiment_config_exec(self, grid_search_id: str, experiment_id: str, config_name: str):
        """
        `Fetch experiment config given the experiment ID & grid search ID from event storage.

        :params: 
             grid_search_id (str): Grid Search ID
             experiment_id (str): Experiment ID
             config_name (str): Name of Configuration file

        :returns: bytes response of JSON file
        """
        requested_full_path = os.path.realpath(os.path.join(self.top_level_logging_path, str(grid_search_id), str(experiment_id), f"{config_name}.json"))
        if FileDataAccess.is_safe_path(base_dir=self.top_level_logging_path, requested_path=requested_full_path):
            if not os.path.isfile(requested_full_path):
                raise InvalidPathError(
                    f"Resource {requested_full_path} not found.")

            generator = FileDataAccess.iterfile(requested_full_path)
            return generator
        else:
            raise InvalidPathError(
                f"File path {requested_full_path} is not safe.")

    def get_checkpoint_resource(self, grid_search_id: str, experiment_id: str, epoch: str, checkpoint_resource: CheckpointResource):
        """
        `Fecth checkpoint resource pickle file given the experiment ID & grid search ID from event storage.

        :params: 
             grid_search_id (str): Grid Search ID
             experiment_id (str): Experiment ID
             epoch (str): Epoch number
             checkpoint_resource (CheckpointResource) : CheckpointResource type

        :returns: bytes response of pickle file
        """
        requested_full_path = os.path.realpath(os.path.join(self.top_level_logging_path, str(grid_search_id), str(experiment_id),
                                                            str(epoch), f"{checkpoint_resource}.bin"))
        if FileDataAccess.is_safe_path(base_dir=self.top_level_logging_path, requested_path=requested_full_path):
            if not os.path.isfile(requested_full_path):
                raise InvalidPathError(
                    f"Resource {requested_full_path} not found.")

            generator = FileDataAccess.iterfile(requested_full_path)
            return generator
        else:
            raise InvalidPathError(
                f"File path {requested_full_path} is not safe.")

    def post_checkpoint_resource_exec(self, grid_search_id: str, experiment_id: str, epoch: str, checkpoint_resource: CheckpointResource, payload_pickle: bytes):
        """
        Add a checkpoint resource pickle file given the epoch, experiment ID & grid search ID to event storage.

        :params: 
             grid_search_id (str): Grid Search ID
             experiment_id (str): Experiment ID
             epoch (str): Epoch number
             checkpoint_resource (CheckpointResource) : CheckpointResource type
             payload_pickle (bytes): Pickle file to be added

        :returns: Pickle file Stream response
        """

        requested_full_path = os.path.realpath(os.path.join(self.top_level_logging_path, str(grid_search_id), str(experiment_id),
                                                            str(epoch), f"{checkpoint_resource}.pickle"))

        if FileDataAccess.is_safe_path(base_dir=self.top_level_logging_path, requested_path=requested_full_path):
            os.makedirs(os.path.dirname(requested_full_path), exist_ok=True)
            with open(requested_full_path, "wb") as fd:
                fd.write(payload_pickle)
        else:
            raise InvalidPathError(
                f"File path {requested_full_path} is not safe.")
    
    def del_checkpoint_resource_exec(self, grid_search_id: str, experiment_id: str, epoch: str, checkpoint_resource: CheckpointResource):
        """
        Delete checkpoint resource pickle file from the event storage 
        given the epoch, experiment ID & grid search ID.

        :params: 
             grid_search_id (str): Grid Search ID
             experiment_id (str): Experiment ID
             epoch (str): Epoch number
             checkpoint_resource (CheckpointResource) : CheckpointResource type    
        """

        requested_full_path = os.path.realpath(os.path.join(self.top_level_logging_path, str(grid_search_id), str(experiment_id),
                                                            str(epoch), f"{checkpoint_resource}.pickle"))

        if FileDataAccess.is_safe_path(base_dir=self.top_level_logging_path, requested_path=requested_full_path):
            os.remove(requested_full_path)
        else:
            raise InvalidPathError(
                f"File path {requested_full_path} is not safe.")

    def get_checkpoint_dict_epoch(self, grid_search_id: str, experiment_id: str, epoch: str):
        """
        Fetch all checkpoint resource pickle files from event storage
        given the epoch, experiment ID & grid search ID.

        :params: 
             grid_search_id (str): Grid Search ID
             experiment_id (str): Experiment ID
             epoch (str): Epoch number

        :returns: List of Checkpoint files
        """
        requested_full_path = os.path.realpath(os.path.join(
            self.top_level_logging_path, str(grid_search_id), str(experiment_id), str(epoch)))

        if FileDataAccess.is_safe_path(base_dir=self.top_level_logging_path, requested_path=requested_full_path):
            files = FileDataAccess.get_checkpoint_files(
                requested_full_path, base_path=self.top_level_logging_path)
            return {os.path.basename(file).split(".")[0]: file for file in files}

        else:
            raise InvalidPathError(
                f"File path {requested_full_path} is not safe.")
