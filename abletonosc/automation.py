from typing import Tuple, Any
from .handler import AbletonOSCHandler


class AutomationHandler(AbletonOSCHandler):
    """
    Clip automation envelopes targeting device parameters on the clip's track.

    Address scheme: (track_index, clip_index, device_index, parameter_index)
    """

    def __init__(self, manager):
        super().__init__(manager)
        self.class_identifier = "automation"

    def _resolve(self, params: Tuple[Any]):
        track_index = int(params[0])
        clip_index = int(params[1])
        device_index = int(params[2])
        parameter_index = int(params[3])
        track = self.song.tracks[track_index]
        clip = track.clip_slots[clip_index].clip
        if clip is None:
            raise LookupError("No clip at track %d slot %d" % (track_index, clip_index))
        parameter = track.devices[device_index].parameters[parameter_index]
        return track_index, clip_index, device_index, parameter_index, clip, parameter

    @staticmethod
    def _get_or_create_envelope(clip, parameter):
        envelope = clip.automation_envelope(parameter)
        if envelope is None:
            envelope = clip.create_automation_envelope(parameter)
        return envelope

    def init_api(self):
        def automation_insert_step(params: Tuple[Any]):
            try:
                ti, ci, di, pi, clip, parameter = self._resolve(params[:4])
            except (LookupError, IndexError) as e:
                self.logger.warning(str(e))
                return (0, str(e))
            time = float(params[4])
            duration = float(params[5])
            value = float(params[6])
            envelope = self._get_or_create_envelope(clip, parameter)
            envelope.insert_step(time, duration, value)
            return (ti, ci, di, pi, 1)

        def automation_value_at_time(params: Tuple[Any]):
            try:
                ti, ci, di, pi, clip, parameter = self._resolve(params[:4])
            except (LookupError, IndexError) as e:
                self.logger.warning(str(e))
                return (0, str(e))
            time = float(params[4])
            envelope = clip.automation_envelope(parameter)
            value = envelope.value_at_time(time) if envelope is not None else parameter.value
            return (ti, ci, di, pi, time, value)

        def automation_sample(params: Tuple[Any]):
            try:
                ti, ci, di, pi, clip, parameter = self._resolve(params[:4])
            except (LookupError, IndexError) as e:
                self.logger.warning(str(e))
                return (0, str(e))
            start = float(params[4])
            end = float(params[5])
            steps = max(2, int(params[6]))
            envelope = clip.automation_envelope(parameter)
            dt = (end - start) / (steps - 1)
            values = []
            for i in range(steps):
                t = start + i * dt
                v = envelope.value_at_time(t) if envelope is not None else parameter.value
                values.extend((t, v))
            return (ti, ci, di, pi, steps, *values)

        def automation_clear(params: Tuple[Any]):
            try:
                ti, ci, di, pi, clip, parameter = self._resolve(params[:4])
            except (LookupError, IndexError) as e:
                self.logger.warning(str(e))
                return (0, str(e))
            if clip.automation_envelope(parameter) is not None:
                clip.clear_envelope(parameter)
            return (ti, ci, di, pi, 1)

        def automation_clear_all(params: Tuple[Any]):
            track_index = int(params[0])
            clip_index = int(params[1])
            try:
                clip = self.song.tracks[track_index].clip_slots[clip_index].clip
            except IndexError as e:
                self.logger.warning(str(e))
                return (0, str(e))
            if clip is None:
                return (0, "No clip at track %d slot %d" % (track_index, clip_index))
            clip.clear_all_envelopes()
            return (track_index, clip_index, 1)

        self.osc_server.add_handler("/live/clip/automation/insert_step", automation_insert_step)
        self.osc_server.add_handler("/live/clip/automation/value_at_time", automation_value_at_time)
        self.osc_server.add_handler("/live/clip/automation/sample", automation_sample)
        self.osc_server.add_handler("/live/clip/automation/clear", automation_clear)
        self.osc_server.add_handler("/live/clip/automation/clear_all", automation_clear_all)
