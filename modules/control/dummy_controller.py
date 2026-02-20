from core.interfaces.controller import BaseController
import numpy as np

class DummyController(BaseController):
    def __init__(self, config=None):
        pass

    def get_control_signal(self, current_state, target_path, dt):
        # Logic from your original 'tick' method
        return 0.5, 0, 0