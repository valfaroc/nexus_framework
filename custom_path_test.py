import carla
import pygame
import numpy as np
import os
from configparser import ConfigParser
from collections import deque

# --- Clase PID mejorada según tu solicitud ---
class PIDController:
    def __init__(self, Kp, Ki, Kd, limits=(-1.0, 1.0)):
        self.Kp, self.Ki, self.Kd = Kp, Ki, Kd
        self.limits = limits
        self.integral = 0
        self.last_error = 0

    def compute(self, set_point, current_value, dt):
        dt = max(dt, 0.001)
        error = set_point - current_value
        self.integral += error * dt
        derivative = (error - self.last_error) / dt
        output = (self.Kp * error) + (self.Ki * self.integral) + (self.Kd * derivative)
        self.last_error = error
        return np.clip(output, self.limits[0], self.limits[1]), error

class SimpleSimulation:
    def __init__(self):
        pygame.init()
        pygame.joystick.init()
        self.width, self.height = 1200, 800
        self.display = pygame.display.set_mode((self.width, self.height))
        self.font = pygame.font.SysFont('mono', 15)
        self.client = carla.Client('localhost', 2000)
        self.world = self.client.get_world()
        
        # Estado
        self.vehicle = None
        self.camera = None
        self.surface = None
        self.automated_mode = False
        self.keyboard_manual_input = True
        self.reverse = False
        self.show_info = True

        # Configuración del Volante Fanatec
        self._setup_wheel()
        
        # Telemetría para gráficas nativas
        self.history_len = 200
        self.lon_history = deque([0]*self.history_len, maxlen=self.history_len)
        self.lat_history = deque([0]*self.history_len, maxlen=self.history_len)

        # Controladores
        self.lon_pid = PIDController(Kp=0.8, Ki=0.05, Kd=0.2)
        self.lat_pid = PIDController(Kp=0.5, Ki=0.05, Kd=0.2)
        
        # Camara seleccionada, 0 por defecto
        self.camera_index = 0
        # Definimos las posiciones: [Location(x, y, z), Rotation(pitch, yaw, roll)]
        self.camera_transforms = [
            # Vista Trasera (Follow)
            [carla.Location(x=-5.5, z=2.8), carla.Rotation(pitch=-15)],
            # Vista Cockpit (Interior) - Ajustada para Tesla Model 3
            [carla.Location(x=0.0, y=-0.4, z=1.3), carla.Rotation(pitch=-10)]
        ]
        self.setup_actors()
        self.path = self.generate_path()

    def _setup_wheel(self):
        """Inicializa el joystick y carga la configuración del .ini"""
        self.joystick = None
        if pygame.joystick.get_count() > 0:
            for i in range(pygame.joystick.get_count()):
                j = pygame.joystick.Joystick(i)
                j.init()
                if "FANATEC" in j.get_name().upper():
                    self.joystick = j
                    print(f"Volante detectado: {j.get_name()}")
                    break
        
        # Carga de mapeo desde wheel_config.ini
        self.parser = ConfigParser()
        # Asumiendo que el archivo esta en el mismo directorio
        ini_path = './wheel_config.ini' 
        if os.path.exists(ini_path):
            self.parser.read(ini_path)
            self._steer_idx = int(self.parser.get('Fanatec DD Pro', 'steering_wheel'))
            self._throttle_idx = int(self.parser.get('Fanatec DD Pro', 'throttle'))
            self._brake_idx = int(self.parser.get('Fanatec DD Pro', 'brake'))
            self._reverse_idx = int(self.parser.get('Fanatec DD Pro', 'reverse'))
        else:
            print("ADVERTENCIA: wheel_config.ini no encontrado. Usando valores por defecto.")
            self._steer_idx, self._throttle_idx, self._brake_idx, self._reverse_idx = 0, 1, 2, 3   

    def setup_actors(self):
        # Vehículo
        bp = self.world.get_blueprint_library().find('vehicle.tesla.cybertruck')
        spawn_point = self.world.get_map().get_spawn_points()[0]
        self.vehicle = self.world.spawn_actor(bp, spawn_point)
        
        # Cámara inicial
        cam_bp = self.world.get_blueprint_library().find('sensor.camera.rgb')
        cam_bp.set_attribute('image_size_x', str(self.width))
        cam_bp.set_attribute('image_size_y', str(self.height))
        
        # Spamear con la primera posición de la lista
        loc, rot = self.camera_transforms[self.camera_index]
        self.camera = self.world.spawn_actor(
            cam_bp, 
            carla.Transform(loc, rot), 
            attach_to=self.vehicle)
        
        self.camera.listen(lambda data: self._parse_image(data))
    
    def next_camera(self):
        """Cambia a la siguiente posición de cámara definida"""
        self.camera_index = (self.camera_index + 1) % len(self.camera_transforms)
        loc, rot = self.camera_transforms[self.camera_index]
        # Aplicamos el nuevo transform localmente al sensor
        self.camera.set_transform(carla.Transform(loc, rot))

    def _parse_image(self, image):
        array = np.frombuffer(image.raw_data, dtype=np.dtype("uint8"))
        array = np.reshape(array, (image.height, image.width, 4))[:, :, :3][:, :, ::-1]
        self.surface = pygame.surfarray.make_surface(array.swapaxes(0, 1))

    def generate_path(self):
        start = self.vehicle.get_transform().location
        pts = [carla.Location(x=start.x + i*2, y=start.y + 4*np.sin(i/10.0), z=start.z + 0.2) for i in range(120)]
        # Dibujamos una sola vez con mucha duración
        for i in range(len(pts) - 1):
            self.world.debug.draw_line(
                pts[i],
                pts[i+1],
                thickness=0.1, 
                color=carla.Color(255,0,0), 
                life_time=100.0
            )
            self.world.debug.draw_point(
                pts[i], 
                size=0.1, 
                color=carla.Color(0,255,0), 
                life_time=100.0
            )
        return pts
    
    def get_wheel_control(self):
        control = carla.VehicleControl()
        if self.joystick:
            # 1. Dirección con sensibilidad corregida
            steer_val = self.joystick.get_axis(self._steer_idx)
            # Aplicamos una zona muerta pequeña para el steering
            control.steer = steer_val if abs(steer_val) > 0.01 else 0.0

            # 2. Acelerador: Fanatec suele ir de 1 (suelto) a -1 (fondo)
            # Usamos una fórmula más robusta para asegurar el 0 absoluto
            throttle_axis = self.joystick.get_axis(self._throttle_idx)
            # Normalizamos de [1, -1] a [0, 1]
            control.throttle = max(0.0, (1.0 - throttle_axis) / 2.0)
            if control.throttle < 0.05: control.throttle = 0.0

            # 3. Freno: Crucial para evitar que el coche se quede "pegado"
            brake_axis = self.joystick.get_axis(self._brake_idx)
            control.brake = max(0.0, (1.0 - brake_axis) / 2.0)
            if control.brake < 0.05: control.brake = 0.0 # Zona muerta

            control.reverse = self.reverse
            control.hand_brake = False # Forzamos que el freno de mano esté quitado
            
        return control
    
    def draw_graph(self, surface, ref, data, pos, title, color, scale=10):
        """Dibuja una gráfica simple directamente en Pygame"""
        width, height = 250, 100
        # Fondo de la gráfica
        pygame.draw.rect(surface, (200, 200, 200), (pos[0], pos[1], width, height))
        
        # Línea de referencia (cero)
        pygame.draw.line(surface, (70, 70, 70), (pos[0], pos[1]+height//2), (pos[0]+width, pos[1]+height//2))
        
        # Dibujar los puntos
        if len(data) > 1:
            points = []
            for i, val in enumerate(data):
                x = pos[0] + i * (width / self.history_len)
                # Escalar valor: el error se multiplica por 'scale' y se centra
                y = pos[1] + height//2 - (val * scale)
                # Clipping para no salir de la caja
                y = np.clip(y, pos[1], pos[1] + height)
                points.append((x, y))
            pygame.draw.lines(surface, color, False, points, 2)
        
        # Titulo
        lbl = self.font.render(title, True, (255, 255, 255))
        surface.blit(lbl, (pos[0], pos[1] - 20))
        # Referencia
        ref_lbl = self.font.render(f"{ref}", True, (0, 0, 0))
        surface.blit(ref_lbl, (pos[0] + 5, pos[1] + height//2 + 5))

    def render_hud(self, speed, steer, lon_ref, lat_ref, e_lon, e_lat):
        if not self.show_info: return
        
        # Panel de datos (Izquierda)
        overlay = pygame.Surface((210, 140))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        # Panel de graficos
        graph_overlay = pygame.Surface((290, 280))
        graph_overlay.set_alpha(180)
        graph_overlay.fill((0, 0, 0))

        self.display.blit(overlay, (10, 10))
        self.display.blit(graph_overlay, (self.width - 300, 20))
        
        lines = [
            f"Vel: {speed:.1f} km/h",
            f"Steer: {steer:.2f}",
            f"E_Lon: {e_lon:.2f}",
            f"E_Lat: {e_lat:.2f}",
            f"Modo: {'AUTO' if self.automated_mode else 'MANUAL'}",
            f"Modo manual: {'Keyboard' if self.keyboard_manual_input else 'Cockpit'}",
            f"Camera: {'1st Person' if self.camera_index else 'Top View'}"
        ]
        for i, text in enumerate(lines):
            self.display.blit(self.font.render(text, True, (255, 255, 255)), (15, 15 + i*18))

        # Gráficas (Derecha)
        self.draw_graph(self.display, lon_ref, self.lon_history, (self.width - 280, 50), "Error Longitudinal", (255, 50, 50), scale=5)
        self.draw_graph(self.display, lat_ref, self.lat_history, (self.width - 280, 180), "Error Lateral", (50, 150, 255), scale=15)

    def run(self):
        clock = pygame.time.Clock()
        try:
            while True:
                clock.tick(60)
                dt = clock.get_time() / 1000.0
                for event in pygame.event.get():
                    if event.type == pygame.QUIT: return
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_p: self.automated_mode = not self.automated_mode
                        if event.key == pygame.K_o: self.keyboard_manual_input = False
                        if event.key == pygame.K_q: self.reverse = not self.reverse
                        if event.key == pygame.K_i: self.show_info = not self.show_info
                        if event.key == pygame.K_c: self.next_camera()
                        if event.key == pygame.K_ESCAPE: return
                    # Botón del volante para alternar Autopilot (101)
                    if event.type == pygame.JOYBUTTONDOWN:
                        # triangulo
                        if event.button == 101: self.automated_mode = not self.automated_mode
                        # circulo
                        if event.button == self._reverse_idx: self.reverse = not self.reverse
                        # equis
                        if event.button == 99: self.next_camera()
                        # cuadrado
                        if event.button == 98: self.keyboard_manual_input = True

                v_trans = self.vehicle.get_transform()
                v_vel = self.vehicle.get_velocity()
                speed = 3.6 * np.sqrt(v_vel.x**2 + v_vel.y**2)
                closest_wp = min(self.path, key=lambda p: v_trans.location.distance(p))
                
                # Cálculo de errores y control
                lon_ref = 25.0
                lat_ref = closest_wp.y
                
                # --- LÓGICA DE SELECCIÓN DE CONTROL ---
                if self.automated_mode:
                    # MODO AUTONOMO
                    accel, e_lon = self.lon_pid.compute(lon_ref, speed, dt)
                    steer, e_lat = self.lat_pid.compute(lat_ref, v_trans.location.y, dt)
                    control = carla.VehicleControl(throttle=max(0, accel), 
                                                 brake=abs(min(0, accel)), 
                                                 steer=steer)
                elif not self.keyboard_manual_input:
                    # MODO VOLANTE (FANATEC) - Prioridad absoluta si está activo
                    control = self.get_wheel_control()
                    # Calculamos errores solo para la gráfica
                    _, e_lon = self.lon_pid.compute(lon_ref, speed, dt)
                    _, e_lat = self.lat_pid.compute(lat_ref, v_trans.location.y, dt)
                else:
                    # MODO TECLADO
                    keys = pygame.key.get_pressed()
                    control = carla.VehicleControl()
                    control.throttle = 1.0 if keys[pygame.K_w] else 0.0
                    control.brake = 1.0 if keys[pygame.K_s] else 0.0
                    control.steer = -0.6 if keys[pygame.K_a] else (0.6 if keys[pygame.K_d] else 0.0)
                    control.reverse = self.reverse
                    # Calculamos errores solo para la gráfica
                    _, e_lon = self.lon_pid.compute(lon_ref, speed, dt)
                    _, e_lat = self.lat_pid.compute(lat_ref, v_trans.location.y, dt)

                # Aplicación única del control
                self.vehicle.apply_control(control)
                self.lon_history.append(e_lon); self.lat_history.append(e_lat)

                if self.surface: self.display.blit(self.surface, (0, 0))
                self.render_hud(speed, control.steer, lon_ref, lat_ref, e_lon, e_lat)
                pygame.display.flip()
        finally:
            if self.camera: self.camera.destroy()
            if self.vehicle: self.vehicle.destroy()
            pygame.quit()

if __name__ == "__main__":
    SimpleSimulation().run()