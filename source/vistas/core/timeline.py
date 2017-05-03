import datetime
from bisect import insort

import wx
import wx.lib.newevent

TimelineValueChangedEvent, EVT_TIMELINE_VALUE_CHANGED = wx.lib.newevent.NewEvent()
TimelineAttrChangedEvent, EVT_TIMELINE_ATTR_CHANGED = wx.lib.newevent.NewEvent()


class Timeline:
    _global_timeline = None

    @classmethod
    def app(cls):
        """ Global timeline """

        if cls._global_timeline is None:
            cls._global_timeline = Timeline()

        return cls._global_timeline

    def __init__(self, start_time=None, end_time=None, current_time=None):

        init_time = datetime.datetime.fromtimestamp(0)

        self._start_time = init_time if start_time is None else start_time
        self._end_time = init_time if end_time is None else end_time
        self._current_time = init_time if current_time is None else current_time
        self._min_step = None
        self._timestamps = []

        # filter settings
        self.use_filter = False
        self.filter_start_time = start_time
        self.filter_end_time = end_time
        self.filter_interval = self._min_step

    @property
    def enabled(self):
        return self.start_time != self.end_time

    @property
    def start_time(self):
        return self._start_time

    @start_time.setter
    def start_time(self, value: datetime.datetime):
        self._start_time = value
        wx.PostEvent(self, TimelineAttrChangedEvent(time=self._current_time))

    @property
    def end_time(self):
        return self._end_time

    @end_time.setter
    def end_time(self, value):
        self._end_time = value
        wx.PostEvent(self, TimelineAttrChangedEvent(time=self._current_time))

    @property
    def current_time(self):
        return self._current_time

    @current_time.setter
    def current_time(self, value: datetime.datetime):
        if self.enabled:
            if value not in self._timestamps:
                if value > self._timestamps[-1]:
                    value = self._timestamps[-1]
                elif value < self._timestamps[0]:
                    value = self._timestamps[0]
                else:
                    # Go to nearest floor step
                    value = list(filter(lambda x: x > value, self._timestamps))[0]
            self._current_time = value
            wx.PostEvent(self, TimelineValueChangedEvent(time=self._current_time))

    @property
    def min_step(self):
        return self._min_step

    @property
    def timestamps(self):
        if self.use_filter:
            filtered_steps = []
            step = self.filter_start_time
            while step <= self.filter_end_time:
                if step in self._timestamps:
                    filtered_steps.append(step)
                step = step + self.filter_interval
            return filtered_steps
        return self._timestamps

    @property
    def num_timestamps(self):
        return len(self.timestamps)

    @property
    def time_format(self):
        _format = "%B %d, %Y"

        hours, minutes, seconds = [False] * 3
        for t in self.timestamps:
            hours = not hours and t.hours > 0
            minutes = not minutes and t.minutes > 0
            seconds = not seconds and t.seconds > 0
            if hours and minutes and seconds:
                break

        if hours or minutes or seconds:
            _format = _format + " %H:%M"
            if seconds:
                _format = _format + ":%S"

        return _format

    def reset(self):
        zero = datetime.datetime.fromtimestamp(0)
        self._timestamps = []
        self._start_time, self._end_time, self._current_time = [zero] * 3
        self.filter_start_time, self.filter_end_time, self.filter_interval = [zero] * 3
        self._min_step, self.filter_interval = [zero] * 2
        self.use_filter = False

    def add_timestamp(self, timestamp: datetime.datetime):
        if timestamp not in self._timestamps:
            if timestamp > self._timestamps[-1]:
                self.end_time = timestamp
            elif timestamp < self._timestamps[0]:
                self.start_time = timestamp
            insort(self._timestamps, timestamp)     # unique and sorted

            # recalculate smallest timedelta
            self._min_step = self._timestamps[-1] - self._timestamps[0]
            for i in range(len(self._timestamps) - 1):
                diff = self._timestamps[i+1] - self._timestamps[i+1]
                self._min_step = diff if diff < self._min_step else self._min_step

    def index_at_time(self, time: datetime.datetime):
        return self.timestamps.index(time)

    @property
    def current_index(self):
        return self.index_at_time(self._current_time)

    def time_at_index(self, index):
        return self.timestamps[index]

    def forward(self, steps=1):
        index = self.current_index + steps
        if index > len(self.timestamps):
            self._current_time = self.end_time
        elif index < 0:
            self._current_time = self.start_time
        else:
            self._current_time = self.timestamps[index]
        wx.PostEvent(self, TimelineValueChangedEvent(time=self._current_time))

    def back(self, steps=1):
        self.forward(steps * -1)
