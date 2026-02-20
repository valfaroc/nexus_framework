import time
import logging
from core.interfaces.simulator import BaseSimulatorBridge

class NexusEngine:
    def __init__(self, simulator: BaseSimulatorBridge):
        self.simulator = simulator
        self.perception = None
        self.planner = None
        self.controller = None
        self._running = False
        self.target_hz = 20.0 # Standard for CCAM control loops

    def setup_modules(self, perception_mod, planner_mod, controller_mod):
        """Plugs the modules into the engine."""
        self.perception = perception_mod
        self.planner = planner_mod
        self.controller = controller_mod
        logging.info("Nexus Engine: Modules initialized successfully.")

    def run(self):
        """The Main CCAM Loop (Sense-Plan-Act)."""
        self._running = True
        last_time = time.time()
        
        logging.info("Nexus Engine: Starting main loop...")
        
        try:
            while self._running:
                current_time = time.time()
                dt = current_time - last_time
                
                if dt >= (1.0 / self.target_hz):
                    # 1. SENSE: Get state from the bridge
                    obs = self.simulator.get_observation()
                    
                    # 2. PERCEIVE: Process surroundings
                    world_model = self.perception.update(obs)
                    
                    # 3. PLAN: Generate trajectory
                    trajectory = self.planner.generate_path(
                        current_pose=self.simulator.get_pose(),
                        world_model=world_model
                    )
                    
                    # 4. ACT: Get control signals
                    control_cmd = self.controller.get_control_signal(
                        current_state=self.simulator.get_state(),
                        target_path=trajectory,
                        dt=dt
                    )
                    
                    # 5. APPLY: Send to CARLA/Hardware
                    self.simulator.apply_control(control_cmd)
                    
                    last_time = current_time
                    
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        self._running = False
        self.simulator.cleanup()
        logging.info("Nexus Engine: Simulation stopped.")