DEFAULT_SETTINGS = {
  "language": "English",
  "partial_results": True, # send results after each vote
  "active_votes": False    # accept only active votes, if False, non-press counts as "abstantiated" 
}
    
class BotSettings():

    def __init__(self, db=None, user_id="DEFAULT", space_id=None):
        self._db = db
        self._user_id = user_id
        self._space_id = space_id
        self._settings = DEFAULT_SETTINGS.copy()
        
    @property
    def settings(self):
        return self._settings

    @settings.setter
    def settings(self, new_settings):
        for (key, value) in new_settings.items():
            self._settings[key] = value
            
    def save(self):
        if self._db is None:
            return
            
        self._db.save_db_record(self._user_id, "SETTINGS", "", **self._settings)
            
    def load(self):
        if self._db is None:
            return
                    
        settings_data = self._db.get_db_record(self._user_id, "SETTINGS")
        for key in ["pk", "sk", "pvalue"]:
            del(settings_data[key])
                
        self.settings = settings_data
