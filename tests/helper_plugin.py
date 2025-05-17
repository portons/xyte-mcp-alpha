received_events = []
received_logs = []

class TestPlugin:
    def on_event(self, event):
        received_events.append(event)

    def on_log(self, message, level):
        received_logs.append((message, level))

plugin = TestPlugin()
