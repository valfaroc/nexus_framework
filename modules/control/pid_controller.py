from core.interfaces.controller import BaseController
from core.data_models import VehicleState, Trajectory
import carla

class PIDModule(BaseController):
    def __init__(self, config=None):
        # Longitudinal PID (Velocity)
        self.lon_pid = PIDController_Logic(Kp=0.8, Ki=0.1, Kd=0.02)
        # Lateral PID (Steering)
        self.lat_pid = PIDController_Logic(Kp=0.5, Ki=0.05, Kd=0.15)

    def get_control_signal(self, current_state, target_path: Trajectory, dt):
        # 1. Get targets from path
        target_speed = target_path.target_velocities[0]
        target_wp = target_path.waypoints[0]

        # 2. Longitudinal Control
        current_speed = current_state.velocity_mag
        accel, _ = self.lon_pid.compute(target_speed, current_speed, dt)

        # 3. Lateral Control
        # Simplified: target_wp.y as the reference
        steer, _ = self.lat_pid.compute(target_wp.position.y, current_state.pose.position.y, dt)

        return carla.VehicleControl(
            throttle=max(0, accel), 
            brake=abs(min(0, accel)), 
            steer=steer
        )
    
    def reset(self):
        # Reset integrals
        pass

# Logic helper (transplanted from your code)
class PIDController_Logic:
    def __init__(self, Kp, Ki, Kd):
        self.Kp, self.Ki, self.Kd = Kp, Ki, Kd
        self.integral = 0
        self.last_error = 0

    def compute(self, set_point, current_value, dt):
        error = set_point - current_value
        self.integral += error * dt
        derivative = (error - self.last_error) / dt
        output = (self.Kp * error) + (self.Ki * self.integral) + (self.Kd * derivative)
        self.last_error = error
        return output, error