class RobotService:
    def __init__(self): self.running = False
    def start(self):
        return {"running": False, "message": "Start blocked: MT5 demo connection and order safeguards are not configured"}
    def stop(self):
        self.running = False
        return {"running": False, "message": "Robot stopped"}
robot = RobotService()
