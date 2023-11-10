import concurrent.futures
from readerwriterlock import rwlock
from datetime import datetime, timedelta
from moesifapi.exceptions.api_exception import *
import logging
from .governance_manager import GovernanceRulesManager

logger = logging.getLogger(__name__)


class ConfigUpdateManager:
    """ This class is responsible for updating the configuration and governance rules from the server.
    It is also responsible for caching the configuration and returning the sampling percentage.
    """
    def __init__(self, api_client, app_config, debug):
        self.MAX_ETAG_REFRESH_TIME_IN_MIN = 5 # in minutes
        self.api_client = api_client
        self.app_config = app_config
        self.govern_manager = GovernanceRulesManager(api_client)
        self.debug = debug
        # We use a single background thread to update the configuration.
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        # We use a fair read-write lock to protect the configuration
        # this allows multiple threads to read the configuration at the same time,
        # but only one thread at a time to update the below values
        self._lock = rwlock.RWLockFairD()
        self.current_etag = None
        self.config = None
        self.last_updated_time = datetime.utcnow() - timedelta(minutes=self.MAX_ETAG_REFRESH_TIME_IN_MIN)
        self.__init_config__()

    def __init_config__(self):
        try:
            # load the config at the start
            with self._lock.gen_wlock():
                self._executor.submit(self.update_configuration)
        except Exception as e:
            logger.exception(f"Error while fetching configuration on start", e)
            pass

    def check_and_update(self, response_etag):
        """ Check if the configuration needs to be updated. If so, update it in a separate thread.
        This is called by the worker thread that is responsible for sending events to Moesif.
        """
        if not response_etag:
            return
        # Acquire a read lock and check if the configuration needs to be updated.
        # but ony if the last update was more than 5 minutes ago.
        with self._lock.gen_rlock():
            if self.current_etag:
                if self.current_etag == response_etag:
                    if datetime.utcnow() >= self.last_updated_time + timedelta(minutes=self.MAX_ETAG_REFRESH_TIME_IN_MIN):
                        self.last_updated_time = datetime.utcnow()
                    return
        # Acquire a write lock, save the new etag and queue the update in a separate thread.
        with self._lock.gen_wlock():
            if self.current_etag != response_etag:
                # saving etag now will prevent us from updating the configuration again while the update is in progress.
                self.current_etag = response_etag
                # Offload the actual update to another thread
                self._executor.submit(self.update_configuration)

    def update_configuration(self):
        """ Update the configuration from the server.
        This is called by the single purpose update thread in self._executor.
        The moesifpythonrequest.app_config.AppConfig class perfoms exception handling.
        """
        config = self.app_config.get_config(self.api_client, self.debug)
        # we don't need the sample rate since it is always accessed via the get_sampling_percentage method.
        new_etag, _, new_last_updated_time = self.app_config.parse_configuration(config, self.debug)
        # also load rules
        self.govern_manager.load_rules(self.debug)

        # Acquire a lock and update the configuration only if the etag has changed since the last time we updated it.
        with self._lock.gen_wlock():
            # We need to check the etag again because it might have changed while we were waiting for the lock.
            # If there was an unrecoverable failure in this update call, new_etag will be None, and saving
            # this value without updating the configuration will cause us to retry the update on the next request.
            # if new_etag != self.current_etag:
            self.current_etag = new_etag
            if config is not None:
                self.config = config
                self.last_updated_time = new_last_updated_time
                if self.debug:
                    logger.debug("config update at " + str(self.last_updated_time))

    def get_sampling_percentage(self, event_data, user_id, company_id):
        """Get sampling percentage.
        This is called by the middleware main thread.
        """
        with self._lock.gen_rlock():
            return self.app_config.get_sampling_percentage(event_data, self.config, user_id, company_id)


    def have_governance_rules(self):
        with self._lock.gen_rlock():
            return self.govern_manager.has_rules()

    def govern_request(self, requestData, userId, companyId, request_body):
        return self.govern_manager.govern_request(self.config, requestData, userId, companyId, request_body)
