# nexus.py
import argparse
import logging
from core.nexus_engine import NexusEngine
from core.factory import ControllerFactory, PerceptionFactory, PlannerFactory
from modules.simulator.carla_bridge import CarlaBridge

def main():
    parser = argparse.ArgumentParser(description="Nexus CCAM Framework CLI")
    parser.add_argument('--controller', type=str, default='pid', help='Controller module to use')
    parser.add_argument('--perception', type=str, default='ground_truth', help='Perception module')
    parser.add_argument('--town', type=str, default='Town03', help='CARLA Town to load')
    parser.add_argument('--planner', type=str, default='sine', help='Path planner module')

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    # 1. Initialize Simulator Bridge
    simulator = CarlaBridge(town=args.town)

    # 2. Use Factories to load modules by name (The "Web Dev" way)
    controller = ControllerFactory.get(args.controller, config=None)
    perception = PerceptionFactory.get(args.perception)
    planner = PlannerFactory.get(args.planner)

    # 3. Start Engine
    engine = NexusEngine(simulator)
    engine.setup_modules(perception, planner, controller)
    
    try:
        engine.run()
    except Exception as e:
        logging.error(f"Simulation failed: {e}")
        raise e
    finally:
        engine.stop()

if __name__ == "__main__":
    main()