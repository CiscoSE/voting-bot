import logging

DEFAULT_SETTINGS = {
  "language": "en_US",
  "partial_results": True,  # send results after each vote
  "active_votes": False,    # accept only votes by pressed button, if False, non-press counts as "abstantiated"
  "user_1_1": False,        # 1-1 space with user already created
  "user_updated": False,    # user has updated the settings
  "timestamp": 0            # timestamp of last save
}
    
class BotSettings():
    """maintain and save Bot settings

    settings are saved in the database. Setter is incremetal so a partial update doesn't delete the non-updated fields.
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    def __init__(self, db=None, settings_id="DEFAULT", auto_save=False):
        self._db = db
        self._settings_id = settings_id
        self._settings = DEFAULT_SETTINGS.copy()
        self.stored = False
        self.auto_save = auto_save
        
        self.load()
            
    def __del__(self):
        if self.auto_save:
            self.save()
        
    @property
    def settings(self):
        return self._settings

    @settings.setter
    def settings(self, new_settings):
        for (key, value) in new_settings.items():
            if str(value).lower() == "yes":
                value = True
            elif str(value).lower() == "no":
                value = False
            self._settings[key] = value
            
    def save(self):
        self.logger.info("setting save, id: {}, data: {}".format(self._settings_id, self._settings))
        if self._db is None:
            return
            
        self._db.save_db_record(self._settings_id, "SETTINGS", "", **self._settings)
        self.stored = True
            
    def load(self):
        if self._db is None:
            return
                    
        settings_data = self._db.get_db_record(self._settings_id, "SETTINGS")
        if settings_data is None:
            return
            
        for key in ["pk", "sk", "pvalue"]:
            del(settings_data[key])
                
        self.settings = settings_data
        self.logger.info("setting load, id: {}, data: {}".format(self._settings_id, self._settings))
        self.stored = True
